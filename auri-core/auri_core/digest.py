"""auri_core.digest — sandbox output → short model feedback + error signatures (owner: AI-1).

Spec: 06/05 §6 (≤ 20 lines, ≤ ~1 KB, "no progress" signature), 06/06 §2 and §7 (normalizeError).
Nothing here may leak an absolute path (user name!) into a prompt, a signature or a log.
"""

from __future__ import annotations

import re

from .contracts import NormalizedError, RunResult

MAX_LINES = 20
MAX_CHARS = 1000

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# 06/06 §7 path rule, extended: file:/// URLs and Windows paths with either slash.
_PATH = re.compile(
    r"file:///[^\s'\"()]+|[A-Za-z]:[\\/][^\s:'\"()]+|/[^\s:'\"()]+\.(?:ts|js|mjs|cjs|py)\b"
)
_ABS_KEEP_NAME = re.compile(r"(?:file:///)?[A-Za-z]:[\\/](?:[^\s'\"():\\/]+[\\/])*([^\s'\"():\\/]+)")
_RUN = re.compile(r"<RUN>[\\/]")
_NOISE = re.compile(
    r"ExperimentalWarning|--trace-warnings|^\s*=+|^\s*-+\s*$|^platform |^rootdir|^plugins:|^cachedir|"
    r"^collected \d+|^configfile|^\s*$|^\(node:\d+\)"
)
_TS_ERR = re.compile(r"error (TS\d{4}): (.+)")
_ERR_LINE = re.compile(
    # a class name (optionally module-qualified), not a call such as Node's `triggerUncaughtException(`
    r"^\s*(?:(?:[a-z_]\w*\.)*[A-Z]\w*(?:Error|Exception)\b(?!\()|ERR_[A-Z_]+)(?: \[[A-Z_]+\])?:?.*$"
)
_LOC = re.compile(r"solution\.(?:py|ts|js|mjs)\"?(?::|, line )(\d+)")

_LABELS = {
    "en": {
        "failed": "FAILED TEST", "expected": "expected", "got": "got", "where": "where",
        "more": "MORE: {n} more test(s) failed (not shown)", "same": "PREVIOUS ROUND: the same failure",
        "tip": "TIP (error knowledge base)", "error": "ERROR",
        "timeout": "TIMEOUT: it ran longer than the limit — check loop conditions and the recursion base case.",
        "oom": "OUT OF MEMORY — check data sizes and recursion.",
        "blocked": "BLOCKED by the sandbox ({r}). Not a logic bug: no network, processes or files outside the run folder.",
    },
    "hu": {
        "failed": "ELBUKOTT TESZT", "expected": "várt", "got": "kapott", "where": "hely",
        "more": "TOVÁBBI: {n} teszt bukott (nem részletezve)", "same": "ELŐZŐ KÖR: ugyanez a hiba",
        "tip": "TIPP (hibatudástár)", "error": "HIBA",
        "timeout": "IDŐTÚLLÉPÉS: tovább futott a korlátnál — nézd meg a ciklusfeltételt és a rekurzió bázisesetét.",
        "oom": "ELFOGYOTT A MEMÓRIA — nézd meg az adatméretet és a rekurziót.",
        "blocked": "A SANDBOX TILTOTTA ({r}). Nem logikai hiba: se hálózat, se folyamat, se a futási mappán kívüli fájl.",
    },
}


def clean(text: str) -> str:
    """ANSI off, absolute paths → file name only, '<RUN>/' prefix off."""
    text = _ANSI.sub("", text or "")
    text = _ABS_KEEP_NAME.sub(lambda m: m.group(1), text)
    return _RUN.sub("", text)


def normalize_error(msg: str) -> NormalizedError:
    """06/06 §7: path → <PATH>, line[:col] → <L>, 'quoted' → '<X>' (slots), hex → <HEX>."""
    slots: list[str] = []
    s = _ANSI.sub("", msg or "").strip()
    s = _PATH.sub("<PATH>", s)
    s = re.sub(r"<RUN>[\\/]\S+", "<PATH>", s)
    s = re.sub(r"\(\d+,\d+\)", "(<L>)", s)  # tsc: file.ts(3,5)
    s = re.sub(r":\d+(?::\d+)?", ":<L>", s)
    s = re.sub(r"\bline \d+", "line <L>", s)

    def _slot(m: re.Match[str]) -> str:
        slots.append(m.group(1))
        return "'<X>'"

    s = re.sub(r"'([^']{1,60})'", _slot, s)
    s = re.sub(r"\b0x[0-9a-fA-F]+\b", "<HEX>", s)
    s = re.sub(r"\s+", " ", s).strip()
    return NormalizedError(s, tuple(slots))


