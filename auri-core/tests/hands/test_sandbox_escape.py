"""S0 escape probes (06/04 §8, 11/02 §4, 09/03 §5). S0 guards against accidents, not hostile code."""

from pathlib import Path

import pytest

from auri_core.sandbox import S0Sandbox

TEST = {"tests/test_visible.py": "import unittest\nfrom solution import f\n\n\nclass T(unittest.TestCase):\n"
        "    def test_f(self):\n        self.assertEqual(f(), 1)\n"}


@pytest.fixture
def sb(tmp_path: Path) -> S0Sandbox:
    return S0Sandbox(runs_dir=tmp_path / "runs", runtime_dir=tmp_path / "no-runtime")


def run(sb: S0Sandbox, body: str, timeout_s: float = 10, mem_mb: int | None = None):
    return sb.run_tests_sync({"solution.py": body}, TEST, "py", timeout_s, mem_mb=mem_mb)


def test_pass_and_fail(sb: S0Sandbox) -> None:
    assert run(sb, "def f():\n    return 1\n").status == "pass"
    r = run(sb, "def f():\n    return 2\n")
    assert r.status == "fail" and r.tests[0].actual == "2" and r.tests[0].expected == "1"
    assert "solution.py" in (r.tests[0].message or "") or "test_visible.py" in (r.tests[0].message or "")


def test_infinite_loop_times_out_without_orphans(sb: S0Sandbox) -> None:
    r = run(sb, "def f():\n    return 1\nwhile True:\n    pass\n", timeout_s=2)
    assert r.status == "timeout" and r.duration_ms < 8000
    assert sb.last_job["active"] == 0


def test_memory_hog_is_oom(sb: S0Sandbox) -> None:
    r = run(sb, "x = bytearray(2 * 1024 ** 3)\ndef f():\n    return 1\n", mem_mb=256)
    assert r.status == "oom"


def test_env_has_no_secrets(sb: S0Sandbox, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk_FAKE_should_not_leak")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "sb_FAKE_should_not_leak")
    r = run(sb, "import os\nprint(sorted(os.environ.items()))\ndef f():\n    return 1\n")
    assert r.status == "pass"
    assert "FAKE_should_not_leak" not in r.stdout and "GROQ" not in r.stdout and "SUPABASE" not in r.stdout


def test_write_outside_run_dir_blocked(sb: S0Sandbox, tmp_path: Path) -> None:
    target = tmp_path / "outside.txt"
    # static filter: literal absolute path
    r = run(sb, f"open({str(target)!r}, 'w').write('x')\ndef f():\n    return 1\n")
    assert r.status == "blocked" and r.phase == "static"
    # audit hook: path built at runtime
    body = ("import os\nP = os.environ['TEMP'] + os.sep + chr(46) * 2 + os.sep + 'escape.txt'\n"
            "def f():\n    open(P, 'w').write('x')\n    return 1\n")
    r = run(sb, body)
    assert r.status == "blocked" and "open" in (r.blocked_reason or "")
    assert not target.exists() and not (sb.runs_dir / "escape.txt").exists()


def test_network_blocked(sb: S0Sandbox) -> None:
    assert run(sb, "import socket\ndef f():\n    return 1\n").status == "blocked"
    body = ("import importlib\ndef f():\n    s = importlib.import_module('so' + 'cket')\n"
            "    s.create_connection(('127.0.0.1', 9), timeout=1)\n    return 1\n")
    r = run(sb, body)
    assert r.status == "blocked" and "socket" in (r.blocked_reason or "")


def test_process_spawn_blocked(sb: S0Sandbox) -> None:
    assert run(sb, "import os\ndef f():\n    os.system('cmd /c echo hi')\n    return 1\n").status == "blocked"
    assert run(sb, "import subprocess\ndef f():\n    return 1\n").status == "blocked"


def test_print_flood_truncated(sb: S0Sandbox) -> None:
    r = run(sb, "for _ in range(200000):\n    print('x' * 100)\ndef f():\n    return 1\n", timeout_s=20)
    assert r.status == "pass"
    assert "output truncated" in r.stdout and len(r.stdout.encode()) <= 8 * 1024 + 200


def test_input_gets_eof(sb: S0Sandbox) -> None:
    r = run(sb, "def f():\n    input()\n    return 1\n", timeout_s=5)
    assert r.status == "fail" and "EOFError" in (r.tests[0].message or "")


def test_solution_may_not_touch_tests(sb: S0Sandbox) -> None:
    r = sb.run_tests_sync({"solution.py": "def f():\n    return 2\n", "tests/test_visible.py": "x = 1\n"}, TEST, "py", 5)
    assert r.status == "blocked"


def test_no_leftover_run_dirs(sb: S0Sandbox) -> None:
    for _ in range(20):
        assert run(sb, "def f():\n    return 1\n").status == "pass"
    assert not sb.runs_dir.exists() or not any(sb.runs_dir.iterdir())
    assert sb.last_job["active"] == 0


def test_output_hides_run_path(sb: S0Sandbox) -> None:
    r = run(sb, "import os\nprint(os.getcwd())\ndef f():\n    return 1\n")
    assert "<RUN>" in r.stdout and str(sb.runs_dir) not in r.stdout


def _runtime() -> Path:
    from auri_core.config import load_config

    return load_config().sandbox_runtime_dir


@pytest.mark.skipif(not (_runtime() / "py" / "python.exe").is_file(), reason="nincs dedikált futtatókörnyezet (setup_runtime.ps1)")
@pytest.mark.parametrize(("exe", "code"), [
    ("py/python.exe", "import socket; socket.create_connection(('1.1.1.1', 443), timeout=5); print('CONNECTED')"),
    ("node/node.exe", "const s=require('net').connect(443,'1.1.1.1');s.setTimeout(5000);s.on('connect',()=>{console.log('CONNECTED');"
                      "process.exit(0)});s.on('error',()=>process.exit(1));s.on('timeout',()=>process.exit(1))"),
])
def test_firewall_blocks_dedicated_runtime(exe: str, code: str) -> None:
    """firewall.ps1 (admin, run 2026-11-21): outbound traffic of the dedicated runtime is blocked; no audit hook here."""
    import subprocess

    args = ["-I", "-c", code] if exe.startswith("py") else ["-e", code]
    # Windows error text is cp1250 (Hungarian locale): never let decoding fail the reader thread
    p = subprocess.run([str(_runtime() / exe), *args], capture_output=True, encoding="utf-8", errors="replace", timeout=30)
    assert "CONNECTED" not in p.stdout and p.returncode != 0
