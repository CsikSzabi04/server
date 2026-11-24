"""Idle watcher + background job runner (owner: AI-3, P4). Spec: thinking/05-tanulas/02-ejszakai-onallo-tanulas.md §2–4.

    OFF ──▶ WAITING ──(idle ≥ threshold, budget left)──▶ STUDYING
              ▲                                            │ user signal (≤ 1 s)
          COOLDOWN ◀──(5 min quiet)── PAUSED ◀── PAUSING ◀─┘
    (switched off · budget used up · 3 failures in a row → OFF)

* Idle = no keyboard/mouse (Windows `GetLastInputInfo`) for the threshold — 10 min in the night window
  (01:00–06:00), 20 min by day — AND no user request on the Core (scheduler) AND no blocker
  ("ma ne tanulj" flag file, a running bench/eval lock). By day only `light` jobs run (no model).
* A job is an async function with a context: `ctx.stop` (set on a user signal — stop at the next step),
  `ctx.load()/ctx.save()` checkpoint in the store's `jobs` table (the PC is off at night: resume next time),
  `ctx.use_call()` counts model calls against the night budget. Model calls still go through
  `scheduler.lease(Priority.BACKGROUND, …)`, whose `preempt` also fires on user activity.
* Cloud: never (background learning is local only).
"""

from __future__ import annotations

import asyncio
import contextlib
import ctypes
import sys
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

State = Literal["OFF", "WAITING", "STUDYING", "PAUSING", "PAUSED", "COOLDOWN"]
JobFn = Callable[["JobContext"], Awaitable[None]]


def seconds_since_input() -> float:
    """Windows: time since the last keyboard/mouse input. Elsewhere 0 (= never idle, safe)."""
    if sys.platform != "win32":
        return 0.0

    class _LastInput(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    li = _LastInput()
    li.cbSize = ctypes.sizeof(_LastInput)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)):  # type: ignore[attr-defined]
        return 0.0
    now = ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF  # type: ignore[attr-defined]
    return max(0.0, ((now - li.dwTime) & 0xFFFFFFFF) / 1000.0)


@dataclass
class IdleConfig:
    night: tuple[int, int] = (1, 6)  # [start, end) hours
    night_idle_s: float = 600.0
    day_idle_s: float = 1200.0
    cooldown_s: float = 300.0
    night_budget_s: float = 4 * 3600.0
    night_calls: int = 200
    max_failures: int = 3
    tick_s: float = 0.5  # while STUDYING: the user signal → stop path stays well under 1 s
    wait_tick_s: float = 30.0


@dataclass
class Job:
    name: str
    fn: JobFn
    light: bool  # True: no model (dedupe, maintenance, sandbox re-runs) — allowed by day too
    every_s: float = 24 * 3600.0  # not more often than this


@dataclass
class JobContext:
    name: str
    store: Any
    stop: asyncio.Event
    watcher: IdleWatcher
    job_id: str = ""

    def load(self) -> Any:
        j = self.store.get_job(self.job_id) if self.job_id else None
        return (j or {}).get("checkpoint")

    def save(self, checkpoint: Any) -> None:
        self.store.update_job(self.job_id, checkpoint=checkpoint)

    def use_call(self) -> bool:
        """Count one model call; False → the night budget is used up, stop."""
        return self.watcher.use_call()


