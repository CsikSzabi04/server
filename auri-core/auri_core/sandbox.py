"""S0 sandbox: run Auri's OWN generated code against frozen tests (owner: AI-2).

Spec: ideas_for_brain/thinking/06-programozas/04-sandbox-kodfuttatas.md §5–§8 and
09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md. S0 is a guard against ACCIDENTS
(infinite loops, memory bombs, stray writes, leaked env), NOT a security boundary against
hostile code — foreign code needs S1 (P1).

Layers (Windows, stdlib only):
  a) Job Object (ctypes): process + job memory, active-process limit, CPU time, BELOW_NORMAL
     priority, CPU-rate hard cap, kill-on-close, UI limits (clipboard, desktop…). The child is
     created SUSPENDED, assigned to the job, then resumed — no gap.
  b) run dir OUTSIDE the repo (config.sandbox_runs_dir/<runId>), deleted after the run.
  c) clean env: only SystemRoot, PATH (runtime dir), TEMP/TMP/HOME/USERPROFILE = run dir.
  d) dedicated runtime (config.sandbox_runtime_dir/py/python.exe) when present — the outbound
     firewall rule targets it (scripts/sandbox/). Fallback: the base interpreter (no firewall).
  f) Python audit hook (boot): blocks writes outside the run dir, reads outside run dir +
     interpreter, sockets, processes, ctypes, winreg.
  g) static pre-filter (AST) → status 'blocked' with a reason the model can act on.

Public API: create_sandbox() -> S0Sandbox (contracts.Sandbox); S0Sandbox.run_tests(...) -> RunResult.
"""

from __future__ import annotations

import ast
import asyncio
import ctypes
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import uuid
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from auri_core.contracts import SOLUTION_FILENAME, InfrastructureError, RunResult, RuntimeEnv, TestCase, tests_hash

MODEL_OUTPUT_CAP = 8 * 1024  # bytes of stdout/stderr kept for the model (06/04 §7)
RAW_OUTPUT_CAP = 1024 * 1024  # bytes read from the child per stream; the rest is discarded (09/03 L2)
DEFAULT_MEM_MB = 512
JOB_MEM_FACTOR = 2  # job memory = 2 × per-process limit (06/04 §5a: 512 MB / 1 GB)
ACTIVE_PROCESS_LIMIT = 8
CPU_TIME_S = 30
CPU_RATE_PERCENT = 50
REPORT_NAME = "_auri_report.json"
BOOT_NAME = "_auri_boot.py"
NODE_BOOT_NAME = "_auri_boot.mjs"
NODE_REPORTER_NAME = "_auri_reporter.mjs"

# ── a) Job Object via ctypes ──────────────────────────────────────────────────

_k32 = ctypes.WinDLL("kernel32", use_last_error=True) if sys.platform == "win32" else None
_ntdll = ctypes.WinDLL("ntdll") if sys.platform == "win32" else None


class _IoCounters(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in ("r_ops", "w_ops", "o_ops", "r_bytes", "w_bytes", "o_bytes")]


class _BasicLimit(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _ExtendedLimit(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimit),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _Accounting(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime", ctypes.c_int64),
        ("TotalKernelTime", ctypes.c_int64),
        ("ThisPeriodTotalUserTime", ctypes.c_int64),
        ("ThisPeriodTotalKernelTime", ctypes.c_int64),
        ("TotalPageFaultCount", wintypes.DWORD),
        ("TotalProcesses", wintypes.DWORD),
        ("ActiveProcesses", wintypes.DWORD),
        ("TotalTerminatedProcesses", wintypes.DWORD),
    ]


_JOB_ACCOUNTING, _JOB_UI, _JOB_EXTENDED, _JOB_CPU_RATE = 1, 4, 9, 15
_LIMIT_PROCESS_TIME, _LIMIT_ACTIVE_PROCESS, _LIMIT_PRIORITY = 0x2, 0x8, 0x20
_LIMIT_PROCESS_MEMORY, _LIMIT_JOB_MEMORY, _LIMIT_DIE_ON_EXC, _LIMIT_KILL_ON_CLOSE = 0x100, 0x200, 0x400, 0x2000
_BELOW_NORMAL = 0x4000
_UI_ALL = 0xFF  # handles, clipboard r/w, system params, display, atoms, desktop, exit windows
_CPU_ENABLE, _CPU_HARD_CAP = 0x1, 0x4
_CREATE_SUSPENDED, _CREATE_NO_WINDOW = 0x4, 0x08000000

if _k32 is not None:
    _k32.CreateJobObjectW.restype = wintypes.HANDLE
    _k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    _k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    _k32.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
    _k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _k32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]


