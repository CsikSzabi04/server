"""M1: orchestrator with fakes — voice/text/trigger turns, barge-in, half duplex, follow-up,
expects_reply, mute, prefs, identity, say/voice.sample."""

from __future__ import annotations

import asyncio
import dataclasses
from collections.abc import AsyncIterator
from typing import Any

import pytest

from auri_jarvis.bus import Bus
from auri_jarvis.contracts import Emit, Event, TurnRequest, UserContext, WakeEvent
from auri_jarvis.fakes import EchoMind, FakeEars, FakeMouth
from auri_jarvis.orchestrator import Orchestrator
from auri_jarvis.state import State

CFG: dict[str, Any] = {
    "guest_defaults": {"address": "you", "wake_word": "hey_auri", "voice": "daniel", "welcome_routine": None},
    "core": {"follow_up_s": 0.3, "listen_start_timeout_s": 0.5, "idle_tick_s": 0, "ack_phrase": "Igen?"},
    "audio": {"full_duplex": False},
}


class RecEars(FakeEars):
    def __init__(self) -> None:
        super().__init__(read_stream=False)
        self.suppress_log: list[bool] = []
        self.wake_words: list[str] = []

    def set_suppressed(self, on: bool) -> None:
        super().set_suppressed(on)
        self.suppress_log.append(on)

    def set_wake_word(self, word):  # type: ignore[override]
        super().set_wake_word(word)
        self.wake_words.append(word)


class RecMouth(FakeMouth):
    def __init__(self, delay_s: float = 0.0, out=None) -> None:
        import io

        super().__init__(out=out or io.StringIO(), delay_s=delay_s)
        self.stops = 0
        self.suppressed_while_speaking: list[bool] = []
        self.ears: RecEars | None = None

    def stop(self) -> None:
        self.stops += 1
        super().stop()

    async def _speak(self, text: str) -> None:
        if self.ears is not None:
            self.suppressed_while_speaking.append(self.ears.suppressed)
        await super()._speak(text)


class ScriptMind(EchoMind):
    """Yields `reply` deltas; optional side effects via `before` (called with emit)."""

    def __init__(self, reply: list[str] | None = None, delay_s: float = 0.0, before=None) -> None:
        super().__init__()
        self.reply = reply if reply is not None else ["Kész", "."]
        self.delay = delay_s
        self.before = before
        self.cancelled = 0

    async def handle(self, req: TurnRequest, emit: Emit) -> AsyncIterator[str]:
        self.requests.append(req)
        try:
            if self.before:
                self.before(req, emit)
            if self.delay:
                await asyncio.sleep(self.delay)
            for d in self.reply:
                yield d
        except asyncio.CancelledError:
            self.cancelled += 1
            raise


async def make(mind=None, *, mouth_delay=0.0, cfg=None, identity=None):
    bus = Bus()
    bus.attach()
    events: list[Event] = []
    bus.on("*", events.append)
    ears = RecEars()
    mouth = RecMouth(delay_s=mouth_delay)
    mouth.ears = ears
    mind = mind or EchoMind()
    orch = Orchestrator(cfg or CFG, bus, ears, mouth, mind, identity=identity)
    await orch.start(warmup=False)
    return orch, bus, ears, mouth, mind, events


async def settle(orch: Orchestrator, bus: Bus, timeout: float = 5.0) -> None:
    """Wait until no conversation / say is running for 3 consecutive ticks (a wake fed from a
    thread is scheduled with call_soon_threadsafe, so 'not busy' right away means nothing)."""

    async def wait():
        quiet = 0
        while quiet < 3:
            await asyncio.sleep(0.01)
            await bus.drain()
            quiet = 0 if (orch.busy or orch._say_tasks) else quiet + 1

    await asyncio.wait_for(wait(), timeout)


def types(events: list[Event], t: str) -> list[Event]:
    return [e for e in events if e.type == t]


async def test_text_turn_echo():
    orch, bus, ears, mouth, mind, ev = await make()
    orch.submit_text("hány óra van")
    await settle(orch, bus)
    assert mind.requests[0].channel == "hud_text" and mind.requests[0].text == "hány óra van"
    assert mouth.said and mouth.said[-1].startswith("Ezt mondtad: hány óra van.")
    assert types(ev, "timing")[0].data["channel"] == "hud_text"
    assert orch.sm.state == State.IDLE
    assert [e.data["state"] for e in types(ev, "state")][-1] == "idle"
    await orch.stop()


