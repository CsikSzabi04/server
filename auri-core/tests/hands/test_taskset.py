"""Task set: parser, validator, and every task is sound (reference green, stub red)."""

from pathlib import Path

import pytest

from auri_core import taskset
from auri_core.contracts import SOLUTION_FILENAME
from auri_core.sandbox import S0Sandbox

TASKS = Path(__file__).resolve().parents[2] / "tasks"


def test_parser_subset() -> None:
    d = taskset.parse_task_yaml(
        "# comment\nid: py-l1-0001   # inline\nlevel: 1\ntopics: [a.b, c]\nfiles: {visible: x, hidden: 'y z'}\n"
        "s: \"a # not a comment\"\np: |\n  line 1\n    indented\n\nn: 2.5\n"
    )
    assert d == {"id": "py-l1-0001", "level": 1, "topics": ["a.b", "c"], "files": {"visible": "x", "hidden": "y z"},
                 "s": "a # not a comment", "p": "line 1\n  indented\n", "n": 2.5}


@pytest.mark.parametrize("bad", ["a:\n  b: 1\n", "a: [x, [y]]\n", "a: 1\na: 2\n", " a: 1\n", "a: &anchor x\n", "a: [x,]\n"])
def test_parser_rejects(bad: str) -> None:
    with pytest.raises(taskset.TaskFormatError):
        taskset.parse_task_yaml(bad)


def test_validator_reports_problems(tmp_path: Path) -> None:
    d = tmp_path / "py-l1-0099"
    d.mkdir()
    (d / "task.yaml").write_text("id: py-l2-0099\nlevel: 1\nlang: py\n", encoding="utf-8")
    with pytest.raises(taskset.TaskFormatError, match="hiányzó mező"):
        taskset.load_raw(d)


def test_all_tasks_load() -> None:
    raws = list(taskset.iter_raw(root=TASKS))
    py = [r for r in raws if r["lang"] == "py"]
    assert [r["id"] for r in py if r["split"] == "practice"] == ["py-l1-0001", "py-l1-0002", "py-l1-0003"]
    dev = [r for r in py if r["split"] == "dev"]
    assert len(dev) == 40 and {r["level"] for r in dev} == {0, 1}  # aurikod-hu v1 dev, Python (06/09 §2)
    ts = [r for r in raws if r["lang"] == "ts" and r["split"] == "dev"]
    assert len(ts) == 40 and {r["level"] for r in ts} == {0, 1}
    for lang in ("py", "ts"):  # aurikod-hu v1 heldout: 60/language (06/09 §2), 18 × L0 + 42 × L1
        held = [r for r in raws if r["lang"] == lang and r["split"] == "heldout"]
        assert len(held) == 60 and sum(r["level"] == 0 for r in held) == 18
    task = taskset.load(TASKS / "py-l1-0001")
    assert task.files.hidden == "tests/test_hidden.py" and task.root and task.limits.wall_s == 20


def test_heldout_frozen(tmp_path: Path) -> None:
    assert taskset.verify_heldout(TASKS) == []  # any edit of a heldout file breaks the frozen manifest
    bad = tmp_path / "tasks"
    (bad / "_manifest").mkdir(parents=True)
    (bad / taskset.HELDOUT_MANIFEST).write_text('{"files": {"py-l0-h-0001/task.yaml": "0"}}', encoding="utf-8")
    assert taskset.verify_heldout(bad) == ["hiányzik: py-l0-h-0001/task.yaml"]


@pytest.mark.parametrize("task_dir", taskset.task_dirs(TASKS), ids=lambda p: p.name)
def test_reference_green_stub_red(task_dir: Path, tmp_path: Path) -> None:
    raw = taskset.load_raw(task_dir)
    sb = S0Sandbox(runs_dir=tmp_path / "runs", runtime_dir=tmp_path / "no-runtime")
    tests = {raw["files"][r]: raw["paths"][r].read_text(encoding="utf-8") for r in ("visible", "hidden")}
    ref = sb.run_tests_sync({SOLUTION_FILENAME[raw["lang"]]: raw["paths"]["reference"].read_text(encoding="utf-8")}, tests, raw["lang"],
                            raw["limits"]["wall_s"])
    assert ref.status == "pass", [t.message for t in ref.tests if not t.ok]
    stub = sb.run_tests_sync({SOLUTION_FILENAME[raw["lang"]]: taskset.stub_source(raw["lang"], raw["signature"])}, tests, raw["lang"],
                             raw["limits"]["wall_s"])
    assert stub.status == "fail" and stub.passed == 0 and stub.failed == len(stub.tests) > 0
