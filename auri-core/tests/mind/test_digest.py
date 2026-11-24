from auri_core.contracts import TestCase
from auri_core.digest import (
    MAX_CHARS,
    MAX_LINES,
    digest,
    error_signature,
    extract_error_line,
    normalize_error,
    round_signature,
)
from auri_core.fakes import make_run


def test_normalize_paths_lines_slots_hex():
    n = normalize_error(r"C:\Users\tesztelek\proj\solution.py:12:3 NameError: name 'foo' is not defined at 0x1F")
    assert "tesztelek" not in n.signature and "<PATH>" in n.signature
    assert ":<L>" in n.signature and "'<X>'" in n.signature and "<HEX>" in n.signature
    assert n.slots == ("foo",)


def test_same_cause_same_signature():
    a = normalize_error("TypeError: Cannot read properties of undefined (reading 'name')")
    b = normalize_error("TypeError: Cannot read properties of undefined (reading 'age')")
    assert a.signature == b.signature


def test_tsc_matches_seed_table():
    line = extract_error_line("solution.ts(3,5): error TS2322: Type 'string' is not assignable to type 'number'.")
    assert normalize_error(line).signature == "TS2322: Type '<X>' is not assignable to type '<X>'."


def test_python_traceback_last_exception_line():
    tb = 'Traceback (most recent call last):\n  File "D:\\x\\solution.py", line 3, in <module>\nKeyError: \'k\'\n'
    assert extract_error_line(tb) == "KeyError: 'k'"
    assert normalize_error(tb.splitlines()[1]).signature.count("<PATH>") == 1


def test_digest_short_no_abs_path_no_noise():
    run = make_run("fail", failing=[(f"test_{i}", "AssertionError: assert 2 == 3") for i in range(30)],
                   stderr="(node:1) ExperimentalWarning: x\nC:\\Users\\tesztelek\\solution.py:2: AssertionError")
    d = digest(run, files={"solution.py": "def double(n):\n    return n + 1\n"})
    assert len(d.splitlines()) <= MAX_LINES and len(d) <= MAX_CHARS
    assert "tesztelek" not in d and "ExperimentalWarning" not in d
    assert "FAILED TEST: test_0" in d and "29 more" in d
    assert "solution.py:2   return n + 1" in d


def test_digest_hu_labels_and_same_round():
    run = make_run("fail", failing=[("t", "AssertionError")])
    d = digest(run, previous_signature=round_signature(run), hint="explicit encoding", lang="hu")
    assert "ELBUKOTT TESZT" in d and "ELŐZŐ KÖR" in d and "TIPP" in d


def test_expected_actual_and_statuses():
    run = make_run("fail")
    run.tests = [TestCase("t", False, None, expected="'a'", actual="'b'")]
    run.failed = 1
    assert "expected: 'a'" in digest(run)
    assert error_signature(make_run("timeout")).signature == "sandbox timeout"
    assert digest(make_run("pass")) == "" and error_signature(make_run("pass")) is None
    assert "BLOCKED" in digest(make_run("blocked", blocked_reason="net"))


def test_node_uncaught_points_at_the_real_error():
    stderr = ("node:internal/modules/run_main:107\n    triggerUncaughtException(\n    ^\n\n<RUN>\\solution.ts:1\n"
              "export function f(s: string) { const x: = 1;\n\n"
              "SyntaxError [ERR_INVALID_TYPESCRIPT_SYNTAX]: Unexpected token `=`.\n    at parseTypeScript (node:x:1:2)\n")
    assert extract_error_line(stderr).startswith("SyntaxError [ERR_INVALID_TYPESCRIPT_SYNTAX]: Unexpected token")
    run = make_run("error", stderr=stderr)
    assert "SyntaxError" in error_signature(run).signature
    assert "triggerUncaught" not in digest(run, files={"solution.ts": "export function f(s: string) { const x: = 1;\n"})
    assert extract_error_line("json.decoder.JSONDecodeError: Expecting value").startswith("json.decoder")