async def test_voice_turn_ack_listen_reply_followup():
    orch, bus, ears, mouth, mind, ev = await make(ScriptMind(["Mind", "járt", " rendben."]))
    ears.feed("nyisd meg a vs code-ot")  # wake + queued speech
    await settle(orch, bus)
    assert mouth.said[0] == "Igen?"  # ack first
    assert mouth.said[1] == "Mindjárt rendben."
    req = mind.requests[0]
    assert req.channel == "voice" and req.text == "nyisd meg a vs code-ot" and req.wake.source == "hotkey"
    tr = types(ev, "transcript")[0].data
    assert tr["text"] == "nyisd meg a vs code-ot" and tr["engine"] == "text"
    # follow-up window: a second listen without wake, with the short timeout
    assert len(ears.listen_calls) == 2 and ears.listen_calls[1]["start_timeout_s"] == pytest.approx(0.3)
    t = types(ev, "timing")[0].data
    assert t["total_ms"] is not None and t["llm_first_ms"] is not None and t["wake_ack_ms"] is not None
    states = [e.data["state"] for e in types(ev, "state")]
    assert states[:4] == ["idle", "listening", "thinking", "speaking"] and states[-1] == "idle"
    await orch.stop()


async def test_followup_speech_continues_conversation():
    orch, bus, ears, mouth, mind, ev = await make(ScriptMind(["Oké."]))
    ears.feed("első")

    async def feed_later():
        while len(ears.listen_calls) < 2:
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.05)
        ears.feed("és holnap?")  # delivered to the follow-up listen, no new wake

    await asyncio.gather(feed_later(), settle(orch, bus))
    assert [r.text for r in mind.requests] == ["első", "és holnap?"]
    assert mind.requests[1].wake.source == "followup"
    assert mouth.said.count("Igen?") == 1  # no ack on follow-up
    await orch.stop()


async def test_half_duplex_suppresses_mic_while_speaking():
    orch, bus, ears, mouth, mind, ev = await make(ScriptMind(["Szia."]))
    ears.feed("szia")
    await settle(orch, bus)
    assert mouth.suppressed_while_speaking and all(mouth.suppressed_while_speaking)
    assert ears.suppressed is False  # restored afterwards
    await orch.stop()


async def test_full_duplex_never_suppresses():
    cfg = {**CFG, "audio": {"full_duplex": True}}
    orch, bus, ears, mouth, mind, ev = await make(ScriptMind(["Szia."]), cfg=cfg)
    ears.feed("szia")
    await settle(orch, bus)
    assert not any(mouth.suppressed_while_speaking)
    await orch.stop()


async def test_barge_in_cancels_running_turn():
    mind = ScriptMind(["lassú válasz"], delay_s=1.0)
    orch, bus, ears, mouth, mind, ev = await make(mind)
    orch.submit_text("első")
    await asyncio.sleep(0.1)
    assert orch.busy
    orch.submit_text("második")
    await settle(orch, bus)
    assert mind.cancelled == 1
    assert [r.text for r in mind.requests] == ["első", "második"]
    assert mouth.stops >= 1
    assert mouth.said == ["lassú válasz"]  # spoken once, for the second request only
    await orch.stop()


async def test_hud_stop_interrupts():
    orch, bus, ears, mouth, mind, ev = await make(ScriptMind(["x"], delay_s=2.0))
    orch.submit_text("valami")
    await asyncio.sleep(0.05)
    await orch.handle_hud(Event("stop"))
    assert not orch.busy and orch.sm.state == State.IDLE and mind.cancelled == 1
    await orch.stop()


async def test_clap_trigger_without_answer_acks_and_listens():
    orch, bus, ears, mouth, mind, ev = await make(EchoMind())
    orch.on_wake(WakeEvent(source="clap2"))
    await settle(orch, bus)
    assert mind.requests[0].channel == "trigger" and mind.requests[0].trigger == "clap2"
    assert mouth.said == ["Igen?"]  # nothing to do → ack + listen
    assert len(ears.listen_calls) == 1
    await orch.stop()


async def test_clap_trigger_with_routine_speaks_and_does_not_listen():
    orch, bus, ears, mouth, mind, ev = await make(ScriptMind(["Üdv itthon."]))
    orch.on_wake(WakeEvent(source="clap2"))
    await settle(orch, bus)
    assert mouth.said == ["Üdv itthon."] and ears.listen_calls == []
    await orch.stop()


