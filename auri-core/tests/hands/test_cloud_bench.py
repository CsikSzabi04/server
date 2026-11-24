"""bench --mode +cloud: the L4 rescue verdict comes from the hidden tests, never from the cloud's word — offline
(httpx.MockTransport instead of Groq, real S0 sandbox)."""

import dataclasses
import json
from pathlib import Path

import httpx
import pytest

from auri_core import taskset
from auri_core.bench import markdown, summarize
from auri_core.cloud.client import CloudClient
from auri_core.cloud_bench import _load_base, cloud_extra, cloud_visible, passed_row, rescue_row
from auri_core.l4 import CloudGate
from auri_core.sandbox import S0Sandbox

TASKS = Path(__file__).resolve().parents[2] / "tasks"
KEY = "gsk_" + "T3stKeyNotReal0123456789ab"
OVERFIT = "def palindrom(s):\n    return s != 'alma'\n"  # green on the visible tests, red on the hidden ones


def _client(cfg, store, code: str, seen: list, *, dict_shape: bool = False, **cfg_kw) -> CloudClient:
    files = {"solution.py": code} if dict_shape else [{"path": "solution.py", "content": code}]
    reply = json.dumps({"files": files})

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(200, json={"choices": [{"message": {"content": reply}}]})

    c = dataclasses.replace(cfg, cloud_mode="ask", groq_api_key=KEY, cloud_daily_cap=10, **cfg_kw)
    return CloudClient(c, store, transport=httpx.MockTransport(handler))


def _base(task_id: str = "py-l1-0004") -> dict:
    return {"task_id": task_id, "model": "gemma4:e2b", "solve_run_id": "run_x", "reason_hu": "a tesztek pirosak maradtak"}


@pytest.mark.parametrize(("good", "want"), [(True, True), (False, False)])
async def test_rescue_verdict_is_the_hidden_tests(cfg, store, tmp_path: Path, good: bool, want: bool) -> None:
    task = taskset.load(TASKS / "py-l1-0004")
    code = (Path(task.root) / task.files.reference).read_text(encoding="utf-8") if good else OVERFIT
    seen: list = []
    client = _client(cfg, store, code, seen)
    sb = S0Sandbox(runs_dir=tmp_path / "runs", runtime_dir=tmp_path / "rt")
    row = await rescue_row(task, _base(), gate=CloudGate(client, "bench", True, True), sandbox=sb, runs_dir=tmp_path / "r",
                           bench_id="t")
    assert row["pass_cloud"] is want and row["local_pass"] is False and row["cloud_used"] is True
    assert row["cloud_answered"] is True and row["model"].startswith("cloud:groq:")
    assert row["false_done"] is False
    assert row["visible_pass_hidden_fail"] is (not good)  # the overfit answer is green on the visible tests only
    assert len(seen) == 1  # one generation, no fix needed
    body = json.dumps([json.loads(r.content) for r in seen])
    assert task.files.hidden not in body  # the hidden test file never leaves the machine
    assert "AURI-CANARY" not in body  # the leak marker is stripped from what goes out (and did not block the send)


async def test_dict_shaped_cloud_answer_is_judged_like_any_other(cfg, store, tmp_path: Path) -> None:
    """gpt-oss answers {"files": {"solution.py": code}} (measured): correct code must not die as INVALID_OUTPUT."""
    task = taskset.load(TASKS / "py-l1-0004")
    code = (Path(task.root) / task.files.reference).read_text(encoding="utf-8")
    seen: list = []
    client = _client(cfg, store, code, seen, dict_shape=True)
    sb = S0Sandbox(runs_dir=tmp_path / "runs", runtime_dir=tmp_path / "rt")
    row = await rescue_row(task, _base(), gate=CloudGate(client, "bench", True, True), sandbox=sb, runs_dir=None,
                           bench_id="t")
    assert row["pass_cloud"] is True and row["cloud_answered"] is True and len(seen) == 1


