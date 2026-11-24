"""auri_core.routing.stats — the measured success table behind the P6 router (owner: AI-1). Spec: 08/02 §2.

Pure core: `build_table(records)` turns normalized `Record`s into per-cell counts, so tests use
fixtures. `load_bench_records(eval_dir)` reads AI-2's `data/eval/*/results.jsonl` and is robust to
missing directories, half-written files (a bench still running) and bad lines.

A cell is (kind, lang, level, model, mode): kind = "code" | "chat" | …, lang = task language
("py", "ts", …), mode = "model-only" | "+repair". `heldout` / `public-sanity` rows are never used:
choosing a model on the exam set would leak it (06/09 §2).
"""

from __future__ import annotations

import json
import math
import statistics
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..contracts import Goal

USABLE_SPLITS = frozenset({"dev", "practice", "regression"})
MODES = ("+repair", "model-only")  # preference order for a loop that repairs
MIN_N = 8  # below this a cell is "not measured" (estimate; Wilson is wide anyway)


def wilson_lower(passed: int, n: int, z: float = 1.96) -> float:
    """Lower end of the 95% Wilson interval; 0.0 for n == 0."""
    if n <= 0:
        return 0.0
    p = passed / n
    den = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - margin) / den)


@dataclass(frozen=True)
class Record:
    kind: str
    lang: str
    level: int
    model: str
    mode: str
    ok: bool
    wall_ms: int | None = None
    prompt_ver: str = ""
    key: str = ""  # dedup key (bench run + task); "" = never deduplicated


Cell = tuple[str, str, int, str, str]  # (kind, lang, level, model, mode)


@dataclass
class CellStats:
    n: int = 0
    passed: int = 0
    wall_ms: list[int] = field(default_factory=list)

    @property
    def rate(self) -> float:
        return self.passed / self.n if self.n else 0.0

    @property
    def lower(self) -> float:
        return wilson_lower(self.passed, self.n)

    @property
    def median_ms(self) -> float | None:
        return statistics.median(self.wall_ms) if self.wall_ms else None

    def add(self, other: CellStats) -> CellStats:
        return CellStats(self.n + other.n, self.passed + other.passed, self.wall_ms + other.wall_ms)

    def short(self) -> str:
        med = f", medián {self.median_ms / 1000:.1f} s" if self.median_ms is not None else ""
        return f"{self.passed}/{self.n} = {self.rate:.0%} (alsó határ {self.lower:.0%}{med})"


class StatsTable:
    """Per-cell counts + pooled views. Implements `contracts.Stats` (success_rate)."""

    def __init__(self, cells: dict[Cell, CellStats] | None = None, *, min_n: int = MIN_N) -> None:
        self.cells: dict[Cell, CellStats] = cells or {}
        self.min_n = min_n

    def __bool__(self) -> bool:
        return any(c.n for c in self.cells.values())

    def models(self) -> set[str]:
        return {c[3] for c in self.cells}

    def get(self, kind: str, lang: str, level: int, model: str, mode: str) -> CellStats:
        return self.cells.get((kind, lang, level, model, mode), CellStats())

    def pooled(self, kind: str, model: str, *, lang: str | None = None, level: int | None = None,
               mode: str | None = None) -> CellStats:
        out = CellStats()
        for (k, lg, lv, m, md), c in self.cells.items():
            if k == kind and m == model and (lang is None or lg == lang) and (level is None or lv == level) \
                    and (mode is None or md == mode):
                out = out.add(c)
        return out

    def best_view(self, kind: str, lang: str, level: int, model: str) -> tuple[CellStats, str]:
        """Most specific measured view for a model: exact cell (repair first) → same level any lang →
        same lang any level → the whole kind. Returns (stats, description) — n may be < min_n."""
        for mode in MODES:
            c = self.get(kind, lang, level, model, mode)
            if c.n >= self.min_n:
                return c, f"{kind}/{lang}/L{level}/{mode}"
        views = [
            (self.pooled(kind, model, level=level, mode=MODES[0]), f"{kind}/*/L{level}/{MODES[0]}"),
            (self.pooled(kind, model, level=level), f"{kind}/*/L{level}"),
            (self.pooled(kind, model, lang=lang), f"{kind}/{lang}/*"),
            (self.pooled(kind, model), f"{kind}/*/*"),
        ]
        for c, what in views:
            if c.n >= self.min_n:
                return c, what
        return views[-1]

    def success_rate(self, kind: str, *, like: Goal | None = None, default: float = 0.5,
                     model: str | None = None) -> float:
        """Pooled success of `kind` (optionally one model), shrunk toward `default` while n is small:
        (passed + default·min_n) / (n + min_n)."""
        del like  # P6: no similarity search over episodes yet (needs embeddings, 08/04)
        c = CellStats()
        for (k, *_rest, m, _md), s in self.cells.items():
            if k == kind and (model is None or m == model):
                c = c.add(s)
        return (c.passed + default * self.min_n) / (c.n + self.min_n)

    def rows(self) -> list[tuple[Cell, CellStats]]:
        return sorted(self.cells.items())


