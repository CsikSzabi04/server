"""L4 cloud bridge (08/03) and /tasks step-level resume (P5) — fakes only (no Ollama, no network)."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

from auri_core.ask import ask
from auri_core.cloud.client import CloudAnswer, CloudRefusal
from auri_core.contracts import GUEST, AskRequest, Cancelled, InfrastructureError, Priority, Scope, SolveOptions
from auri_core.fakes import FakeLLM, FakeSandbox, FakeScheduler, FakeStore, make_run, make_task
from auri_core.l4 import CloudGate, make_gate
from auri_core.solve import solve

TESTS = {"tests/test_visible.py": "from solution import double\n\ndef test_ok():\n    assert double(2) == 4\n"}
GOOD = "def double(n: int) -> int:\n    return n * 2\n"
USER = Scope("user", "u-test-1")

_spec = importlib.util.spec_from_file_location("_ph", Path(__file__).with_name("test_ask_phases.py"))
_ph = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ph)


def sol(code: str = GOOD) -> dict:
    return {"files": [{"path": "solution.py", "content": code}]}


def answer(obj) -> CloudAnswer:
    return CloudAnswer(obj if isinstance(obj, str) else json.dumps(obj), "groq", "gpt-oss", "cloud:groq:gpt-oss")


class FakeCloud:
    def __init__(self, replies, mode: str = "ask") -> None:
        self.cfg = SimpleNamespace(cloud_mode=mode)
        self.enabled = True
        self.replies = list(replies)
        self.calls: list[dict] = []

    async def chat(self, messages, *, purpose, interactive, user_id, background=False, names=None):
        self.calls.append({"purpose": purpose, "interactive": interactive, "user_id": user_id, "n": len(messages)})
        return self.replies.pop(0)


class Router4:
    """Measured router stand-in: L2 failed, nothing stronger locally → L4."""

    def __init__(self) -> None:
        self.seen = None
        self.last_reason = "L2 bukott, nincs L3 → L4"

    def chat_model(self):
        return "m2", "teszt"

    def code_model(self, task):
        return "m2", "teszt"

    def pick(self, kind, lang, level, *, tier):
        return (None, "nincs mért L3") if tier == 3 else ("m2", "")

    def escalate(self, level, failure, **kw):
        self.seen = (level, failure, kw)
        return 4


async def run_solve(gate, *, local=None, script=None, opts=None, store=None):
    sch, events = FakeScheduler(), []
    llm = FakeLLM(local or [sol("def double(n):\n    return n + 1\n")], scheduler=sch)
    sb = FakeSandbox(script or [make_run("fail", failing=[("test_ok", "AssertionError")]), "pass"])
    out = await solve(make_task(), llm=llm, sandbox=sb, store=store, scheduler=sch,
                      opts=opts or SolveOptions(repair_rounds=0), visible=TESTS, router=Router4(),
                      on_event=lambda e, d: events.append((e, d)), cloud=gate)
    return out, llm, sb, sch, events


# ── the gate: who may send what ───────────────────────────────────────────────
def test_gate_needs_a_user_and_consent():
    c = FakeCloud([])
    assert make_gate(c, AskRequest("szia"), GUEST) is None  # guests never
    assert make_gate(None, AskRequest("szia"), USER) is None
    assert make_gate(c, AskRequest("szia"), USER).consent is False  # mode "ask": every time asked
    assert make_gate(c, AskRequest("szia", allow_cloud=True), USER).usable
    auto = FakeCloud([], mode="auto_general")
    assert make_gate(auto, AskRequest("Mi a fotoszintézis?"), USER).consent  # a general chat may go
    assert not make_gate(auto, AskRequest("javítsd", context=("def f(): ...",)), USER).consent  # own code: ask
    assert not make_gate(auto, AskRequest("írj kódot", mode="code"), USER).consent
    bg = make_gate(c, AskRequest("x", allow_cloud=True, priority=Priority.TASK), USER)
    assert bg.consent and not bg.live and not bg.usable  # long/background tasks never go to the cloud


# ── solve(): one cloud attempt, verified locally, never learned ─────────────
async def test_l4_cloud_code_is_verified_in_the_sandbox_and_not_learned():
    cloud = FakeCloud([answer(sol())])
    store = FakeStore()
    out, llm, sb, sch, events = await run_solve(CloudGate(cloud, "u-test-1", True), store=store)
    assert out.kind == "pass" and out.model == "cloud:groq:gpt-oss" and out.files["solution.py"] == GOOD
    assert len(llm.calls) == 1 and len(sch.leases) == 1  # the cloud call took no Ollama lane
    assert len(sb.calls) == 2 and sb.calls[1]["tests"] == TESTS  # the same visible tests decided
    assert cloud.calls == [{"purpose": "code", "interactive": True, "user_id": "u-test-1", "n": 2}]
    assert store.solutions == {}  # 08/03 §7: nothing from the cloud is learned
    assert ("cloud", {"ok": True, "provenance": "cloud:groq:gpt-oss"}) in events


async def test_l4_refusal_keeps_the_local_outcome_with_the_reason():
    cloud = FakeCloud([CloudRefusal("személyes adat van a kérésben, ezért nem küldöm a felhőbe", "personal")])
    out, *_ = await run_solve(CloudGate(cloud, "u-test-1", True))
    assert out.kind == "give_up" and out.model == "m2"
    assert "felhő (L4): személyes adat van a kérésben" in out.reason_hu


async def test_l4_without_consent_only_offers():
    cloud = FakeCloud([])
    out, _, sb, _, events = await run_solve(CloudGate(cloud, "u-test-1", False))
    assert out.kind == "give_up" and cloud.calls == [] and len(sb.calls) == 1
    assert ("cloud_offer", {"live": True}) in events


async def test_l4_red_cloud_code_is_not_called_green():
    cloud = FakeCloud([answer(sol("def double(n):\n    return 0\n"))])
    out, *_ = await run_solve(CloudGate(cloud, "u-test-1", True),
                              script=[make_run("fail", failing=[("test_ok", "AssertionError")]),
                                      make_run("fail", failing=[("test_ok", "AssertionError")])])
    assert out.kind == "give_up" and "a felhőben is: groq · gpt-oss" in out.reason_hu


# ── ask(): code task and chat ──────────────────────────────────────────────────
async def test_ask_code_task_marks_who_wrote_the_code():
    from auri_core.ask import _ask_task  # ask() needs a task directory for the visible tests

    sch = FakeScheduler()
    llm = FakeLLM([sol("def double(n):\n    return n + 1\n")] * 5, scheduler=sch)  # the whole local loop fails
    cloud = FakeCloud([answer(sol())])
    sb = FakeSandbox(judge=lambda f, t: "pass" if f.get("solution.py") == GOOD else
                     make_run("fail", failing=[("test_ok", "AssertionError")]))
    req = AskRequest("", mode="code", task=make_task(), allow_cloud=True)
    evs = [e async for e in _ask_task(req, req.task, llm=llm, scheduler=sch, sandbox=sb, store=None, router=Router4(),
                                      runs_dir=None, prompt_lang="en", visible=TESTS,
                                      cloud=make_gate(cloud, req, USER))]
    done = evs[-1].data
    assert done["verified"] and done["provenance"] == "cloud:groq:gpt-oss" and done["level"] == 4
    assert any(e.type == "delta" and "A kódot a felhő írta" in e.data["text"] for e in evs)


async def test_ask_chat_ollama_down_goes_to_the_cloud_with_consent():
    sch = FakeScheduler()
    cloud = FakeCloud([answer("A fotoszintézis a növények energiatermelése.")])
    req = AskRequest("Mi a fotoszintézis?", allow_cloud=True)
    evs = [e async for e in ask(req, llm=FakeLLM([InfrastructureError("ollama down")], scheduler=sch),
                                scheduler=sch, router=Router4(), scope=USER, cloud=cloud)]
    routes = [e.data["level"] for e in evs if e.type == "route"]
    assert routes == [2, 4] and evs[-1].type == "done" and evs[-1].data["provenance"] == "cloud:groq:gpt-oss"
    assert evs[-1].data["verified"] is False
    assert "fotoszintézis" in "".join(e.data["text"] for e in evs if e.type == "delta")
    assert cloud.calls[0]["purpose"] == "chat"


async def test_ask_chat_ollama_down_without_consent_or_as_guest():
    sch = FakeScheduler()
    cloud = FakeCloud([])
    evs = [e async for e in ask(AskRequest("Mi a fotoszintézis?"), llm=FakeLLM([InfrastructureError("x")], scheduler=sch),
                                scheduler=sch, router=Router4(), scope=USER, cloud=cloud)]
    assert evs[-1].type == "error" and evs[-1].data["cloud_offer"] is True and cloud.calls == []
    evs = [e async for e in ask(AskRequest("Mi a fotoszintézis?", allow_cloud=True),
                                llm=FakeLLM([InfrastructureError("x")], scheduler=sch), scheduler=sch,
                                router=Router4(), scope=GUEST, cloud=cloud)]
    assert evs[-1].type == "error" and "cloud_offer" not in evs[-1].data and cloud.calls == []


# ── /tasks resume: continue a project at the step boundary ──────────────────
async def test_project_resume_continues_after_the_last_checkpoint(tmp_path):
    def judge(files, tests):
        return "pass" if files.get("calc.py") == _ph.CALC else make_run("fail", failing=[("test_add", "ImportError")])

    sb = FakeSandbox(judge=judge)
    req = AskRequest("Írj egy add függvényt tesztekkel!", mode="code", plan=True)
    first = [_ph.plan_dict(), {"files": [{"path": "test_calc.py", "content": _ph.CALC_TESTS}]},
             Cancelled("hang jött")]
    evs, _ = await _ph.collect(req, first, sandbox=sb, store=FakeStore(), runs_dir=tmp_path)
    run_id = evs[0].data["run_id"]
    assert evs[-1].type == "error" and evs[-1].data["kind"] == "paused"

    evs, llm = await _ph.collect(req, [{"files": [{"path": "calc.py", "content": _ph.CALC}]}], sandbox=sb,
                                 store=FakeStore(), runs_dir=tmp_path, resume_run_id=run_id)
    states = [e.data.get("state") for e in evs if e.type == "step"]
    assert "RESUME" in states and "PLAN" not in states and len(llm.calls) == 1  # no re-planning, F1 not redone
    done = evs[-1].data
    assert done["outcome"] == "pass" and done["episode_id"] == run_id
    assert done["files"] == {"test_calc.py": _ph.CALC_TESTS, "calc.py": _ph.CALC}  # F1 from the checkpoint


async def test_project_resume_with_a_bad_id_starts_fresh(tmp_path):
    steps = [_ph.plan_dict(), {"files": [{"path": "test_calc.py", "content": _ph.CALC_TESTS}]},
             {"files": [{"path": "calc.py", "content": _ph.CALC}]}]
    sb = FakeSandbox(judge=lambda f, t: "pass" if f.get("calc.py") == _ph.CALC else make_run("fail", failing=[("t", "E")]))
    evs, _ = await _ph.collect(AskRequest("Írj egy add függvényt!", mode="code", plan=True), steps, sandbox=sb,
                               store=FakeStore(), runs_dir=tmp_path, resume_run_id="../../etc")
    states = [e.data.get("state") for e in evs if e.type == "step"]
    assert states[:2] == ["RESUME_FAILED", "PLAN"] and evs[-1].data["outcome"] == "pass"
