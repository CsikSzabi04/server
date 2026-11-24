"""Multi-file project manifest (07/03 §3) + the deterministic repo map (07/03 §5, no model).

`depends_on` per file = the project files it imports (from the repo map or the plan's reads);
validation rejects unknown owners, duplicate/unsafe paths, imports of unknown files, import cycles,
dependencies off the allowlist and a missing test command.
"""

from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass, field
from typing import Literal

from .model import Plan
from .validate import is_safe_path, is_test_path

FileRole = Literal["contract", "impl", "test", "fake", "config", "doc"]
FILE_ROLES = ("contract", "impl", "test", "fake", "config", "doc")
PROJECT_KINDS = ("python", "node", "react", "js", "java")  # = web/src/lib/codeProjects.ts ProjectKind
SPECIAL_OWNERS = ("scaffold", "integrator")
_ROLE_OF_KIND = {"contract": "contract", "test": "test", "code": "impl", "config": "config", "doc": "doc",
                 "research": "doc", "integrate": "impl", "scaffold": "config", "edit": "impl"}


@dataclass(frozen=True)
class Dependency:
    name: str
    version: str


@dataclass(frozen=True)
class ProjectFile:
    path: str
    role: str
    owner: str  # Task.id | "scaffold" | "integrator"
    frozen: bool = False  # contract after its task; test during the code task
    sha: str = ""
    exports: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()  # project files this one imports


@dataclass
class ProjectManifest:
    name: str
    kind: str
    files: list[ProjectFile]
    commands: dict[str, str] = field(default_factory=dict)  # test (required), smoke, start
    deps: list[Dependency] = field(default_factory=list)  # allowlist only, written by the integrator
    runtime: dict[str, str] = field(default_factory=dict)  # e.g. {"node": "24.14.0"}


def file_sha(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.replace("\r\n", "\n").encode("utf-8")).hexdigest()


# ───────────────────────────── repo map ─────────────────────────────

_JS_EXPORT = re.compile(
    r"^\s*export\s+(?:default\s+)?(?:async\s+)?(function\*?\s+\w+\s*\([^)]*\)|class\s+\w+|(?:const|let|var)\s+\w+)",
    re.M)
_JS_IMPORT = re.compile(r"""(?:import\s[^'"]*?from\s*|import\s*\(\s*|require\s*\(\s*)['"](\.{1,2}/[^'"]+)['"]""")


def _py_exports(src: str) -> tuple[str, ...]:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return ()
    out = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.name.startswith("_"):
            ret = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
            out.append(f"def {node.name}({ast.unparse(node.args)}){ret}")
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            out.append(f"class {node.name}")
        elif isinstance(node, ast.Assign):
            out += [t.id for t in node.targets if isinstance(t, ast.Name) and t.id.isupper()]
    return tuple(out)


def _py_imports(path: str, src: str, known: set[str]) -> tuple[str, ...]:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return ()
    base = path.rsplit("/", 1)[0] if "/" in path else ""
    found: set[str] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [("." * node.level) + node.module] if node.level else [node.module]
        for n in names:
            rel = n.lstrip(".").replace(".", "/")
            for cand in (f"{rel}.py", f"{rel}/__init__.py", f"{base}/{rel}.py" if base else ""):
                if cand and cand in known and cand != path:
                    found.add(cand)
    return tuple(sorted(found))


def _js_imports(path: str, src: str, known: set[str]) -> tuple[str, ...]:
    base = path.rsplit("/", 1)[0].split("/") if "/" in path else []
    found: set[str] = set()
    for spec in _JS_IMPORT.findall(src):
        parts = list(base)
        for seg in spec.split("/"):
            if seg == "..":
                if parts:
                    parts.pop()
            elif seg not in (".", ""):
                parts.append(seg)
        target = "/".join(parts)
        for cand in (target, *(f"{target}{ext}" for ext in (".js", ".ts", ".mjs", ".jsx", ".tsx"))):
            if cand in known and cand != path:
                found.add(cand)
                break
    return tuple(sorted(found))


def exports_of(path: str, src: str) -> tuple[str, ...]:
    if path.endswith(".py"):
        return _py_exports(src)
    if path.endswith((".js", ".mjs", ".ts", ".jsx", ".tsx")):
        return tuple(re.sub(r"\s+", " ", m).strip() for m in _JS_EXPORT.findall(src))
    return ()


