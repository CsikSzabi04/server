"""P3 debate protocol (02/02): check first, critique only where needed, a rule decides. Fakes only."""

from auri_core.contracts import EndState
from auri_core.fakes import FakeLLM, FakeSandbox, FakeScheduler, make_run, make_task
from auri_core.roles import DebateState, RolesConfig, RoleSession, debate_code, debate_text, decide, schemas, teach_from
from auri_core.roles.turns import Issue

TESTS = {"tests/test_visible.py": "import unittest\nfrom solution import double\n"}
GOOD = "def double(n: int) -> int:\n    return n * 2\n"
BAD = "def double(n: int) -> int:\n    return n + 1\n"
KERDEZO_OK = {"goal": "double", "subquestions": [{"q": "ints?", "why": "w", "source": "store"}], "unknowns": [],
              "ask_user": None}
BLOCK = Issue("K1", "blocking", "solution.py:2", "wrong", "AssertionError")


def prop(code=GOOD):
    return {"approach": "a", "files": [{"path": "solution.py", "content": code}]}


def rev(code=GOOD, addresses=("K1",)):
    return {"addresses": list(addresses), "rejected": [], "files": [{"path": "solution.py", "content": code}]}


def crit(*issues, verdict="revise"):
    return {"verdict": verdict, "issues": [dict(id=i, severity="blocking", where="solution.py:2", problem="p",
                                                evidence="AssertionError: 3 != 4") for i in issues]}


def red(msg="AssertionError: 3 != 4 : double(2)"):
    return make_run("fail", failing=[("test_ok", msg)])


def unclear():
    return make_run("error", phase="test", stderr="")  # no failing test, no message: the cause is unclear


async def run(replies, script, **cfg):
    sch = FakeScheduler()
    llm = FakeLLM(replies, scheduler=sch)
    sb = FakeSandbox(script)
    out = await debate_code(make_task(), llm=llm, sandbox=sb, scheduler=sch,
                            cfg=RolesConfig(enabled=True, **cfg), visible=TESTS)
    return out, llm, sb


def test_decide_rules():
    s = DebateState("code", "interactive", max_rounds=1)
    s.check_passed = True
    assert decide(s) == "accept"
    s.blocking = [BLOCK]
    assert decide(s) == "continue"
    s.round = 1
    assert decide(s) == "ask_help"
    s.mode = "idle"
    assert decide(s) == "give_up"
    t = DebateState("text", "idle", critique_verdict="accept")
    assert decide(t) == "accept"
    b = DebateState("code", "idle", budget_exhausted=True, check_passed=False)
    assert decide(b) == "ask_help"
    o = DebateState("code", "idle", check_passed=False, hashes=["a", "b", "a"], signatures=["x", "y", "z"])
    assert decide(o) == "give_up"  # A → B → A
    same = DebateState("code", "idle", check_passed=False, hashes=["a", "b"], signatures=["x", "x"], last_similarity=0.97)
    assert decide(same) == "give_up"
    moved = DebateState("code", "idle", check_passed=False, hashes=["a", "b"], signatures=["x", "y"], last_similarity=0.97)
    assert decide(moved) == "continue"  # a small change that changed the failure is progress


async def test_green_first_try_interactive_is_one_call():
    out, llm, sb = await run([prop()], ["pass"])
    assert out.verdict == "accept" and out.verified and out.end_state == EndState.DONE
    assert len(llm.calls) == 1 and out.files == {"solution.py": GOOD} and sb.calls[0]["tests"] == TESTS


async def test_clear_failure_skips_the_critic_interactively():
    out, llm, _ = await run([prop(BAD), rev(GOOD, ["T:test_ok"])], [red(), "pass"])
    assert out.verdict == "accept" and out.rounds == 1 and out.critiques == []
    assert [c["format"] for c in llm.calls] == [schemas.GONDOLKODO, schemas.GONDOLKODO_REVISE]
    assert "T:test_ok" in llm.calls[1]["messages"][-1]["content"]


