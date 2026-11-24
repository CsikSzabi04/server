"""ask() wiring of P2 research, P3 TESZTELO and P5 planner — fakes only (no Ollama, no network)."""

import importlib.util
from pathlib import Path

from auri_core.ask import ask
from auri_core.contracts import AskRequest
from auri_core.fakes import FakeLLM, FakeSandbox, FakeScheduler, FakeStore, make_run
from auri_core.research.fakes import FakeFetcher, FakeSearch
from auri_core.roles import RolesConfig

PY_TESTS = (
    "import unittest\nfrom solution import double\n\n\nclass T(unittest.TestCase):\n"
    "    def test_pos(self):\n        self.assertEqual(double(2), 4, msg='double(2)')\n\n"
    "    def test_zero(self):\n        self.assertEqual(double(0), 0, msg='double(0)')\n"
)
CALC_TESTS = ("import unittest\nfrom calc import add\n\n\nclass T(unittest.TestCase):\n"
              "    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n")
CALC = "def add(a: int, b: int) -> int:\n    return a + b\n"

# the P2 fixtures (fictional pages + a scripted extraction reply), shared with test_research_pipeline.py
_spec = importlib.util.spec_from_file_location("_rp", Path(__file__).with_name("test_research_pipeline.py"))
_rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rp)
HITS, PAGES, Q, model_reply = _rp.HITS, _rp.PAGES, _rp.Q, _rp.model_reply


async def collect(req, replies, **kw):
    sch = kw.pop("scheduler", None) or FakeScheduler()
    llm = FakeLLM(replies, scheduler=sch)
    return [e async for e in ask(req, llm=llm, scheduler=sch, **kw)], llm


def types(evs):
    return [e.type for e in evs]


async def test_research_needs_allow_web_then_streams_and_stores():
    evs, llm = await collect(AskRequest(Q, mode="research"), [])
    assert types(evs) == ["error"] and "allow_web" in evs[0].data["message"] and llm.calls == []
    st = FakeStore()
    evs, llm = await collect(AskRequest(Q, mode="research", allow_web=True), [model_reply], store=st,
                             search=FakeSearch(default=HITS), fetcher=FakeFetcher(PAGES))
    t = types(evs)
    assert t[0] == "route" and t[-1] == "done" and "delta" in t
    assert {e.data["state"] for e in evs if e.type == "step"} >= {"RESEARCH:search", "RESEARCH:read"}
    done = evs[-1].data
    assert done["verified"] and done["web_checked"] and done["stored"] >= 1
    assert "https://docs.python.org/3/library/stdtypes.html" in done["sources"]


async def test_free_text_code_with_roles_gets_tests_then_the_loop():
    draft = {"framework": "unittest", "interface": "def double(n: int) -> int",
             "files": [{"path": "t.py", "content": PY_TESTS}], "covers": ["pos", "zero"]}
    sol = {"files": [{"path": "solution.py", "content": "def double(n: int) -> int:\n    return n * 2\n"}]}
    stub_red = make_run("fail", failing=[("test_pos", "NotImplementedError"), ("test_zero", "NotImplementedError")])
    store = FakeStore()
    evs, llm = await collect(AskRequest("Írj egy függvényt, ami egy szám kétszeresét adja.", mode="code"),
                             [draft, sol], sandbox=FakeSandbox([stub_red, "pass"]), store=store,
                             roles=RolesConfig(enabled=True))
    states = [e.data.get("state") for e in evs if e.type == "step"]
    assert types(evs).count("route") == 1 and "TESZTELO" in states and "TESZTELO_DONE" in states
    done = evs[-1].data
    assert done["verified"] and done["tests_source"] == "tesztelo" and store.solutions == {}  # own tests: no learning


async def test_free_text_code_rejected_tests_fall_back_to_unverified_chat():
    evs, _ = await collect(AskRequest("Írj egy double függvényt.", mode="code"), ["junk", "junk", "def double(n): ..."],
                           sandbox=FakeSandbox([]), roles=RolesConfig(enabled=True))
    assert any(e.data.get("state") == "TESZTELO_REJECTED" for e in evs if e.type == "step")
    assert evs[-1].type == "done" and evs[-1].data["verified"] is False and types(evs).count("route") == 1


def plan_dict():
    return {"acceptance": ["AC1: az add(2, 3) 5"],
            "milestones": [{"id": "M1", "title": "Tesztek"}, {"id": "M2", "title": "Kód"}],
            "tasks": [
                {"id": "F1", "milestone": "M1", "title": "Tesztek az add függvényhez.", "kind": "test",
                 "writes": ["test_calc.py"], "reads": [], "depends_on": [],
                 "accept": [{"kind": "red-test", "target": "test_calc.py"}]},
                {"id": "F2", "milestone": "M2", "title": "Az add megírása.", "kind": "code", "writes": ["calc.py"],
                 "reads": ["test_calc.py"], "depends_on": ["F1"],
                 "accept": [{"kind": "test", "target": "test_calc.py"}, {"kind": "guard", "target": "calc.py"}]},
            ]}