def _check(ok: Any, what: str) -> None:
    if not ok:
        raise InfrastructureError(f"{what} failed (WinError {ctypes.get_last_error()})")


class _Job:
    """A Windows Job Object with the 06/04 §5a limits."""

    def __init__(self, mem_mb: int) -> None:
        self.handle = _k32.CreateJobObjectW(None, None)
        _check(self.handle, "CreateJobObject")
        info = _ExtendedLimit()
        b = info.BasicLimitInformation
        b.LimitFlags = (_LIMIT_PROCESS_TIME | _LIMIT_ACTIVE_PROCESS | _LIMIT_PRIORITY | _LIMIT_PROCESS_MEMORY
                        | _LIMIT_JOB_MEMORY | _LIMIT_DIE_ON_EXC | _LIMIT_KILL_ON_CLOSE)
        b.PerProcessUserTimeLimit = CPU_TIME_S * 10_000_000  # 100 ns units
        b.ActiveProcessLimit = ACTIVE_PROCESS_LIMIT
        b.PriorityClass = _BELOW_NORMAL
        info.ProcessMemoryLimit = mem_mb * 1024 * 1024
        info.JobMemoryLimit = mem_mb * JOB_MEM_FACTOR * 1024 * 1024
        _check(_k32.SetInformationJobObject(self.handle, _JOB_EXTENDED, ctypes.byref(info), ctypes.sizeof(info)),
               "SetInformationJobObject(limits)")
        ui = wintypes.DWORD(_UI_ALL)
        _check(_k32.SetInformationJobObject(self.handle, _JOB_UI, ctypes.byref(ui), ctypes.sizeof(ui)), "SetInformationJobObject(ui)")
        cpu = (wintypes.DWORD * 2)(_CPU_ENABLE | _CPU_HARD_CAP, CPU_RATE_PERCENT * 100)
        _check(_k32.SetInformationJobObject(self.handle, _JOB_CPU_RATE, ctypes.byref(cpu), ctypes.sizeof(cpu)),
               "SetInformationJobObject(cpu)")

    def assign_and_resume(self, proc: subprocess.Popen[bytes]) -> None:
        h = wintypes.HANDLE(int(proc._handle))  # type: ignore[attr-defined]
        _check(_k32.AssignProcessToJobObject(self.handle, h), "AssignProcessToJobObject")
        _check(_ntdll.NtResumeProcess(h) == 0, "NtResumeProcess")

    def terminate(self) -> None:
        _k32.TerminateJobObject(self.handle, 1)

    def stats(self) -> dict[str, int]:
        ext, acc = _ExtendedLimit(), _Accounting()
        _k32.QueryInformationJobObject(self.handle, _JOB_EXTENDED, ctypes.byref(ext), ctypes.sizeof(ext), None)
        _k32.QueryInformationJobObject(self.handle, _JOB_ACCOUNTING, ctypes.byref(acc), ctypes.sizeof(acc), None)
        return {"peak_process": ext.PeakProcessMemoryUsed, "peak_job": ext.PeakJobMemoryUsed,
                "active": acc.ActiveProcesses, "total": acc.TotalProcesses}

    def close(self) -> None:
        if self.handle:
            _k32.CloseHandle(self.handle)  # KILL_ON_JOB_CLOSE: nothing survives
            self.handle = None


# ── output capture with a cap ─────────────────────────────────────────────────


class _Capture(threading.Thread):
    def __init__(self, stream: Any) -> None:
        super().__init__(daemon=True)
        self.stream, self.buf, self.total = stream, bytearray(), 0

    def run(self) -> None:
        while chunk := self.stream.read(65536):
            self.total += len(chunk)
            room = RAW_OUTPUT_CAP - len(self.buf)
            if room > 0:
                self.buf += chunk[:room]


# ── g) static pre-filter (Python) ─────────────────────────────────────────────

