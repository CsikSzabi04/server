"""TESZTELO before code: free-text request → tests from the spec → a non-learnable CodeTask for solve()."""

import pytest

from auri_core.contracts import LEARNABLE_SPLITS, SolveOptions
from auri_core.fakes import FakeLLM, FakeSandbox, FakeScheduler, FakeStore, make_run
from auri_core.roles import RolesConfig, RoleSession, SpecTestsRejected, check_tests, interface_name, spec_to_task
from auri_core.solve import solve

PY_TESTS = (
    "import unittest\nfrom solution import double\n\n\nclass T(unittest.TestCase):\n"
    "    def test_pos(self):\n        self.assertEqual(double(2), 4, msg='double(2)')\n\n"
    "    def test_zero(self):\n        self.assertEqual(double(0), 0, msg='double(0)')\n"
)
TS_TESTS = (
    "import { test } from 'node:test';\nimport assert from 'node:assert/strict';\n"
    "import { double } from '../solution.ts';\n\n"
    "test('double(2)', () => assert.equal(double(2), 4, 'double(2)'));\n"
    "test('double(0)', () => assert.equal(double(0), 0, 'double(0)'));\n"
)
REQ = "Írj egy függvényt, ami egy egész szám kétszeresét adja vissza."


def draft(files, framework="unittest", interface=None):
    d = {"framework": framework, "files": [{"path": p, "content": c} for p, c in files.items()], "covers": ["pos", "zero"]}
    if interface:
        d["interface"] = interface
    return d


def session(replies):
    sch = FakeScheduler()
    llm = FakeLLM(replies, scheduler=sch)
    return RoleSession(llm, sch, cfg=RolesConfig(enabled=True)), llm, sch


async def test_python_request_becomes_a_non_learnable_task():
    s, llm, _ = session([draft({"my_tests.py": PY_TESTS}, interface="def double(n: int) -> int")])
    spec = await spec_to_task(s, REQ, lang="py")
    assert spec.task.signature == "def double(n: int) -> int" and spec.task.split not in LEARNABLE_SPLITS
    assert spec.learn is False and spec.task.id.startswith("free-py-") and spec.task.source.kind == "generated"
    assert list(spec.visible) == ["tests/test_visible.py"] and spec.task.files.visible == "tests/test_visible.py"
    assert spec.covers == ("pos", "zero")
    msg = llm.calls[0]["messages"][-1]["content"]
    assert msg.startswith("<szerep>TESZTELO</szerep>") and "unittest" in msg and "choose ONE function" in msg


async def test_given_interface_and_typescript():
    s, llm, _ = session([draft({"tests/visible.test.ts": TS_TESTS}, framework="node:test")])
    spec = await spec_to_task(s, REQ, lang="ts", interface="export function double(n: number): number")
    assert list(spec.visible) == ["tests/visible.test.ts"] and spec.task.lang == "ts"
    assert "export function double(n: number): number" in llm.calls[0]["messages"][-1]["content"]


@pytest.mark.parametrize(("tests", "why"), [
    (PY_TESTS.replace("from solution import double", "def double(n):\n    return n * 2"), "importálják"),
    (PY_TESTS + "\ndef double(n):\n    return 2 * n\n", "implementálja"),
    ("import unittest\nfrom solution import double\nclass T(unittest.TestCase):\n    def test_a(self): pass\n", "kevés"),
])
def test_static_checks(tests, why):
    assert why in check_tests("py", {"tests/test_visible.py": tests}, "double")


def test_interface_name():
    assert interface_name("def parse_forint(s: str) -> int") == "parse_forint"
    assert interface_name("export function slugifyHu(s: string): string") == "slugifyHu"
    assert interface_name("export const add = (a: number) => a") == "add"
    assert interface_name("valami") is None


async def test_rejections_are_honest():
    s, *_ = session(["junk", "junk"])
    with pytest.raises(SpecTestsRejected, match="nem adott érvényes"):
        await spec_to_task(s, REQ, lang="py", interface="def double(n: int) -> int")
    s2, *_ = session([draft({"t.py": PY_TESTS})])
    with pytest.raises(SpecTestsRejected, match="felület"):
        await spec_to_task(s2, REQ, lang="py")  # no interface anywhere
    s3, *_ = session([draft({"t.py": PY_TESTS})])
    with pytest.raises(SpecTestsRejected, match="nyelvhez"):
        await spec_to_task(s3, REQ, lang="sql")


async def test_stub_check_rejects_vacuous_and_broken_tests():
    sig = "def double(n: int) -> int"
    s, *_ = session([draft({"t.py": PY_TESTS})])
    with pytest.raises(SpecTestsRejected, match="csonkon is zöldek"):
        await spec_to_task(s, REQ, lang="py", interface=sig, sandbox=FakeSandbox(["pass"]))
    s2, *_ = session([draft({"t.py": PY_TESTS})])
    broken = make_run("error", failing=[("import test_visible", "SyntaxError: invalid syntax")])
    with pytest.raises(SpecTestsRejected, match="be sem töltődik"):
        await spec_to_task(s2, REQ, lang="py", interface=sig, sandbox=FakeSandbox([broken]))
    s3, *_ = session([draft({"t.py": PY_TESTS})])
    sb = FakeSandbox([make_run("fail", failing=[("test_pos", "NotImplementedError"), ("test_zero", "NotImplementedError")])])
    spec = await spec_to_task(s3, REQ, lang="py", interface=sig, sandbox=sb)
    assert "raise NotImplementedError" in sb.calls[0]["files"]["solution.py"] and spec.visible == sb.calls[0]["tests"]


async def test_spec_task_runs_through_the_p0_loop_without_learning():
    s, *_ = session([draft({"t.py": PY_TESTS}, interface="def double(n: int) -> int")])
    spec = await spec_to_task(s, REQ, lang="py")
    sch, store = FakeScheduler(), FakeStore()
    llm = FakeLLM([{"files": [{"path": "solution.py", "content": "def double(n: int) -> int:\n    return n * 2\n"}]}],
                  scheduler=sch)
    sb = FakeSandbox(["pass"])
    out = await solve(spec.task, llm=llm, sandbox=sb, store=store, scheduler=sch, visible=spec.visible,
                      opts=SolveOptions(learn=spec.learn))
    assert out.kind == "pass" and store.solutions == {} and sb.calls[0]["tests"] == spec.visible
