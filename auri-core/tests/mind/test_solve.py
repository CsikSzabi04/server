"""solve() with fakes only — no Ollama, no sandbox (06/05 §9, 01/02 §8)."""

from auri_core.contracts import EndState, InfrastructureError, Priority, SolveOptions
from auri_core.fakes import FakeLLM, FakeSandbox, FakeScheduler, FakeStore, make_run, make_task
from auri_core.solve import load_prompts, pick_solution, solve, task_signature

TESTS = {"tests/test_visible.py": "from solution import double\n\ndef test_ok():\n    assert double(2) == 4\n"}
GOOD = "def double(n: int) -> int:\n    return n * 2\n"


def sol(code: str = GOOD, path: str = "solution.py") -> dict:
    return {"approach": "x", "files": [{"path": path, "content": code}]}


def fail(name: str = "test_ok", msg: str = "AssertionError: assert 3 == 4"):
    return make_run("fail", failing=[(name, msg)])


async def run(replies, script, *, store=None, task=None, opts=None, tmp_path=None):
    sch = FakeScheduler()
    llm = FakeLLM(replies, scheduler=sch)  # asserts every call is inside a lease
    sb = FakeSandbox(script)
    out = await solve(task or make_task(), llm=llm, sandbox=sb, store=store, scheduler=sch, opts=opts,
                      visible=TESTS, runs_dir=tmp_path)
    return out, llm, sb, sch


async def test_green_first_try_is_stored(tmp_path):
    store = FakeStore()
    out, llm, sb, sch = await run([sol()], ["pass"], store=store, tmp_path=tmp_path)
    assert out.kind == "pass" and out.end_state == EndState.DONE and out.rounds == 0
    assert out.files == {"solution.py": GOOD} and out.snippet_id and len(store.solutions) == 1
    assert sb.calls[0]["tests"] == TESTS and set(sb.calls[0]["files"]) == {"solution.py"}
    assert all(lease.prio == Priority.TASK for lease in sch.leases)
    assert (tmp_path / out.run_id / "journal.jsonl").exists()


async def test_second_time_from_memory_zero_llm_calls():
    store = FakeStore()
    await run([sol()], ["pass"], store=store)
    out, llm, *_ = await run([], ["pass"], store=store)
    assert out.kind == "pass" and out.from_memory and out.llm_calls == 0 and llm.calls == []
    assert store.uses[-1][2] is True


async def test_repairs_then_green_learns_error_pattern():
    store = FakeStore()
    out, llm, *_ = await run([sol("x"), sol("y"), sol()],
                             [fail(msg="NameError: name 'a' is not defined"), fail(), "pass"], store=store)
    assert out.kind == "pass" and out.rounds == 2 and out.llm_calls == 3
    assert "<ellenorzes>" in llm.calls[1]["messages"][-1]["content"]
    assert len(llm.calls[2]["messages"]) == 6  # appended, same system prompt (KV-cache friendly)
    assert len(store.errors) == 1


async def test_gives_up_after_three_rounds():
    msgs = [f"AssertionError: assert {i} == 4" for i in range(4)]
    out, llm, sb, _ = await run([sol(f"v{i}") for i in range(4)], [fail(msg=m) for m in msgs], store=FakeStore())
    assert out.kind == "give_up" and out.end_state == EndState.GIVE_UP and out.rounds == 3
    assert len(sb.calls) == 4 and out.reason_hu


async def test_no_progress_regenerates_once_then_gives_up():
    out, llm, *_ = await run([sol("a"), sol("b"), sol("c")], [fail(), fail(), fail()])
    assert out.kind == "give_up" and out.no_progress
    assert "No progress" in llm.calls[2]["messages"][-1]["content"]
    assert llm.calls[1]["temperature"] == 0.0 and llm.calls[2]["temperature"] == 0.7
    regen = llm.calls[2]["messages"]
    assert [m["role"] for m in regen] == ["system", "user"] and "double(n)" in regen[1]["content"]  # clean context


async def test_model_only_mode_no_repair():
    out, llm, *_ = await run([sol("x")], [fail()], opts=SolveOptions(repair_rounds=0))
    assert out.kind == "give_up" and out.rounds == 0 and len(llm.calls) == 1


async def test_dev_split_is_not_learned():
    store = FakeStore()
    out, *_ = await run([sol()], ["pass"], store=store, task=make_task(split="dev"))
    assert out.kind == "pass" and store.solutions == {}


async def test_invalid_json_gets_one_fix_request():
    out, llm, *_ = await run(["not json", sol()], ["pass"])
    assert out.kind == "pass" and len(llm.calls) == 2
    assert llm.calls[1]["messages"][-1]["content"] == "Output only valid JSON for the schema."


async def test_model_cannot_change_tests():
    reply = {"files": [{"path": "tests/test_visible.py", "content": "def test_ok(): pass"},
                       {"path": "solution.py", "content": GOOD}]}
    out, llm, sb, _ = await run([reply], ["pass"])
    assert out.kind == "pass" and sb.calls[0]["tests"] == TESTS and set(sb.calls[0]["files"]) == {"solution.py"}


