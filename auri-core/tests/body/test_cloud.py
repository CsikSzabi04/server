"""AI-3 P6: cloud fallback (08/03 §8): off → no traffic; personal/secret → not sent; 429 → next; audit; breaker."""

from __future__ import annotations

import dataclasses
import json

import httpx

from auri_core.cloud import CloudAnswer, CloudClient, CloudRefusal, prepare_payload

GROQ_KEY = "gsk_" + "T3stKeyNotReal0123456789ab"
MSG = [{"role": "user", "content": r"Miért dob TypeError-t ez? C:\Users\valaki\proj\a.py, gép: PCNEV01"}]


def _cfg(cfg, **kw):
    base = {"cloud_mode": "auto_general", "groq_api_key": GROQ_KEY}
    return dataclasses.replace(cfg, **{**base, **kw})


def _transport(script: list, seen: list):
    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        kind = script.pop(0) if script else "ok"
        if kind == "429":
            return httpx.Response(429, headers={"retry-after": "2"})
        if kind == "429-long":
            return httpx.Response(429, headers={"retry-after": "3600"})
        if kind == "500":
            return httpx.Response(500, text="echo of the request")
        if "groq" in req.url.host:
            return httpx.Response(200, json={"choices": [{"message": {"content": "Hiányzik a return."}}]})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Gemini válasz"}]}}]})
    return httpx.MockTransport(handler)


async def test_off_means_zero_requests(cfg, store):
    seen: list = []
    c = CloudClient(_cfg(cfg, cloud_mode="off"), store, transport=_transport([], seen))
    r = await c.chat(MSG, purpose="t", interactive=True, user_id="u1")
    assert isinstance(r, CloudRefusal) and r.kind == "off" and seen == []
    for kw in ({"background": True}, {}):
        r = await CloudClient(_cfg(cfg), store, transport=_transport([], seen)).chat(
            MSG, purpose="t", interactive=True, user_id=None if not kw else "u1", **kw)
        assert r.kind in ("background", "guest")
    assert seen == []


async def test_personal_or_secret_not_sent(cfg, store):
    seen: list = []
    c = CloudClient(_cfg(cfg), store, transport=_transport([], seen))
    r = await c.chat([{"role": "user", "content": "Teszt Elek, 1990.01.01 — javítsd ki a kódot"}], purpose="t",
                     interactive=True, user_id="u1")
    assert r.kind == "personal" and "személyes adat" in r.reason
    r = await c.chat([{"role": "user", "content": 'API_KEY = "sk-' + 'abcdefABCDEF1234567890"'}], purpose="t",
                     interactive=True, user_id="u1")
    assert r.kind == "secret" and seen == []


def test_masking():
    pl = prepare_payload(MSG, purpose="t", host="PCNEV01")
    assert not isinstance(pl, CloudRefusal)
    assert "valaki" not in pl.text and "<HOME>" in pl.text and "<HOST>" in pl.text and pl.redactions == 2


async def test_answer_audit_and_no_key_in_log(cfg, store):
    seen: list = []
    c = CloudClient(_cfg(cfg), store, transport=_transport([], seen), host="PCNEV01")
    r = await c.chat(MSG, purpose="L4", interactive=True, user_id="u1")
    assert isinstance(r, CloudAnswer) and r.provider == "groq" and r.provenance.startswith("cloud:groq:")
    sent = json.loads(seen[0].content)
    assert "valaki" not in json.dumps(sent)
    log = c.audit_log()
    assert len(log) == 1 and "<HOME>" in log[0]["text"] and GROQ_KEY not in json.dumps(log)


async def test_429_waits_once_then_next_provider(cfg, store):
    seen: list = []
    waits: list = []

    async def sleep(s):
        waits.append(s)

    c = CloudClient(_cfg(cfg, gemini_api_key="g", gemini_paid=True), store, transport=_transport(["429", "429-long"], seen),
                    sleep=sleep, host="x")
    r = await c.chat(MSG, purpose="t", interactive=True, user_id="u1")
    assert waits == [2.0] and isinstance(r, CloudAnswer) and r.provider == "gemini"
    assert store.db.execute("SELECT exhausted_until FROM cloud_quota WHERE key='provider:groq'").fetchone()[0]
    seen.clear()
    r = await c.chat(MSG, purpose="t", interactive=True, user_id="u1")
    assert r.provider == "gemini" and all("groq" not in q.url.host for q in seen)  # groq skipped until tomorrow


async def test_gemini_free_tier_never_and_breaker(cfg, store):
    seen: list = []
    c = CloudClient(_cfg(cfg, gemini_api_key="g", gemini_paid=False), store, transport=_transport(["500"] * 3, seen), host="x")
    assert [p.name for p in c.providers] == ["groq"]
    for _ in range(3):
        assert (await c.chat(MSG, purpose="t", interactive=False, user_id="u1")).kind == "quota"
    n = len(seen)
    assert (await c.chat(MSG, purpose="t", interactive=False, user_id="u1")).kind == "quota" and len(seen) == n  # breaker open


async def test_daily_user_cap(cfg, store):
    c = CloudClient(_cfg(cfg, cloud_daily_cap=1), store, transport=_transport([], []), host="x")
    assert isinstance(await c.chat(MSG, purpose="t", interactive=True, user_id="u1"), CloudAnswer)
    assert (await c.chat(MSG, purpose="t", interactive=True, user_id="u1")).kind == "cap"
