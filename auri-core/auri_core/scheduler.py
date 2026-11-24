"""Scheduler — the owner of the single Ollama lane (owner: AI-3).

P0: one lane (one lock) with priority-ordered waiters: VOICE > CHAT > TASK > BACKGROUND.
Every model call needs an active `Lease` (`llm.OllamaClient` refuses to call without one).

    async with scheduler.lease(Priority.TASK, "gemma4:e2b") as lease:
        text, stats = await llm.chat(lease, messages)

Interim rule (NK14 f, not measured yet): while a VOICE lease is held or waiting, nothing
else starts — that falls out of the priority order, since VOICE is always served first.
P1 adds: `/activity`, idle detection, BACKGROUND giving the lane up immediately.
"""

from __future__ import annotations

import asyncio
import enum
import heapq
import itertools
import time
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field

try:  # the shared type lives in contracts.py (owner: AI-1)
    from .contracts import Priority  # type: ignore[attr-defined]
except ImportError:  # until contracts.py ships — same names as the spec (01/01 §4)

    class Priority(enum.IntEnum):  # type: ignore[no-redef]
        BACKGROUND = 0
        TASK = 1
        CHAT = 2
        VOICE = 3


# Rank by NAME, so the order holds whatever numeric values contracts.py chooses.
_RANK: dict[str, int] = {"VOICE": 0, "CHAT": 1, "TASK": 2, "BACKGROUND": 3}
USER_PRIORITIES = frozenset({"VOICE", "CHAT"})


def rank(prio: object) -> int:
    name = getattr(prio, "name", str(prio)).upper()
    if name not in _RANK:
        raise ValueError(f"unknown priority: {prio!r}")
    return _RANK[name]


class LeaseError(RuntimeError):
    """A model call without a valid, active lease (the gate was bypassed)."""


@dataclass(eq=False)
class Lease:
    id: int
    prio: object
    model: str
    scheduler: Scheduler
    granted_at: float = 0.0
    released_at: float | None = None
    wait_ms: int = 0
    # Set when a higher-priority request wants the lane (P0: advisory; BACKGROUND
    # work should check it between steps and stop).
    preempt: asyncio.Event = field(default_factory=asyncio.Event)

    @property
    def active(self) -> bool:
        return self.granted_at > 0 and self.released_at is None and self.scheduler.holder is self

    def check(self, model: str | None = None) -> None:
        """Raise LeaseError unless this lease may make a model call now."""
        if not self.active:
            raise LeaseError("modellhívás aktív bérlet nélkül")
        if model is not None and model != self.model:
            raise LeaseError(f"a bérlet a(z) {self.model} modellre szól, nem a(z) {model} modellre")


class Scheduler:
    """One lane, priority-ordered (FIFO within one priority). Not thread-safe: one event loop."""

    def __init__(self, *, user_idle_s: float = 15 * 60) -> None:
        self._seq = itertools.count(1)
        self._waiters: list[tuple[int, int, asyncio.Future[None], Lease]] = []
        self.holder: Lease | None = None
        self.user_idle_s = user_idle_s
        self._last_user_activity: float | None = None
        self.stats = {"granted": 0, "max_wait_ms": 0}

    # ── public API (Protocol: lease, user_active) ─────────────────────────────
    @asynccontextmanager
    async def lease(self, prio: object, model: str) -> AsyncIterator[Lease]:
        r = rank(prio)
        lease = Lease(id=next(self._seq), prio=prio, model=model, scheduler=self)
        if rank_name(prio) in USER_PRIORITIES:
            self.note_user_activity()
        t0 = time.perf_counter()
        await self._acquire(r, lease)
        lease.wait_ms = int((time.perf_counter() - t0) * 1000)
        self.stats["granted"] += 1
        self.stats["max_wait_ms"] = max(self.stats["max_wait_ms"], lease.wait_ms)
        try:
            yield lease
        finally:
            self._release(lease)

    def user_active(self) -> bool:
        """True while the user is (or was recently) using the lane: a VOICE/CHAT lease is
        held or waiting, or user activity was noted within `user_idle_s`."""
        if self.holder is not None and rank_name(self.holder.prio) in USER_PRIORITIES:
            return True
        if any(rank_name(w[3].prio) in USER_PRIORITIES for w in self._waiters if not w[2].done()):
            return True
        last = self._last_user_activity
        return last is not None and (time.monotonic() - last) < self.user_idle_s

    def note_user_activity(self) -> None:
        """Called on VOICE/CHAT leases; P1: also by the `/activity` endpoint (Jarvis, web)."""
        self._last_user_activity = time.monotonic()

    @property
    def queue_len(self) -> int:
        return sum(1 for w in self._waiters if not w[2].done())

    # ── internals ────────────────────────────────────────────────────────────
    async def _acquire(self, r: int, lease: Lease) -> None:
        if self.holder is None and not self._has_waiters():
            self._grant(lease)
            return
        fut: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        heapq.heappush(self._waiters, (r, lease.id, fut, lease))
        if self.holder is not None and r < rank(self.holder.prio):
            self.holder.preempt.set()  # ask the lower-priority holder to yield soon
        try:
            await fut
        except asyncio.CancelledError:
            if fut.done() and not fut.cancelled() and self.holder is lease:
                self._release(lease)  # granted and cancelled in the same tick
            raise

    def _has_waiters(self) -> bool:
        return any(not w[2].done() for w in self._waiters)

    def _grant(self, lease: Lease) -> None:
        self.holder = lease
        lease.granted_at = time.monotonic()

    def _release(self, lease: Lease) -> None:
        if lease.released_at is not None:
            return
        lease.released_at = time.monotonic()
        if self.holder is not lease:
            return
        self.holder = None
        while self._waiters:
            _, _, fut, nxt = heapq.heappop(self._waiters)
            if fut.done():  # cancelled while waiting
                continue
            self._grant(nxt)
            fut.set_result(None)
            return


def rank_name(prio: object) -> str:
    return getattr(prio, "name", str(prio)).upper()


_default: Scheduler | None = None


def get_scheduler() -> Scheduler:
    """The process-wide scheduler (one lane per process)."""
    global _default
    if _default is None:
        _default = Scheduler()
    return _default


def lease(prio: object, model: str) -> AbstractAsyncContextManager[Lease]:
    """Module-level shortcut: `async with scheduler.lease(Priority.TASK, model) as l:`."""
    return get_scheduler().lease(prio, model)


def user_active() -> bool:
    return get_scheduler().user_active()
