"""Task set loader and validator: `aurikod-hu` tasks in `auri-core/tasks/<id>/` (owner: AI-2).

Format: ideas_for_brain/thinking/06-programozas/08-gyakorlofeladatok.md §1 (`task.yaml` + `tests/` + `ref/`).
`task.yaml` is read with a small, strict YAML-subset parser (stdlib only, no PyYAML):

    key: scalar | "quoted" | 'quoted' | [a, b] | {k: v, k2: v2}     # one flow level, inline comments allowed
    key: |                                                          # literal block, indented lines
      text…

Anything else is rejected loudly with the line number — a malformed task must never be half-loaded.

Public API (ideas_for_brain/ai_prompts.md §1.4):
    load(path) -> CodeTask                  # the contract type lives in auri_core.contracts (AI-1)
    iter_tasks(split, lang) -> Iterator[CodeTask]
    load_raw(path) -> dict                  # validated plain dict (no contract import needed)
    stub_source(lang, signature) -> str     # the "not implemented" stub every test must fail on
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

LANGS = ("py", "ts", "js", "sql")
SPLITS = ("practice", "dev", "heldout", "regression", "public-sanity")
SOURCE_KINDS = ("own", "exercism", "generated")
REQUIRED = ("id", "level", "lang", "topics", "title_hu", "prompt_hu", "signature", "files", "source", "limits", "split",
            "family", "rating")
ID_RE = re.compile(r"^(?P<lang>py|ts|js|sql)-l(?P<level>[0-4])-(?:[a-z]-)?\d{4}$")
CANARY_RE = re.compile(r"AURI-CANARY-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
CANARY_SPLITS = ("dev", "heldout")  # 09-meres-es-benchmark.md §8.2 + ai_prompts.md §4/1


class TaskFormatError(ValueError):
    """A task directory or task.yaml that does not match the format (message is Hungarian, user-facing)."""


# ── YAML subset ────────────────────────────────────────────────────────────────

_KEY_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*):(?:\s+(?P<rest>.*))?$")
_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+\.\d+$")


def _strip_comment(s: str) -> str:
    """Drop a trailing ` # comment` that is outside quotes."""
    quote: str | None = None
    for i, ch in enumerate(s):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or s[i - 1] in " \t"):
            return s[:i].rstrip()
    return s.rstrip()


def _scalar(tok: str, line_no: int) -> Any:
    tok = tok.strip()
    if not tok:
        raise TaskFormatError(f"{line_no}. sor: üres érték")
    if tok[0] == '"':
        if len(tok) < 2 or tok[-1] != '"':
            raise TaskFormatError(f"{line_no}. sor: lezáratlan idézőjel")
        body = tok[1:-1]
        try:
            return body.encode("latin-1", "backslashreplace").decode("unicode_escape") if "\\" in body else body
        except UnicodeDecodeError as e:
            raise TaskFormatError(f"{line_no}. sor: hibás escape: {e}") from None
    if tok[0] == "'":
        if len(tok) < 2 or tok[-1] != "'":
            raise TaskFormatError(f"{line_no}. sor: lezáratlan aposztróf")
        return tok[1:-1].replace("''", "'")
    if tok[0] in "[{&*!|>%@`":
        raise TaskFormatError(f"{line_no}. sor: nem támogatott YAML-szerkezet: {tok[:20]!r}")
    if _INT_RE.match(tok):
        return int(tok)
    if _FLOAT_RE.match(tok):
        return float(tok)
    if tok in ("true", "false"):
        return tok == "true"
    if tok in ("null", "~"):
        return None
    return tok


def _split_flow(body: str, line_no: int) -> list[str]:
    """Split a flow collection body on top-level commas (quotes respected, no nesting)."""
    parts: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    for ch in body:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch in "[]{}":
            raise TaskFormatError(f"{line_no}. sor: egymásba ágyazott gyűjtemény nem támogatott")
        elif ch == ",":
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if quote:
        raise TaskFormatError(f"{line_no}. sor: lezáratlan idézőjel")
    tail = "".join(buf).strip()
    if tail or parts:
        parts.append(tail)
    if any(not p for p in parts):
        raise TaskFormatError(f"{line_no}. sor: üres elem a listában")
    return parts


def _value(rest: str, line_no: int) -> Any:
    rest = rest.strip()
    if rest.startswith("["):
        if not rest.endswith("]"):
            raise TaskFormatError(f"{line_no}. sor: lezáratlan lista")
        return [_scalar(p, line_no) for p in _split_flow(rest[1:-1], line_no)]
    if rest.startswith("{"):
        if not rest.endswith("}"):
            raise TaskFormatError(f"{line_no}. sor: lezáratlan leképezés")
        out: dict[str, Any] = {}
        for part in _split_flow(rest[1:-1], line_no):
            key, sep, val = part.partition(":")
            if not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key.strip()):
                raise TaskFormatError(f"{line_no}. sor: hibás kulcs–érték pár: {part!r}")
            if key.strip() in out:
                raise TaskFormatError(f"{line_no}. sor: ismétlődő kulcs: {key.strip()}")
            out[key.strip()] = _scalar(val, line_no)
        return out
    return _scalar(rest, line_no)


def parse_task_yaml(text: str) -> dict[str, Any]:
    """Parse the strict YAML subset used by task.yaml (see module docstring)."""
    lines = text.splitlines()
    data: dict[str, Any] = {}
    i = 0
    while i < len(lines):
        raw = lines[i]
        line_no = i + 1
        i += 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[0] in " \t":
            raise TaskFormatError(f"{line_no}. sor: váratlan behúzás")
        m = _KEY_RE.match(_strip_comment(raw))
        if not m:
            raise TaskFormatError(f"{line_no}. sor: „kulcs: érték” formát vártam: {raw[:40]!r}")
        key, rest = m.group("key"), (m.group("rest") or "").strip()
        if key in data:
            raise TaskFormatError(f"{line_no}. sor: ismétlődő kulcs: {key}")
        if rest == "|":
            block: list[str] = []
            while i < len(lines) and (not lines[i].strip() or lines[i][0] in " \t"):
                block.append(lines[i])
                i += 1
            while block and not block[-1].strip():
                block.pop()
            if not block:
                raise TaskFormatError(f"{line_no}. sor: üres szövegblokk")
            indent = min(len(b) - len(b.lstrip(" ")) for b in block if b.strip())
            if indent == 0 or any(b.strip() and "\t" in b[: len(b) - len(b.lstrip())] for b in block):
                raise TaskFormatError(f"{line_no}. sor: a szövegblokkot szóközökkel kell behúzni")
            data[key] = "\n".join(b[indent:] for b in block) + "\n"
        elif not rest:
            raise TaskFormatError(f"{line_no}. sor: hiányzó érték ({key}); beágyazott blokk nem támogatott")
        else:
            data[key] = _value(rest, line_no)
    return data


# ── validation ────────────────────────────────────────────────────────────────


def _canaries(text: str) -> set[str]:
    return set(CANARY_RE.findall(text))


def validate(raw: dict[str, Any], task_dir: Path) -> list[str]:
    """All problems of a parsed task (empty list = valid). Messages are Hungarian."""
    errs: list[str] = []
    missing = [k for k in REQUIRED if k not in raw]
    if missing:
        return [f"hiányzó mező(k): {', '.join(missing)}"]
    unknown = sorted(set(raw) - set(REQUIRED))
    if unknown:
        errs.append(f"ismeretlen mező(k): {', '.join(unknown)}")

    tid = raw["id"]
    m = ID_RE.match(tid) if isinstance(tid, str) else None
    if not m:
        errs.append(f"hibás id: {tid!r} (minta: py-l1-0001)")
    elif tid != task_dir.name:
        errs.append(f"az id ({tid}) nem egyezik a mappa nevével ({task_dir.name})")
    if not isinstance(raw["level"], int) or not 0 <= raw["level"] <= 4:
        errs.append(f"hibás level: {raw['level']!r} (0–4)")
    if raw["lang"] not in LANGS:
        errs.append(f"hibás lang: {raw['lang']!r} ({', '.join(LANGS)})")
    if m and (m.group("lang") != raw["lang"] or int(m.group("level")) != raw["level"]):
        errs.append("az id nyelve/szintje nem egyezik a lang/level mezővel")
    if not isinstance(raw["topics"], list) or not raw["topics"] or not all(isinstance(t, str) for t in raw["topics"]):
        errs.append("a topics nem üres szöveglista kell legyen")
    for k in ("title_hu", "prompt_hu", "signature", "family"):
        if not isinstance(raw[k], str) or not raw[k].strip():
            errs.append(f"üres vagy nem szöveg: {k}")
    if raw["split"] not in SPLITS:
        errs.append(f"hibás split: {raw['split']!r} ({', '.join(SPLITS)})")
    if not isinstance(raw["rating"], int):
        errs.append("a rating egész szám kell legyen")

    src = raw["source"]
    if not isinstance(src, dict) or src.get("kind") not in SOURCE_KINDS or not src.get("license"):
        errs.append("a source {kind: own|exercism|generated, license: …} kell legyen")
    elif src["kind"] == "exercism" and (src.get("license") != "MIT" or not src.get("url")):
        errs.append("Exercism-forrás csak MIT-licenccel és url-lel vehető át")

    lim = raw["limits"]
    if not isinstance(lim, dict) or set(lim) != {"wall_s", "mem_mb"} or not all(
        isinstance(v, int | float) and v > 0 for v in lim.values()
    ):
        errs.append("a limits {wall_s: >0, mem_mb: >0} kell legyen")

    files = raw["files"]
    if not isinstance(files, dict) or set(files) != {"visible", "hidden", "reference"}:
        errs.append("a files {visible, hidden, reference} kell legyen")
        return errs
    texts: dict[str, str] = {}
    for role, rel in files.items():
        p = (task_dir / str(rel)).resolve()
        if task_dir.resolve() not in p.parents:
            errs.append(f"a(z) {role} fájl a feladatmappán kívülre mutat: {rel}")
        elif not p.is_file():
            errs.append(f"hiányzó {role} fájl: {rel}")
        else:
            texts[role] = p.read_text(encoding="utf-8")

    if raw["split"] in CANARY_SPLITS:
        yaml_text = (task_dir / "task.yaml").read_text(encoding="utf-8")
        found = [_canaries(yaml_text), *(_canaries(t) for t in texts.values())]
        if any(len(c) != 1 for c in found) or len(set().union(*found)) != 1:
            errs.append("dev/heldout feladatnál a task.yaml és minden fájl ugyanazt az egy AURI-CANARY sort tartalmazza")
    return errs


def load_raw(path: str | Path) -> dict[str, Any]:
    """Parse + validate one task (dir or its task.yaml). Returns the dict with `dir` and absolute `paths`."""
    p = Path(path)
    task_dir = p.parent if p.name == "task.yaml" else p
    yaml_path = task_dir / "task.yaml"
    if not yaml_path.is_file():
        raise TaskFormatError(f"nincs task.yaml: {task_dir}")
    try:
        raw = parse_task_yaml(yaml_path.read_text(encoding="utf-8"))
    except TaskFormatError as e:
        raise TaskFormatError(f"{yaml_path}: {e}") from None
    errs = validate(raw, task_dir)
    if errs:
        raise TaskFormatError(f"{task_dir.name}: " + "; ".join(errs))
    raw["dir"] = task_dir.resolve()
    raw["paths"] = {role: (task_dir / rel).resolve() for role, rel in raw["files"].items()}
    return raw


def task_dirs(root: str | Path | None = None) -> list[Path]:
    """All task directories under the tasks root (sorted by id)."""
    base = Path(root) if root is not None else _default_root()
    return sorted(d for d in base.iterdir() if (d / "task.yaml").is_file())


def iter_raw(split: str | None = None, lang: str | None = None, root: str | Path | None = None) -> Iterator[dict[str, Any]]:
    for d in task_dirs(root):
        raw = load_raw(d)
        if (split is None or raw["split"] == split) and (lang is None or raw["lang"] == lang):
            yield raw


HELDOUT_MANIFEST = "_manifest/heldout-v1.json"  # frozen sha256 list (06/09 §2, ai_prompts §4/6)


def heldout_hashes(root: str | Path | None = None) -> dict[str, str]:
    """sha256 of every file of every heldout task (CRLF→LF, so a git autocrlf checkout does not count as a change)."""
    base = Path(root) if root is not None else _default_root()
    out: dict[str, str] = {}
    for d in task_dirs(base):
        if load_raw(d)["split"] != "heldout":
            continue
        for f in sorted(p for p in d.rglob("*") if p.is_file()):
            out[f.relative_to(base).as_posix()] = hashlib.sha256(f.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    return out


def verify_heldout(root: str | Path | None = None) -> list[str]:
    """Differences from the frozen manifest; [] = the heldout split is intact."""
    base = Path(root) if root is not None else _default_root()
    mf = base / HELDOUT_MANIFEST
    if not mf.is_file():
        return ["nincs heldout-manifeszt (a készlet nincs befagyasztva)"]
    want: dict[str, str] = json.loads(mf.read_text(encoding="utf-8"))["files"]
    have = heldout_hashes(base)
    errs = [f"hiányzik: {k}" for k in want if k not in have]
    errs += [f"megváltozott: {k}" for k in want if k in have and have[k] != want[k]]
    return errs + [f"nincs a manifesztben: {k}" for k in have if k not in want]


def _default_root() -> Path:
    from auri_core.config import load_config

    return load_config().tasks_dir


# ── stubs (06/05 §3: every test must fail on the stub) ────────────────────────


def stub_source(lang: str, signature: str) -> str:
    sig = signature.strip()
    if lang == "py":
        return f"{sig.rstrip(':')}:\n    raise NotImplementedError\n"
    if lang in ("ts", "js"):
        return f"{sig.rstrip(';').rstrip()} {{\n  throw new Error('not implemented');\n}}\n"
    raise TaskFormatError(f"csonk nem készíthető ehhez a nyelvhez: {lang}")


# ── contract boundary (CodeTask lives in auri_core.contracts, owner AI-1) ────


def load(path: str | Path) -> Any:
    """Load one task as a `contracts.CodeTask`."""
    return _to_code_task(load_raw(path))


def iter_tasks(split: str | None = None, lang: str | None = None, root: str | Path | None = None) -> Iterator[Any]:
    for raw in iter_raw(split, lang, root):
        yield _to_code_task(raw)


def _to_code_task(raw: dict[str, Any]) -> Any:
    from dataclasses import fields

    from auri_core.contracts import CodeTask, TaskFiles, TaskLimits, TaskSource

    def build(cls: Any, d: dict[str, Any]) -> Any:
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names})

    return CodeTask(
        id=raw["id"], level=raw["level"], lang=raw["lang"], topics=tuple(raw["topics"]),
        title_hu=raw["title_hu"], prompt_hu=raw["prompt_hu"], signature=raw["signature"],
        files=build(TaskFiles, raw["files"]), source=build(TaskSource, raw["source"]),
        limits=build(TaskLimits, raw["limits"]), split=raw["split"], family=raw["family"],
        rating=raw["rating"], root=str(raw["dir"]),
    )
