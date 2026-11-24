"""AI-3 (BODY) tests: CLI, config, scheduler gate, llm gate, privacy gate, store rules."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from auri_core import __main__ as cli
from auri_core import privacy
from auri_core.llm import OllamaClient
from auri_core.scheduler import LeaseError, Priority, Scheduler
from auri_core.store import StoreError, task_signature


# ── CLI / config ──────────────────────────────────────────────────────────────
def test_cli_help_and_unknown(capsys):
    assert cli.main([]) == 0
    assert cli.main(["nope"]) == 2


def test_cli_missing_module_is_isolated(monkeypatch):
    monkeypatch.setitem(cli.COMMANDS, "ghost", ("auri_core.does_not_exist", "main", ""))
    assert cli.main(["ghost"]) == 3
    assert cli.main(["config"]) == 0


def test_config_env_override(cfg):
    assert cfg.db_path.name == "core.db" and cfg.db_path.parent == cfg.data_dir
    assert cfg.server_host == "127.0.0.1" and cfg.server_port == 8791
    assert "Auri" in str(cfg.sandbox_runs_dir)


# ── scheduler ─────────────────────────────────────────────────────────────────
async def test_priority_order_voice_first():
    s = Scheduler()
    order: list[str] = []

    async def job(p, name):
        async with s.lease(p, "m"):
            order.append(name)
            await asyncio.sleep(0)

    async with s.lease(Priority.BACKGROUND, "m") as first:
        tasks = [asyncio.create_task(job(Priority.BACKGROUND, "bg")), asyncio.create_task(job(Priority.TASK, "task"))]
        await asyncio.sleep(0)
        tasks.append(asyncio.create_task(job(Priority.VOICE, "voice")))
        await asyncio.sleep(0)
        assert first.preempt.is_set()
        assert s.user_active()
    await asyncio.gather(*tasks)
    assert order == ["voice", "task", "bg"]


async def test_cancelled_waiter_does_not_block():
    s = Scheduler()
    async with s.lease(Priority.TASK, "m"):
        t = asyncio.create_task(s.lease(Priority.TASK, "m").__aenter__())
        await asyncio.sleep(0)
        t.cancel()
    async with s.lease(Priority.TASK, "m") as lz:
        assert lz.active


# ── llm: no call without a lease ──────────────────────────────────────────────
def _mock_ollama(calls: list):
    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(json.loads(req.content))
        lines = [{"message": {"content": '{"a": 1}'}, "done": False},
                 {"message": {"content": ""}, "done": True, "eval_count": 3, "eval_duration": 1_000_000, "model": "m"}]
        return httpx.Response(200, text="\n".join(json.dumps(x) for x in lines))
    return httpx.MockTransport(handler)


async def test_llm_requires_active_lease(cfg):
    calls: list = []
    client = OllamaClient(cfg, transport=_mock_ollama(calls))
    s = Scheduler()
    async with s.lease(Priority.TASK, "m") as lz:
        data, res = await client.chat_json(lz, [{"role": "user", "content": "x"}], options={"num_thread": 4})
    assert data == {"a": 1} and res.stats.eval_tokens == 3
    assert calls[0]["model"] == "m" and calls[0]["format"] == "json" and calls[0]["options"]["num_thread"] == 4
    with pytest.raises(LeaseError):  # lease released → refused before any I/O
        await client.chat(lz, [{"role": "user", "content": "x"}])
    assert len(calls) == 1 and client.stats.calls == 1
    await client.aclose()


def test_only_llm_module_talks_to_ollama():
    """Gate check: no other auri_core module calls the Ollama HTTP API directly."""
    from pathlib import Path

    pkg = Path(cli.__file__).parent
    offenders = [p.name for p in pkg.rglob("*.py") if p.name != "llm.py" and ("/api/chat" in p.read_text("utf-8") or "/api/generate" in p.read_text("utf-8"))]
    assert offenders == []


# ── privacy ───────────────────────────────────────────────────────────────────
def test_fictional_person_rejected():
    assert privacy.is_personal("Teszt Elek, 1990.01.01")
    assert privacy.is_personal("my name is Teszt Elek")
    assert not privacy.is_personal("A list comprehension rövidebb, mint a for ciklus.")
    assert not privacy.is_personal("assert f(1000000) == 1000001", kind="code")


def test_fake_api_key_masked():
    fake = "sk-test" + "A1b2C3d4E5f6G7h8I9j0"
    out = privacy.redact(f"OPENAI_API_KEY={fake}\nx = 1")
    assert fake not in out and "x = 1" in out
    assert privacy.redact("token = get_token()", kind="code") == "token = get_token()"
    with pytest.raises(privacy.PrivacyError):
        privacy.guard({"code": f'KEY = "{fake}"'}, code_fields=("code",))


# ── store ─────────────────────────────────────────────────────────────────────
def _snippet(status="pass"):
    return {"lang": "py", "title": "add", "summary_hu": "két szám összege", "code": "def add(a, b):\n    return a + b\n",
            "tests": [{"framework": "unittest", "code": "assert add(1, 2) == 3"}],
            "source": {"kind": "own-loop", "license": "own"}, "verification": {"status": status, "runId": "run_1"}}


async def test_green_only_and_recall(store):
    sig = task_signature("py-l1-0001", "add two numbers")
    with pytest.raises(StoreError):
        await store.put_snippet(_snippet("fail"), task_sig=sig)
    sid = await store.put_snippet(_snippet(), task_sig=sig)
    hit = await store.find_snippet_for_task(sig, "py")
    assert hit and hit["id"] == sid and hit["status"] == "verified" and hit["tests"]
    assert await store.find_snippet_for_task(task_signature("other"), "py") is None


async def test_every_write_goes_through_gate(store, monkeypatch):
    seen: list = []
    real = privacy.guard
    monkeypatch.setattr(privacy, "guard", lambda f, **kw: (seen.append(f), real(f, **kw))[1])
    await store.put_snippet(_snippet(), task_sig="s")
    await store.put({"title": "t", "body": "b"}, [{"relation": "derived_from", "ref_type": "seed", "ref_id": "x"}])
    await store.record_episode({"goal": "g", "outcome": "DONE"})
    await store.put_error_pattern({"lang": "py", "signature": "E", "example": "E"})
    await store.add_lesson("l", episode_id=None, success=True)
    assert len(seen) >= 5
    with pytest.raises(privacy.PrivacyError):
        await store.record_episode({"goal": "Teszt Elek, 1990.01.01", "outcome": "DONE"})


async def test_provenance_rules(store):
    with pytest.raises(StoreError):
        await store.put({"title": "t", "body": "b"}, [])
    with pytest.raises(StoreError):
        await store.put({"title": "t", "body": "b", "status": "verified"},
                        [{"relation": "generated_by", "ref_type": "model", "ref_id": "gemma4:e2b"}])
    kid = await store.put({"title": "t", "body": "b"}, [{"relation": "generated_by", "ref_type": "model", "ref_id": "m"}])
    with pytest.raises(StoreError):
        await store.promote(kid, {"verification": "critic_ok", "ref_type": "model", "ref_id": "m"})


async def test_fts_diacritics_both_ways(store):
    prov = [{"relation": "derived_from", "ref_type": "seed", "ref_id": "s"}]
    await store.put({"title": "árvíztűrő tükörfúrógép", "body": "x"}, prov)
    await store.put({"title": "fuggveny", "body": "y"}, prov)
    assert [h.title for h in await store.search("arvizturo")] == ["árvíztűrő tükörfúrógép"]
    assert [h.title for h in await store.search("függvény")] == ["fuggveny"]


async def test_error_pattern_fix_lifts_trust(store):
    await store.put_error_pattern({"lang": "py", "signature": "TypeError: <X>", "example": "e",
                                   "fixes": [{"text_hu": "return hiányzik", "worked": 1, "failed": 0}]})
    p = await store.find_error_pattern("TypeError: <X>", "py")
    assert p and p["trust_level"] == 2


async def test_code_memory_contract_roundtrip(tmp_path):
    from auri_core.contracts import (
        ErrorFix,
        ErrorPattern,
        PatternSource,
        PrivacyRejected,
        Provenance,
        SnippetEnv,
        SnippetSource,
        SnippetTest,
        SnippetUsage,
        SnippetVerification,
        VerifiedSnippet,
    )
    from auri_core.store import open_store

    m = open_store(tmp_path / "core.db")
    snip = VerifiedSnippet(id="snip_py_add_01", lang="py", title="add", summary_hu="összeg", code="def add(a, b):\n    return a + b\n",
                           tests=[SnippetTest(framework="pytest", code="assert add(1, 2) == 3")], env=SnippetEnv(python="3.12"),
                           topics=["basics"], symbols=[], source=SnippetSource(kind="own-loop", license="own"), trust=2,
                           verification=SnippetVerification(status="pass", run_id="r1"), usage=SnippetUsage(), created_at="", updated_at="")
    await m.save_solution(snip, task_signature="sig1", prov=[Provenance("verified_by", "episode", "ep1")])
    got = await m.find_solution("sig1", "py")
    assert got and got.code == snip.code and got.tests[0].code == "assert add(1, 2) == 3" and got.trust == 2
    await m.record_use(got.id, "py-l1-0001", True)
    await m.save_error(ErrorPattern(id="e1", lang="py", signature="NameError: <X>", example="x", causes=[],
                                    fixes=[ErrorFix(text_hu="import", worked=1)], source=PatternSource(kind="own-loop", license="own"), trust=0))
    e = await m.find_error("NameError: <X>", "py")
    assert e and e.trust == 2 and e.fixes[0].worked == 1
    with pytest.raises(PrivacyRejected):
        await m.record_episode({"goal": "Teszt Elek, 1990.01.01", "outcome": "DONE"})
    m.close()


def test_migrate_idempotent(tmp_path):
    from auri_core.store import SqliteKnowledgeStore

    s = SqliteKnowledgeStore(tmp_path / "core.db")
    s.migrate()
    assert s.schema_version() == 1
    s.close()
