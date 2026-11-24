"""Tiny HU/EN language guess for transcripts and TTS voice choice (no dependencies)."""

from __future__ import annotations

import re

_HU_ACCENTS = re.compile(r"[áéíóöőúüű]", re.IGNORECASE)
_HU_WORDS = re.compile(
    r"\b(a|az|és|nem|hogy|van|vagy|egy|ez|ki|mi|mit|hol|miért|mikor|milyen|hány|kérlek|igen|"
    r"nyisd|indítsd|kapcsold|szólj|állíts|hangerő|szia|köszi|meg|be|ki|le|fel)\b",
    re.IGNORECASE,
)
_EN_WORDS = re.compile(
    r"\b(the|and|is|are|what|who|where|why|how|please|open|play|stop|turn|set|you|i|my|it|to|of)\b",
    re.IGNORECASE,
)


def guess_lang(text: str, default: str = "hu") -> str:
    """'hu' or 'en' (Hungarian wins ties: the user's primary language)."""
    if not text.strip():
        return default
    if _HU_ACCENTS.search(text):
        return "hu"
    hu, en = len(_HU_WORDS.findall(text)), len(_EN_WORDS.findall(text))
    if en > hu:
        return "en"
    if hu > 0:
        return "hu"
    return default
