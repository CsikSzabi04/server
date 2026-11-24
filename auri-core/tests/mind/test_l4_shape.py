"""L4 answer shape: a cloud model has no grammar-constrained decoding, so the one common alternative shape
{"files": {"name": "code"}} is accepted (rewritten to the schema shape); nothing else is touched."""

import json

import pytest

from auri_core.l4 import canonical_files
from auri_core.solve import pick_solution

CODE = "def f(x):\n    return x + 1\n"


def test_dict_shape_becomes_the_schema_shape() -> None:
    out = canonical_files(json.dumps({"approach": "a", "files": {"solution.py": CODE}}))
    data = json.loads(out)
    assert data["approach"] == "a"
    assert data["files"] == [{"path": "solution.py", "content": CODE}]
    assert pick_solution(data, "solution.py") == (CODE, [])  # the strict local picker accepts it now


def test_fenced_json_is_handled() -> None:
    out = canonical_files("```json\n" + json.dumps({"files": {"solution.py": CODE}}) + "\n```")
    assert json.loads(out)["files"][0]["path"] == "solution.py"


@pytest.mark.parametrize("text", [
    json.dumps({"files": [{"path": "solution.py", "content": CODE}]}),  # already the schema shape
    json.dumps({"files": {}}),  # empty
    json.dumps({"files": {"solution.py": 3}}),  # not code
    json.dumps({"files": {"solution.py": CODE, "x": None}}),
    json.dumps(["not", "a", "dict"]),
    "no json at all",
    "",
])
def test_everything_else_is_untouched(text: str) -> None:
    assert canonical_files(text) == text


def test_tests_are_still_dropped_after_the_rewrite() -> None:
    """The cloud may not touch the tests either (06/05 §8): the rewrite does not bypass pick_solution."""
    data = json.loads(canonical_files(json.dumps({"files": {"solution.py": CODE, "test_visible.py": "assert False"}})))
    code, dropped = pick_solution(data, "solution.py")
    assert code == CODE and dropped == ["test_visible.py"]
