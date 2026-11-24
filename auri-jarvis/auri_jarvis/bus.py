"""auri_jarvis.bus — thread-safe event bus (owner: AI-3).

`bus.emit(Event)` may be called from ANY thread (PortAudio callbacks, worker threads, the
loop itself). Every event is handed to the asyncio loop with `call_soon_threadsafe` and
dispatched there, in emit order, to:

- type handlers registered with `bus.on("say", fn)` (`"*"` = every event); a handler may be a
  plain function or a coroutine function (scheduled as a task, exceptions logged);
- queues from `bus.subscribe_queue()` (the HUD WebSocket connections).

`level` events are thinned to ~15 Hz per source and dropped when the value hardly changed.
The last event of each "sticky" type is kept so a freshly connected HUD gets the current
picture (`bus.snapshot()`).

The wire format (HUD WebSocket JSON) is `{"type": ..., "data": {...}, "t": ...}` —
`event_to_dict()` / `event_from_dict()`.
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import enum
import inspect
import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .contracts import Event

log = logging.getLogger(__name__)

Handler = Callable[[Event], Any]

STICKY_TYPES = frozenset(
    {"state", "identity", "options", "stats", "tts.credits", "prefs.changed", "onboarding", "mute", "warmup"}
)


def to_jsonable(v: Any) -> Any:
    """Best-effort conversion of event payloads (dataclasses, tuples, enums, paths) to JSON types."""
    if dataclasses.is_dataclass(v) and not isinstance(v, type):
        return {f.name: to_jsonable(getattr(v, f.name)) for f in dataclasses.fields(v)}
    if isinstance(v, dict):
        return {str(k): to_jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set, frozenset)):
        return [to_jsonable(x) for x in v]
    if isinstance(v, enum.Enum):
        return v.value
    if isinstance(v, Path):
        return str(v)
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    return str(v)


def event_to_dict(ev: Event) -> dict[str, Any]:
    return {"type": ev.type, "data": to_jsonable(ev.data), "t": ev.t}


def event_from_dict(d: Any) -> Event:
    """Parse an incoming HUD message. Raises ValueError on a malformed envelope."""
    if not isinstance(d, dict):
        raise ValueError("message must be a JSON object")
    typ = d.get("type")
    if not isinstance(typ, str) or not typ or len(typ) > 64:
        raise ValueError("missing/invalid 'type'")
    data = d.get("data", {})
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("'data' must be an object")
    t = d.get("t")
    return Event(typ, data, float(t)) if isinstance(t, (int, float)) else Event(typ, data)


class Bus:
    def __init__(self, *, level_hz: float = 15.0, level_min_delta: float = 0.01, pending_max: int = 1000):
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()
        self._pending: deque[Event] = deque(maxlen=pending_max)
        self._handlers: dict[str, list[Handler]] = {}
        self._queues: set[asyncio.Queue[Event]] = set()
        self._sticky: dict[str, Event] = {}
        self._tasks: set[asyncio.Task[Any]] = set()
        self._level_period = 1.0 / level_hz if level_hz > 0 else 0.0
        self._level_min_delta = level_min_delta
        self._level_last: dict[str, tuple[float, float]] = {}  # source -> (monotonic, rms)
        self.dropped_levels = 0

    # ── lifecycle ────────────────────────────────────────────────────────────
    def attach(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Bind to the running loop; events emitted before this are flushed now."""
        loop = loop or asyncio.get_running_loop()
        with self._lock:
            self._loop = loop
            pending = list(self._pending)
            self._pending.clear()
        for ev in pending:
            loop.call_soon_threadsafe(self._dispatch, ev)

    @property
    def loop(self) -> asyncio.AbstractEventLoop | None:
        return self._loop

    async def drain(self) -> None:
        """Let queued dispatches and handler tasks run (tests / shutdown)."""
        for _ in range(3):
            await asyncio.sleep(0)
        if self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)
        await asyncio.sleep(0)

    # ── emit (any thread) ────────────────────────────────────────────────────
    def emit(self, ev: Event) -> None:
        if not isinstance(ev, Event):
            raise TypeError(f"bus.emit expects contracts.Event, got {type(ev).__name__}")
        if ev.type == "level" and not self._level_pass(ev):
            return
        with self._lock:
            loop = self._loop
            if loop is None:
                self._pending.append(ev)
                return
        try:
            loop.call_soon_threadsafe(self._dispatch, ev)
        except RuntimeError:  # loop closed (shutdown) — nothing to deliver to
            pass

    def emit_type(self, type_: str, **data: Any) -> None:
        self.emit(Event(type_, data))

    def _level_pass(self, ev: Event) -> bool:
        src = str(ev.data.get("source", "mic"))
        try:
            rms = float(ev.data.get("rms", 0.0))
        except (TypeError, ValueError):
            return False
        now = time.monotonic()
        with self._lock:
            last = self._level_last.get(src)
            if last is not None:
                last_t, last_rms = last
                if now - last_t < self._level_period or abs(rms - last_rms) < self._level_min_delta:
                    self.dropped_levels += 1
                    return False
            self._level_last[src] = (now, rms)
        return True

    # ── subscription ─────────────────────────────────────────────────────────
    def on(self, type_: str, handler: Handler) -> Callable[[], None]:
        self._handlers.setdefault(type_, []).append(handler)

        def off() -> None:
            with contextlib.suppress(ValueError):
                self._handlers.get(type_, []).remove(handler)

        return off

    def subscribe_queue(self, maxsize: int = 500) -> asyncio.Queue[Event]:
        q: asyncio.Queue[Event] = asyncio.Queue(maxsize=maxsize)
        self._queues.add(q)
        return q

    def unsubscribe_queue(self, q: asyncio.Queue[Event]) -> None:
        self._queues.discard(q)

    def snapshot(self) -> list[Event]:
        return list(self._sticky.values())

    def last(self, type_: str) -> Event | None:
        return self._sticky.get(type_)

    # ── dispatch (loop thread) ───────────────────────────────────────────────
    def _dispatch(self, ev: Event) -> None:
        if ev.type in STICKY_TYPES:
            self._sticky[ev.type] = ev
        for h in (*self._handlers.get(ev.type, ()), *self._handlers.get("*", ())):
            try:
                res = h(ev)
            except Exception:
                log.exception("bus handler failed for %s", ev.type)
                continue
            if inspect.isawaitable(res):
                task = asyncio.ensure_future(res)
                self._tasks.add(task)
                task.add_done_callback(self._task_done)
        for q in list(self._queues):
            if q.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    q.get_nowait()  # drop the oldest — a slow HUD must not block the daemon
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait(ev)

    def _task_done(self, task: asyncio.Task[Any]) -> None:
        self._tasks.discard(task)
        if not task.cancelled() and task.exception() is not None:
            log.error("bus async handler failed", exc_info=task.exception())
