"""auri_jarvis.fakes — stand-ins for the real Ears / Mouth / Mind (owner: AI-3).

Used by `python -m auri_jarvis --text`, by the tests, and by the orchestrator until AI-1 and
AI-2 deliver their modules. They implement the contracts exactly.

- FakeEars: every stdin line is "transcribed speech". A line typed while nobody is listening
  fires a wake (source "hotkey") and becomes the next `listen()` result; a line typed while a
  `listen()` is waiting goes straight to it (follow-up). An empty line = wake only.
- FakeMouth: prints what it would say ("Auri: …").
- EchoMind: echoes the request + tells the time; emits route / reply.delta / reply.done.
"""

from __future__ import annotations

import asyncio
import contextlib
import queue
import sys
import threading
import time
from collections.abc import AsyncIterator, Callable, Iterable
from datetime import datetime
from typing import Any, TextIO

from .contracts import (
    Emit,
    Event,
    Transcript,
    TurnRequest,
    UserContext,
    VoiceName,
    WakeEvent,
    WakeWord,
)

_EOF = object()


class FakeEars:
    """Text-driven Ears. Feed lines with `feed()` or from a stream (stdin) via `start()`."""

    def __init__(
        self,
        *,
        stream: TextIO | Iterable[str] | None = None,
        on_eof: Callable[[], None] | None = None,
        read_stream: bool = True,
    ) -> None:
        self._stream = stream if stream is not None else sys.stdin
        self._read_stream = read_stream
        self._on_eof = on_eof
        self._on_wake: Callable[[WakeEvent], None] | None = None
        self._lines: queue.Queue[Any] = queue.Queue()
        self._lock = threading.Lock()
        self._waiting = 0  # number of listen() calls currently waiting
        self._thread: threading.Thread | None = None
        self._stopped = threading.Event()
        self.wake_word: WakeWord = "hey_auri"
        self.suppressed = False
        self.listen_calls: list[dict[str, Any]] = []

    # contract ─────────────────────────────────────────────────────────────────
    def start(self, on_wake: Callable[[WakeEvent], None]) -> None:
        self._on_wake = on_wake
        if self._read_stream and self._thread is None:
            self._thread = threading.Thread(target=self._reader, name="FakeEars-stdin", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stopped.set()
        self._lines.put(_EOF)

    def set_wake_word(self, word: WakeWord) -> None:
        self.wake_word = word

    def set_suppressed(self, on: bool) -> None:
        self.suppressed = on

    async def listen(self, *, max_s: float = 15.0, accurate: bool = False, start_timeout_s: float = 4.0) -> Transcript | None:
        self.listen_calls.append({"max_s": max_s, "accurate": accurate, "start_timeout_s": start_timeout_s})
        with self._lock:
            self._waiting += 1
        try:
            item = await asyncio.to_thread(self._get, start_timeout_s)
        finally:
            with self._lock:
                self._waiting -= 1
        if item is None or item is _EOF:
            if item is _EOF:
                self._lines.put(_EOF)  # keep EOF visible for the next caller
            return None
        text = str(item)
        return Transcript(raw=text, text=text, lang="hu", confidence=1.0, engine="text", speech_ms=0, stt_ms=0)

    @property
    def level(self) -> float:
        return 0.0

    # helpers ──────────────────────────────────────────────────────────────────
    def feed(self, line: str) -> None:
        """Inject one line as if typed (thread-safe)."""
        line = line.rstrip("\r\n")
        with self._lock:
            listening = self._waiting > 0
            backlog = not self._lines.empty()
        if line:
            self._lines.put(line)
        if listening and line:
            return  # goes straight to the waiting listen() (follow-up)
        if backlog and line:
            return  # earlier speech not consumed yet → it's queued speech, not a new wake
        if self._on_wake is not None:
            self._on_wake(WakeEvent(source="hotkey"))

    def _get(self, timeout: float) -> Any:
        try:
            return self._lines.get(timeout=max(0.0, timeout))
        except queue.Empty:
            return None

    def _reader(self) -> None:
        try:
            for line in self._stream:
                if self._stopped.is_set():
                    return
                self.feed(line)
        except (OSError, ValueError):
            pass
        if not self._stopped.is_set() and self._on_eof is not None:
            self._on_eof()


class FakeMouth:
    """Prints instead of speaking. `delay_s` simulates synthesis time per sentence."""

    def __init__(self, *, out: TextIO | None = None, prefix: str = "Auri: ", delay_s: float = 0.0) -> None:
        self._out = out if out is not None else sys.stdout
        self._prefix = prefix
        self._delay = delay_s
        self._speaking = False
        self._stopped_flag = False
        self.voice: VoiceName = "daniel"
        self.said: list[str] = []
        self.samples: list[str] = []

    async def say(self, text: str, *, signature: bool = False) -> None:
        self._stopped_flag = False
        await self._speak(text)

    async def say_stream(self, chunks: AsyncIterator[str]) -> None:
        self._stopped_flag = False
        buf: list[str] = []
        try:
            async for c in chunks:
                if self._stopped_flag:
                    break
                buf.append(c)
                if not self._speaking:
                    self._speaking = True
        finally:
            text = "".join(buf).strip()
            self._speaking = False
        if text and not self._stopped_flag:
            await self._speak(text)

    async def play_sample(self, voice: VoiceName) -> None:
        self.samples.append(voice)
        await self._speak(f"[hangminta: {voice}]")

    def stop(self) -> None:
        self._stopped_flag = True
        self._speaking = False

    def set_voice(self, voice: VoiceName) -> None:
        self.voice = voice

    @property
    def speaking(self) -> bool:
        return self._speaking

    @property
    def out_level(self) -> float:
        return 0.3 if self._speaking else 0.0

    async def _speak(self, text: str) -> None:
        self._speaking = True
        try:
            if self._delay:
                await asyncio.sleep(self._delay)
            if self._stopped_flag:
                return
            self.said.append(text)
            with contextlib.suppress(OSError, ValueError):
                print(f"{self._prefix}{text}", file=self._out, flush=True)
        finally:
            self._speaking = False


class EchoMind:
    """Minimal Mind: echo + current time. Records hook calls for tests."""

    def __init__(self, *, delay_s: float = 0.0) -> None:
        self._delay = delay_s
        self.requests: list[TurnRequest] = []
        self.identity_changes: list[UserContext] = []
        self.hud_events: list[Event] = []
        self.idle_ticks: list[float] = []
        self.warmed_up = False

    async def handle(self, req: TurnRequest, emit: Emit) -> AsyncIterator[str]:
        self.requests.append(req)
        if req.channel == "trigger":
            emit(Event("route", {"path": "trigger", "intent": req.trigger}))
            return  # nothing to say → the orchestrator acks + listens
        emit(Event("route", {"path": "llm", "intent": "echo"}))
        if self._delay:
            await asyncio.sleep(self._delay)
        now = datetime.now().strftime("%H:%M")
        text = req.text.strip()
        reply = f"Ezt mondtad: {text}. Az idő {now}." if text else f"Itt vagyok. Az idő {now}."
        t0 = time.monotonic()
        parts = reply.split(" ")
        for i, word in enumerate(parts):
            delta = word if i == 0 else " " + word
            emit(Event("reply.delta", {"text": delta}))
            yield delta
        emit(
            Event(
                "reply.done",
                {
                    "text": reply,
                    "model": "echo",
                    "llm_first_ms": int((time.monotonic() - t0) * 1000),
                    "tokens": len(parts),
                },
            )
        )

    async def on_identity_change(self, user: UserContext) -> None:
        self.identity_changes.append(user)

    async def on_hud_event(self, ev: Event, user: UserContext) -> None:
        self.hud_events.append(ev)

    async def idle_tick(self, idle_s: float, user: UserContext) -> None:
        self.idle_ticks.append(idle_s)

    async def warmup(self) -> None:
        self.warmed_up = True


# Factory-shaped constructors (same signature as the real ones) ──────────────────
def create_fake_ears(cfg: dict[str, Any], emit: Emit) -> FakeEars:
    return FakeEars()


def create_fake_mouth(cfg: dict[str, Any], emit: Emit) -> FakeMouth:
    return FakeMouth()


def create_echo_mind(cfg: dict[str, Any], emit: Emit) -> EchoMind:
    return EchoMind()
