"""App / URL allowlist from config/apps.yaml + spoken-name resolution (AI-2).

Resolution is deliberately strict: exact alias match, otherwise rapidfuzz ratio ≥ 85 on
the normalised name with a clear margin over the runner-up. Anything less → None, so the
fast-path hands the utterance to the LLM instead of opening the wrong thing (spec App. B).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml
from rapidfuzz import fuzz

from ..mind.hu_text import name_candidates, norm

FUZZY_MIN = 85
FUZZY_MARGIN = 5


@dataclass(frozen=True)
class AppEntry:
    id: str
    kind: Literal["app", "url"]
    name: str
    target: str  # exe path (expanded) or URL
    args: tuple[str, ...] = ()
    window_match: str | None = None
    public: bool = False
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Match:
    entry: AppEntry
    score: float


@dataclass
class AppCatalog:
    entries: dict[str, AppEntry] = field(default_factory=dict)
    browser: str | None = None  # app id used for open_url

    @classmethod
    def load(cls, path: Path) -> AppCatalog:
        try:
            data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except FileNotFoundError:
            return cls()
        cat = cls()
        for kind, section in (("app", "apps"), ("url", "urls")):
            for app_id, spec in (data.get(section) or {}).items():
                if not isinstance(spec, dict):
                    continue
                target = spec.get("path") if kind == "app" else spec.get("url")
                if not target:
                    continue
                if kind == "app":
                    target = os.path.expandvars(str(target))
                aliases = tuple(norm(a) for a in [app_id, spec.get("name", ""), *(spec.get("aliases") or [])] if a)
                cat.entries[str(app_id)] = AppEntry(
                    id=str(app_id),
                    kind=kind,  # type: ignore[arg-type]
                    name=str(spec.get("name") or app_id),
                    target=str(target),
                    args=tuple(str(a) for a in spec.get("args") or ()),
                    window_match=spec.get("window_match"),
                    public=bool(spec.get("public", False)),
                    aliases=tuple(dict.fromkeys(aliases)),
                )
        browser = data.get("browser")
        cat.browser = str(browser) if browser else None
        return cat

    def get(self, app_id: str) -> AppEntry | None:
        return self.entries.get(app_id)

    def browser_path(self) -> str | None:
        b = self.entries.get(self.browser or "")
        return b.target if b and b.kind == "app" else None

    def resolve(self, phrase: str, *, kind: Literal["app", "url"] | None = None) -> Match | None:
        """Spoken phrase ("a VS Code-ot", "krómot") → entry, or None when unsure."""
        cands = name_candidates(phrase)
        if not cands:
            return None
        best: dict[str, float] = {}
        for e in self.entries.values():
            if kind and e.kind != kind:
                continue
            score = 0.0
            for c in cands:
                for a in e.aliases:
                    s = 100.0 if c == a else fuzz.ratio(c, a)
                    score = max(score, s)
            best[e.id] = score
        if not best:
            return None
        ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)
        top_id, top = ranked[0]
        second = ranked[1][1] if len(ranked) > 1 else 0.0
        if top < FUZZY_MIN or (top < 100 and top - second < FUZZY_MARGIN):
            return None
        return Match(self.entries[top_id], top)