async def test_idle_mode_runs_kerdezo_and_critic_on_unclear_failure():
    out, llm, _ = await run([KERDEZO_OK, prop(BAD), crit("K1"), rev(GOOD)], [unclear(), "pass"], mode="idle")
    assert out.verdict == "accept" and out.understanding.goal == "double"
    assert [c["format"] for c in llm.calls] == [schemas.KERDEZO, schemas.GONDOLKODO, schemas.KRITIKUS,
                                                schemas.GONDOLKODO_REVISE]
    revise_msg = llm.calls[3]["messages"][-1]["content"]
    assert "K1 [blocking] solution.py:2" in revise_msg and "goal: double" in llm.calls[1]["messages"][-1]["content"]


async def test_clarifying_question_stops_before_any_code():
    ask = {**KERDEZO_OK, "ask_user": {"question": "Python vagy TypeScript?", "options": ["Python", "TypeScript"],
                                      "default": "Python"}}
    out, llm, sb = await run([ask], [], use_kerdezo="always")
    assert out.verdict == "ask_help" and out.end_state == EndState.ASK_USER
    assert out.user_question.default == "Python" and len(llm.calls) == 1 and sb.calls == []


async def test_never_done_without_green_and_honest_ask_help():
    out, llm, _ = await run([prop(BAD), rev("def double(n):\n    return n - 1\n", ["T:test_ok"])],
                            [red(), red("AssertionError: 1 != 4 : double(2)")])
    assert out.verdict == "ask_help" and not out.verified and out.end_state == EndState.ASK_USER
    assert out.rounds == 1 and out.reason_hu


async def test_critic_on_green_then_regression_reverts_to_last_green():
    out, llm, _ = await run([prop(GOOD), crit("K1"), rev(BAD), crit("K2")],
                            ["pass", red()], mode="idle", critic_on_green=True, max_rounds=1,
                            use_kerdezo="never")
    assert out.verdict == "accept" and out.reverted_to_green and out.verified
    assert out.files == {"solution.py": GOOD} and out.last_run.ok


async def test_rejecting_a_green_critique_with_reason_accepts():
    reject = {"addresses": [], "rejected": [{"id": "K1", "reason": "the green tests contradict it"}], "files": []}
    out, *_ = await run([prop(GOOD), crit("K1"), reject], ["pass"], mode="idle", critic_on_green=True,
                        use_kerdezo="never")
    assert out.verdict == "accept" and out.rejected[0]["id"] == "K1" and out.verified


async def test_oscillation_gives_up_and_preemption_pauses():
    out, *_ = await run([prop(BAD), rev(GOOD + "#b\n", []), rev(BAD, [])],
                        [red(), red("AssertionError: 9 != 4 : double(2)"), red("AssertionError: 7 != 4")],
                        mode="idle", use_kritikus="never", use_kerdezo="never")
    assert out.verdict == "give_up" and out.rounds == 2
    sch = FakeScheduler()
    sch.preempt_next = True
    o2 = await debate_code(make_task(), llm=FakeLLM([prop()], scheduler=sch), sandbox=FakeSandbox(["pass"]),
                           scheduler=sch, cfg=RolesConfig(enabled=True), visible=TESTS)
    assert o2.verdict == "paused" and o2.end_state == EndState.PAUSED and not o2.verified


async def test_debate_text_accepts_only_an_evidence_free_critique():
    draft = {"approach": "Use a dict.", "steps": ["count"], "assumptions": []}
    sch = FakeScheduler()
    llm = FakeLLM([draft, crit("K1"), draft | {"approach": "Use collections.Counter."}, crit(verdict="accept")],
                  scheduler=sch)
    out = await debate_text("Hogyan számoljak szavakat?", llm=llm, scheduler=sch, cfg=RolesConfig(enabled=True, mode="idle"))
    assert out.verdict == "accept" and not out.verified and out.approach == "Use collections.Counter."
    assert "K1 [blocking]" in llm.calls[2]["messages"][-1]["content"]


async def test_teach_from_uses_the_real_evidence():
    out, *_ = await run([prop()], ["pass"])
    sch = FakeScheduler()
    card = {"title": "t", "lesson_en": "l", "lesson_hu": "l", "when_applies": "w", "snippet": None, "tags": [],
            "evidence": "unverified"}
    s = RoleSession(FakeLLM([card], scheduler=sch), sch, cfg=RolesConfig(enabled=True))
    c = await teach_from(s, out)
    assert c.evidence == "tests_passed"