async def test_infrastructure_error_and_preemption():
    out, *_ = await run([sol()], [InfrastructureError("sandbox down")])
    assert out.kind == "give_up" and out.reason_hu.startswith("infrastruktúra")
    sch = FakeScheduler()
    sch.preempt_next = True
    o2 = await solve(make_task(), llm=FakeLLM([sol()], scheduler=sch), sandbox=FakeSandbox(["pass"]), store=None,
                     scheduler=sch, visible=TESTS)
    assert o2.end_state == EndState.PAUSED and o2.kind == "give_up"


async def test_privacy_rejection_does_not_break_pass():
    out, *_ = await run([sol()], ["pass"], store=FakeStore(reject=lambda t: True))
    assert out.kind == "pass" and out.snippet_id is None


def test_pick_solution_and_signature():
    assert pick_solution({"files": [{"path": "x/solution.py", "content": GOOD}]}, "solution.py")[0] == GOOD
    assert pick_solution({"files": [{"path": "solution.py", "content": "# rest unchanged"}]}, "solution.py")[0] is None
    assert pick_solution("nope", "solution.py") == (None, [])
    assert task_signature(make_task()) == task_signature(make_task(id="other"))  # same task text → same key


def test_prompts_load_and_render():
    for lang in ("en", "hu"):
        p = load_prompts(lang)
        assert {"system", "generate", "repair", "regenerate", "json_fix"} <= set(p.sections)
        assert p.version.startswith(f"code.{lang}:")
        assert "{{" not in p.render("repair", solution_file="solution.py", feedback="f")


async def test_truncated_reply_gets_no_json_fix():
    from auri_core.contracts import LLMReply, LLMStats

    cut = LLMReply('{"files": [{"path": "solution.py", "content": "def d', LLMStats(done_reason="length"))
    out, llm, *_ = await run([cut, sol()], ["pass"])
    assert out.kind == "pass" and len(llm.calls) == 2
    assert "Output only valid JSON" not in llm.calls[1]["messages"][-1]["content"]
    assert llm.calls[0]["num_predict"] == 400 * 2 + 200


async def test_cut_off_garbage_leaves_the_context():
    from auri_core.contracts import LLMReply, LLMStats
    from auri_core.solve import GARBAGE, LOOP_VERSION

    loop = LLMReply('{"files": [{"path": "solution.py", "content": "aaaa' + "a" * 50, LLMStats(done_reason="length"))
    out, llm, *_ = await run([loop, sol()], ["pass"])
    assert out.kind == "pass" and llm.calls[1]["messages"][2] == {"role": "assistant", "content": GARBAGE}
    assert out.prompt_ver.endswith("+" + LOOP_VERSION)


class _Router:
    """Measured-router double: L2 model fails, the stats say L3 is better."""

    last_reason = ""

    def code_model(self, task):
        return "m2", "test"

    def pick(self, kind, lang, level, *, tier):
        return ("m3", "mérve jobb") if tier == 3 else ("m2", "")

    def escalate(self, level, failure, **kw):
        self.seen = (level, failure, kw)
        self.last_reason = "L2 bukott → L3"
        return 3


async def test_escalates_once_to_the_measured_l3_model():
    sch, r = FakeScheduler(), _Router()
    llm = FakeLLM([sol("x"), sol()], scheduler=sch)
    events = []
    out = await solve(make_task(), llm=llm, sandbox=FakeSandbox([fail(), "pass"]), store=None, scheduler=sch,
                      opts=SolveOptions(repair_rounds=0), visible=TESTS, router=r,
                      on_event=lambda e, d: events.append(e))
    assert out.kind == "pass" and out.model == "m3" and [c["model"] for c in llm.calls] == ["m2", "m3"]
    assert r.seen[0] == 2 and r.seen[1].kind == "tests_failed" and "escalate" in events


async def test_no_escalation_when_the_model_is_fixed():
    sch = FakeScheduler()
    out = await solve(make_task(), llm=FakeLLM([sol("x")], scheduler=sch), sandbox=FakeSandbox([fail()]), store=None,
                      scheduler=sch, opts=SolveOptions(repair_rounds=0, model="m2"), visible=TESTS, router=_Router())
    assert out.kind == "give_up" and out.model == "m2"


async def test_prompt_variant_v2_is_opt_in():
    from auri_core.solve import load_prompts

    for lang in ("en", "hu"):
        v1, v2 = load_prompts(lang), load_prompts(lang, variant="v2")
        assert v2.version.startswith(f"code.{lang}.v2:") and v1.version.startswith(f"code.{lang}:")
        assert v1.sections["system"] == v2.sections["system"]  # same KV-cache prefix
        assert v2.sections["generate"] != v1.sections["generate"]
    assert "EXAMPLES" in load_prompts("en", variant="v2").sections["generate"]
    out, llm, *_ = await run([sol()], ["pass"], opts=SolveOptions(prompt_variant="v2"))
    assert out.prompt_ver.startswith("code.en.v2:") and "EXAMPLES" in llm.calls[0]["messages"][1]["content"]
    out, *_ = await run([sol()], ["pass"])
    assert out.prompt_ver.startswith("code.en:")
