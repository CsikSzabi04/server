"""RECALL on the real stack (AI-3 SQLite store + AI-2 S0 sandbox), no model: P0 gate (4)."""

from pathlib import Path

from auri_core import sandbox, store, taskset
from auri_core.fakes import FakeLLM, FakeScheduler
from auri_core.solve import solve

TASK = Path(__file__).resolve().parents[2] / "tasks" / "py-l1-0002"


async def test_second_run_comes_from_store_with_zero_llm_calls(tmp_path):
    task = taskset.load(TASK)
    ref = (TASK / task.files.reference).read_text(encoding="utf-8")
    sch, mem, sb = FakeScheduler(), store.open_store(tmp_path / "core.db"), sandbox.create_sandbox()
    first = await solve(task, llm=FakeLLM([{"files": [{"path": "solution.py", "content": ref}]}], scheduler=sch),
                        sandbox=sb, store=mem, scheduler=sch)
    assert first.kind == "pass" and first.snippet_id
    llm2 = FakeLLM([], scheduler=sch)
    second = await solve(task, llm=llm2, sandbox=sb, store=mem, scheduler=sch)
    assert second.kind == "pass" and second.from_memory and second.llm_calls == 0 and llm2.calls == []
    assert second.last_run is not None and second.last_run.ok