async def test_expects_reply_opens_accurate_listen():
    def before(req, emit):
        if req.channel == "hud_text":
            emit(Event("mind.expects_reply", {"timeout_s": 3, "accurate": True}))

    orch, bus, ears, mouth, mind, ev = await make(ScriptMind(["Mit jegyezzek fel?"], before=before))
    orch.submit_text("jegyezd fel")
    await settle(orch, bus)
    assert ears.listen_calls == [{"max_s": 60.0, "accurate": True, "start_timeout_s": 3.0}]
    await orch.stop()


async def test_mute_blocks_wakeword_but_not_hotkey():
    orch, bus, ears, mouth, mind, ev = await make(ScriptMind(["ok"]))
    await orch.handle_hud(Event("mute", {"on": True}))
    assert ears.suppressed is True
    orch.on_wake(WakeEvent(source="wakeword", word="hey_auri"))
    await settle(orch, bus)
    assert mind.requests == [] and ears.listen_calls == []
    ears._lines.put("hotkey parancs")
    orch.on_wake(WakeEvent(source="hotkey"))
    await settle(orch, bus)
    assert [r.text for r in mind.requests] == ["hotkey parancs"]
    assert len(ears.listen_calls) == 1  # muted → no follow-up window
    assert ears.suppressed is True
    assert types(ev, "mute")[0].data == {"on": True}
    await orch.stop()


async def test_say_request_while_idle():
    orch, bus, ears, mouth, mind, ev = await make()
    bus.emit(Event("say", {"text": "Lejárt az időzítő.", "signature": False}))
    await bus.drain()
    await settle(orch, bus)
    assert mouth.said == ["Lejárt az időzítő."]
    states = [e.data["state"] for e in types(ev, "state")]
    assert states[-2:] == ["speaking", "idle"]
    await orch.stop()


async def test_say_then_expects_reply_keeps_the_say():
    orch, bus, ears, mouth, mind, ev = await make(ScriptMind(["rendben"]))
    bus.emit(Event("say", {"text": "Kérsz még öt percet?"}))
    bus.emit(Event("mind.expects_reply", {"timeout_s": 2}))
    await bus.drain()
    await settle(orch, bus)
    assert mouth.said[0] == "Kérsz még öt percet?"
    assert ears.listen_calls and ears.listen_calls[0]["start_timeout_s"] == 2.0
    await orch.stop()


async def test_voice_sample_request():
    orch, bus, ears, mouth, mind, ev = await make()
    bus.emit(Event("voice.sample", {"voice": "george"}))
    bus.emit(Event("voice.sample", {"voice": "evil"}))
    await bus.drain()
    await settle(orch, bus)
    assert mouth.samples == ["george"]
    assert any(e.data["where"] == "voice.sample" for e in types(ev, "error"))
    await orch.stop()


class FakeIdentity:
    def __init__(self) -> None:
        self.saved: list[UserContext] = []

    async def verify(self, access_token: str) -> UserContext:
        if access_token != "good":
            raise PermissionError("bad token")
        return UserContext(tier="user", user_id="u1", display_name="Teszt")

    async def save_prefs(self, user: UserContext) -> float:
        self.saved.append(user)
        return 1234.5

    async def logout(self) -> None:
        pass


async def test_guest_cannot_change_prefs():
    orch, bus, ears, mouth, mind, ev = await make(identity=FakeIdentity())
    bus.emit(Event("prefs.proposed", {"voice": "george"}))
    await bus.drain()
    assert orch.user.tier == "guest" and orch.user.prefs.voice == "daniel"
    assert types(ev, "error")[-1].data["where"] == "prefs"
    await orch.stop()