_BLOCKED_MODULES = {
    "subprocess": "no processes", "multiprocessing": "no processes", "_winapi": "no processes",
    "socket": "no network", "ssl": "no network", "urllib.request": "no network", "http.client": "no network",
    "requests": "no network", "httpx": "no network", "ftplib": "no network", "smtplib": "no network",
    "webbrowser": "no browser", "ctypes": "no native calls", "winreg": "no registry",
}
_BLOCKED_OS_ATTRS = {"system", "popen", "startfile", "kill", "fork", "execv", "execve", "execl", "execlp", "execvp",
                     "spawnl", "spawnv", "spawnve", "posix_spawn"}
_ABS_PATH_RE = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\)|(?:^|[\\/])\.\.(?:[\\/]|$)")


def static_check_python(source: str) -> str | None:
    """Reason to block (English, fed back to the model) or None. A heuristic, not a boundary."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
        for n in names:
            for mod, why in _BLOCKED_MODULES.items():
                if n == mod or n.startswith(mod + "."):
                    return f"import of '{mod}' is not allowed in the sandbox ({why}); solve it in pure Python or mock it"
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "os" and node.attr in _BLOCKED_OS_ATTRS:
                return f"os.{node.attr} is not allowed in the sandbox (no processes)"
            if node.value.id == "shutil" and node.attr == "rmtree":
                return "shutil.rmtree is not allowed in the sandbox"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "__import__":
            return "__import__ is not allowed in the sandbox; use a normal import"
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and _ABS_PATH_RE.search(node.value):
            return f"absolute or parent paths are not allowed ({node.value[:40]!r}); use files in the working directory only"
    return None


# ── f) boot script: audit hook + unittest runner → JSON report ───────────────

_BOOT = r'''
import json, os, sys, threading, traceback, unittest
RUN = os.path.realpath(sys.argv[1])
NONCE = sys.stdin.readline().strip()
os.close(0)
import io
sys.stdin = io.StringIO("")
MODS = sys.argv[2:]
_READ = [RUN] + sorted({os.path.realpath(p) for p in (sys.prefix, sys.base_prefix, sys.exec_prefix, os.path.dirname(sys.executable))})
_BLOCK_PREFIX = ("socket.", "subprocess.", "os.system", "os.exec", "os.spawn", "os.posix_spawn", "os.startfile", "os.kill",
                 "os.fork", "_winapi.", "ctypes.", "winreg.", "webbrowser.", "urllib.Request", "http.client.", "sys.addaudithook")
_WRITE_EVENTS = {"os.remove", "os.rename", "os.replace", "os.mkdir", "os.rmdir", "os.symlink", "os.link", "os.truncate",
                 "os.chmod", "os.utime", "shutil.rmtree", "shutil.copyfile", "shutil.copymode", "shutil.move", "os.chdir"}
_READ_EVENTS = {"os.listdir", "os.scandir", "glob.glob"}
_WFLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
BLOCKED = []
_tl = threading.local()

def _inside(p, roots):
    p = os.path.normcase(os.path.realpath(os.fsdecode(p)))
    return any(p == os.path.normcase(r) or p.startswith(os.path.normcase(r) + os.sep) for r in roots)

def _deny(event, detail):
    if len(BLOCKED) < 20:
        BLOCKED.append(f"{event}: {detail}"[:200])
    raise PermissionError(f"sandbox: {event} blocked ({detail})"[:200])

def _hook(event, args):
    if getattr(_tl, "busy", False):
        return
    _tl.busy = True
    try:
        if event == "open":
            path, mode, flags = args
            if path is None or isinstance(path, int):
                return
            write = bool(mode and any(c in mode for c in "wax+")) or bool(flags and flags & _WFLAGS)
            if not _inside(path, [RUN] if write else _READ):
                _deny(event, ("write " if write else "read ") + os.fsdecode(path))
        elif event.startswith(_BLOCK_PREFIX):
            _deny(event, "not allowed")
        elif event in _WRITE_EVENTS or event in _READ_EVENTS:
            roots = [RUN] if event in _WRITE_EVENTS else _READ
            for a in args:
                if isinstance(a, (str, bytes, os.PathLike)) and not _inside(a, roots):
                    _deny(event, os.fsdecode(a))
    finally:
        _tl.busy = False

class _Result(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.cases = {}

    def _case(self, test):
        name = test.id()
        if name.startswith("unittest.loader._FailedTest."):
            name = "import " + name.rsplit(".", 1)[-1]
        return self.cases.setdefault(name, {"name": name, "ok": True, "fails": 0})

    def _bad(self, test, err, sub=None):
        c = self._case(test)
        c["ok"] = False
        c["fails"] += 1
        if "message" in c:
            return
        et, ev, tb = err
        msg = f"{et.__name__}: {ev}".strip()
        first = msg.splitlines()[0] if msg else et.__name__
        if sub is not None and getattr(sub, "params", None):
            first += " [" + ", ".join(f"{k}={v!r}" for k, v in sub.params.items())[:200] + "]"
        loc = []
        for fr in traceback.extract_tb(tb):
            if os.path.normcase(os.path.realpath(fr.filename)).startswith(os.path.normcase(RUN)):
                rel = os.path.relpath(fr.filename, RUN).replace(os.sep, "/")
                loc.append(f"{rel}:{fr.lineno}: {(fr.line or '').strip()}"[:200])
        c["message"] = (first[:500] + ("\n" + "\n".join(loc[-3:]) if loc else ""))
        if et is AssertionError and " != " in first:
            actual, _, expected = first.partition(": ")[2].partition(" != ")
            c["actual"], c["expected"] = actual[:300], expected.split(" [")[0].split(" : ")[0][:300]  # drop subTest / msg=

    def addSuccess(self, test): self._case(test)
    def addFailure(self, test, err): self._bad(test, err)
    def addError(self, test, err): self._bad(test, err)
    def addSkip(self, test, reason): self._bad(test, (unittest.SkipTest, unittest.SkipTest("skip is not allowed: " + str(reason)), None))
    def addExpectedFailure(self, test, err): self._case(test)
    def addUnexpectedSuccess(self, test): self._bad(test, (AssertionError, AssertionError("unexpected success"), None))
    def addSubTest(self, test, sub, err):
        if err is not None:
            self._bad(test, err, sub)
        else:
            self._case(test)

def main():
    os.chdir(RUN)
    for d in {RUN} | {os.path.dirname(os.path.join(RUN, m)) for m in MODS}:
        sys.path.insert(0, d)
    sys.addaudithook(_hook)
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for m in MODS:
        suite.addTests(loader.loadTestsFromName(os.path.splitext(os.path.basename(m))[0]))
    result = _Result()
    suite.run(result)
    cases = list(result.cases.values())
    with open(os.path.join(RUN, "''' + REPORT_NAME + r'''"), "w", encoding="utf-8") as f:
        json.dump({"nonce": NONCE, "tests": cases, "blocked": BLOCKED, "python": sys.version.split()[0]}, f)
    sys.stdout.flush()
    os._exit(0 if cases and all(c["ok"] for c in cases) else 1)

main()
'''


# ── the sandbox ───────────────────────────────────────────────────────────────


@dataclass
class _Spawn:
    exit_code: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes
    out_total: int
    err_total: int
    ms: int
    job: dict[str, int] = field(default_factory=dict)


_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


@dataclass
class S0Sandbox:
    runs_dir: Path
    runtime_dir: Path
    keep_runs: bool = False
    level: str = "S0"
    last_job: dict[str, int] = field(default_factory=dict)  # job accounting of the last run (tests: no orphans)

    # contracts.Sandbox
    async def run_tests(self, files: dict[str, str], tests: dict[str, str], lang: str, timeout_s: float, *,
                        mem_mb: int | None = None) -> RunResult:
        return await asyncio.to_thread(self.run_tests_sync, files, tests, lang, timeout_s, mem_mb=mem_mb)

    def python_exe(self) -> tuple[str, bool]:
        """(interpreter, firewalled?) — the dedicated runtime when installed, else the base interpreter."""
        dedicated = self.runtime_dir / "py" / "python.exe"
        if dedicated.is_file():
            return str(dedicated), True
        return getattr(sys, "_base_executable", sys.executable), False

    def node_exe(self) -> str:
        """The dedicated node.exe when installed (firewalled), else the one on PATH."""
        dedicated = self.runtime_dir / "node" / "node.exe"
        found = str(dedicated) if dedicated.is_file() else shutil.which("node")
        if not found:
            raise InfrastructureError("node.exe not found (scripts/sandbox/setup_runtime.ps1)")
        return found

    def run_tests_sync(self, files: dict[str, str], tests: dict[str, str], lang: str, timeout_s: float, *,
                       mem_mb: int | None = None) -> RunResult:
        run_id = time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
        th = tests_hash(tests)
        t0 = time.perf_counter()

        def result(status: str, phase: str, **kw: Any) -> RunResult:
            base: dict[str, Any] = {"run_id": run_id, "status": status, "phase": phase, "tests": [], "passed": 0, "failed": 0,
                                    "stdout": "", "stderr": "", "duration_ms": int((time.perf_counter() - t0) * 1000),
                                    "exit_code": None, "sandbox": self.level, "env": RuntimeEnv(), "tests_hash": th}
            base.update(kw)
            return RunResult(**base)

        bad = self._bad_paths(files, tests)
        if bad:
            return result("blocked", "static", blocked_reason=bad)
        if lang not in ("py", "ts", "js"):
            return result("error", "static", stderr=f"[sandbox] language '{lang}' is not supported by S0 yet")
        sol = SOLUTION_FILENAME[lang]
        src_ext = (".py",) if lang == "py" else (".ts", ".js", ".mjs")
        if sol not in files and not any(n.endswith(src_ext) for n in files):  # multi-file workspace (P5) is fine
            return result("error", "static", stderr=f"[sandbox] missing solution file {sol} (no {lang} source at all)")
        for name, src in files.items():
            if lang == "py":
                if not name.endswith(".py"):
                    continue
                try:
                    compile(src, name, "exec")
                except SyntaxError as e:
                    return result("error", "static", stderr=f"SyntaxError: {e.msg} ({name}, line {e.lineno})")
                reason = static_check_python(src)
            else:
                reason = static_check_js(src)
            if reason:
                return result("blocked", "static", blocked_reason=f"{name}: {reason}")

        mem = mem_mb or DEFAULT_MEM_MB
        run_dir = self.runs_dir / run_id
        try:
            run_dir.mkdir(parents=True)
            for rel, content in {**files, **tests}.items():
                p = run_dir / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8", newline="\n")
            nonce = secrets.token_hex(16)
            if lang == "py":
                (run_dir / BOOT_NAME).write_text(_BOOT, encoding="utf-8")
                exe, _ = self.python_exe()
                mods = sorted(t for t in tests if t.endswith(".py"))
                cmd = [exe, "-I", "-B", "-X", "utf8", str(run_dir / BOOT_NAME), str(run_dir), *mods]
                env = _clean_env(run_dir, exe)
            else:
                (run_dir / NODE_BOOT_NAME).write_text(_NODE_BOOT, encoding="utf-8")
                (run_dir / NODE_REPORTER_NAME).write_text(_NODE_REPORTER, encoding="utf-8")
                exe = self.node_exe()
                mods = sorted(t for t in tests if t.endswith((".ts", ".js", ".mjs")))
                cmd = [exe, "--permission", f"--allow-fs-read={run_dir}", f"--allow-fs-write={run_dir}",
                       f"--max-old-space-size={max(64, mem // 2)}", "--disable-warning=ExperimentalWarning",
                       f"--test-reporter=./{NODE_REPORTER_NAME}", NODE_BOOT_NAME, *mods]
                env = {**_clean_env(run_dir, exe), "AURI_NONCE": nonce}
            sp = _spawn(cmd, run_dir, env, timeout_s, mem, nonce)
            report = _read_report(run_dir, nonce)
            self.last_job = sp.job
        except OSError as e:
            raise InfrastructureError(f"sandbox I/O failed: {e}") from e
        finally:
            if not self.keep_runs:
                shutil.rmtree(run_dir, ignore_errors=True)

        limit = mem * 1024 * 1024
        stdout = _normalize(sp.stdout, sp.out_total, run_dir)
        stderr = _normalize(sp.stderr, sp.err_total, run_dir)
        cases = [TestCase(name=c["name"], ok=c["ok"], message=c.get("message"), expected=c.get("expected"),
                          actual=c.get("actual")) for c in (report or {}).get("tests", [])]
        passed = sum(c.ok for c in cases)
        rep = report or {}
        common: dict[str, Any] = {
            "tests": cases, "passed": passed, "failed": len(cases) - passed, "stdout": stdout, "stderr": stderr,
            "duration_ms": sp.ms, "exit_code": sp.exit_code, "peak_mem_mb": round(sp.job.get("peak_process", 0) / 2**20, 1),
            "env": RuntimeEnv(python=rep.get("python"), node=rep.get("node")),
        }
        oom_markers = ("MemoryError", "heap out of memory", "Allocation failed")
        oom = sp.job.get("peak_process", 0) >= 0.9 * limit or any(
            m in stderr or any(m in (c.message or "") for c in cases) for m in oom_markers)
        if sp.timed_out:
            return result("timeout", "test", **common)
        if oom:
            return result("oom", "test", **common)
        if report is None:
            return result("error", "test", **common)
        if report.get("blocked"):
            return result("blocked", "test", blocked_reason="; ".join(report["blocked"])[:500], **common)
        if not cases:
            return result("error", "test", **{**common, "stderr": (stderr + "\n[sandbox] no tests ran").strip()})
        return result("pass" if passed == len(cases) else "fail", "test", **common)

    @staticmethod
    def _bad_paths(files: dict[str, str], tests: dict[str, str]) -> str | None:
        for rel in [*files, *tests]:
            pp = Path(rel)
            if pp.is_absolute() or ".." in pp.parts or pp.name in (BOOT_NAME, REPORT_NAME, NODE_BOOT_NAME, NODE_REPORTER_NAME) or ":" in rel:
                return f"illegal path: {rel!r}"
        clash = sorted(set(files) & set(tests)) or sorted(f for f in files if Path(f).name.startswith("test"))
        if clash:
            return f"the solution may not contain or change test files: {', '.join(clash)}"
        return None


_JS_BLOCK: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\brequire\s*\("), "require() is not allowed; use ES module imports"),
    (re.compile(r"""(?:\bfrom|\bimport)\s*['"](?:node:)?(child_process|cluster|worker_threads|net|tls|https?|http2|dgram|dns|vm|"""
                r"""inspector|v8|wasi|repl)['"]"""), "module '{0}' is not allowed in the sandbox (no processes/network)"),
    (re.compile(r"\bimport\s*\("), "dynamic import() is not allowed; use a static import"),
    (re.compile(r"\beval\s*\(|\bnew\s+Function\b"), "eval / new Function is not allowed"),
    (re.compile(r"\bfetch\s*\(|\bWebSocket\b|\bXMLHttpRequest\b"), "network access is not allowed in the sandbox; mock it"),
    (re.compile(r"\bprocess\s*\.\s*(binding|dlopen|kill|exit|abort|chdir)\b"), "process.{0} is not allowed in the sandbox"),
    (re.compile(r"""['"`](?:[A-Za-z]:[\\/]|\\\\)|['"`/\\]\.\.[\\/]"""), "absolute or parent paths are not allowed; use the working directory only"),
]


