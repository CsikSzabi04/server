"""AI-3 P1: guest vs signed-in (T0/T1), /learn, /feedback, /import/brain-state, account delete."""

from __future__ import annotations

import dataclasses
import json

import httpx
import pytest

from auri_core.fakes import FakeScheduler, FakeStreamLLM
from auri_core.server import create_app
from auri_core.server.identity import Verifier

TOKEN = "t" * 40
AUTH = {"Authorization": f"Bearer {TOKEN}"}
USER = {**AUTH, "X-Auri-User": "good-access-token"}
SEED = [{"relation": "derived_from", "ref_type": "seed", "ref_id": "knowledge.ts#lista"}]


def _supabase() -> httpx.MockTransport:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/auth/v1/user" and req.headers.get("authorization") == "Bearer good-access-token":
            return httpx.Response(200, json={"id": "00000000-0000-4000-8000-000000000001"})
        return httpx.Response(401, json={"msg": "bad jwt"})
    return httpx.MockTransport(handler)


@pytest.fixture
def setup(cfg, store, tmp_path):
    cfg = dataclasses.replace(cfg, supabase_url="https://example.supabase.co", supabase_anon_key="anon",
                              users_dir=tmp_path / "users", runs_dir=tmp_path / "runs")
    sched = FakeScheduler()
    app = create_app(cfg, token=TOKEN, llm=FakeStreamLLM(["Szia."] * 3, scheduler=sched), scheduler=sched, store=store,
                     verifier=Verifier(cfg, transport=_supabase()))
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8791")
    return cfg, store, client


async def test_guest_reads_t0_only_and_writes_nothing(setup):
    cfg, store, c = setup
    await store.put({"title": "lista rendezése", "body": "sorted()", "status": "verified"}, SEED)
    async with c:
        assert (await c.get("/core/v1/whoami", headers={**AUTH, "X-Auri-User": "bad"})).json()["guest"] is True
        assert (await c.post("/core/v1/learn", headers=AUTH, json={"title": "x", "body": "y"})).status_code == 403
        assert (await c.post("/core/v1/feedback", headers=AUTH, json={"item_id": "x", "verdict": "good"})).status_code == 403
        r = await c.post("/core/v1/ask", headers=AUTH, json={"text": "szia"})
        assert "event: done" in r.text
        items = (await c.post("/core/v1/recall", headers=AUTH, json={"query": "lista"})).json()["items"]
        assert [i["tier"] for i in items] == ["T0"]
    assert not cfg.users_dir.exists() and not cfg.runs_dir.exists()  # no disk write after a guest round


async def test_learn_goes_to_own_t1_as_hypothesis_and_is_not_seen_by_guest(setup):
    cfg, _store, c = setup
    async with c:
        r = await c.post("/core/v1/learn", headers=USER, json={"title": "lista tipp", "body": "a list.sort() helyben rendez"})
        assert r.json()["tier"] == "T1" and r.json()["status"] == "hypothesis"
        own = (await c.post("/core/v1/recall", headers=USER, json={"query": "lista"})).json()["items"]
        assert own and own[0]["tier"] == "T1"
        assert (await c.post("/core/v1/recall", headers=AUTH, json={"query": "lista"})).json()["items"] == []
        bad = await c.post("/core/v1/learn", headers=USER, json={"title": "én", "body": "Teszt Elek, 1990.01.01"})
        assert bad.status_code == 422
    assert len(list(cfg.users_dir.glob("*.db"))) == 1
    assert "00000000" not in next(cfg.users_dir.glob("*.db")).name  # file name is a hash, not the user id


async def test_feedback_t0_trust_and_t1_confirm(setup):
    _cfg, store, c = setup
    kid = await store.put({"title": "t", "body": "b", "status": "verified", "trust": 0.7}, SEED)
    async with c:
        assert (await c.post("/core/v1/feedback", headers=USER, json={"item_id": kid, "verdict": "good"})).json()["tier"] == "T0"
        r = await c.post("/core/v1/feedback", headers=USER, json={"item_id": kid, "verdict": "fix", "correction": "inkább így"})
        assert r.json()["correction_id"]
        lid = (await c.post("/core/v1/learn", headers=USER, json={"title": "saját", "body": "jegyzet"})).json()["id"]
        assert (await c.post("/core/v1/feedback", headers=USER, json={"item_id": lid, "verdict": "good"})).json()["tier"] == "T1"
        assert (await c.post("/core/v1/feedback", headers=USER, json={"item_id": "nincs", "verdict": "good"})).status_code == 404
    row = store.db.execute("SELECT status, trust FROM knowledge_items WHERE id=?", (kid,)).fetchone()
    assert row[0] == "contested" and abs(row[1] - 0.7) < 1e-9  # +0.05 then -0.05; one user only contests T0


async def test_import_brain_state_filters_personal(setup):
    cfg, _store, c = setup
    state = {"vocab": {}, "transitions": {}, "trainSteps": 1, "updatedAt": "",
             "qa": [{"q": "mi a rekurzió", "a": "amikor egy függvény önmagát hívja", "keys": []},
                    {"q": "ki vagyok", "a": "Teszt Elek, 1990.01.01", "keys": []}, {"q": "", "a": "x", "keys": []}]}
    async with c:
        assert (await c.post("/core/v1/import/brain-state", headers=AUTH, json={"state": state})).status_code == 403
        r = (await c.post("/core/v1/import/brain-state", headers=USER, json={"state": state})).json()
        assert (r["added"], r["dropped"], r["skipped"]) == (1, 1, 1)
        assert (await c.delete("/core/v1/account", headers=USER)).json()["deleted"] is True
    assert list(cfg.users_dir.glob("*.db")) == []
    assert "Teszt Elek" not in json.dumps(r)
