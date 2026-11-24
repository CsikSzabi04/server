"""AI-3 P5: long tasks — start, follow (SSE), pause/resume/cancel, owner isolation, restart recovery."""

from __future__ import annotations

import asyncio
import dataclasses

import httpx
import pytest

from auri_core.contracts import AskEvent
from auri_core.fakes import FakeScheduler, FakeStreamLLM
from auri_core.server import create_app
from auri_core.server.tasks import TaskManager

from .test_tiers import AUTH, TOKEN, USER, _supabase

OTHER = {**AUTH, "X-Auri-User": "other-token"}


def _two_users() -> httpx.MockTransport:
    base = _supabase()

    def handler(req: httpx.Request) -> httpx.Response:
        if req.headers.get("authorization") == "Bearer other-token":
            return httpx.Response(200, json={"id": "00000000-0000-4000-8000-000000000002"})
        return base.handle_request(req)
    return httpx.MockTransport(handler)


async def _fake_run(payload):
    yield AskEvent("route", {"level": 2})
    for i in range(3):
        yield AskEvent("step", {"state": f"T{i}", "ms": 0})
        await asyncio.sleep(0.01)
        yield AskEvent("delta", {"text": f"rész{i} "})
    yield AskEvent("done", {"outcome": "answered"})


async def _slow_run(payload):
    yield AskEvent("step", {"state": "PLAN", "ms": 0})
    await asyncio.sleep(30)
    yield AskEvent("done", {"outcome": "answered"})


@pytest.fixture
def mk(cfg, store, tmp_path):
    from auri_core.server.identity import Verifier

    cfg = dataclasses.replace(cfg, supabase_url="https://example.supabase.co", supabase_anon_key="anon",
                              users_dir=tmp_path / "users", runs_dir=tmp_path / "runs")

    def make(run):
        sched = FakeScheduler()
        return create_app(cfg, token=TOKEN, llm=FakeStreamLLM([]), scheduler=sched, store=store,
                          verifier=Verifier(cfg, transport=_two_users()), task_run=run)
    return make


def _client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8791")


async def test_task_lifecycle_and_isolation(mk, store):
    app = mk(_fake_run)
    async with _client(app) as c:
        assert (await c.post("/core/v1/tasks", headers=AUTH, json={"text": "csinálj egy todo appot"})).status_code == 403
        jid = (await c.post("/core/v1/tasks", headers=USER, json={"text": "csinálj egy todo appot"})).json()["id"]
        sse = (await c.get(f"/core/v1/tasks/{jid}/events", headers=USER)).text
        assert "event: done" in sse and all(f"rész{i}" in sse for i in range(3))
        t = (await c.get(f"/core/v1/tasks/{jid}", headers=USER)).json()
        assert t["state"] == "done" and t["attempts"] == 1 and t["outcome"] == "answered"
        assert (await c.get(f"/core/v1/tasks/{jid}", headers=OTHER)).status_code == 404  # not someone else's
        assert [x["id"] for x in (await c.get("/core/v1/tasks", headers=USER)).json()["tasks"]] == [jid]
        assert (await c.get("/core/v1/tasks", headers=OTHER)).json()["tasks"] == []
    row = store.db.execute("SELECT payload FROM jobs WHERE id=?", (jid,)).fetchone()[0]
    assert "00000000" not in row  # raw user id never stored


async def test_pause_resume_cancel(mk):
    app = mk(_slow_run)
    async with _client(app) as c:
        jid = (await c.post("/core/v1/tasks", headers=USER, json={"text": "hosszú munka"})).json()["id"]
        await asyncio.sleep(0.05)
        assert (await c.post(f"/core/v1/tasks/{jid}/pause", headers=USER)).json()["task"]["state"] == "paused"
        assert (await c.post(f"/core/v1/tasks/{jid}/resume", headers=USER)).json()["ok"] is True
        await asyncio.sleep(0.05)
        r = (await c.post(f"/core/v1/tasks/{jid}/cancel", headers=USER)).json()
        assert r["task"]["state"] == "cancelled" and r["task"]["attempts"] == 2
        assert (await c.post(f"/core/v1/tasks/{jid}/resume", headers=USER)).json()["ok"] is False  # terminal


async def test_restart_marks_running_as_interrupted(store):
    jid = store.create_job("task", {"text": "x", "owner": "o"})
    store.update_job(jid, state="running")
    TaskManager(store, _fake_run)
    assert store.get_job(jid)["state"] == "interrupted"


async def test_task_goal_goes_through_privacy_gate(mk):
    app = mk(_fake_run)
    async with _client(app) as c:
        r = await c.post("/core/v1/tasks", headers=USER, json={"text": "Teszt Elek, 1990.01.01 adatait írd ki"})
    assert r.status_code == 422


async def test_adjacent_deltas_are_merged(store):
    async def run(payload):
        for w in ("a", "b", "c"):
            yield AskEvent("delta", {"text": w})
        yield AskEvent("done", {"outcome": "answered"})

    tm = TaskManager(store, run)
    jid = tm.start({"text": "x"}, "u1")
    await tm.live[jid].task
    evs = [e async for e in tm.follow(jid)]
    assert [e["type"] for e in evs] == ["step", "delta", "done"] and evs[1]["data"]["text"] == "abc"


async def test_resume_continues_the_project_run_at_its_checkpoint(store):
    seen = []

    async def run(payload):
        seen.append(payload.get("resume_run_id"))
        yield AskEvent("route", {"level": 2, "model": "m", "mode": "code", "lang": "hu", "run_id": "proj_abc123"})
        if len(seen) == 1:
            yield AskEvent("error", {"kind": "paused", "message": "megszakítva"})
        else:
            yield AskEvent("done", {"outcome": "pass"})

    tm = TaskManager(store, run)
    jid = tm.start({"text": "projekt", "mode": "project"}, "u1")
    await tm.live[jid].task
    assert tm.get(jid, "u1")["state"] == "paused" and tm.resume(jid, "u1")
    await tm.live[jid].task
    assert seen == [None, "proj_abc123"] and tm.get(jid, "u1")["state"] == "done"