def static_check_js(source: str) -> str | None:
    """Reason to block a TS/JS solution (English, fed back to the model) or None. A heuristic, not a boundary."""
    for rx, why in _JS_BLOCK:
        m = rx.search(source)
        if m:
            return why.format(*(m.groups() or ("",)))
    return None


_NODE_BOOT = r"""import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
globalThis.__auriNonce = process.env.AURI_NONCE;
delete process.env.AURI_NONCE;
for (const f of process.argv.slice(2)) await import(pathToFileURL(resolve(f)).href);
"""

_NODE_REPORTER = r"""import { writeFileSync } from 'node:fs';
import { inspect } from 'node:util';
const RUN = process.cwd();
const norm = (p) => p.replaceAll('\\', '/').toLowerCase();
function where(stack) {
  const out = [];
  for (const m of String(stack || '').matchAll(/(?:file:\/\/\/)?([A-Za-z]:[\\/][^():\n]*):(\d+):\d+/g)) {
    const f = decodeURIComponent(m[1]);
    if (norm(f).startsWith(norm(RUN) + '/')) out.push(`${f.slice(RUN.length + 1).replaceAll('\\', '/')}:${m[2]}`);
  }
  return [...new Set(out)].slice(0, 3);
}
export default async function* (source) {
  const tests = [];
  for await (const ev of source) {
    if (ev.type !== 'test:pass' && ev.type !== 'test:fail') continue;
    const d = ev.data;
    if (d.details?.type === 'suite') continue;
    const ok = ev.type === 'test:pass' && !d.skip && !d.todo;
    const rec = { name: d.name, ok };
    if (!ok) {
      const e = d.details?.error;
      const c = e?.cause ?? e;
      let msg = (d.skip || d.todo) ? 'skip/todo is not allowed' : `${c?.name ?? 'Error'}: ${String(c?.message ?? e)}`;
      msg = msg.split('\n').filter((l) => l.trim()).slice(0, 4).join('\n').slice(0, 500);
      const loc = where(c?.stack);
      rec.message = loc.length ? `${msg}\n${loc.join('\n')}` : msg;
      if (c?.code === 'ERR_ASSERTION' && c && 'expected' in c) {
        rec.actual = inspect(c.actual).slice(0, 300);
        rec.expected = inspect(c.expected).slice(0, 300);
      }
      if (c?.code === 'ERR_ACCESS_DENIED') rec.denied = String(c.message).slice(0, 200);
    }
    tests.push(rec);
  }
  const blocked = tests.filter((t) => t.denied).map((t) => t.denied);
  writeFileSync(RUN + '/""" + REPORT_NAME + r"""', JSON.stringify({ nonce: globalThis.__auriNonce, tests, blocked, node: process.version }));
  yield '';
}
"""


