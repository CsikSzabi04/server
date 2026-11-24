"""evals (P3 +roles, P5 e5, P2 research): verdict logic offline — real S0 sandbox, model-facing parts replaced."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from auri_core import evals, planner, project, roles, taskset
from auri_core.bench import markdown, summarize
from auri_core.sandbox import S0Sandbox

TASKS = Path(__file__).resolve().parents[2] / "tasks"
E5 = evals.load_e5(TASKS)


@pytest.fixture
def sb(tmp_path: Path) -> S0Sandbox:
    return S0Sandbox(runs_dir=tmp_path / "runs", runtime_dir=tmp_path / "rt")


@pytest.mark.parametrize("p", E5, ids=lambda p: p["id"])
async def test_e5_reference_green_empty_red(p: dict, sb: S0Sandbox) -> None:
    ok = await sb.run_tests(p["ref"], p["accept"], "py", 60, mem_mb=512)
    assert ok.status == "pass", [t.message for t in ok.tests if not t.ok]
    bad = await sb.run_tests({"README.md": "semmi\n"}, p["accept"], "py", 60, mem_mb=512)
    assert bad.status != "pass"


def _patch_planner(monkeypatch: pytest.MonkeyPatch, state: str, files: dict[str, str]) -> None:
    async def make_plan(*_a, **_k):
        return SimpleNamespace(ok=True, plan=SimpleNamespace(tasks=[1, 2]), llm_calls=1, tokens_out=10, prompt_ver="t", errors=[])

    async def execute(plan, **_k):
        return SimpleNamespace(state=state, plan=plan, done=["a", "b"] if state == "done" else ["a"], replans=0,
                               tokens_out=5, files=files, failed_task=None)

    monkeypatch.setattr(planner, "make_plan", make_plan)
    monkeypatch.setattr(planner, "execute", execute)
    monkeypatch.setattr(planner, "make_replanner", lambda **_k: None)
    monkeypatch.setattr(project, "make_step_runner", lambda **_k: None)


@pytest.mark.parametrize(("good", "want_pass", "want_false_done"), [(True, True, False), (False, False, True)])
async def test_run_project_verdict(monkeypatch: pytest.MonkeyPatch, sb: S0Sandbox, good: bool, want_pass: bool,
                                   want_false_done: bool) -> None:
    p = E5[0]
    files = p["ref"] if good else {**p["ref"], "formaz.py": "def szoveg(lista):\n    return ''\n"}
    _patch_planner(monkeypatch, "done", files)
    row = await evals.run_project(p, llm=None, sandbox=sb, scheduler=None, model="fake", runs_dir=None, bench_id="t")
    assert row["project_pass"] is want_pass and row["false_done"] is want_false_done and row["done_steps"] == 2
    s = evals.summarize_suite("e5", [row])
    assert s["false_done"] == int(want_false_done) and "hamis „kész”" in evals.suite_markdown({"model": "m", "bench_id": "b"}, s, [row])


@pytest.mark.parametrize(("code", "critic", "want"), [
    (None, "accept", {"pass_roles3": True, "critic_false_accept": False, "critic_false_alarm": False}),
    ("def palindrom(s):\n    return s != 'alma'\n", "accept", {"pass_roles3": False, "critic_false_accept": True}),
    (None, "revise", {"pass_roles3": True, "critic_false_alarm": True}),
])
async def test_bench_roles_verdict(monkeypatch: pytest.MonkeyPatch, sb: S0Sandbox, code: str | None, critic: str,
                                   want: dict) -> None:
    task = taskset.load(TASKS / "py-l1-0004")  # palindrom
    code = code or (Path(task.root) / task.files.reference).read_text(encoding="utf-8")
    vis = await sb.run_tests({"solution.py": code}, {task.files.visible: (Path(task.root) / task.files.visible).read_text(encoding="utf-8")},
                             "py", 20, mem_mb=512)

    async def debate_code(*_a, **_k):
        return SimpleNamespace(verdict="accept", end_state="DONE", files={"solution.py": code}, last_run=vis, rounds=1,
                               critiques=[SimpleNamespace(verdict=critic)], understanding=None, reverted_to_green=False,
                               prompt_ver="roles:t", out_tokens=9, llm_calls=3, sid="s", reason_hu=None)

    monkeypatch.setattr(roles, "debate_code", debate_code)
    row = await evals.bench_roles_task(task, llm=None, sandbox=sb, scheduler=None, model="fake", bench_id="t")
    assert {k: row[k] for k in want} == want and row["false_done"] is False
    s = summarize([row], "+roles")
    assert s["metric"] == "pass_roles3" and s["critic_judged"] == 1
    assert "Kritikus" in markdown({"taskset": "x", "split": "dev", "lang": "py", "model": "m", "bench_id": "b"}, s, [row])


def test_research_scoring() -> None:
    assert evals.keyword_hit("A Python 3.0 2008 decemberében jelent meg.", ("2008",))
    assert evals.keyword_hit("1 024 bájt", ("1024",)) and not evals.keyword_hit("ismeretlen", ("kékes",))
    rows = [{"q": "r1", "correct": True, "kind": "answered", "web_checked": True, "verified": 2, "corroborated": 1,
             "rejected_quotes": 1, "sources": 3, "wall_ms": 1000},
            {"q": "r2", "correct": False, "kind": "answered", "web_checked": True, "verified": 0, "corroborated": 0,
             "rejected_quotes": 0, "sources": 1, "wall_ms": 3000}]
    s = evals.summarize_suite("research", rows)
    assert s["passed"] == 1 and s["no_verified_answers"] == 1 and s["corroborated"] == 1
    assert "igazolt állítás nélküli válasz: 1" in evals.suite_markdown({"model": "m", "bench_id": "b"}, s, rows)