async def test_login_triggers_onboarding_then_prefs_apply_and_logout():
    ident = FakeIdentity()
    orch, bus, ears, mouth, mind, ev = await make(ScriptMind([]), identity=ident)
    await orch.handle_hud(Event("auth", {"access_token": "bad"}))
    await bus.drain()
    assert orch.user.tier == "guest" and types(ev, "error")[-1].data["where"] == "auth"
    await orch.handle_hud(Event("auth", {"access_token": "good"}))
    await settle(orch, bus)
    assert orch.user.tier == "user" and orch.user.display_name == "Teszt"
    assert mind.requests[-1].channel == "trigger" and mind.requests[-1].trigger == "login"
    assert mind.identity_changes[-1].user_id == "u1"
    assert types(ev, "identity")[-1].data["tier"] == "user"

    bus.emit(Event("prefs.proposed", {"wake_word": "hey_jarvis", "voice": "george", "answered": ["wake_word", "voice"]}))
    await bus.drain()
    assert orch.user.prefs.wake_word == "hey_jarvis" and ears.wake_words[-1] == "hey_jarvis"
    assert mouth.voice == "george"
    pc = types(ev, "prefs.changed")[-1].data
    assert pc["updated_at"] == 1234.5 and pc["prefs"]["voice"] == "george" and pc["source"] == "mind"
    assert ident.saved[-1].prefs.voice == "george"

    await orch.handle_hud(Event("prefs.set", {"voice": "nope"}))  # invalid from HUD
    assert orch.user.prefs.voice == "george"

    await orch.handle_hud(Event("logout"))
    assert orch.user.tier == "guest" and orch.user.prefs.wake_word == "hey_auri"
    assert ears.wake_words[-1] == "hey_auri" and mouth.voice == "daniel"
    await orch.stop()


async def test_onboarded_login_does_not_trigger():
    ident = FakeIdentity()
    orch, bus, ears, mouth, mind, ev = await make(ScriptMind([]), identity=ident)
    user = UserContext(tier="user", user_id="u2")
    user = dataclasses.replace(user, prefs=dataclasses.replace(user.prefs, onboarded=True))
    await orch.set_user(user, reason="login")
    await settle(orch, bus)
    assert mind.requests == []
    await orch.stop()


async def test_mind_exception_reports_error_and_returns_idle():
    class Boom(EchoMind):
        async def handle(self, req, emit):
            raise RuntimeError("model crashed")
            yield  # pragma: no cover

    orch, bus, ears, mouth, mind, ev = await make(Boom())
    orch.submit_text("x")
    await settle(orch, bus)
    err = types(ev, "error")[-1].data
    assert err["where"] == "orchestrator" and "model crashed" in err["message"]
    assert orch.sm.state == State.IDLE
    await orch.stop()


async def test_route_fastpath_sets_acting():
    def before(req, emit):
        emit(Event("route", {"path": "fastpath", "intent": "set_volume"}))

    orch, bus, ears, mouth, mind, ev = await make(ScriptMind(["Kész."], delay_s=0.05, before=before))
    orch.submit_text("hangerő 30")
    await settle(orch, bus)
    assert "acting" in [e.data["state"] for e in types(ev, "state")]
    assert types(ev, "timing")[-1].data["path"] == "fastpath"
    await orch.stop()


async def test_wake_from_foreign_thread():
    import threading

    orch, bus, ears, mouth, mind, ev = await make(ScriptMind(["ok"]))
    ears._lines.put("szálról")
    th = threading.Thread(target=orch._on_wake_threadsafe, args=(WakeEvent(source="wakeword", word="hey_auri"),))
    th.start()
    th.join()
    await asyncio.sleep(0.05)
    await settle(orch, bus)
    assert mind.requests and mind.requests[0].text == "szálról"
    await orch.stop()


class PushIdentity(FakeIdentity):
    def consume_push(self, user_id):
        return user_id == "u1"

    def prefs_updated_at(self, user_id):
        return 777.0


async def test_local_newer_prefs_are_pushed_and_setup_again_retriggers():
    orch, bus, ears, mouth, mind, ev = await make(ScriptMind([]), identity=PushIdentity())
    await orch.handle_hud(Event("auth", {"access_token": "good"}))
    await settle(orch, bus)
    pc = types(ev, "prefs.changed")[-1].data
    assert pc["source"] == "local" and pc["updated_at"] == 777.0
    # finish onboarding, then "Beállítás újra" from the HUD → login trigger again, answered reset
    await orch.handle_hud(Event("prefs.set", {"answered": ["address", "wake_word", "voice", "welcome_routine"]}))
    assert orch.user.prefs.onboarded
    n = len([r for r in mind.requests if r.trigger == "login"])
    await orch.handle_hud(Event("prefs.set", {"onboarded": False}))
    await settle(orch, bus)
    assert not orch.user.prefs.onboarded and orch.user.prefs.answered == ()
    assert len([r for r in mind.requests if r.trigger == "login"]) == n + 1
    await orch.stop()
