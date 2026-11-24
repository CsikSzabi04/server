"""Hungarian text helpers for the fast-path and the tools (AI-2): normalisation, suffix
stripping, number words, durations, monitor phrases, simple date/time phrases.

Conservative by design: every parser returns None when it isn't sure, so the caller
hands the utterance to the LLM instead of guessing (spec 5.5 / Appendix B).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta

from rapidfuzz import fuzz, process

# ── normalisation ────────────────────────────────────────────────────────────


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm(s: str) -> str:
    """Lower-case, accents removed, punctuation → space, single spaces."""
    s = strip_accents(s.lower())
    s = re.sub(r"[^\w%:\-]+", " ", s)
    return " ".join(s.split())


_ARTICLE = re.compile(r"^(?:a|az|egy)\s+", re.IGNORECASE)
_HYPHEN_SUFFIX = re.compile(r"-(?:t|ot|et|öt|at|ra|re|ba|be|ban|ben|on|en|ön|n|val|vel|nak|nek)$", re.IGNORECASE)
_ACC_SUFFIX = re.compile(r"(?:ot|et|öt|at|t)$", re.IGNORECASE)


def name_candidates(phrase: str) -> list[str]:
    """Spoken object phrase → normalised candidates for an alias lookup.

    "a VS Code-ot" → ["vs code"], "a böngészőt" → ["bongeszot", "bongeszo"],
    "a figmát" → [..., "figma"] (Hungarian lengthens a final a/e before a suffix).
    """
    p = _ARTICLE.sub("", phrase.strip().strip(".,!?").strip())
    p = _HYPHEN_SUFFIX.sub("", p)
    out = [norm(p)]
    words = p.split()
    if words:
        last = words[-1]
        stem = _ACC_SUFFIX.sub("", last)
        if stem and stem != last:
            variants = {stem}
            if stem[-1:] in "áé":
                variants.add(stem[:-1] + {"á": "a", "é": "e"}[stem[-1]])
            for v in variants:
                out.append(norm(" ".join([*words[:-1], v])))
    seen: list[str] = []
    for c in out:
        if c and c not in seen:
            seen.append(c)
    return seen


# ── numbers ──────────────────────────────────────────────────────────────────

_UNITS = {"egy": 1, "kettő": 2, "két": 2, "három": 3, "négy": 4, "öt": 5, "hat": 6, "hét": 7, "nyolc": 8, "kilenc": 9}
_TENS = {
    10: "tíz",
    20: "húsz",
    30: "harminc",
    40: "negyven",
    50: "ötven",
    60: "hatvan",
    70: "hetven",
    80: "nyolcvan",
    90: "kilencven",
}
_TENS_PREFIX = {10: "tizen", 20: "huszon"}


def _number_words() -> dict[str, int]:
    words: dict[str, int] = {"nulla": 0, "száz": 100, "egyszáz": 100}
    words.update(_UNITS)
    for tens, w in _TENS.items():
        words[w] = tens
        prefix = _TENS_PREFIX.get(tens, w)
        for uw, u in _UNITS.items():
            words[prefix + uw] = tens + u
    return words


NUMBER_WORDS_HU = _number_words()  # correctly accented spellings, 0..100 (+ "két" variants)
NUMBER_WORDS = {strip_accents(k): v for k, v in NUMBER_WORDS_HU.items()}  # accent-free (fuzzy)
# Accented suffixes: "ötvenet" = ötven+et ✓, but "huszöt" ≠ húsz+öt (that would be "húszat"),
# so a misheard "Huszöt" can't be mis-parsed as 20 — it falls through to fuzzy (→ 25).
_NUM_SUFFIXES = (
    "re",
    "ra",
    "as",
    "es",
    "ös",
    "os",
    "et",
    "at",
    "ot",
    "öt",
    "szor",
    "szer",
    "ször",
    "kor",
    "an",
    "en",
    "ig",
    "ból",
    "ből",
    "tól",
    "től",
)
_DIGITS = re.compile(r"^(\d{1,4})(?:[-%].*|[a-z]*)$")


def parse_number(token: str) -> int | None:
    """One token → int. Digits ("25", "25-re", "30%"), words ("huszonöt", "harmincra",
    "ötvenet"), and STT misspellings via fuzzy match for tokens ≥ 5 letters ("Huszöt" → 25).
    Short words must be spelled right: "hat" = 6 but "hát" (well…) = None."""
    raw = token.lower().strip(".,!?;:")
    t = norm(token).replace(" ", "")
    if not t:
        return None
    m = _DIGITS.match(t)
    if m:
        return int(m.group(1))
    if raw in NUMBER_WORDS_HU:
        return NUMBER_WORDS_HU[raw]
    for s in sorted(_NUM_SUFFIXES, key=len, reverse=True):
        if raw.endswith(s) and raw[: -len(s)] in NUMBER_WORDS_HU:
            return NUMBER_WORDS_HU[raw[: -len(s)]]
    if len(t) >= 5:  # short words ("hat"/"hát", "het"/"hét") are too ambiguous to fuzz
        hit = process.extractOne(t, NUMBER_WORDS.keys(), scorer=fuzz.ratio, score_cutoff=85)
        if hit:
            return NUMBER_WORDS[hit[0]]
    return None


def split_number(token: str) -> tuple[int, str] | None:
    """Exact (no fuzzy) number word + Hungarian suffix: "nyolckor" → (8, "kor")."""
    raw = token.lower()
    if raw in NUMBER_WORDS_HU:
        return NUMBER_WORDS_HU[raw], ""
    for s in sorted(_NUM_SUFFIXES, key=len, reverse=True):
        if raw.endswith(s) and raw[: -len(s)] in NUMBER_WORDS_HU:
            return NUMBER_WORDS_HU[raw[: -len(s)]], s
    return None


_UNIT_NEXT = re.compile(r"^(?:másodperc|masodperc|perc|óra|ora|százalék|szazalek|fok|%)\w*$")


def digitize(text: str) -> str:
    """Spell-out numbers → digits where it is unambiguous, for the LLM's sake.

    MEASURED (2026-11-21, eval_tools, gemma4:e2b): "huszonöt perces" → 1200 s, "holnap reggel
    nyolckor" → 09:00, "este hétkor" → 10:00. Small models are bad at Hungarian number words;
    the deterministic parser is not. Converted only when unambiguous: long words
    ("huszonöt"), the "-kor" time suffix ("nyolckor" → "8-kor"), or a unit right after
    ("hét perc" → "7 perc"). "egy" (also the article), "hét" (also "week"), "hat" (also a
    verb) etc. stay words otherwise: "jövő héten", "egy kis zene", "a hét napjai" untouched.
    """
    parts = re.split(r"(\s+)", text)
    words = [i for i, p in enumerate(parts) if p and not p.isspace()]
    for pos, i in enumerate(words):
        tok = parts[i]
        core = tok.rstrip(".,!?;:…")
        punct = tok[len(core) :]
        hit = split_number(core)
        if hit is None:
            continue
        value, suffix = hit
        stem = core[: len(core) - len(suffix)] if suffix else core
        nxt = parts[words[pos + 1]].lower().strip(".,!?;:…") if pos + 1 < len(words) else ""
        if not (len(strip_accents(stem)) >= 5 or suffix == "kor" or _UNIT_NEXT.match(nxt)):
            continue
        parts[i] = f"{value}-{suffix}{punct}" if suffix else f"{value}{punct}"
    return "".join(parts)


# ── durations ────────────────────────────────────────────────────────────────

_FRACTIONS = {"másfél": 5400, "háromnegyed": 2700, "negyed": 900, "fél": 1800}
_UNIT_S = {"másodperc": 1, "masodperc": 1, "mp": 1, "perc": 60, "óra": 3600, "ora": 3600}
_UNIT_RX = "másodperc|masodperc|mp|perc|óra|ora"
_DUR = re.compile(rf"(?P<num>[\w%-]+)\s+(?P<unit>{_UNIT_RX})\w*")


def parse_duration(text: str) -> int | None:
    """Total seconds from phrases like "25 perc", "huszonöt percre", "fél óra",
    "egy óra tíz perc", "negyed óra múlva". None if no clear duration.
    Works on the accented text (number words need their accents, see parse_number)."""
    t = " ".join(re.sub(r"[^\w%\-]+", " ", text.lower()).split())
    total = 0
    found = False
    for frac, secs in _FRACTIONS.items():
        rx = rf"\b{frac}\s+(?:óra|ora)\w*"
        if re.search(rx, t):
            total += secs
            found = True
            t = re.sub(rx, " ", t)
    for m in _DUR.finditer(t):
        n = parse_number(m.group("num"))
        if n is None:
            continue
        total += n * _UNIT_S[m.group("unit")]
        found = True
    return total if found and total > 0 else None


def say_duration(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h} óra")
    if m:
        parts.append(f"{m} perc")
    if s and not h:
        parts.append(f"{s} másodperc")
    return " ".join(parts) or "0 másodperc"


# ── monitors ─────────────────────────────────────────────────────────────────

_MON_WORDS = {
    "bal": 1, "baloldali": 1, "bal oldali": 1, "elso": 1, "egyes": 1, "1": 1, "1-es": 1,
    "kozep": 2, "kozepso": 2, "masodik": 2, "kettes": 2, "2": 2, "2-es": 2, "fo": 2,
    "jobb": 3, "jobboldali": 3, "jobb oldali": 3, "harmadik": 3, "harmas": 3, "3": 3, "3-as": 3,
}  # fmt: skip
_MON_KEYS = "|".join(sorted((re.escape(k) for k in _MON_WORDS), key=len, reverse=True))
_MON_PHRASE = re.compile(
    rf"\b(?:(?:a|az)\s+)?(?P<w>{_MON_KEYS})\s*(?:oldali\s+)?(?:monitor|kepernyo|kijelzo)\w*",
)
_MON_SHORT = re.compile(r"\b(?:a|az)\s+(?P<w>egyes|kettes|harmas)(?:en|on|re|ra|en)\b")
_MON_NUM = re.compile(r"\b(?:monitor|kepernyo)\w*\s+(?P<w>[123])\b")


def extract_monitor(text: str) -> tuple[int | None, str]:
    """("nyisd meg a vs code-ot a középső monitoron") → (2, "nyisd meg a vs code-ot").
    Works on the normalised text; returns the rest normalised too."""
    t = norm(text)
    for rx in (_MON_PHRASE, _MON_SHORT, _MON_NUM):
        m = rx.search(t)
        if m:
            rest = " ".join((t[: m.start()] + " " + t[m.end() :]).split())
            return _MON_WORDS[m.group("w")], rest
    return None, t


# ── simple date/time phrases (set_reminder) ──────────────────────────────────

_HHMM = re.compile(r"\b(?P<h>[01]?\d|2[0-3])(?::|\.|\s+ora\s+)(?P<m>[0-5]\d)\b")
_H_KOR = re.compile(r"\b(?P<h>[01]?\d|2[0-3])(?:-?kor|\s+orakor)\b")
_ISO = re.compile(r"\b(?P<d>\d{4}-\d{2}-\d{2})[ t](?P<h>\d{1,2}):(?P<m>\d{2})\b")


def parse_when(text: str, now: datetime) -> datetime | None:
    """ "18:30", "holnap 9-kor", "2026-11-21 18:30", "10 perc múlva", "fél óra múlva",
    "este 8-kor" → datetime (future). None if unclear."""
    t = norm(text)
    m = _ISO.search(text)
    if m:
        try:
            return datetime.fromisoformat(f"{m.group('d')} {int(m.group('h')):02d}:{m.group('m')}")
        except ValueError:
            return None
    if "mulva" in t or t.startswith(("in ", "ido ")):
        secs = parse_duration(text)  # the accented original (number words need accents)
        return now + timedelta(seconds=secs) if secs else None
    day = now.date()
    if re.search(r"\bholnaputan\b", t):
        day += timedelta(days=2)
    elif re.search(r"\bholnap\b", t):
        day += timedelta(days=1)
    hm: tuple[int, int] | None = None
    if m := _HHMM.search(t):
        hm = (int(m.group("h")), int(m.group("m")))
    elif m := _H_KOR.search(t):
        hm = (int(m.group("h")), 0)
    if hm is None:
        return None
    h, mi = hm
    if h < 12 and re.search(r"\b(?:este|delutan|ejjel)\b", t) and h != 0:
        h += 12
    when = datetime.combine(day, datetime.min.time()).replace(hour=h % 24, minute=mi)
    if when <= now and day == now.date():
        when += timedelta(days=1)  # "9-kor" said at 10:00 → tomorrow 9:00
    return when


def say_when(when: datetime, now: datetime) -> str:
    if when.date() == now.date():
        day = "ma"
    elif when.date() == (now + timedelta(days=1)).date():
        day = "holnap"
    else:
        day = when.strftime("%m.%d.")
    return f"{day} {when:%H:%M}"
