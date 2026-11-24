"""AI-3 P1 server tests: Host/Origin/token gate, SSE /ask, /activity preempts background work."""

from __future__ import annotations

import httpx
import pytest

from auri_core.fakes import FakeScheduler, FakeStreamLLM
from auri_core.scheduler import Priority, Scheduler
from auri_core.server import create_app, load_or_create_token

TOKEN = "t" * 40
BASE = "http://127.0.0.1:8791"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE)


@pytest.fixture
def app(cfg):
    sched = FakeScheduler()
    return create_app(cfg, token=TOKEN, llm=FakeStreamLLM(["Szia, itt Auri."], scheduler=sched), scheduler=sched)


async def test_gate_host_origin_token(app):
    async with _client(app) as c:
        assert (await c.get("/core/v1/health")).status_code == 401
        assert (await c.get("/core/v1/health", headers={"Authorization": "Bearer rossz"})).status_code == 401
        assert (await c.get("/core/v1/health", headers={**AUTH, "Host": "evil.example:8791"})).status_code == 403
        assert (await c.get("/core/v1/health", headers={**AUTH, "Origin": "https://evil.example"})).status_code == 403
        r = await c.get("/core/v1/health", headers={**AUTH, "Origin": "http://localhost:5173"})
        assert r.status_code == 200 and r.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert r.json()["lane"]["busy"] is False
        pre = await c.options("/core/v1/ask", headers={"Origin": "http://localhost:5173"})
        assert pre.status_code == 204


async def test_ask_streams_sse(app):
    async with _client(app) as c:
        r = await c.post("/core/v1/ask", headers=AUTH, json={"text": "szia", "mode": "chat"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    types = [ln[7:] for ln in r.text.splitlines() if ln.startswith("event: ")]
    assert types[0] == "route" and types[-1] == "done" and "delta" in types
    assert "Auri" in r.text


async def test_ask_validation(app):
    async with _client(app) as c:
        assert (await c.post("/core/v1/ask", headers=AUTH, json={"text": "x" * 8001})).status_code == 422


async def test_activity_preempts_background(cfg):
    sched = Scheduler()
    app = create_app(cfg, token=TOKEN, llm=FakeStreamLLM([]), scheduler=sched)
    async with _client(app) as c, sched.lease(Priority.BACKGROUND, "m") as bg:
        r = await c.post("/core/v1/activity", headers=AUTH, json={"source": "jarvis"})
        assert r.json()["preempted"] is True and bg.preempt.is_set() and sched.user_active()


def test_token_file_stable(tmp_path):
    a = load_or_create_token(tmp_path)
    assert len(a) >= 32 and load_or_create_token(tmp_path) == a


async def test_recall_only_verified_with_sources(cfg, store):
    prov = [{"relation": "derived_from", "ref_type": "seed", "ref_id": "knowledge.ts#lista"}]
    await store.put({"title": "lista rendezése", "body": "sorted() új listát ad", "status": "verified"}, prov)
    await store.put({"title": "lista hipotézis", "body": "talán gyorsabb"}, prov)
    app = create_app(cfg, token=TOKEN, llm=FakeStreamLLM([]), scheduler=FakeScheduler(), store=store)
    async with _client(app) as c:
        items = (await c.post("/core/v1/recall", headers=AUTH, json={"query": "lista"})).json()["items"]
        assert [i["title"] for i in items] == ["lista rendezése"]
        assert items[0]["sources"][0]["ref_id"] == "knowledge.ts#lista"
        assert (await c.post("/core/v1/recall", headers=AUTH, json={"query": ""})).status_code == 422
        assert (await c.get("/core/v1/stats", headers=AUTH)).json()["counts"]["knowledge_items"] == 2


async def test_background_ask_yields_lane_on_activity(cfg):
    import asyncio

    from auri_core.ask import ask
    from auri_core.contracts import AskRequest

    sched = Scheduler()

    class SlowLLM:
        async def chat_stream(self, lease, messages, **kw):
            from auri_core.fakes import FakeChunk

            for _ in range(1000):
                await asyncio.sleep(0.005)
                yield FakeChunk("szó ")

    llm = SlowLLM()
    app = create_app(cfg, token=TOKEN, llm=llm, scheduler=sched)
    events: list[str] = []

    async def bg():
        async for ev in ask(AskRequest(text="hosszú", priority=Priority.BACKGROUND), llm=llm, scheduler=sched):
            events.append(ev.data.get("kind", ev.type) if ev.type == "error" else ev.type)

    task = asyncio.create_task(bg())
    while events.count("delta") < 3:
        await asyncio.sleep(0.005)
    async with _client(app) as c:
        assert (await c.post("/core/v1/activity", headers=AUTH, json={"source": "jarvis"})).json()["preempted"] is True
    await asyncio.wait_for(task, 1)
    assert events[-1] == "paused" and sched.holder is None


async def test_recall_prompt_block_and_stats_router(cfg, store):
    prov = [{"relation": "derived_from", "ref_type": "seed", "ref_id": "knowledge.ts#rekurzio"}]
    await store.put({"title": "rekurzió", "body": "a függvény önmagát hívja", "status": "verified"}, prov)
    app = create_app(cfg, token=TOKEN, llm=FakeStreamLLM([]), scheduler=FakeScheduler(), store=store)
    async with _client(app) as c:
        r = (await c.post("/core/v1/recall", headers=AUTH, json={"query": "rekurzió"})).json()
        assert "rekurzió" in r["prompt_block"] and r["withheld"] == 0
        assert isinstance((await c.get("/core/v1/stats", headers=AUTH)).json().get("router"), list)
