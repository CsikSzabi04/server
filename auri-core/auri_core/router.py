"""auri_core.router — model and level choice (owner: AI-1). Spec: 08/02, 08/01, 08/03, 08/04.

- `SimpleRouter` (P0/P1): one fixed model, no escalation. Kept as the fallback.
- `StatsRouter` (P6): measured choice per (kind, task language, level) from bench results
  (`routing.stats`), Wilson lower bound + minimum sample size, median latency as tie-breaker,
  only configured models that fit in RAM, one-model-on-the-lane preference (NK14: two models in
  parallel ~5.5× slower first token, a reload ~8.5 s), escalation L2 → L3 only when L3 is not
  measured worse, L4 (cloud) only when allowed AND configured AND interactive. L0 = verified hit.
- `load_router(cfg)` → StatsRouter when there are measurements, else SimpleRouter.

Every decision returns (or stores in `last_reason`) a reason string for the journal.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path
from typing import Any

from .contracts import BUDGETS, Assessment, Budget, CodeTask, Failure, Goal, Recall, Stats
from .routing.models import DEFAULT_RAM_BUDGET_GB, tier_of, usable_models
from .routing.stats import CellStats, StatsTable, build_table, load_bench_records

DEFAULT_CODE_MODEL = "gemma4:e2b"
SWITCH_MARGIN = 0.05  # a non-lane model must beat the lane model's lower bound by this much (reload cost)
TIE = 0.02  # lower bounds closer than this → the faster (median) model wins
L3_THRESHOLD = 0.6  # difficulty from which L3 is chosen up front (08/02 §2, estimate)
_DOC_ERRORS = re.compile(r"\b(ImportError|ModuleNotFoundError|AttributeError|TS2305|TS2339|TS2307)\b")


def _configured_code_model() -> str:
    try:
        from .config import load_config  # AI-3

        return load_config().models.code or DEFAULT_CODE_MODEL
    except Exception:  # config not available → spec default
        return DEFAULT_CODE_MODEL


class SimpleRouter:
    def __init__(self, code_model: str | None = None) -> None:
        self.model = code_model or _configured_code_model()

    def code_model(self, task: CodeTask) -> tuple[str, str]:
        """(model, reason) for a CodeTask."""
        return self.model, f"P0: fixed code model for L{task.level} ({task.lang})"

    def chat_model(self) -> tuple[str, str]:
        """P1: chat uses the same model as code — one model on the lane (NK14: two in parallel is very slow)."""
        return self.model, "P1: one model on the lane (NK14)"

    def assess(self, goal: Goal, recall: Recall, history: Stats | None = None) -> Assessment:
        budget = BUDGETS.get(goal.mode, BUDGETS["chat"])
        if (hit := recall.verified_fresh()) is not None:
            return Assessment(kind=goal.mode, level=0, model="", difficulty=0.0, predicted_success=0.9,
                              budget=budget, reason=f"L0: verified hit {_hit_id(hit)}")
        return Assessment(kind=goal.mode, level=2, model=self.model, difficulty=0.5, predicted_success=0.5,
                          budget=budget, reason="P0: L2 small local model (no difficulty estimate yet)")

    def escalate(self, level: int, failure: Failure) -> int | None:
        return None  # P0: nothing stronger installed (L3 = P6, L4 = cloud, off)


# ───────────────────────────── P6 ─────────────────────────────


def _hit_id(hit: Any) -> str:
    return str(getattr(hit, "item_id", None) or getattr(hit, "id", "?"))


def estimate_size(text: str) -> float:
    """0..1, "function" < "class" < "project" (08/02 §2 `size`; keyword estimate, to be calibrated)."""
    t = text.lower()
    if re.search(r"projekt|project|több fájl|tobb fajl|multi-?file|alkalmazás|application|\bapp\b", t):
        return 1.0
    if re.search(r"osztály|osztaly|\bclass\b|modul|module|\bapi\b|parser|értelmez", t):
        return 0.6
    if re.search(r"függvény|fuggveny|function|\bdef\b|metódus|method", t):
        return 0.25
    return min(len(t) / 2000, 1.0)


def difficulty(known: float, sim: float, size: float, freshness: float) -> float:
    """08/02 §2: d = 0.35·(1−known) + 0.35·(1−sim) + 0.2·size + 0.1·freshness (weights: estimates)."""
    clamp = lambda x: min(max(x, 0.0), 1.0)  # noqa: E731
    return round(0.35 * (1 - clamp(known)) + 0.35 * (1 - clamp(sim)) + 0.2 * clamp(size)
                 + 0.1 * clamp(freshness), 3)


def scale_budget(b: Budget, d: float) -> Budget:
    """`BUDGETS[kind].scaled(d)`: tokens and wall time ×0.75 (easy) … ×1.25 (hard); counts unchanged."""
    f = 0.75 + 0.5 * min(max(d, 0.0), 1.0)
    return replace(b, out_tokens=int(b.out_tokens * f), wall_s=round(b.wall_s * f, 1))


class StatsRouter:
    """Measured router (P6). Drop-in for SimpleRouter (`code_model`, `chat_model`, `assess`, `escalate`)."""

    def __init__(
        self,
        table: StatsTable,
        *,
        lane_model: str | None = None,
        models: Iterable[str] | None = None,
        ram_budget_gb: float = DEFAULT_RAM_BUDGET_GB,
        allow_cloud: bool = False,
        cloud_model: str | None = None,
        interactive: bool = True,
    ) -> None:
        self.table = table
        self.lane = lane_model or _configured_code_model()
        self.model = self.lane  # SimpleRouter compatibility
        self.available = usable_models(list(models) if models is not None else [self.lane], self.lane, ram_budget_gb)
        self.cloud_model = cloud_model if (allow_cloud and cloud_model) else None  # 08/03: off by default
        self.interactive = interactive
        self.last_reason = ""

    # ── model choice ──
    def _view(self, kind: str, lang: str | None, level: int | None, model: str) -> tuple[CellStats, str]:
        if lang is not None and level is not None:
            return self.table.best_view(kind, lang, level, model)
        return self.table.pooled(kind, model, lang=lang, level=level), f"{kind}/{lang or '*'}/" + (
            f"L{level}" if level is not None else "*")

    def pick(self, kind: str, lang: str | None, level: int | None, tier: int = 2) -> tuple[str | None, str]:
        """Best model of `tier` for the cell, with a reason. None if no usable model on that tier."""
        cands = [m for m in self.available if tier_of(m) == tier]
        if not cands:
            return None, f"nincs L{tier} modell (telepítve/beállítva és a RAM-keretbe férő)"
        views = {m: self._view(kind, lang, level, m) for m in cands}
        measured = {m: v for m, v in views.items() if v[0].n >= self.table.min_n}
        default = self.lane if self.lane in cands else cands[0]
        if not measured:
            c, what = views[default]
            return default, (f"{default}: nincs elég mérés ({what}: n={c.n} < {self.table.min_n}); "
                             f"{'a sáv modellje marad (NK14)' if default == self.lane else 'az első alkalmas modell'}")
        best_lower = max(v[0].lower for v in measured.values())
        near = [m for m, v in measured.items() if v[0].lower >= best_lower - TIE]
        best = min(near, key=lambda m: (measured[m][0].median_ms or float("inf"), m != self.lane))
        if best != self.lane and self.lane in measured:
            lane_c = measured[self.lane][0]
            if measured[best][0].lower < lane_c.lower + SWITCH_MARGIN:
                best = self.lane  # not enough gain for a reload (~8.5 s) and a cold Jarvis prefix
        elif best != self.lane and self.lane in cands and self.lane not in measured:
            best = self.lane  # the lane model is unknown here, not worse: stay (one model on the lane)
        c, what = views[best]
        if best == self.lane:
            note = "egy modell a sávon (NK14)"
        elif self.lane in cands:
            note = f"váltás: mérve jobb, mint {self.lane} (> +{SWITCH_MARGIN:.0%} alsó határ)"
        else:
            note = f"L{tier} modell"
        return best, f"{best}: {what} {c.short()}; {note}"

    def code_model(self, task: CodeTask) -> tuple[str, str]:
        model, why = self.pick("code", task.lang, task.level, tier=2)
        if model is None:
            model, why = self.lane, f"{self.lane}: {why}, marad a sáv modellje"
        self.last_reason = f"P6: {why}"
        return model, self.last_reason

    def chat_model(self) -> tuple[str, str]:
        model, why = self.pick("chat", None, None, tier=2)
        if model is None:
            model = self.lane
        self.last_reason = f"P6: {why}"
        return model, self.last_reason

    # ── 08/02 §2 ──
    def assess(self, goal: Goal, recall: Recall, history: Stats | None = None) -> Assessment:
        kind = goal.mode if goal.mode in BUDGETS else "chat"
        if (hit := recall.verified_fresh()) is not None:
            self.last_reason = f"L0: ellenőrzött találat {_hit_id(hit)} — nincs modellhívás"
            return Assessment(kind=kind, level=0, model="", difficulty=0.0, predicted_success=0.95,
                              budget=BUDGETS[kind], reason=self.last_reason)
        sim = (history or self.table).success_rate(kind, like=goal, default=0.5)
        size = estimate_size(goal.text)
        d = difficulty(recall.known_ratio, sim, size, goal.freshness_risk)
        level, why_level = 2, f"d={d:.2f} < {L3_THRESHOLD}"
        model, why_model = self.pick(kind, None, None, tier=2)
        if d >= L3_THRESHOLD and kind != "chat":
            m3, why3 = self.pick(kind, None, None, tier=3)
            if m3 is not None:
                level, model, why_model = 3, m3, why3
                why_level = f"d={d:.2f} ≥ {L3_THRESHOLD}" + ("" if not goal.interactive else "; élőben: a felhasználó tudtával")
            else:
                why_level = f"d={d:.2f} ≥ {L3_THRESHOLD}, de {why3} → L2"
        model = model or self.lane
        self.last_reason = (f"L{level}: {why_level} (known={recall.known_ratio:.2f}, siker={sim:.2f}, "
                            f"méret={size:.2f}); {why_model}")
        return Assessment(kind=kind, level=level, model=model, difficulty=d,  # type: ignore[arg-type]
                          predicted_success=round(1 - d, 3), budget=scale_budget(BUDGETS[kind], d),
                          reason=self.last_reason)

    # ── 08/02 §3 ──
    def escalate(self, level: int, failure: Failure, *, interactive: bool | None = None,
                 kind: str = "code", lang: str | None = None, task_level: int | None = None) -> int | None:
        """Next level after a failure (None = give up). The reason is in `last_reason`."""
        live = self.interactive if interactive is None else interactive
        nxt, why = self._escalate(level, failure, live, kind, lang, task_level)
        self.last_reason = why
        return nxt

    def _cloud(self, live: bool, what: str) -> tuple[int | None, str]:
        if not live:
            return None, f"{what}; háttérmunka soha nem megy felhőbe (08/03) → GIVE_UP"
        if self.cloud_model is None:
            return None, f"{what}; a felhő ki van kapcsolva (08/03) → GIVE_UP + hiánylista"
        return 4, f"{what} → L4 ({self.cloud_model}), egyszer, jelezve, kitakarás után"

    def _escalate(self, level: int, f: Failure, live: bool, kind: str, lang: str | None,
                  task_level: int | None) -> tuple[int | None, str]:
        sig = f.signature or ""
        if level >= 4:
            return None, "L4 is bukott → GIVE_UP"
        if f.kind == "llm_unavailable":
            return self._cloud(live, "az Ollama nem érhető el")
        if level <= 1:
            return 2, f"L{level} nem elég ({f.kind}) → L2"
        if f.kind == "missing_knowledge":
            return level, "hiányzó tudás → Web-szörföző (P2), a szint marad"
        if f.kind == "no_progress" and _DOC_ERRORS.search(sig):
            return level, f"ismétlődő {_DOC_ERRORS.search(sig).group(1)} → dokumentáció a webről (P2), a szint marad"  # type: ignore[union-attr]
        if f.kind == "timeout":
            return level, "időtúllépés → ugyanez a szint kisebb részfeladattal (a második után GIVE_UP)"
        if level == 2:
            m3, why3 = self.pick(kind, lang, task_level, tier=3)
            if m3 is None:
                return self._cloud(live, f"L2 bukott ({f.kind}), {why3}")
            c3, _ = self._view(kind, lang, task_level, m3)
            c2, _ = self._view(kind, lang, task_level, self.lane)
            if c3.n >= self.table.min_n and c2.n >= self.table.min_n and c3.rate <= c2.rate:
                return self._cloud(live, f"L2 bukott, de az L3 ({m3}) mérve nem jobb "
                                         f"({c3.passed}/{c3.n} vs {c2.passed}/{c2.n})")
            return 3, f"L2 bukott ({f.kind}) → L3: {why3}"
        return self._cloud(live, f"L3 bukott ({f.kind})")

    def describe(self) -> list[dict[str, Any]]:
        """The measured table, for GET /stats and reports."""
        return [{"kind": k, "lang": lg, "level": lv, "model": m, "mode": md, "n": c.n, "passed": c.passed,
                 "rate": round(c.rate, 3), "lower": round(c.lower, 3),
                 "median_s": None if c.median_ms is None else round(c.median_ms / 1000, 1)}
                for (k, lg, lv, m, md), c in self.table.rows()]


def load_router(cfg: Any = None, *, eval_dir: Path | str | None = None, extra_models: Iterable[str] = (),
                allow_cloud: bool | None = None, cloud_model: str | None = None,
                interactive: bool = True) -> SimpleRouter | StatsRouter:
    """StatsRouter from `<data_dir>/eval/*/results.jsonl` when measurements exist, else SimpleRouter.
    Never raises: a broken config or missing data falls back to the P0 router."""
    try:
        if cfg is None:
            from .config import load_config  # AI-3

            cfg = load_config()
        lane = cfg.models.code or DEFAULT_CODE_MODEL
        root = eval_dir if eval_dir is not None else Path(cfg.data_dir) / "eval"
    except Exception:
        return SimpleRouter()
    table = build_table(load_bench_records(root))
    if not table:
        return SimpleRouter(lane)
    models = [lane, getattr(cfg.models, "roles", None), getattr(cfg.models, "l3", None), *extra_models]
    cloud_on = allow_cloud if allow_cloud is not None else getattr(cfg, "cloud_mode", "off") != "off"
    return StatsRouter(table, lane_model=lane, models=[m for m in models if m],
                       ram_budget_gb=float(getattr(cfg, "ram_budget_gb", DEFAULT_RAM_BUDGET_GB)),
                       allow_cloud=cloud_on,  # the client picks the provider; the label only names L4
                       cloud_model=cloud_model or getattr(cfg, "cloud_model", None) or ("cloud" if cloud_on else None),
                       interactive=interactive)