def build_table(records: Iterable[Record], *, min_n: int = MIN_N) -> StatsTable:
    """Pure: records → table. Later duplicates (same non-empty key) replace earlier ones (a resumed bench)."""
    latest: dict[str, Record] = {}
    loose: list[Record] = []
    for r in records:
        if r.key:
            latest[r.key] = r
        else:
            loose.append(r)
    cells: dict[Cell, CellStats] = {}
    for r in [*latest.values(), *loose]:
        c = cells.setdefault((r.kind, r.lang, r.level, r.model, r.mode), CellStats())
        c.n += 1
        c.passed += int(r.ok)
        if r.wall_ms is not None:
            c.wall_ms.append(int(r.wall_ms))
    return StatsTable(cells, min_n=min_n)


def record_from_bench(row: dict[str, Any]) -> Record | None:
    """One `results.jsonl` row (AI-2's bench, 06/09) → Record, or None if unusable."""
    try:
        if row.get("split") not in USABLE_SPLITS or row.get("cloud_calls"):
            return None
        if str(row.get("reason_hu") or "").startswith("infrastruktúra") or (
                row.get("llm_calls") == 0 and not row.get("kb_hit")):
            return None  # Ollama down / sandbox missing (2026-11-22: 36 such rows): not the model's result
        mode = str(row["mode"])
        if mode not in MODES:
            return None
        if mode == "model-only" and "pass1" in row:
            ok = bool(row["pass1"])
        elif mode == "+repair" and "pass_repair3" in row:
            ok = bool(row["pass_repair3"])
        else:  # older rows: the verdict is on the HIDDEN tests
            hidden = row.get("hidden") or {}
            ok = row.get("outcome") == "pass" and hidden.get("status") == "pass"
        if row.get("false_done"):
            ok = False
        return Record(kind="code", lang=str(row["lang"]), level=int(row["level"]), model=str(row["model"]),
                      mode=mode, ok=ok, wall_ms=int(row["wall_ms"]) if row.get("wall_ms") is not None else None,
                      prompt_ver=str(row.get("prompt_ver", "")),
                      key=f"{row.get('run_id', '')}/{row.get('task_id', '')}" if row.get("task_id") else "")
    except (KeyError, TypeError, ValueError):
        return None


def load_bench_records(eval_dir: Path | str | None) -> list[Record]:
    """All usable rows of `<eval_dir>/*/results.jsonl`; never raises for missing / partial files."""
    out: list[Record] = []
    if eval_dir is None:
        return out
    root = Path(eval_dir)
    try:
        files = sorted(root.glob("*/results.jsonl"))
    except OSError:
        return out
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue  # a half-written last line of a running bench
            if isinstance(row, dict) and (rec := record_from_bench(row)) is not None:
                out.append(rec)
    return out