def _clean_env(run_dir: Path, exe: str) -> dict[str, str]:
    return {
        "SystemRoot": os.environ.get("SYSTEMROOT", r"C:\Windows"),
        "PATH": str(Path(exe).parent),
        "TEMP": str(run_dir), "TMP": str(run_dir), "HOME": str(run_dir), "USERPROFILE": str(run_dir),
        "PYTHONUTF8": "1",
    }


def _spawn(cmd: list[str], cwd: Path, env: dict[str, str], timeout_s: float, mem_mb: int, nonce: str) -> _Spawn:
    job = _Job(mem_mb)
    try:
        t0 = time.perf_counter()
        proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                creationflags=_CREATE_SUSPENDED | _CREATE_NO_WINDOW)
        try:
            job.assign_and_resume(proc)
        except Exception:
            proc.kill()
            raise
        out, err = _Capture(proc.stdout), _Capture(proc.stderr)
        out.start()
        err.start()
        try:
            proc.stdin.write((nonce + "\n").encode())  # type: ignore[union-attr]
            proc.stdin.close()  # type: ignore[union-attr]
        except OSError:
            pass
        timed_out = False
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            job.terminate()
            proc.wait(timeout=10)
        job.terminate()  # nothing may outlive the run (children included)
        out.join(5)
        err.join(5)
        for pipe in (proc.stdout, proc.stderr):  # close explicitly: no ResourceWarning from the GC
            if pipe is not None:
                pipe.close()
        ms = int((time.perf_counter() - t0) * 1000)
        stats = job.stats()
        return _Spawn(proc.returncode, timed_out, bytes(out.buf), bytes(err.buf), out.total, err.total, ms, stats)
    finally:
        job.close()


