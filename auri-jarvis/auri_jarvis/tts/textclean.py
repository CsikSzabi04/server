"""Make text speakable: no markdown, emoji or raw URLs; times / symbols read naturally.

Numbers stay as digits — Piper's espeak-ng reads Hungarian digits correctly (measured:
"25 perc", "2026. november 20." come out right). Only "HH:MM" needs help, because it
would otherwise be read as two separate numbers.
"""

from __future__ import annotations

import re

_LINK_SAID = {"hu": "a linket kiírtam a képernyőre", "en": "the link is on the screen"}
_EMOJI = re.compile("[\U0001f000-\U0001faff\U00002600-\U000027bf\U00002300-\U000023ff\U0000fe0f\U0000200d\U00002b50\U00002b55]+")
_TIME = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)(?:-(\w+))?\b")
# suffix after a time: "9:00-kor" → "9 órakor", "10:00-ig" → "10 óráig", "8:30-ra" → "8 óra 30 percre"
_ORA = {"kor": "órakor", "ra": "órára", "re": "órára", "ig": "óráig", "tól": "órától", "től": "órától"}
_PERC = {"kor": "perckor", "ra": "percre", "re": "percre", "ig": "percig", "tól": "perctől", "től": "perctől"}


def _time_hu(m: re.Match[str]) -> str:
    h, mm, suf = int(m.group(1)), int(m.group(2)), (m.group(3) or "")
    if mm == 0:
        return f"{h} {_ORA.get(suf, 'óra' + suf)}"
    return f"{h} óra {mm} {_PERC.get(suf, 'perc' + suf)}"


def clean_for_tts(text: str, lang: str = "hu") -> str:
    t = text
    t = re.sub(r"```.*?```", " ", t, flags=re.S)  # stray fenced code
    t = re.sub(r"`([^`]+)`", r"\1", t)  # inline code → plain words
    t = re.sub(r"!?\[([^\]]+)\]\((?:https?://)?[^)]+\)", r"\1", t)  # [text](url) → text
    t = re.sub(r"https?://\S+|www\.\S+", _LINK_SAID.get(lang, _LINK_SAID["en"]), t)
    t = re.sub(r"(\*\*|__|~~)(?=\S)(.+?)(?<=\S)\1", r"\2", t)  # bold / strike
    t = re.sub(r"(?<!\w)([*_])(?=\S)(.+?)(?<=\S)\1(?!\w)", r"\2", t)  # italics (not snake_case)
    t = re.sub(r"^\s{0,3}(#{1,6}\s+|[-*+•]\s+|>\s?)", "", t, flags=re.M)  # headings, bullets, quotes
    t = re.sub(r"^\s{0,3}\d+[.)]\s+(?=\S)", "", t, flags=re.M)  # numbered list markers
    t = re.sub(r"\|", ", ", t)  # table pipes
    t = _EMOJI.sub("", t)
    if lang == "hu":
        t = _TIME.sub(_time_hu, t)
        t = re.sub(r"(\d)\s?%", r"\1 százalék", t)
        t = t.replace("&", " és ")
    else:
        t = re.sub(r"(\d)\s?%", r"\1 percent", t)
        t = t.replace("&", " and ")
    t = re.sub(r"\s*(->|→|=>)\s*", ", ", t)
    t = re.sub(r"[*#_~`]+", " ", t)  # leftovers
    return re.sub(r"\s+", " ", t).strip()
