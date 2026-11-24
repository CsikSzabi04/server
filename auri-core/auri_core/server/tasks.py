"""Long tasks (P5; 01/03 §4 `/tasks`, 01/02 §7): start · state · SSE events · pause · resume · cancel.

A task is one `ask()` run (a multi-step project, `plan=True`, or research) in the background of the
server process, owned by one signed-in user. Its row lives in the store's durable `jobs` table:
state + a checkpoint (events so far, last step). A server restart marks running tasks `interrupted`;
they can be resumed: a project continues at its last checkpoint (`ask(resume_run_id=…)`, the run id
comes from the earlier `route` event); research re-runs. The events of earlier attempts stay in the history.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any

from ..contracts import AskEvent

KIND = "task"
MAX_EVENTS = 500  # kept per task (deltas are merged), enough to replay a project's progress
TERMINAL = frozenset({"done", "failed", "cancelled"})
RunFn = Callable[[dict[str, Any]], AsyncIterator[AskEvent]]


def owner_key(user_id: str) -> str:
    return hashlib.sha256(f"auri-core-task:{user_id}".encode()).hexdigest()[:24]


@dataclass
class _Live:
    task: asyncio.Task[None] | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    changed: asyncio.Condition = field(default_factory=asyncio.Condition)
    stop_as: str | None = None  # "paused" | "cancelled" when the user stopped it


class TaskManager:
    def __init__(self, store: Any, run: RunFn) -> None:
        self.store = store
        self.run = run
        self.live: dict[str, _Live] = {}
        for j in store.list_jobs(kind=KIND, states=("running", "queued"), limit=500):  # crash/restart recovery
            store.update_job(j["id"], state="interrupted")

    # ── queries ────────────────────────────────────────────────────────────
    def get(self, job_id: str, user_id: str) -> dict[str, Any] | None:
        j = self.store.get_job(job_id)
        if j is None or j["kind"] != KIND or j["payload"].get("owner") != owner_key(user_id):
            return None
        cp = j["checkpoint"] or {}
        live = self.live.get(job_id)
        events = live.events if live and live.events else cp.get("events", [])
        return {"id": j["id"], "state": j["state"], "goal": j["payload"].get("text", ""), "mode": j["payload"].get("mode"),
                "created_at": j["created_at"], "updated_at": j["updated_at"], "attempts": cp.get("attempts", 0),
                "last_step": cp.get("last_step"), "outcome": cp.get("outcome"), "events": len(events)}

    def list(self, user_id: str) -> list[dict[str, Any]]:
        own = owner_key(user_id)
        return [t for j in self.store.list_jobs(kind=KIND, limit=100) if j["payload"].get("owner") == own
                for t in [self.get(j["id"], user_id)] if t]

    async def follow(self, job_id: str, start: int = 0) -> AsyncIterator[dict[str, Any]]:
        """History from `start`, then live events until the task stops."""
        i = start
        while True:
            live = self.live.get(job_id)
            events = live.events if live else ((self.store.get_job(job_id) or {}).get("checkpoint") or {}).get("events", [])
            while i < len(events):
                yield events[i]
                i += 1
            if live is None or live.task is None or live.task.done():
                return
            async with live.changed:
                if i >= len(live.events) and not live.task.done():
                    with contextlib.suppress(TimeoutError):
                        await asyncio.wait_for(live.changed.wait(), timeout=15)

    # ── control ────────────────────────────────────────────────────────────
    def start(self, payload: dict[str, Any], user_id: str) -> str:
        p = {k: v for k, v in payload.items() if k != "user_id"}  # the raw id never goes into the T0 db
        p["owner"] = owner_key(user_id)
        job_id = self.store.create_job(KIND, p, priority=1, text_fields=("text",))
        self._launch(job_id, user_id, attempts=0, history=[])
        return job_id

    def resume(self, job_id: str, user_id: str) -> bool:
        t = self.get(job_id, user_id)
        if t is None or t["state"] not in ("paused", "interrupted", "failed"):
            return False
        cp = self.store.get_job(job_id)["checkpoint"] or {}
        self._launch(job_id, user_id, attempts=int(cp.get("attempts", 0)), history=list(cp.get("events", [])))
        return True

    async def stop(self, job_id: str, user_id: str, *, as_state: str) -> bool:
        t = self.get(job_id, user_id)
        if t is None or t["state"] in TERMINAL:
            return False
        live = self.live.get(job_id)
        if live and live.task and not live.task.done():
            live.stop_as = as_state
            live.task.cancel()  # → aclosing in ask(): the model stream closes, the lane is freed
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await live.task
        else:
            self.store.update_job(job_id, state=as_state)
        return True

    async def aclose(self) -> None:
        for job_id, live in list(self.live.items()):
            if live.task and not live.task.done():
                live.stop_as = "interrupted"
                live.task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await live.task
            self.live.pop(job_id, None)

    # ── internals ──────────────────────────────────────────────────────────
    def _launch(self, job_id: str, user_id: str, *, attempts: int, history: list[dict[str, Any]]) -> None:
        live = _Live(events=history)
        self.live[job_id] = live
        payload = {**self.store.get_job(job_id)["payload"], "user_id": user_id}  # in memory only
        run_id = next((e["data"].get("run_id") for e in reversed(history)
                       if e.get("type") == "route" and e.get("data", {}).get("run_id")), None)
        if run_id:
            payload["resume_run_id"] = run_id
        live.task = asyncio.create_task(self._drive(job_id, payload, live, attempts + 1))

    async def _push(self, live: _Live, ev: dict[str, Any]) -> None:
        if ev["type"] == "delta" and live.events and live.events[-1]["type"] == "delta":
            live.events[-1] = {"type": "delta", "data": {"text": live.events[-1]["data"]["text"] + ev["data"].get("text", "")}}
        else:
            live.events.append(ev)
            del live.events[:-MAX_EVENTS]
        async with live.changed:
            live.changed.notify_all()

    def _save(self, job_id: str, live: _Live, state: str, attempt: int, *, outcome: str | None = None) -> None:
        last = next((e["data"].get("state") for e in reversed(live.events) if e["type"] == "step"), None)
        self.store.update_job(job_id, state=state, checkpoint={"events": live.events, "attempts": attempt,
                                                                "last_step": last, "outcome": outcome})

    async def _drive(self, job_id: str, payload: dict[str, Any], live: _Live, attempt: int) -> None:
        self._save(job_id, live, "running", attempt)
        await self._push(live, {"type": "step", "data": {"state": "ATTEMPT", "attempt": attempt}})
        final, outcome = "failed", None
        try:
            async with contextlib.aclosing(self.run(payload)) as events:
                async for ev in events:
                    await self._push(live, {"type": ev.type, "data": ev.data})
                    if ev.type == "step":
                        self._save(job_id, live, "running", attempt)  # checkpoint at every step boundary
                    elif ev.type == "done":
                        final, outcome = "done", str(ev.data.get("outcome"))
                    elif ev.type == "error":
                        final = "paused" if ev.data.get("kind") == "paused" else "failed"
                        outcome = str(ev.data.get("kind"))
        except asyncio.CancelledError:
            final = live.stop_as or "interrupted"
        except Exception as e:  # a bug, never the user's fault — no details that could hold secrets
            await self._push(live, {"type": "error", "data": {"kind": "infra", "message": f"belső hiba ({type(e).__name__})"}})
        finally:
            self._save(job_id, live, final, attempt, outcome=outcome)
            async with live.changed:
                live.changed.notify_all()
