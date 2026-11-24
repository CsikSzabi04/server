"""auri_core.lang — the ONE shared language detector (NK11, owner: AI-1).

Port of web/src/brain/lang.ts (accent check + function-word voting). The regression cases of
web/tests/brain-answers.test.ts are in tests/mind/test_lang.py. One deliberate difference: Python's
`\\b` is Unicode-aware, JS's is ASCII-only, so here "öa" is one word (no vote for "a"). That is the
more correct reading and does not change any shared case.
"""

from __future__ import annotations

import re

from .contracts import HumanLang

_HU_FUNC = re.compile(
    r"\b(a|az|és|nem|hogy|vagyok|vagy|vagyunk|vannak|te|én|ő|mi|ti|ők|ki|kik|mik|igen|köszönöm|koszi|szia|"
    r"sziasztok|van|nincs|mit|hol|miért|mikor|milyen|melyik|mennyi|hogyan|kérlek|jó|egy|ez|ezt|azt|de|meg|"
    r"csak|kell|lehet|tudsz|tudod)\b"
)
_DE_FUNC = re.compile(r"\b(der|die|das|und|nicht|ich|ist|ein|eine|mit|auch|wie|was|ja|nein|danke|hallo|du|wir|sie|sehr)\b")
_EN_FUNC = re.compile(r"\b(the|and|not|is|are|a|an|i|you|we|they|yes|no|thanks|hello|what|where|why|please|have)\b")


def detect_lang(text: str) -> HumanLang:
    """Best-effort guess: 'hu' | 'en' | 'de' | 'unknown'."""
    t = text.lower()
    if not re.search(r"[a-zäöüßáéíóúőű]", t):
        return "unknown"
    if re.search(r"[őűáéíóú]", t):  # Hungarian-unique accents (German has none of these)
        return "hu"
    if re.search(r"[äß]", t):  # German-unique marks
        return "de"
    hu, de, en = (len(r.findall(t)) for r in (_HU_FUNC, _DE_FUNC, _EN_FUNC))
    # strict '>': a tie (the lone article "a" is Hungarian and English) falls through to English
    if hu > 0 and hu > de and hu > en:
        return "hu"
    if de > 0 and de > en:
        return "de"
    if hu > 0 and hu >= en and re.search(r"[öü]", t):  # "a Föld" → Hungarian
        return "hu"
    if en > 0:
        return "en"
    if re.search(r"[öü]", t):  # ö/ü with no other signal leans German
        return "de"
    return "en"


def answer_lang(text: str, requested: str | None = None) -> str:
    """The language Auri answers in: the caller's choice, else Hungarian only when detected (hu/en)."""
    if requested in ("hu", "en"):
        return requested
    return "hu" if detect_lang(text) == "hu" else "en"