def imports_of(path: str, src: str, known: set[str]) -> tuple[str, ...]:
    if path.endswith(".py"):
        return _py_imports(path, src, known)
    if path.endswith((".js", ".mjs", ".ts", ".jsx", ".tsx")):
        return _js_imports(path, src, known)
    return ()


def repo_map(files: dict[str, str]) -> str:
    """Signatures only — what a file task sees of the other modules (07/03 §5)."""
    lines = []
    for path in sorted(files):
        ex = exports_of(path, files[path])
        if ex:
            lines.append(f"{path}: " + "; ".join(ex))
    return "\n".join(lines)


# ───────────────────────────── manifest ─────────────────────────────


def manifest_from_plan(plan: Plan, files: dict[str, str], *, name: str, kind: str,
                       commands: dict[str, str], deps: list[Dependency] | None = None,
                       runtime: dict[str, str] | None = None) -> ProjectManifest:
    """Owners/roles from the plan, sha/exports/imports from the workspace files."""
    owner: dict[str, str] = {p: "scaffold" for p in plan.scaffold}
    role: dict[str, str] = {}
    for t in plan.tasks:
        for f in t.writes:
            if t.kind != "edit":
                owner[f] = t.id if t.kind != "integrate" else "integrator"
                role[f] = "test" if is_test_path(f) else _ROLE_OF_KIND.get(t.kind, "impl")
    known = set(files) | set(owner)
    out = []
    for path in sorted(known):
        src = files.get(path, "")
        r = role.get(path) or ("test" if is_test_path(path) else "config")
        out.append(ProjectFile(path=path, role=r, owner=owner.get(path, "integrator"),
                               frozen=r in ("contract", "test"), sha=file_sha(src) if path in files else "",
                               exports=exports_of(path, src), depends_on=imports_of(path, src, known)))
    return ProjectManifest(name=name, kind=kind, files=out, commands=dict(commands), deps=list(deps or []),
                           runtime=dict(runtime or {}))


def _cycle(edges: dict[str, tuple[str, ...]]) -> list[str] | None:
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(n: str) -> list[str] | None:
        state[n] = 1
        stack.append(n)
        for m in edges.get(n, ()):
            if state.get(m) == 1:
                return [*stack[stack.index(m):], m]
            if state.get(m) is None and (c := visit(m)):
                return c
        stack.pop()
        state[n] = 2
        return None

    for n in sorted(edges):
        if state.get(n) is None and (c := visit(n)):
            return c
    return None


def validate_manifest(m: ProjectManifest, *, plan: Plan | None = None,
                      allowlist: set[str] | None = None) -> list[str]:
    errs: list[str] = []
    if not m.name.strip():
        errs.append("a projektnek nincs neve")
    if m.kind not in PROJECT_KINDS:
        errs.append(f"ismeretlen projekttípus: {m.kind}")
    if not (m.commands.get("test") or "").strip():
        errs.append("hiányzik a tesztparancs (commands.test)")
    paths = [f.path for f in m.files]
    dup = sorted({p for p in paths if paths.count(p) > 1})
    errs += [f"{p}: kétszer szerepel" for p in dup]
    known = set(paths)
    task_ids = {t.id for t in plan.tasks} if plan else None
    for f in m.files:
        if not is_safe_path(f.path):
            errs.append(f"{f.path}: érvénytelen útvonal")
        if f.role not in FILE_ROLES:
            errs.append(f"{f.path}: ismeretlen szerep: {f.role}")
        if f.owner not in SPECIAL_OWNERS and task_ids is not None and f.owner not in task_ids:
            errs.append(f"{f.path}: ismeretlen tulajdonos: {f.owner}")
        if f.sha and not re.fullmatch(r"sha256:[0-9a-f]{64}", f.sha):
            errs.append(f"{f.path}: hibás hash")
        if f.role == "contract" and not f.frozen:
            errs.append(f"{f.path}: a szerződésnek befagyasztottnak kell lennie")
        for d in f.depends_on:
            if d not in known:
                errs.append(f"{f.path} importálja: {d}, de az nincs a projektben")
    cyc = _cycle({f.path: tuple(d for d in f.depends_on if d in known) for f in m.files})
    if cyc:
        errs.append("körkörös import: " + " → ".join(cyc))
    for d in m.deps:
        if not d.name.strip() or not d.version.strip():
            errs.append("hiányos függőség (név/verzió)")
        elif allowlist is not None and d.name not in allowlist:
            errs.append(f"{d.name}: nincs az engedélylistán")
    return errs