def test_cloud_visible_strips_only_the_canary_line() -> None:
    task = taskset.load(TASKS / "py-l1-0004")
    raw = (Path(task.root) / task.files.visible).read_text(encoding="utf-8")
    assert "AURI-CANARY" in raw  # the premise: dev tasks carry a marker
    out = cloud_visible(task)[task.files.visible]
    assert "AURI-CANARY" not in out
    assert out.replace("\n", "") == "".join(ln for ln in raw.splitlines(True) if "AURI-CANARY" not in ln).replace("\n", "")


async def test_real_secret_in_a_task_is_still_refused(cfg, store, tmp_path: Path) -> None:
    """Stripping the canary must not weaken the production gate: a key-like blob in the tests is not sent."""
    task = taskset.load(TASKS / "py-l1-0004")
    seen: list = []
    client = _client(cfg, store, OVERFIT, seen)
    sb = S0Sandbox(runs_dir=tmp_path / "runs", runtime_dir=tmp_path / "rt")
    from auri_core import cloud_bench

    orig = cloud_bench.cloud_visible
    cloud_bench.cloud_visible = lambda t: {**orig(t), "x.py": 'API_KEY = "sk-' + 'abcdefABCDEF1234567890"'}  # type: ignore[assignment]
    try:
        row = await rescue_row(task, _base(), gate=CloudGate(client, "bench", True, True), sandbox=sb, runs_dir=None,
                               bench_id="t")
    finally:
        cloud_bench.cloud_visible = orig
    assert seen == [] and row["cloud_answered"] is False and "titoknak" in str(row["reason_hu"])


async def test_cloud_off_sends_nothing_and_is_a_fail(cfg, store, tmp_path: Path) -> None:
    task = taskset.load(TASKS / "py-l1-0004")
    seen: list = []
    client = _client(cfg, store, OVERFIT, seen, )
    client.cfg = dataclasses.replace(client.cfg, cloud_mode="off")  # the user's switch is respected, even in a bench
    sb = S0Sandbox(runs_dir=tmp_path / "runs", runtime_dir=tmp_path / "rt")
    row = await rescue_row(task, _base(), gate=CloudGate(client, "bench", True, True), sandbox=sb, runs_dir=None,
                           bench_id="t")
    assert seen == []
    assert row["pass_cloud"] is False and row["cloud_answered"] is False and row["cloud_calls"] == 0


def test_passed_row_and_summary() -> None:
    base_pass = {"task_id": "a", "level": 1, "pass_repair3": True, "wall_ms": 1000, "llm_calls": 2, "tokens_out": 10,
                 "rounds": 1, "no_progress": False, "false_done": False, "visible_pass_hidden_fail": False,
                 "hidden": {"status": "pass", "passed": 3, "total": 3}, "outcome": "pass"}
    rows = [passed_row(base_pass, "b"),
            {**base_pass, "task_id": "b", "pass_repair3": False, "pass_cloud": True, "local_pass": False,
             "cloud_used": True, "cloud_answered": True},
            {**base_pass, "task_id": "c", "pass_repair3": False, "pass_cloud": False, "local_pass": False,
             "cloud_used": True, "cloud_answered": False}]
    assert cloud_extra(rows) == {"local_passed": 1, "cloud_tried": 2, "cloud_answered": 1, "cloud_rescued": 1,
                                 "cloud_refused": 1}
    s = summarize(rows, "+cloud")
    assert (s["passed"], s["n"], s["metric"]) == (2, 3, "pass_cloud") and s["cloud_rescued"] == 1
    md = markdown({"taskset": "x", "split": "dev", "lang": "py", "model": "m", "bench_id": "b", "base": "old",
                   "cloud_model": "gpt-oss"}, s, rows)
    assert "1 mentve" in md.replace("**", "")


@pytest.mark.parametrize(("meta", "needle"), [
    ({"mode": "+repair", "split": "heldout"}, "heldout"),
    ({"mode": "model-only", "split": "dev"}, "+repair kell"),
])
def test_base_run_guards(tmp_path: Path, meta: dict, needle: str) -> None:
    (tmp_path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (tmp_path / "results.jsonl").write_text("", encoding="utf-8")
    msg = _load_base(tmp_path)
    assert isinstance(msg, str) and needle in msg
    assert isinstance(_load_base(tmp_path / "nincs"), str)
