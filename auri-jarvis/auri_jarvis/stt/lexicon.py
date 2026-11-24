"""Lexicon correction for STT output (spec 5.4).

Parakeet is fast (~0.2 s) but mishears Hungarian verbs and English brand names inside
Hungarian sentences (measured: "nyisd meg" → "nycs meg", "Visual Studio" → "visol studió").
Two conservative layers fix that without touching ordinary words:
  1. `replace`: known mishearings → correct phrase (case-insensitive, whole words)
  2. `terms`: fuzzy match of 1–3 word spans against known names (apps, "Auri"…);
     a Hungarian suffix after a hyphen is kept ("Crome-ot" → "Chrome-ot").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_WORD = re.compile(r"\w+(?:-\w+)*", re.UNICODE)


def _with_suffix(replacement: str, suffix: str) -> str:
    """Re-attach a Hungarian suffix; proper names get a hyphen ("VS Code-ot")."""
    if not suffix:
        return replacement
    return f"{replacement}-{suffix}" if any(c.isupper() for c in replacement) else replacement + suffix


@dataclass
class Lexicon:
    replace: dict[str, str] = field(default_factory=dict)
    terms: list[str] = field(default_factory=list)
    threshold: float = 85.0

    def __post_init__(self) -> None:
        # longest phrases first so "visol studió" wins over "studió"; a Hungarian suffix
        # glued to the misheard word is kept ("vízkódot" → "VS Code-ot")
        self._rules = [
            (re.compile(rf"(?<!\w){re.escape(k)}(\w*)", re.IGNORECASE), v)
            for k, v in sorted(self.replace.items(), key=lambda kv: -len(kv[0]))
        ]
        self._terms = [(t, t.casefold(), len(t.split())) for t in self.terms if len(t) >= 4]

    @classmethod
    def load(cls, path: str | Path) -> Lexicon:
        import yaml

        p = Path(path)
        if not p.is_file():
            return cls()
        data = yaml.safe_load(p.read_text("utf-8")) or {}
        return cls(
            replace=dict(data.get("replace") or {}),
            terms=list(data.get("terms") or []),
            threshold=float(data.get("threshold", 85)),
        )

    def correct(self, text: str) -> str:
        out = text
        for rx, repl in self._rules:
            out = rx.sub(lambda m, r=repl: _with_suffix(r, m.group(1)), out)
        return self._fuzzy_terms(out)

    def _fuzzy_terms(self, text: str) -> str:
        if not self._terms:
            return text
        from rapidfuzz import fuzz

        words = list(_WORD.finditer(text))
        result: list[tuple[int, int, str]] = []  # (start, end, replacement)
        i = 0
        while i < len(words):
            best: tuple[float, int, str, str] | None = None  # score, n, term, suffix
            for term, folded, n in self._terms:
                if i + n > len(words):
                    continue
                span_words = [w.group() for w in words[i : i + n]]
                last, suffix = span_words[-1], ""
                if "-" in last:  # keep a Hungarian suffix: "Crome-ot" → base "Crome", "-ot"
                    base, _, rest = last.partition("-")
                    span_words[-1], suffix = base, "-" + rest
                candidate = " ".join(span_words)
                if candidate.casefold().startswith(folded):
                    best = None  # already correct, maybe with a suffix ("Aurit") — never "fix" it
                    break
                if abs(len(candidate) - len(term)) > max(2, len(term) // 3):
                    continue
                score = fuzz.ratio(candidate.casefold(), folded)
                if score >= self.threshold and (best is None or score > best[0]):
                    best = (score, n, term, suffix)
            if best is not None:
                _, n, term, suffix = best
                result.append((words[i].start(), words[i + n - 1].end(), term + suffix))
                i += n
            else:
                i += 1
        for start, end, repl in reversed(result):
            text = text[:start] + repl + text[end:]
        return text
