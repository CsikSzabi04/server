"""ask(): the P1 event stream, with fakes only (no Ollama, no sandbox)."""

from auri_core import ask as ask_mod
from auri_core.ask import ask
from auri_core.contracts import AskRequest, LLMReply, LLMStats, Priority
from auri_core.fakes import FakeLLM, FakeSandbox, FakeScheduler, FakeStore, FakeStreamLLM, make_run, make_task

TESTS = {"tests/test_visible.py": "from solution import double\n\ndef test_ok():\n    assert double(2) == 4\n"}
GOOD = "def double(n: int) -> int:\n    return n * 2\n"


async def collect(req, llm=None, **kw):
    sch = kw.pop("scheduler", None) or FakeScheduler()
    llm = llm or FakeStreamLLM(["Auri vagyok, a helyi asszisztensed."], scheduler=sch)
    return [e async for e in ask(req, llm=llm, scheduler=sch, **kw)], llm, sch


def types(evs):
    return [e.type for e in evs]


def task_dir(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_visible.py").write_text(TESTS["tests/test_visible.py"], encoding="utf-8")
    return str(tmp_path)


async def test_chat_streams_in_order_inside_a_chat_lease(tmp_path):
    evs, llm, sch = await collect(AskRequest("ki vagy?"), runs_dir=tmp_path)
    assert types(evs)[:2] == ["route", "step"] and types(evs)[-1] == "done"
    assert "".join(e.data["text"] for e in evs if e.type == "delta") == "Auri vagyok, a helyi asszisztensed."
    assert evs[0].data["lang"] == "hu" and "Hungarian" in llm.calls[0]["messages"][0]["content"]
    assert [lease.prio for lease in sch.leases] == [Priority.CHAT]
    done = evs[-1].data
    assert done["verified"] is False and done["outcome"] == "answered"
    assert (tmp_path / done["episode_id"] / "journal.jsonl").exists()
    assert llm.calls[0]["num_predict"] == 400


async def test_hu_prompt_variant_and_context_is_data():
    evs, llm, _ = await collect(AskRequest("what is gravity", context=("Teszt kontextus",)), prompt_lang="hu")
    sys_msg, user_msg = llm.calls[0]["messages"]
    assert "angolul" in sys_msg["content"]
    assert user_msg["content"].startswith("<context>\nTeszt kontextus\n</context>") and evs[-1].type == "done"


async def test_plain_llm_without_stream_gives_one_delta():
    sch = FakeScheduler()
    evs, *_ = await collect(AskRequest("hello"), llm=FakeLLM(["Hi."], scheduler=sch), scheduler=sch)
    assert [e.data["text"] for e in evs if e.type == "delta"] == ["Hi."]


async def test_truncated_answer_is_partial():
    sch = FakeScheduler()
    cut = LLMReply("hosszu valasz", LLMStats(done_reason="length"))
    evs, *_ = await collect(AskRequest("mesélj"), llm=FakeStreamLLM([cut], scheduler=sch), scheduler=sch)
    assert evs[-1].data["outcome"] == "partial"


async def test_preempted_lease_pauses_without_model_call():
    sch = FakeScheduler()
    sch.preempt_next = True
    llm = FakeStreamLLM(["x"], scheduler=sch)
    evs, *_ = await collect(AskRequest("szia"), llm=llm, scheduler=sch)
    assert types(evs)[-1] == "error" and evs[-1].data["kind"] == "paused" and llm.calls == []


async def test_client_disconnect_closes_the_model_stream():
    sch = FakeScheduler()
    llm = FakeStreamLLM(["egy ketto harom negy ot hat"], scheduler=sch)
    gen = ask(AskRequest("szia"), llm=llm, scheduler=sch)
    async for e in gen:
        if e.type == "delta":
            break
    await gen.aclose()
    assert llm.closed and llm.pulled < 6 and sch.holder is None


async def test_errors_are_hungarian_and_secret_free():
    class Boom(Exception):
        user_message = "az Ollama nem érhető el"

    sch = FakeScheduler()
    llm = FakeStreamLLM([Boom("C:/secret/path token=abc")], scheduler=sch)
    evs, *_ = await collect(AskRequest("szia"), llm=llm, scheduler=sch)
    assert evs[-1].data == {"kind": "infra", "message": "az Ollama nem érhető el"}
    for req, kind in [(AskRequest("  "), "bad_request"), (AskRequest("x" * 8001), "bad_request"),
                      (AskRequest("keress", mode="research"), "not_available"),
                      (AskRequest("oldd meg", mode="code", task=make_task()), "not_available")]:
        evs, llm, _ = await collect(req)
        assert types(evs) == ["error"] and evs[0].data["kind"] == kind and llm.calls == []


async def test_code_without_tests_is_never_verified():
    evs, llm, _ = await collect(AskRequest("írj egy double függvényt", mode="code"))
    assert evs[-1].data["verified"] is False
    assert "NOT tested" in llm.calls[0]["messages"][0]["content"]


async def test_code_task_runs_the_loop_as_events(tmp_path):
    sch, store = FakeScheduler(), FakeStore()
    llm = FakeLLM([{"files": [{"path": "solution.py", "content": "x"}]},
                   {"files": [{"path": "solution.py", "content": GOOD}]}], scheduler=sch)
    task = make_task(root=task_dir(tmp_path))
    sb = FakeSandbox([make_run("fail", failing=[("test_ok", "AssertionError: assert 3 == 4")]), "pass"])
    evs, *_ = await collect(AskRequest("", mode="code", task=task), llm=llm, scheduler=sch, sandbox=sb, store=store,
                            runs_dir=tmp_path / "runs")
    assert types(evs)[0] == "route" and types(evs)[-1] == "done"
    assert [e.data["ok"] for e in evs if e.type == "verify"] == [False, True]
    assert [e.data["state"] for e in evs if e.type == "step"] == ["ACT", "REPAIR", "STORE"]
    done = evs[-1].data
    assert done["verified"] and done["outcome"] == "pass" and done["files"] == {"solution.py": GOOD}
    assert any(e.type == "delta" and GOOD.strip() in e.data["text"] for e in evs)
    # second time: from memory, 0 model calls, the snippet is the source
    evs2, llm2, _ = await collect(AskRequest("", mode="code", task=task), llm=FakeLLM([], scheduler=sch),
                                  scheduler=sch, sandbox=FakeSandbox(["pass"]), store=store)
    assert evs2[-1].data["from_memory"] and evs2[-1].data["sources"] and llm2.calls == []


async def test_code_task_give_up_is_honest(tmp_path, monkeypatch):
    sch = FakeScheduler()
    llm = FakeLLM([{"files": [{"path": "solution.py", "content": "x"}]}], scheduler=sch)
    task = make_task(split="dev", root=task_dir(tmp_path))
    sb = FakeSandbox([make_run("fail", failing=[("test_ok", "AssertionError")])])
    orig = ask_mod.SolveOptions
    monkeypatch.setattr(ask_mod, "SolveOptions", lambda **kw: orig(repair_rounds=0, **kw))  # model-only
    evs, *_ = await collect(AskRequest("", mode="code", task=task), llm=llm, scheduler=sch, sandbox=sb)
    assert evs[-1].data["verified"] is False and evs[-1].data["outcome"] == "give_up"
    assert any(e.type == "delta" and e.data["text"].startswith("Nem lett zöld") for e in evs)
