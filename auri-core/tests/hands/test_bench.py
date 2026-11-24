"""bench: hidden-test verdict, metrics, honesty counters — offline (FakeLLM, real S0 sandbox)."""

import argparse
import json
import time
from pathlib import Path

import pytest

from auri_core import taskset
from auri_core.bench import bench_task, heldout_guard, markdown, summarize, wilson
from auri_core.fakes import FakeLLM, FakeScheduler
from auri_core.sandbox import S0Sandbox

TASKS = Path(__file__).resolve().parents[2] / "tasks"
OVERFIT = "def palindrom(s):\n    return s != 'alma'\n"  # green on the visible tests, red on the hidden ones


@pytest.mark.parametrize(("code", "want_pass", "overfit"), [
    (None, True, False),
    ("def palindrom(s):\n    return True\n", False, False),
    (OVERFIT, False, True),
])
async def test_bench_task_verdict(tmp_path: Path, code: str | None, want_pass: bool, overfit: bool) -> None:
    task = taskset.load(TASKS / "py-l1-0004")  # palindrom
    code = code or (Path(task.root) / task.files.reference).read_text(encoding="utf-8")
    sched = FakeScheduler()
    llm = FakeLLM([{"files": [{"path": "solution.py", "content": code}]}] * 4, scheduler=sched)
    sb = S0Sandbox(runs_dir=tmp_path / "runs", runtime_dir=tmp_path / "rt")
    row = await bench_task(task, mode="model-only", llm=llm, sandbox=sb, scheduler=sched, model="fake", bench_id="t")
    assert row["pass1"] is want_pass
    assert row["false_done"] is False
    assert row["visible_pass_hidden_fail"] is overfit
    assert row["hidden"]["total"] > 0 and row["llm_calls"] >= 1


def test_wilson_and_summary() -> None:
    lo, hi = wilson(30, 60)
    assert 0.37 < lo < 0.38 and 0.62 < hi < 0.63  # ±12–13 points at 50% (06/09 §7)
    rows = [{"task_id": f"t{i}", "level": i % 2, "pass1": i < 3, "wall_ms": 1000 * (i + 1), "llm_calls": 1, "tokens_out": 100,
             "rounds": 0, "no_progress": False, "false_done": False, "visible_pass_hidden_fail": False, "outcome": "pass",
             "hidden": {"passed": 1, "total": 1}} for i in range(5)]
    s = summarize(rows, "model-only")
    assert s["passed"] == 3 and s["n"] == 5 and s["wall_s_median"] == 3.0 and s["false_done"] == 0
    md = markdown({"taskset": "x", "split": "dev", "lang": "py", "model": "m", "bench_id": "b"}, s, rows)
    assert "3/5" in md and "hamis „kész”: **0**" in md


def test_heldout_guard(tmp_path: Path) -> None:
    a = argparse.Namespace(official=False, tasks_dir=str(TASKS), resume="", lang="py", mode="model-only")
    assert "--official" in heldout_guard(a, eval_dir=tmp_path)
    a.official = True
    assert heldout_guard(a, eval_dir=tmp_path) == ""
    run = tmp_path / "bench_x"
    run.mkdir()
    meta = {"bench_id": "bench_x", "split": "heldout", "lang": "py", "mode": "model-only", "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (run / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    assert "hetente" in heldout_guard(a, eval_dir=tmp_path)  # at most one official run per week
    assert heldout_guard(a, eval_dir=tmp_path, now=time.time() + 8 * 86400) == ""


def test_infra_rows_are_not_fails(tmp_path: Path) -> None:
    from auri_core.bench import is_infra, load_resumable

    res = tmp_path / "results.jsonl"
    rows = [{"task_id": "a", "reason_hu": None}, {"task_id": "b", "reason_hu": "infrastruktúra: Nem érem el az Ollamát."},
            {"q": "r1", "reason": "infrastruktúra: LLMError"}]
    res.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    assert [is_infra(r) for r in rows] == [False, True, True]
    assert [r["task_id"] for r in load_resumable(res)] == ["a"]  # dropped → they run again on --resume
    assert [json.loads(x)["task_id"] for x in res.read_text(encoding="utf-8").splitlines()] == ["a"]