def extract_error_line(text: str) -> str | None:
    """The one line that names the error: tsc 'TSxxxx: …', else the exception line
    (the last one for a Python traceback, the first one otherwise)."""
    text = _ANSI.sub("", text or "")
    if m := _TS_ERR.search(text):
        return f"{m.group(1)}: {m.group(2).strip()}"
    hits = [ln.strip() for ln in text.splitlines() if _ERR_LINE.match(ln) and "Warning" not in ln]
    if not hits:
        return None
    return hits[-1] if "Traceback" in text else hits[0]


def _failing(run: RunResult) -> list:
    return [t for t in run.tests if not t.ok]


def error_signature(run: RunResult) -> NormalizedError | None:
    """Key for the error knowledge base (06/06 §7). None when the run passed."""
    if run.ok:
        return None
    if run.status in ("timeout", "oom"):
        return NormalizedError(f"sandbox {run.status}", ())
    if run.status == "blocked":
        return normalize_error(f"sandbox blocked: {run.blocked_reason or ''}".strip())
    bad = _failing(run)
    src = None
    if bad:
        first = bad[0]
        src = (first.message or "").strip().splitlines()[0] if first.message else None
        if src is None and (first.expected is not None or first.actual is not None):
            src = "AssertionError: expected != actual"
    src = src or extract_error_line(run.stderr + "\n" + run.stdout) or f"exit code {run.exit_code}"
    return normalize_error(src)


def round_signature(run: RunResult) -> str:
    """'No progress' key (06/05 §6): names of the failing tests + the normalized error."""
    names = ",".join(sorted(t.name for t in _failing(run)))
    sig = error_signature(run)
    return f"{names} :: {sig.signature if sig else 'pass'}"


def _location(text: str, files: dict[str, str] | None) -> str | None:
    m = _LOC.search(text or "")
    if not m:
        return None
    line_no = int(m.group(1))
    src = ""
    if files:
        body = next(iter(files.values()))
        lines = body.splitlines()
        if 1 <= line_no <= len(lines):
            src = "   " + lines[line_no - 1].strip()[:120]
    name = m.group(0).split('"')[0].split(":")[0].split(",")[0]
    return f"{name}:{line_no}{src}"


def digest(
    run: RunResult,
    *,
    files: dict[str, str] | None = None,
    previous_signature: str | None = None,
    hint: str | None = None,
    lang: str = "en",
) -> str:
    """Short, structured feedback for the repair prompt (06/05 §6). Empty string for a pass."""
    if run.ok:
        return ""
    L = _LABELS["hu" if lang == "hu" else "en"]
    out: list[str] = []
    bad = _failing(run)
    if run.status in ("timeout", "oom"):
        out.append(L[run.status])
    elif run.status == "blocked":
        out.append(L["blocked"].format(r=clean(run.blocked_reason or "?")))
    if bad:
        t = bad[0]
        out.append(f"{L['failed']}: {t.name}")
        if t.expected is not None or t.actual is not None:
            out.append(f"  {L['expected']}: {clean(str(t.expected))[:200]}")
            out.append(f"  {L['got']}: {clean(str(t.actual))[:200]}")
        msg_lines = [ln for ln in clean(t.message or "").splitlines() if not _NOISE.search(ln)]
        out += ["  " + ln[:200] for ln in msg_lines[:6]]
        loc = _location((t.message or "") + "\n" + run.stderr, files)
        if loc:
            out.append(f"  {L['where']}: {loc}")
        if len(bad) > 1:
            out.append(L["more"].format(n=len(bad) - 1))
    elif run.status in ("fail", "error"):
        err = extract_error_line(run.stderr + "\n" + run.stdout)
        out.append(f"{L['error']} ({run.phase}): {clean(err or f'exit code {run.exit_code}')[:300]}")
        loc = _location(run.stderr + "\n" + run.stdout, files)
        if loc:
            out.append(f"  {L['where']}: {loc}")
        tail = [ln for ln in clean(run.stderr).splitlines() if not _NOISE.search(ln)][-4:]
        out += ["  " + ln[:200] for ln in tail if ln.strip() and ln.strip() != (err or "").strip()]
    if previous_signature is not None and previous_signature == round_signature(run):
        out.append(L["same"])
    if hint:
        out.append(f"{L['tip']}: {clean(hint)[:200]}")
    text = "\n".join(out[:MAX_LINES])
    return text[:MAX_CHARS]
