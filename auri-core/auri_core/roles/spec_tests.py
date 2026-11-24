"""TESZTELO before the code (02/01, 06/05): a free-text code request → tests from the SPEC → a CodeTask
that `solve.solve(task, visible=spec.visible, opts=SolveOptions(learn=False))` can run.

The tests are Auri's own, so a green run means "passes its own tests from the spec", weaker than a
curated task: `learn` is False and the split is not learnable (the user must confirm before storing)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from ..contracts import (
    LEARNABLE_SPLITS,
    SOLUTION_FILENAME,
    CodeTask,
    Lang,
    Sandbox,
    TaskFiles,
    TaskLimits,
    TaskSource,
)
from .session import RoleCallFailed, RoleSession
from .turns import TestsDraft, draft_tests

TEST_PATH = {"py": "tests/test_visible.py", "ts": "tests/visible.test.ts", "js": "tests/visible.test.js"}
FRAMEWORK = {"py": "unittest", "ts": "node:test", "js": "node:test"}
FRAMEWORK_RULES = {
    "py": ("Use only the standard library `unittest` (no pytest). Import with `from solution import NAME`. "
           "One `unittest.TestCase` class; every assert gets `msg=` with the call and its input."),
    "ts": ("Use `import { test } from 'node:test'` and `import assert from 'node:assert/strict'`. "
           "Import with `import { NAME } from '../solution.ts'`. The 3rd assert argument is the call with its input."),
    "js": ("Use `import { test } from 'node:test'` and `import assert from 'node:assert/strict'`. "
           "Import with `import { NAME } from '../solution.js'`. The 3rd assert argument is the call with its input."),
}
NON_LEARNABLE_SPLIT = "dev"  # not in LEARNABLE_SPLITS: solve() never stores it as verified knowledge
assert NON_LEARNABLE_SPLIT not in LEARNABLE_SPLITS


class SpecTestsRejected(Exception):
    """The drafted tests are unusable (no tests, implementation inside, vacuous). `reason_hu` says why."""

    def __init__(self, reason_hu: str) -> None:
        super().__init__(reason_hu)
        self.reason_hu = reason_hu


@dataclass(frozen=True)
class SpecTask:
    task: CodeTask
    visible: dict[str, str]
    covers: tuple[str, ...]
    learn: bool = False  # own tests: never stored as verified knowledge without the user's OK
    tests_source: str = "tesztelo"


def interface_name(interface: str) -> str | None:
    m = re.search(r"(?:def|function|class)\s+([A-Za-z_]\w*)", interface or "") or \
        re.search(r"(?:const|let)\s+([A-Za-z_]\w*)\s*=", interface or "")
    return m.group(1) if m else None


def check_tests(lang: str, files: dict[str, str], name: str) -> str | None:
    """Static checks of drafted tests; None = ok, else a Hungarian reason."""
    if not files:
        return "a Tesztelő nem adott tesztfájlt"
    body = "\n".join(files.values())
    if lang == "py":
        if "unittest" not in body or len(re.findall(r"^\s*def test", body, re.M)) < 2:
            return "kevés teszt (legalább 2 `unittest` tesztmetódus kell)"
        if not re.search(rf"from\s+solution\s+import\s+[^\n]*\b{re.escape(name)}\b", body):
            return f"a tesztek nem a megoldásból importálják ezt: {name}"
        if re.search(rf"^\s*def\s+{re.escape(name)}\s*\(", body, re.M):
            return "a tesztfájl maga implementálja a függvényt (a specifikációt kell tesztelni)"
    else:
        if "node:test" not in body or len(re.findall(r"\btest\s*\(", body)) < 2:
            return "kevés teszt (legalább 2 `node:test` teszt kell)"
        if not re.search(rf"import\s*\{{[^}}]*\b{re.escape(name)}\b[^}}]*\}}\s*from\s*['\"]\.\./solution", body):
            return f"a tesztek nem a megoldásból importálják ezt: {name}"
        if re.search(rf"\bfunction\s+{re.escape(name)}\s*\(|\b(?:const|let)\s+{re.escape(name)}\s*=", body):
            return "a tesztfájl maga implementálja a függvényt (a specifikációt kell tesztelni)"
    return None


def _normalize(lang: str, draft: TestsDraft) -> dict[str, str]:
    """At most 2 files, under tests/, with names the sandbox runs (test_*.py / *.test.ts)."""
    out: dict[str, str] = {}
    for i, (path, body) in enumerate(draft.files.items()):
        base = path.replace("\\", "/").rsplit("/", 1)[-1]
        if lang == "py":
            ok = re.fullmatch(r"test_\w+\.py", base)
            name = base if ok else TEST_PATH["py"].rsplit("/", 1)[-1].replace(".py", f"{i or ''}.py")
        else:
            ext = f".test.{lang}"
            ok = base.endswith(ext) and re.fullmatch(r"[\w.-]+", base)
            name = base if ok else f"visible{i or ''}{ext}"
        out[f"tests/{name}"] = body.replace("\r\n", "\n")
    return out


async def spec_to_task(session: RoleSession, request: str, *, lang: Lang, interface: str | None = None,
                       title_hu: str | None = None, sandbox: Sandbox | None = None, stub: str | None = None,
                       level: int = 1) -> SpecTask:
    """Draft tests from the request (never from code) and wrap them as a non-learnable CodeTask.
    With a `sandbox`, the tests are also run against a stub (default: taskset.stub_source) and must be
    RED — tests a stub passes prove nothing (02/04 T4 checklist: "tests too weak")."""
    if lang not in FRAMEWORK:
        raise SpecTestsRejected(f"ehhez a nyelvhez még nincs Tesztelő-sablon: {lang}")
    try:
        draft = await draft_tests(session, request, framework=FRAMEWORK[lang], framework_rules=FRAMEWORK_RULES[lang],
                                  interface=interface or "(choose ONE function and return it in `interface`)")
    except RoleCallFailed as e:
        raise SpecTestsRejected("a Tesztelő nem adott érvényes választ") from e
    sig = (interface or draft.interface or "").strip()
    name = interface_name(sig)
    if not name:
        raise SpecTestsRejected("nem derült ki a nyilvános felület (függvényszignatúra)")
    files = _normalize(lang, draft)
    if reason := check_tests(lang, files, name):
        session.transcript.write("TESZTELO", rejected=reason)
        raise SpecTestsRejected(reason)
    digest = hashlib.sha256(f"{lang}\n{sig}\n{request}".encode()).hexdigest()[:10]
    first_test = next(iter(files))
    task = CodeTask(
        id=f"free-{lang}-{digest}", level=max(0, min(4, level)), lang=lang, topics=(),  # type: ignore[arg-type]
        title_hu=(title_hu or request.strip().splitlines()[0])[:80], prompt_hu=request.strip(), signature=sig,
        files=TaskFiles(visible=first_test, hidden="", reference=""), source=TaskSource("generated", "own"),
        limits=TaskLimits(), split=NON_LEARNABLE_SPLIT, family="free", rating=0,  # type: ignore[arg-type]
    )
    if sandbox is not None:
        if stub is None:
            from ..taskset import stub_source

            stub = stub_source(lang, sig)
        run = await sandbox.run_tests({SOLUTION_FILENAME[lang]: stub}, files, lang, task.limits.wall_s,
                                      mem_mb=task.limits.mem_mb)
        session.transcript.write("SANDBOX", cmd="stub-check", status=run.status, passed=run.passed, failed=run.failed)
        if run.ok:
            raise SpecTestsRejected("a tesztek egy üres csonkon is zöldek, így semmit nem bizonyítanak")
        real = [t for t in run.tests if not t.name.startswith("import ")]
        if run.status != "blocked" and not real:
            raise SpecTestsRejected("a tesztfájl be sem töltődik (szintaxis- vagy importhiba), így nem futtatható")
        if run.status == "blocked":
            raise SpecTestsRejected(f"a sandbox letiltotta a teszteket ({run.blocked_reason or 'ismeretlen ok'})")
    return SpecTask(task, files, tuple(draft.covers))