def _read_report(run_dir: Path, nonce: str) -> dict[str, Any] | None:
    try:
        data = json.loads((run_dir / REPORT_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("nonce") == nonce else None


def _normalize(raw: bytes, total: int, run_dir: Path) -> str:
    """Decode, strip ANSI, hide paths, cap at MODEL_OUTPUT_CAP (head + tail kept)."""
    text = _ANSI_RE.sub("", raw.decode("utf-8", errors="replace")).replace("\r\n", "\n")
    for path, alias in ((str(run_dir), "<RUN>"), (str(Path.home()), "<HOME>")):
        text = re.sub(re.escape(path).replace(r"\\", r"[\\/]"), alias, text, flags=re.IGNORECASE)
    if total > len(raw):
        text += f"\n[sandbox] output truncated: {total} bytes total"
    if len(text.encode("utf-8")) > MODEL_OUTPUT_CAP:
        head, tail = text[:2048], text[-(MODEL_OUTPUT_CAP - 2048 - 64):]
        text = f"{head}\n[sandbox] … {len(text) - len(head) - len(tail)} characters omitted …\n{tail}"
    return text


def create_sandbox() -> S0Sandbox:
    """Factory named in contracts (wiring): the S0 sandbox with paths from config."""
    from auri_core.config import load_config

    cfg = load_config()
    return S0Sandbox(runs_dir=cfg.sandbox_runs_dir, runtime_dir=cfg.sandbox_runtime_dir)
