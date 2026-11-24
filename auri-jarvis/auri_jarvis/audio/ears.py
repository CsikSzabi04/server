"""Auri's ears — implements contracts.Ears.

  start(on_wake) → microphone stream + push-to-talk hotkey (+ wake words / claps in M2)
  listen()       → VAD endpointing → Parakeet (or Whisper in accurate mode) → lexicon fix
Blocking work (endpointing, STT) runs in worker threads, never on the asyncio loop.
"""

from __future__ import annotations

import asyncio
import logging
import re
import threading
import time
from collections.abc import Callable
from typing import Any

from ..contracts import Event, Transcript, WakeEvent
from ..stt.engines import ParakeetStt, WhisperStt
from ..stt.lexicon import Lexicon
from ._paths import resolve
from .capture import AudioCapture
from .vad import EndpointConfig, Endpointer

log = logging.getLogger("auri.voice.ears")

LEVEL_EVERY_S = 1 / 15
# Auri's own spoken acks at the very start of a transcript (picked up from the speakers)
_ACK_ECHO = re.compile(r"^\s*(igen|hallgatlak|máris|yes|listening)\b[\s,.!?…]*", re.IGNORECASE)


class AuriEars:
    def __init__(self, cfg: dict[str, Any], emit=None, *, capture: AudioCapture | None = None) -> None:
        audio, wake, stt = cfg.get("audio") or {}, cfg.get("wake") or {}, cfg.get("stt") or {}
        self._cfg = cfg
        self._emit = emit or (lambda ev: None)
        self._device_spec = audio.get("input_device", "auto")
        self._capture = capture  # injected in tests (file source)
        self._ring_s = float(audio.get("ring_seconds", 10))
        self._hotkey_combo = str(wake.get("hotkey", "ctrl+alt+space"))
        self._hotkey = None
        self._on_wake: Callable[[WakeEvent], None] | None = None
        self._suppressed = False
        self._wake_word = "hey_auri"
        self._endpoint_cfg = EndpointConfig.from_cfg(cfg.get("vad"))
        self._endpointer: Endpointer | None = None
        self._fast = ParakeetStt(stt.get("parakeet_model", "nemo-parakeet-tdt-0.6b-v3"), stt.get("parakeet_quantization", "int8"))
        lexicon = Lexicon.load(resolve(stt.get("lexicon", "config/lexicon.yaml")))
        self._lexicon = lexicon
        self._accurate = WhisperStt(
            stt.get("whisper_model", "large-v3-turbo"),
            stt.get("whisper_language", "hu"),
            hotwords=", ".join(lexicon.terms),
            threads=int(stt.get("whisper_threads", 6)),
        )
        self._cancel = threading.Event()
        self._last_level_emit = 0.0
        self._unsub_level: Callable[[], None] | None = None
        self._unsub_wake: Callable[[], None] | None = None
        self._wake_cfg = wake
        self._hub = None
        self._last_wake_word_t = 0.0  # monotonic time of the last spoken-wake-word detection
        self._history_s = float(wake.get("command_history_s", 2.5))
        self._stopping = threading.Event()

    # ── microphone watchdog (device unplugged / driver hiccup) ─────────────
    def _watchdog(self) -> None:
        """No frames for 3 s → report once (`error`, where="ears.device") and try to re-open
        the stream every 3 s. (A brand-new device needs a restart: PortAudio lists devices once.)"""
        from .devices import pick_input

        lost, next_try = False, 0.0
        while not self._stopping.wait(1.0):
            cap = self._capture
            if cap is None:
                continue
            stale = time.monotonic() - cap.last_frame_t > 3.0
            if stale and not lost:
                lost = True
                log.warning("microphone stopped delivering audio — trying to re-open it")
                self._emit(Event("error", {"where": "ears.device", "message": "A mikrofon nem ad hangot — újracsatlakozás…"}))
            if stale and time.monotonic() >= next_try:
                next_try = time.monotonic() + 3.0
                try:
                    cap.reopen(pick_input(self._device_spec).index)
                except Exception as e:
                    log.info("microphone re-open failed: %s", e)
            elif not stale and lost:
                lost = False
                log.info("microphone delivers audio again")

    # ── contract: Ears ─────────────────────────────────────────────────────
    def start(self, on_wake: Callable[[WakeEvent], None]) -> None:
        self._on_wake = on_wake
        if self._capture is None:
            from .devices import pick_input

            choice = pick_input(self._device_spec)
            self._capture = AudioCapture(choice.index, ring_seconds=self._ring_s)
            self._capture.start()
            threading.Thread(target=self._watchdog, name="auri-mic-watchdog", daemon=True).start()
        self._unsub_level = self._capture.subscribe(self._level_tap)
        from ..wake.hotkey import Hotkey

        self._hotkey = Hotkey(self._hotkey_combo, lambda: self._fire(WakeEvent(source="hotkey")))
        self._hotkey.start()
        if self._wake_cfg.get("enabled", True):
            from ..wake.hub import WakeHub

            self._hub = WakeHub(self._wake_cfg, self._on_auto_wake, stt=self._fast)
            self._hub.set_word(self._wake_word)
            self._hub.suppressed = self._suppressed
            self._hub.start()
            self._unsub_wake = self._capture.subscribe(self._hub.feed)
        # load the heavy models in the background so the first listen() is fast
        threading.Thread(target=self._warmup, name="auri-stt-warmup", daemon=True).start()

    def stop(self) -> None:
        self._cancel.set()
        self._stopping.set()
        if self._hotkey is not None:
            self._hotkey.stop()
        if self._unsub_level is not None:
            self._unsub_level()
        if self._unsub_wake is not None:
            self._unsub_wake()
        if self._hub is not None:
            self._hub.stop()
        if self._capture is not None:
            self._capture.stop()

    def set_wake_word(self, word: str) -> None:
        self._wake_word = word
        if self._hub is not None:
            self._hub.set_word(word)

    def set_suppressed(self, on: bool) -> None:
        # Silences automatic wakes (wake word / claps) while Auri speaks or the HUD mutes the
        # mic. The hotkey is never suppressed (explicit user action = barge-in).
        self._suppressed = on
        if self._hub is not None:
            self._hub.suppressed = on

    async def listen(self, *, max_s: float = 15.0, accurate: bool = False, start_timeout_s: float = 4.0) -> Transcript | None:
        if self._capture is None:
            raise RuntimeError("Ears.listen() before start()")
        self._cancel.set()  # cancel a previous listen, if any
        cancel = threading.Event()
        self._cancel = cancel
        try:
            utt = await asyncio.to_thread(self._capture_utterance, max_s, start_timeout_s, cancel)
        except asyncio.CancelledError:
            cancel.set()
            raise
        if utt is None or utt.speech_ms < 200:
            return None
        used_history = time.monotonic() - self._last_wake_word_t < self._history_s + max_s
        engine = self._accurate if accurate else self._fast
        t = time.perf_counter()
        raw, lang = await asyncio.to_thread(engine.transcribe, utt.pcm)
        stt_ms = int((time.perf_counter() - t) * 1000)
        if not raw:
            return None
        from ..wake.hub import strip_wake_phrase

        text = strip_wake_phrase(self._lexicon.correct(raw))  # "Hey Auri, hány óra van" → "Hány óra van"
        if used_history:  # the audio since the wake word may contain Auri's own ack ("Igen?") via speakers
            text = _ACK_ECHO.sub("", text, count=1)
            text = text[:1].upper() + text[1:]
        if not text.strip(" ,.!?"):
            return None  # only the wake word itself was heard
        return Transcript(
            raw=raw, text=text, lang=lang, confidence=1.0, engine=engine.name, speech_ms=utt.speech_ms, stt_ms=stt_ms
        )

    @property
    def level(self) -> float:
        return self._capture.level if self._capture is not None else 0.0

    # ── internals ──────────────────────────────────────────────────────────
    def _capture_utterance(self, max_s: float, start_timeout_s: float, cancel: threading.Event):
        if self._endpointer is None:
            self._endpointer = Endpointer(self._endpoint_cfg)
        # A command spoken right after "Hey Auri" (no pause) has already started by now:
        # include the audio since the wake word so its first words are not lost.
        since = time.monotonic() - self._last_wake_word_t
        history = since + 0.15 if since < self._history_s else 0.0
        return self._endpointer.capture(
            self._capture.subscribe,
            max_s=max_s,
            start_timeout_s=start_timeout_s,
            cancel=cancel,
            history=history,
            capture=self._capture,
        )

    def _on_auto_wake(self, source: str, word: str | None, confidence: float) -> None:
        if source == "wakeword":
            self._last_wake_word_t = time.monotonic()
        self._fire(WakeEvent(source=source, word=word, confidence=confidence))  # type: ignore[arg-type]

    def _fire(self, ev: WakeEvent) -> None:
        if ev.source not in ("hotkey", "hud") and self._suppressed:
            return
        self._emit(Event("wake", {"source": ev.source, "word": ev.word, "confidence": ev.confidence}))
        if self._on_wake is not None:
            self._on_wake(ev)

    def _level_tap(self, _frame) -> None:
        now = time.monotonic()
        if now - self._last_level_emit >= LEVEL_EVERY_S:
            self._last_level_emit = now
            self._emit(Event("level", {"source": "mic", "rms": round(self.level, 4)}))

    def _warmup(self) -> None:
        try:
            self._fast.load()
            if self._endpointer is None:
                self._endpointer = Endpointer(self._endpoint_cfg)
        except Exception as e:
            log.warning("STT warm-up failed: %s", e)