async def test_project_goal_plans_runs_real_checks_and_saves_a_recipe(tmp_path):
    def judge(files, tests):
        return "pass" if files.get("calc.py") == CALC else make_run("fail", failing=[("test_add", "ImportError")])

    steps = [plan_dict(),
             {"files": [{"path": "test_calc.py", "content": CALC_TESTS}]},
             {"files": [{"path": "calc.py", "content": CALC}, {"path": "test_calc.py", "content": "hacked"}]}]
    store, sb = FakeStore(), FakeSandbox(judge=judge)
    evs, llm = await collect(AskRequest("Írj egy add függvényt tesztekkel!", mode="code", plan=True), steps,
                             sandbox=sb, store=store, runs_dir=tmp_path)
    assert types(evs)[0] == "route" and types(evs)[-1] == "done"
    assert [e.data["ok"] for e in evs if e.type == "verify"] == [True, True]
    done = evs[-1].data
    assert done["verified"] and done["outcome"] == "pass" and done["files"]["calc.py"] == CALC
    assert done["files"]["test_calc.py"] == CALC_TESTS  # F2 may not overwrite the test it does not own
    assert done["recipe"] and any(i.kind == "howto" for i in store.items.values())
    assert sb.calls[0]["files"] == {}  # red-test ran with no implementation
    assert done["tests_source"] == "own" and any("saját tesztjeim" in e.data.get("text", "")
                                                 for e in evs if e.type == "delta")


async def test_project_without_sandbox_or_with_bad_plan_is_honest():
    evs, _ = await collect(AskRequest("projekt", mode="code", plan=True), [])
    assert types(evs) == ["error"] and evs[0].data["kind"] == "not_available"
    evs, _ = await collect(AskRequest("projekt", mode="code", plan=True), ["junk", "junk", "junk", "junk"],
                           sandbox=FakeSandbox([]))
    assert evs[-1].type == "done" and evs[-1].data["outcome"] == "give_up" and evs[-1].data["verified"] is False


async def test_study_is_not_on_request():
    evs, _ = await collect(AskRequest("tanulj", mode="study"), [])
    assert types(evs) == ["error"] and evs[0].data["kind"] == "not_available"


async def test_research_on_the_real_store_records_sources_and_recall_cites_them(tmp_path):
    from auri_core import store as core_store
    from auri_core.ask import _Web
    from auri_core.contracts import RecallRequest
    from auri_core.recall import recall

    mem = core_store.open_store(tmp_path / "core.db")
    evs, _ = await collect(AskRequest(Q, mode="research", allow_web=True), [model_reply], store=mem,
                           search=FakeSearch(default=HITS), fetcher=FakeFetcher(PAGES))
    assert evs[-1].data["stored"] >= 1
    n = mem.db.execute("SELECT COUNT(*) FROM sources WHERE domain IN ('python.org', 'docs.python.org', 'realpython.com')")
    assert n.fetchone()[0] >= 2
    r = await recall(RecallRequest("removeprefix", kinds=("knowledge",)), store=mem)
    assert r.items and any(p.relation == "derived_from" for p in r.items[0].sources)
    web = _Web(None, FakeFetcher({}), mem)  # default adapters get the persistent SQLite search cache
    assert type(web.search.cache).__name__ == "SqliteSearchCache"


async def test_a_broken_test_file_is_not_a_red_test_and_the_step_is_repaired(tmp_path):
    """e5 2026-11-24: a test with a SyntaxError 'failed' without code, so it passed as red; then no code could pass."""
    def judge(files, tests):
        return "pass" if files.get("calc.py") == CALC else make_run("fail", failing=[("test_add", "ImportError")])

    steps = [plan_dict(), {"files": [{"path": "test_calc.py", "content": 'x = ".!?\n'}]},
             {"files": [{"path": "test_calc.py", "content": CALC_TESTS}]},
             {"files": [{"path": "calc.py", "content": CALC}]}]
    sb = FakeSandbox(judge=judge)
    evs, _ = await collect(AskRequest("Írj egy add függvényt tesztekkel!", mode="code", plan=True), steps,
                           sandbox=sb, store=FakeStore(), runs_dir=tmp_path)
    assert [e.data["ok"] for e in evs if e.type == "verify"] == [False, True, True]
    assert evs[-1].data["verified"] and len(sb.calls) == 2  # the broken file never reached the sandbox
