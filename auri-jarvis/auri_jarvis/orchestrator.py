"""auri_jarvis.orchestrator — wires Ears + Mouth + Mind into conversations (owner: AI-3).

One conversation runs at a time (`self._turn_task`). A new wake / HUD command / trigger
*barges in*: the Mouth is silenced, the running conversation is cancelled and awaited (so its
cleanup can't clobber the new one), then the new one starts.

Voice turn:  wake → state LISTENING → ack ("Igen?", signature) → ears.listen() → `transcript`
             → TurnRequest → mind.handle() deltas → mouth.say_stream() → follow-up window
Text turn:   HUD `command` → TurnRequest(channel="hud_text") → same Mind/Mouth path
Trigger:     clap2/clap3/login/… → TurnRequest(channel="trigger"); clap with an empty answer
             → ack + listen (spec 5.1)
Follow-up:   after a voice turn the mic stays open `core.follow_up_s` without a wake word;
             `mind.expects_reply` {timeout_s, accurate} → listen again (accurate = dictation).
Half duplex: while Auri speaks, `ears.set_suppressed(True)` (unless audio.full_duplex).
Internal requests (2.3): `say`, `voice.sample`, `prefs.proposed`.
HUD → daemon messages arrive through `handle_hud()` (called by the HUD server after its
token/Origin/Host checks).

`reply.delta` / `reply.done` are emitted by the Mind (2.3) — the orchestrator does not
duplicate them; it only stamps timings and drives the state machine.
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from typing import Any, Protocol

from .bus import Bus
from .config import get
from .contracts import (
    Ears,
    Event,
    Mind,
    Mouth,
    Trigger,
    TurnRequest,
    UserContext,
    WakeEvent,
)
from .identity.prefs import VOICES, PrefsError, apply_partial, guest_user, prefs_to_dict, validate_partial
from .state import State, StateMachine
from .timing import TimingLog, TurnTiming

log = logging.getLogger(__name__)

WAKE_TRIGGERS: frozenset[str] = frozenset({"clap2", "clap3"})
MAX_COMMAND_CHARS = 2000


class IdentityBackend(Protocol):
    """Implemented by auri_jarvis.identity.manager (M3)."""

    async def verify(self, access_token: str) -> UserContext: ...  # raises on failure
    async def save_prefs(self, user: UserContext) -> float: ...  # returns updated_at (epoch s)
    async def logout(self) -> None: ...


@dataclasses.dataclass
class _Expect:
    timeout_s: float
    accurate: bool


class Orchestrator:
    def __init__(
        self,
        cfg: Mapping[str, Any],
        bus: Bus,
        ears: Ears,
        mouth: Mouth,
        mind: Mind,
        *,
        timing_log: TimingLog | None = None,
        identity: IdentityBackend | None = None,
        ack: bool = True,
    ) -> None:
        self.cfg, self.bus, self.ears, self.mouth, self.mind = cfg, bus, ears, mouth, mind
        self.identity = identity
        self.timing_log = timing_log or TimingLog()
        self.sm = StateMachine(bus.emit)
        self.user: UserContext = guest_user(cfg)

        self.ack_enabled = ack
        self.ack_phrase: str = get(cfg, "core.ack_phrase", "Igen?")
        # per wake source: "phrase" (ack_phrase) · "earcon" (short sound, if the Mouth has one) · "none"
        self.ack_by_source: dict[str, str] = {str(k): str(v) for k, v in (get(cfg, "core.ack_by_source", {}) or {}).items()}
        # awaited before mind.warmup() (e.g. wait for Ollama after an autostart) — set by __main__
        self.pre_warmup: Callable[[], Awaitable[None]] | None = None
        self.warm: dict[str, str] = {"mind": "loading", "voice": "loading"}
        self.no_speech_phrase: str = get(cfg, "core.no_speech_phrase", "") or ""
        self.follow_up_s = float(get(cfg, "core.follow_up_s", 5.0))
        self.listen_timeout_s = float(get(cfg, "core.listen_start_timeout_s", 4.0))
        self.listen_max_s = float(get(cfg, "core.listen_max_s", 15.0))
        self.dictation_max_s = float(get(cfg, "core.dictation_max_s", 60.0))
        self.idle_tick_s = float(get(cfg, "core.idle_tick_s", 60.0))
        self.full_duplex = bool(get(cfg, "audio.full_duplex", False))

        self.loop: asyncio.AbstractEventLoop | None = None
        self._turn_task: asyncio.Task[None] | None = None
        self._say_tasks: set[asyncio.Task[Any]] = set()
        self._bg: set[asyncio.Task[Any]] = set()
        self._speak_lock = asyncio.Lock()
        self._unsubs: list[Callable[[], None]] = []
        self._turn_seq = 0
        self._expect_now: _Expect | None = None
        self._pending_expect: _Expect | None = None
        self._current_timing: TurnTiming | None = None
        self._last_activity = time.monotonic()
        # mic suppression inputs
        self._muted = False
        self._speaking = 0
        self._listening = False
        self._suppressed: bool | None = None
        self.started = False

    # ── lifecycle ────────────────────────────────────────────────────────────
    async def start(self, *, warmup: bool = True) -> None:
        self.loop = asyncio.get_running_loop()
        if self.bus.loop is None:
            self.bus.attach(self.loop)
        for typ, h in (
            ("route", self._on_route),
            ("tool", self._on_tool),
            ("vad", self._on_vad),
            ("mind.expects_reply", self._on_expects_reply),
            ("say", self._on_say),
            ("voice.sample", self._on_voice_sample),
            ("prefs.proposed", self._on_prefs_proposed),
        ):
            self._unsubs.append(self.bus.on(typ, h))
        self.ears.set_wake_word(self.user.prefs.wake_word)
        self.mouth.set_voice(self.user.prefs.voice)
        self._apply_suppression()
        self.sm.announce()
        self._emit_identity()
        try:
            await self.mind.on_identity_change(self.user)  # guest, or the cached last user
        except Exception as e:
            log.exception("mind.on_identity_change failed")
            self._error("mind.on_identity_change", e)
        self.ears.start(self._on_wake_threadsafe)
        if warmup:
            self._spawn(self._warmup())
        if self.idle_tick_s > 0:
            self._spawn(self._idle_loop())
        self.started = True

    async def stop(self) -> None:
        self.started = False
        for off in self._unsubs:
            off()
        self._unsubs.clear()
        with contextlib.suppress(Exception):
            self.ears.stop()
        await self._interrupt()
        for t in list(self._bg):
            t.cancel()
        await asyncio.gather(*self._bg, return_exceptions=True)
        self._bg.clear()
        self.sm.set(State.IDLE)

    def _spawn(self, coro: Awaitable[Any], bucket: set[asyncio.Task[Any]] | None = None) -> asyncio.Task[Any]:
        bucket = self._bg if bucket is None else bucket
        task = asyncio.ensure_future(coro)
        bucket.add(task)

        def done(t: asyncio.Task[Any]) -> None:
            bucket.discard(t)
            if not t.cancelled() and t.exception() is not None:
                log.error("background task failed", exc_info=t.exception())

        task.add_done_callback(done)
        return task

    async def _warmup(self) -> None:
        """Background: never blocks wakes. Emits `warmup` {mind, voice, ms} for the HUD
        ("Agy töltődik…"); a turn during warm-up simply runs slower (the Mind waits its lock)."""
        t0 = time.monotonic()
        self._emit_warmup(t0)
        await asyncio.gather(self._warm_mind(t0), self._warm_voice(t0))

    async def _warm_mind(self, t0: float) -> None:
        try:
            if self.pre_warmup is not None:
                await self.pre_warmup()
            await self.mind.warmup()
            self.warm["mind"] = "ready"
        except Exception as e:
            log.exception("mind.warmup failed")
            self.warm["mind"] = "error"
            self._error("mind.warmup", e)
        self._emit_warmup(t0)

    async def _warm_voice(self, t0: float) -> None:
        wait_ready = getattr(self.mouth, "wait_ready", None)  # AI-1 extra (not in the contract)
        if wait_ready is None:
            self.warm["voice"] = "ready"
        else:
            try:
                ok = await asyncio.to_thread(wait_ready, 120.0)
                self.warm["voice"] = "ready" if ok is not False else "error"
            except Exception:
                log.exception("mouth.wait_ready failed")
                self.warm["voice"] = "error"
        self._emit_warmup(t0)

    def _emit_warmup(self, t0: float) -> None:
        self.bus.emit(Event("warmup", {**self.warm, "ms": round((time.monotonic() - t0) * 1000)}))

    async def _idle_loop(self) -> None:
        while True:
            await asyncio.sleep(self.idle_tick_s)
            if self.busy or not self.sm.idle:
                continue
            try:
                await self.mind.idle_tick(time.monotonic() - self._last_activity, self.user)
            except Exception as e:
                log.exception("mind.idle_tick failed")
                self._error("mind.idle_tick", e)

    @property
    def busy(self) -> bool:
        return self._turn_task is not None and not self._turn_task.done()

    async def wait_idle(self, timeout_s: float = 30.0) -> bool:
        """Wait until no conversation or `say` has run for a few ticks. False on timeout."""
        deadline = time.monotonic() + timeout_s
        quiet = 0
        while quiet < 3:
            if time.monotonic() > deadline:
                return False
            await asyncio.sleep(0.02)
            quiet = 0 if (self.busy or self._say_tasks) else quiet + 1
        return True

    # ── entry points ─────────────────────────────────────────────────────────
    def _on_wake_threadsafe(self, wake: WakeEvent) -> None:
        loop = self.loop
        if loop is None or loop.is_closed():
            return
        loop.call_soon_threadsafe(self.on_wake, wake)

    def on_wake(self, wake: WakeEvent) -> None:
        """Loop thread only. Hotkey/HUD always work; other sources are ignored while muted."""
        if self._muted and wake.source not in ("hotkey", "hud"):
            log.debug("wake ignored (muted): %s", wake.source)
            return
        if wake.source in WAKE_TRIGGERS:
            self._start(self._conversation_trigger(wake.source, wake))  # type: ignore[arg-type]
        else:
            self._start(self._conversation_voice(wake))

    def submit_text(self, text: str) -> None:
        text = text.strip()[:MAX_COMMAND_CHARS]
        if text:
            self._start(self._conversation_text(text))

    def submit_trigger(self, trigger: Trigger) -> None:
        self._start(self._conversation_trigger(trigger, None))

    def submit_routine(self, name: str) -> None:
        """HUD/REST "run routine": trigger `hud_button` with the routine id in `text`."""
        self._start(self._conversation_trigger("hud_button", None, text=name.strip()[:64]))

    async def stop_speaking(self) -> None:
        """HUD `stop`: silence now + abort the conversation."""
        await self._interrupt()
        self.sm.set(State.IDLE)

    def _start(self, coro: Awaitable[None], *, barge: bool = True) -> None:
        """Start a conversation. barge=True (wake/command/stop): silence + drop queued `say`s."""
        prev = self._turn_task
        if barge:
            self._silence()
            self._cancel_says()
        self._turn_task = asyncio.ensure_future(self._run(prev, coro))

    async def _run(self, prev: asyncio.Task[None] | None, coro: Awaitable[None]) -> None:
        me = asyncio.current_task()
        if prev is not None and not prev.done():
            prev.cancel()
            await asyncio.gather(prev, return_exceptions=True)
        self._last_activity = time.monotonic()
        try:
            await coro
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("conversation failed")
            self._error("orchestrator", e)
        finally:
            self._listening = False
            self._apply_suppression()
            self._last_activity = time.monotonic()
            if self._turn_task is me:
                self.sm.set(State.IDLE)

    async def _interrupt(self) -> None:
        self._silence()
        self._cancel_says()
        task = self._turn_task
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    def _silence(self) -> None:
        with contextlib.suppress(Exception):
            self.mouth.stop()

    def _cancel_says(self) -> None:
        for t in list(self._say_tasks):
            t.cancel()

    # ── conversations ────────────────────────────────────────────────────────
    async def _conversation_voice(self, wake: WakeEvent | None) -> None:
        while wake is not None:
            wake = await self._voice_turn(wake)

    async def _conversation_text(self, text: str) -> None:
        timing = self._new_timing("hud_text")
        req = TurnRequest(turn_id=timing.turn, user=self.user, channel="hud_text", text=text)
        await self._mind_turn(req, timing)
        self._record(timing)
        await self._conversation_voice(self._next_listen(after_voice=False))

    async def _conversation_trigger(self, trigger: Trigger, wake: WakeEvent | None, *, text: str = "") -> None:
        timing = self._new_timing("trigger", t0=wake.t if wake else None)
        req = TurnRequest(turn_id=timing.turn, user=self.user, channel="trigger", trigger=trigger, wake=wake, text=text)
        spoke = await self._mind_turn(req, timing)
        self._record(timing)
        if not spoke and trigger in WAKE_TRIGGERS and self._expect_now is None:
            # clap with nothing to do (no routine / guest) → behave like a wake
            await self._conversation_voice(wake or WakeEvent(source=trigger))  # type: ignore[arg-type]
            return
        await self._conversation_voice(self._next_listen(after_voice=False))

    def _next_listen(self, *, after_voice: bool) -> WakeEvent | None:
        """Decide whether to keep listening without a wake word after a turn."""
        if self._muted:
            return None
        if self._expect_now is not None:
            self._pending_expect, self._expect_now = self._expect_now, None
            return WakeEvent(source="followup")
        if after_voice and self.follow_up_s > 0:
            return WakeEvent(source="followup")
        return None

    async def _voice_turn(self, wake: WakeEvent) -> WakeEvent | None:
        followup = wake.source == "followup"
        expect, self._pending_expect = self._pending_expect, None
        self._expect_now = None
        timing = self._new_timing("voice", t0=wake.t)
        self.sm.set(State.LISTENING, follow_up=followup)
        if wake.source == "hud":
            self.bus.emit(Event("wake", {"source": "hud", "word": None, "confidence": 1.0}))
        if not followup and self.ack_enabled:
            await self._ack(timing, wake.source)

        accurate = bool(expect and expect.accurate)
        if expect is not None:
            start_timeout = expect.timeout_s
        else:
            start_timeout = self.follow_up_s if followup else self.listen_timeout_s
        if followup:
            async with self._speak_lock:  # let a queued `say` finish before opening the mic
                pass
        self._listening = True
        self._apply_suppression()
        try:
            tr = await self.ears.listen(
                max_s=self.dictation_max_s if accurate else self.listen_max_s,
                accurate=accurate,
                start_timeout_s=start_timeout,
            )
        finally:
            self._listening = False
            self._apply_suppression()

        if tr is None or not tr.text.strip():
            if not followup and self.no_speech_phrase:
                await self._say_locked(self.no_speech_phrase, signature=True)
            return None
        timing.speech_ms, timing.stt_ms = tr.speech_ms, tr.stt_ms
        self.bus.emit(
            Event(
                "transcript",
                {
                    "raw": tr.raw,
                    "text": tr.text,
                    "lang": tr.lang,
                    "engine": tr.engine,
                    "stt_ms": tr.stt_ms,
                    "speech_ms": tr.speech_ms,
                    "confidence": tr.confidence,
                },
            )
        )
        req = TurnRequest(turn_id=timing.turn, user=self.user, channel="voice", text=tr.text, transcript=tr, wake=wake)
        await self._mind_turn(req, timing)
        self._record(timing)
        return self._next_listen(after_voice=True)

    async def _ack(self, timing: TurnTiming, source: str) -> None:
        mode = self.ack_by_source.get(source, "phrase")
        earcon = getattr(self.mouth, "earcon", None) if mode == "earcon" else None  # optional AI-1 extra
        if mode == "none" or (earcon is None and not self.ack_phrase):
            return
        watcher = asyncio.ensure_future(self._watch_audio(timing, "ack"))
        try:
            if earcon is not None:
                await self._speak_locked(lambda: earcon("wake"))
            else:  # "phrase", or "earcon" without Mouth support → the spoken ack
                await self._say_locked(self.ack_phrase, signature=True)
        finally:
            watcher.cancel()
            timing.mark("ack")  # fallback if the Mouth never reported `speaking`

    async def _mind_turn(self, req: TurnRequest, timing: TurnTiming) -> bool:
        """Run the Mind, speak its deltas. Returns True if anything was spoken."""
        self._expect_now = None
        self._current_timing = timing
        self.sm.set(State.THINKING)
        timing.mark("mind_start")
        gen = self.mind.handle(req, self.bus.emit)
        it = gen.__aiter__()
        watcher: asyncio.Task[None] | None = None
        try:
            first = await _next_nonempty(it)
            if first is None:
                return False
            timing.mark("llm_first")
            self.sm.set(State.SPEAKING)
            watcher = asyncio.ensure_future(self._watch_audio(timing, "tts_first"))

            async def chain() -> AsyncIterator[str]:
                yield first
                async for d in it:
                    if d:
                        yield d

            async with self._speak_lock:
                self._speaking += 1
                self._apply_suppression()
                try:
                    await self.mouth.say_stream(chain())
                finally:
                    self._speaking -= 1
                    self._apply_suppression()
            timing.mark("tts_first")  # fallback (Mouth never reported speaking)
            return True
        finally:
            if watcher is not None:
                watcher.cancel()
            aclose = getattr(gen, "aclose", None)
            if aclose is not None:
                with contextlib.suppress(Exception):
                    await aclose()
            timing.mark("end")
            self._current_timing = None

    async def _watch_audio(self, timing: TurnTiming, mark: str, timeout_s: float = 60.0) -> None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if self.mouth.speaking:
                timing.mark(mark)
                return
            await asyncio.sleep(0.01)

    def _new_timing(self, channel: str, t0: float | None = None) -> TurnTiming:
        self._turn_seq += 1
        return TurnTiming(self._turn_seq, channel, t0=time.monotonic() if t0 is None else t0)

    def _record(self, timing: TurnTiming) -> None:
        timing.mark("end")
        rec = timing.result()
        self.timing_log.add(rec)
        self.bus.emit(Event("timing", rec))
        log.info(
            "turn %d %s: total=%sms llm_first=%sms tts_first=%sms stt=%sms",
            rec["turn"],
            rec["channel"],
            rec["total_ms"],
            rec["llm_first_ms"],
            rec["tts_first_ms"],
            rec["stt_ms"],
        )

    # ── speaking outside a turn (say / voice.sample) ─────────────────────────
    async def _say_locked(self, text: str, *, signature: bool = False) -> None:
        await self._speak_locked(lambda: self.mouth.say(text, signature=signature))

    async def _speak_locked(self, fn: Callable[[], Awaitable[Any]]) -> None:
        async with self._speak_lock:
            self._speaking += 1
            self._apply_suppression()
            try:
                await fn()
            finally:
                self._speaking -= 1
                self._apply_suppression()

    async def _speak_request(self, fn: Callable[[], Awaitable[None]]) -> None:
        idle_before = not self.busy
        async with self._speak_lock:
            if idle_before and not self.busy:
                self.sm.set(State.SPEAKING)
            self._speaking += 1
            self._apply_suppression()
            try:
                await fn()
            finally:
                self._speaking -= 1
                self._apply_suppression()
                if idle_before and not self.busy and self.sm.state == State.SPEAKING:
                    self.sm.set(State.IDLE)

    def _on_say(self, ev: Event) -> None:
        text = str(ev.data.get("text") or "").strip()
        if not text:
            return
        signature = bool(ev.data.get("signature", False))
        self._spawn(self._speak_request(lambda: self.mouth.say(text, signature=signature)), self._say_tasks)

    def _on_voice_sample(self, ev: Event) -> None:
        self.play_sample(ev.data.get("voice"))

    def play_sample(self, voice: Any) -> None:
        if voice not in VOICES:
            self._error("voice.sample", ValueError(f"unknown voice: {voice!r}"))
            return
        self._spawn(self._speak_request(lambda: self.mouth.play_sample(voice)), self._say_tasks)

    # ── bus handlers (Mind side information) ─────────────────────────────────
    def _on_route(self, ev: Event) -> None:
        t = self._current_timing
        if t is not None and t.path is None:
            t.path = str(ev.data.get("path") or "") or None
        if ev.data.get("path") == "fastpath" and self.sm.state == State.THINKING:
            self.sm.set(State.ACTING)

    def _on_tool(self, ev: Event) -> None:
        if self.sm.state == State.THINKING:
            self.sm.set(State.ACTING)

    def _on_vad(self, ev: Event) -> None:
        # optional AI-1 event {"speech": "start"|"end"} (proposed in JARVIS_BUILD §6)
        if ev.data.get("speech") == "end" and self.sm.state == State.LISTENING:
            self.sm.set(State.TRANSCRIBING)

    def _on_expects_reply(self, ev: Event) -> None:
        try:
            timeout_s = float(ev.data.get("timeout_s", self.follow_up_s))
        except (TypeError, ValueError):
            timeout_s = self.follow_up_s
        exp = _Expect(timeout_s=max(1.0, min(timeout_s, 120.0)), accurate=bool(ev.data.get("accurate", False)))
        if self.busy:
            self._expect_now = exp
        else:  # e.g. after a `say` from a timer: open the mic once that speech is done
            self._pending_expect = exp
            self._start(self._conversation_voice(WakeEvent(source="followup")), barge=False)

    def _on_prefs_proposed(self, ev: Event) -> Awaitable[None]:
        return self.apply_prefs(ev.data, source="mind")

    # ── identity + prefs ─────────────────────────────────────────────────────
    async def set_user(self, user: UserContext, *, reason: str = "identity") -> None:
        old = self.user
        self.user = user
        if old.prefs.wake_word != user.prefs.wake_word or reason == "start":
            self.ears.set_wake_word(user.prefs.wake_word)
        if old.prefs.voice != user.prefs.voice or reason == "start":
            self.mouth.set_voice(user.prefs.voice)
        self._emit_identity()
        try:
            await self.mind.on_identity_change(user)
        except Exception as e:
            log.exception("mind.on_identity_change failed")
            self._error("mind.on_identity_change", e)
        new_login = user.tier == "user" and (old.tier != "user" or old.user_id != user.user_id)
        if new_login and not user.prefs.onboarded and reason == "login":
            self.submit_trigger("login")

    async def apply_prefs(self, partial: Any, *, source: str) -> bool:
        if self.user.tier != "user":
            self._error("prefs", PrefsError("Vendég módban nem menthető beállítás."))
            return False
        try:
            clean = validate_partial(partial)
        except PrefsError as e:
            self._error("prefs", e)
            return False
        new_prefs = apply_partial(self.user.prefs, clean)
        user = dataclasses.replace(self.user, prefs=new_prefs)
        updated_at = time.time()
        if self.identity is not None:
            try:
                updated_at = await self.identity.save_prefs(user)
            except Exception as e:
                log.exception("identity.save_prefs failed")
                self._error("prefs.save", e)
        restart_onboarding = self.user.prefs.onboarded and not new_prefs.onboarded and source == "hud"
        await self.set_user(user, reason="prefs")
        self.bus.emit(Event("prefs.changed", {"prefs": prefs_to_dict(new_prefs), "updated_at": updated_at, "source": source}))
        if restart_onboarding:  # HUD "Beállítás újra" → Auri asks the 4 questions again (AI-2)
            self.submit_trigger("login")
        return True

    def _emit_identity(self) -> None:
        u = self.user
        self.bus.emit(
            Event(
                "identity",
                {
                    "tier": u.tier,
                    "name": u.display_name,
                    "user_id": u.user_id,
                    "prefs": prefs_to_dict(u.prefs),
                },
            )
        )

    # ── HUD → daemon ─────────────────────────────────────────────────────────
    async def handle_hud(self, ev: Event) -> None:
        """Called by the HUD server for an authenticated message (token/Origin/Host checked)."""
        d = ev.data
        typ = ev.type
        if typ == "ptt":
            if d.get("down", True):
                self.on_wake(WakeEvent(source="hud"))
        elif typ == "command":
            text = d.get("text")
            if isinstance(text, str):
                self.submit_text(text)
        elif typ == "stop":
            await self.stop_speaking()
        elif typ == "mute":
            self.set_muted(bool(d.get("on", True)))
        elif typ == "auth":
            await self._hud_auth(d.get("access_token"))
        elif typ == "logout":
            await self.logout()
        elif typ == "prefs.set":
            await self.apply_prefs(d, source="hud")
        elif typ == "voice.sample":
            self.play_sample(d.get("voice"))
        elif typ == "proposal.answer":
            try:
                await self.mind.on_hud_event(ev, self.user)
            except Exception as e:
                log.exception("mind.on_hud_event failed")
                self._error("mind.on_hud_event", e)
        elif typ == "hello":
            pass  # connection greeting; the server replays the snapshot
        else:
            log.debug("hud: unknown message type %s", typ)

    def set_muted(self, on: bool) -> None:
        self._muted = on
        self._apply_suppression()
        self.bus.emit(Event("mute", {"on": on}))
        if on and self.busy and self.sm.state == State.LISTENING:
            self._start(_noop())  # cancel an open listen

    async def _hud_auth(self, token: Any) -> None:
        if self.identity is None:
            self._error("auth", RuntimeError("A bejelentkezés-ellenőrzés még nincs bekötve."))
            return
        if not isinstance(token, str) or not token or len(token) > 8192:
            self._error("auth", ValueError("Hiányzó vagy hibás token."))
            return
        try:
            user = await self.identity.verify(token)
        except Exception as e:
            log.warning("auth failed: %s", type(e).__name__)
            self._error("auth", e)
            if self.user.tier == "user":  # a failed re-login never keeps the previous user
                await self.set_user(guest_user(self.cfg), reason="logout")
            return
        await self.set_user(user, reason="login")
        consume = getattr(self.identity, "consume_push", None)
        if consume is not None and consume(user.user_id):
            updated = getattr(self.identity, "prefs_updated_at", lambda _u: None)(user.user_id) or time.time()
            self.bus.emit(Event("prefs.changed", {"prefs": prefs_to_dict(user.prefs), "updated_at": updated, "source": "local"}))

    async def logout(self) -> None:
        if self.identity is not None:
            with contextlib.suppress(Exception):
                await self.identity.logout()
        if self.user.tier != "guest":
            await self.set_user(guest_user(self.cfg), reason="logout")

    # ── helpers ──────────────────────────────────────────────────────────────
    def _apply_suppression(self) -> None:
        on = (self._speaking > 0 and not self.full_duplex) or (self._muted and not self._listening)
        if on != self._suppressed:
            self._suppressed = on
            try:
                self.ears.set_suppressed(on)
            except Exception:
                log.exception("ears.set_suppressed failed")

    def _error(self, where: str, e: BaseException) -> None:
        msg = str(e) if isinstance(e, (PrefsError, ValueError, RuntimeError)) else type(e).__name__
        self.bus.emit(Event("error", {"where": where, "message": msg[:300]}))


async def _next_nonempty(it: AsyncIterator[str]) -> str | None:
    async for d in it:
        if d:
            return d
    return None


async def _noop() -> None:
    return None
