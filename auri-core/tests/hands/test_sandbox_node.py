"""S0 sandbox, TS/JS path (Node 24: type stripping + --permission + in-process node:test reporter)."""

from pathlib import Path

import pytest

from auri_core.sandbox import S0Sandbox

TEST = {"tests/visible.test.ts": "import { test } from 'node:test';\nimport assert from 'node:assert/strict';\n"
        "import { f } from '../solution.ts';\ntest('f', () => assert.equal(f(), 1, 'f()'));\n"}


@pytest.fixture
def sb(tmp_path: Path) -> S0Sandbox:
    return S0Sandbox(runs_dir=tmp_path / "runs", runtime_dir=tmp_path / "no-runtime")


def run(sb: S0Sandbox, body: str, timeout_s: float = 15, mem_mb: int | None = None):
    return sb.run_tests_sync({"solution.ts": body}, TEST, "ts", timeout_s, mem_mb=mem_mb)


def test_pass_and_fail(sb: S0Sandbox) -> None:
    ok = run(sb, "export function f(): number { return 1; }\n")
    assert ok.status == "pass" and ok.passed == 1 and ok.env.node
    r = run(sb, "export function f(): number { return 2; }\n")
    assert r.status == "fail" and r.tests[0].actual == "2" and r.tests[0].expected == "1"
    assert "f()" in (r.tests[0].message or "")


def test_non_erasable_ts_is_an_error(sb: S0Sandbox) -> None:
    r = run(sb, "enum E { A }\nexport function f(): number { return 1; }\n")
    assert r.status in ("error", "fail") and r.passed == 0


def test_infinite_loop_times_out(sb: S0Sandbox) -> None:
    r = run(sb, "while (true) {}\nexport function f(): number { return 1; }\n", timeout_s=3)
    assert r.status == "timeout" and sb.last_job["active"] == 0


def test_heap_hog_is_oom(sb: S0Sandbox) -> None:
    body = "const a: number[][] = [];\nwhile (true) a.push(new Array(1e6).fill(1));\nexport function f(): number { return 1; }\n"
    assert run(sb, body, timeout_s=20, mem_mb=256).status == "oom"


def test_write_outside_denied(sb: S0Sandbox, tmp_path: Path) -> None:
    body = ("import { writeFileSync } from 'node:fs';\nimport { join } from 'node:path';\n"
            "export function f(): number { writeFileSync(join(process.cwd(), String.fromCharCode(46, 46), 'x.txt'), 'x'); return 1; }\n")
    r = run(sb, body)
    assert r.status == "blocked" and not (sb.runs_dir / "x.txt").exists()


def test_static_blocks(sb: S0Sandbox) -> None:
    for body in ["import { exec } from 'node:child_process';\nexport function f() { return 1; }\n",
                 "export function f() { fetch('https://example.com'); return 1; }\n",
                 "const fs = require('fs');\nexport function f() { return 1; }\n"]:
        assert run(sb, body).status == "blocked", body


def test_env_has_no_secrets(sb: S0Sandbox, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk_FAKE_should_not_leak")
    r = run(sb, "console.log(JSON.stringify(process.env));\nexport function f(): number { return 1; }\n")
    assert r.status == "pass" and "FAKE_should_not_leak" not in r.stdout and "AURI_NONCE" not in r.stdout