@dataclass
class IdleWatcher:
    store: Any
    scheduler: Any = None
    cfg: IdleConfig = field(default_factory=IdleConfig)
    mode: Literal["off", "light", "full"] = "light"
    flag_dir: Path | None = None  # `no_study` (manual "ma ne tanulj") and `bench.lock` live here
    input_idle: Callable[[], float] = seconds_since_input
    clock: Callable[[], float] = time.monotonic
    wall: Callable[[], datetime] = datetime.now
    state: State = "WAITING"
    jobs: list[Job] = field(default_factory=list)
    reason: str = ""
    failures: int = 0
    calls_used: int = 0
    worked_s: float = 0.0
    _since: float = 0.0
    _study_start: float = 0.0
    _current: tuple[Job, asyncio.Task[None], JobContext] | None = None
    _budget_day: str = ""
    last_pause_ms: float | None = None

    def __post_init__(self) -> None:
        if self.mode == "off":
            self.state = "OFF"

    # ── registry ───────────────────────────────────────────────────────────
    def register(self, name: str, fn: JobFn, *, light: bool, every_s: float = 24 * 3600.0) -> None:
        self.jobs = [j for j in self.jobs if j.name != name] + [Job(name, fn, light, every_s)]

    # ── signals ────────────────────────────────────────────────────────────
    def is_night(self) -> bool:
        h = self.wall().hour
        a, b = self.cfg.night
        return a <= h < b if a < b else (h >= a or h < b)

    def blocker(self) -> str | None:
        if self.flag_dir is not None:
            if (self.flag_dir / "no_study").exists():
                return "kézi tiltás (ma ne tanulj)"
            if (self.flag_dir / "bench.lock").exists():
                return "mérés fut (bench.lock)"
        if self.scheduler is not None and self.scheduler.user_active():
            return "a felhasználó használja a Core-t"
        return None

    def idle_enough(self) -> bool:
        need = self.cfg.night_idle_s if self.is_night() else self.cfg.day_idle_s
        return self.input_idle() >= need

    def user_back(self) -> bool:
        return self.input_idle() < 5.0 or (self.scheduler is not None and self.scheduler.user_active())

    def use_call(self) -> bool:
        if self.calls_used >= self.cfg.night_calls:
            return False
        self.calls_used += 1
        return True

    def _reset_budget(self) -> None:
        day = self.wall().strftime("%Y-%m-%d")
        if day != self._budget_day:
            self._budget_day, self.calls_used, self.worked_s = day, 0, 0.0

    # ── state machine (one step; the loop calls it) ───────────────────────────
    def _pick(self) -> Job | None:
        light_only = self.mode == "light" or not self.is_night()
        for job in self.jobs:
            if light_only and not job.light:
                continue
            last = self.store.list_jobs(kind=f"bg:{job.name}", states=("done",), limit=1)
            if last and _age_s(last[0]["updated_at"]) < job.every_s:
                continue
            return job
        return None

    async def step(self) -> State:
        now = self.clock()
        self._reset_budget()
        if self.state == "OFF":
            return self.state
        if self.state == "STUDYING":
            assert self._current is not None
            job, task, ctx = self._current
            if self.user_back() or self.blocker():
                self.worked_s += now - self._study_start
                self.state, self._since = "PAUSING", now
                ctx.stop.set()
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
                self.last_pause_ms = (self.clock() - now) * 1000
                self.store.update_job(ctx.job_id, state="paused")
                self._current = None
                self.state, self._since, self.reason = "PAUSED", self.clock(), "a felhasználó visszajött"
            elif task.done():
                self.worked_s += now - self._study_start
                ok = not task.cancelled() and task.exception() is None
                self.store.update_job(ctx.job_id, state="done" if ok else "failed")
                self.failures = 0 if ok else self.failures + 1
                self._current = None
                self.state, self._since = "WAITING", now
                if self.failures >= self.cfg.max_failures:
                    self.state, self.reason = "OFF", "3 egymás utáni hiba"
            return self.state
        if self.state == "PAUSED":
            if not self.user_back():
                self.state, self._since = "COOLDOWN", now
            return self.state
        if self.state == "COOLDOWN":
            if self.user_back():
                self.state, self._since = "PAUSED", now
            elif now - self._since >= self.cfg.cooldown_s:
                self.state, self._since = "WAITING", now
            return self.state
        # WAITING
        b = self.blocker()
        if b:
            self.reason = b
            return self.state
        if self.worked_s >= self.cfg.night_budget_s:
            self.reason = "a napi keret elfogyott"
            return self.state
        if not self.idle_enough():
            self.reason = "nem tétlen"
            return self.state
        job = self._pick()
        if job is None:
            self.reason = "nincs esedékes munka"
            return self.state
        prev = self.store.list_jobs(kind=f"bg:{job.name}", states=("paused", "interrupted", "running"), limit=1)
        job_id = prev[0]["id"] if prev else self.store.create_job(f"bg:{job.name}", {"name": job.name}, priority=0)
        ctx = JobContext(job.name, self.store, asyncio.Event(), self, job_id)
        self.store.update_job(job_id, state="running")
        self._current = (job, asyncio.create_task(job.fn(ctx)), ctx)
        self.state, self._since, self._study_start, self.reason = "STUDYING", now, now, job.name
        return self.state

    async def run(self) -> None:
        """The loop (server lifespan task). Cancelled on shutdown → the running job is interrupted."""
        try:
            while True:
                await self.step()
                await asyncio.sleep(self.cfg.tick_s if self.state in ("STUDYING", "PAUSED", "COOLDOWN") else self.cfg.wait_tick_s)
        finally:
            if self._current is not None:
                _, task, ctx = self._current
                ctx.stop.set()
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
                self.store.update_job(ctx.job_id, state="interrupted")

    def describe(self) -> dict[str, Any]:
        return {"state": self.state, "mode": self.mode, "reason": self.reason, "night": self.is_night(),
                "job": self._current[0].name if self._current else None, "calls_used": self.calls_used,
                "worked_min": round(self.worked_s / 60, 1), "last_pause_ms": self.last_pause_ms,
                "jobs": [{"name": j.name, "light": j.light} for j in self.jobs]}


def _age_s(iso: str) -> float:
    try:
        t = datetime.fromisoformat(iso)
    except ValueError:
        return float("inf")
    now = datetime.now(t.tzinfo) if t.tzinfo else datetime.now()
    return (now - t).total_seconds()


async def maintenance_job(ctx: JobContext) -> None:
    """Built-in light job (no model): validity/usefulness clocks, dedupe, privacy audit → checkpoint report."""
    st = ctx.store
    report: dict[str, Any] = {"at": datetime.now().isoformat(timespec="seconds")}
    report.update(st.maintain())
    if ctx.stop.is_set():
        return ctx.save(report)
    report["merged"] = len(st.dedupe())
    if ctx.stop.is_set():
        return ctx.save(report)
    report["personal_flagged"] = len(st.audit_personal())  # ids only, never content; target: 0
    ctx.save(report)
    return None
