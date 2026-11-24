"""Pure text helpers ported from web/src/lib/memory.ts + web/src/autolearn/** (03/01 §8).

extract_keywords · text_similar · norm_url · redact_for_search · key_sentences · fold · norm_quote.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from urllib.parse import urlsplit

# Hungarian + English stop-words (memory.ts STOP, verbatim).
STOP = frozenset(
    [
        "a", "az", "egy", "és", "vagy", "de", "hogy", "nem", "is", "meg", "ki", "be", "el", "fel", "le", "rá",
        "rol", "ról", "ben", "ban", "nak", "nek", "val", "vel", "mint", "csak", "már", "még", "ez", "az", "ezt",
        "azt", "itt", "ott", "így", "úgy", "mert", "ha", "majd", "lesz", "volt", "van", "vannak", "lenne", "te",
        "én", "ő", "mi", "ti", "ők", "enyém", "tied", "övé", "nekem", "neked", "neki", "minden", "semmi", "valami",
        "nagyon", "kicsit", "kérlek", "the", "a", "an", "and", "or", "but", "that", "not", "is", "are", "was",
        "were", "be", "been", "being", "to", "of", "in", "on", "at", "for", "with", "as", "by", "this", "that",
        "these", "those", "it", "its", "from", "your", "you", "i", "we", "they", "he", "she", "my", "me", "do",
        "does", "did", "so", "if", "then", "what", "which", "who", "how", "why", "when", "where", "can", "will",
        "would", "could", "should", "just", "like", "about", "into", "over"
    ]
)
_WORD = re.compile(r"[^\W_]{3,}")  # letters/digits, 3+ (unicode-aware, like [\p{L}\p{N}]{3,})
_TOKENS = _WORD


def extract_keywords(text: str, max_n: int = 10) -> list[str]:
    """Top-frequency keywords, stop-words removed (memory.ts extractKeywords; ties keep first-seen order)."""
    words = [w for w in _WORD.findall(text.lower()) if w not in STOP]
    return [w for w, _ in Counter(words).most_common(max_n)]


def tokens(s: str) -> set[str]:
    return set(_TOKENS.findall(s.lower()))


def text_similar(a: str, b: str) -> float:
    """Jaccard similarity of two short texts (dedup.ts textSimilar)."""
    A, B = tokens(a), tokens(b)
    if not A or not B:
        return 0.0
    inter = len(A & B)
    return inter / (len(A) + len(B) - inter)


def norm_url(url: str) -> str:
    """Host (without www.) + path without trailing slash, lower-case (dedup.ts normUrl)."""
    try:
        u = urlsplit(url)
        if not u.hostname:
            raise ValueError
        return (u.hostname.removeprefix("www.") + u.path.rstrip("/")).lower()
    except ValueError:
        return url.strip().lower()


_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE = re.compile(r"(?:\+?\d[\s-]?){7,}")
_LONGNUM = re.compile(r"\b\d{6,}\b")
_WINPATH = re.compile(r"[A-Za-z]:[\\/](?:[^\s\\/]+[\\/])*")  # C:\Users\<name>\… (error-message mode)
_UNIXHOME = re.compile(r"/(?:home|Users)/[^\s/]+")


def redact_for_search(query: str, names: tuple[str, ...] = ()) -> str:
    """Strip obvious PII before a query leaves the machine (redact.ts + path filter, 03/01 §3)."""
    q = _WINPATH.sub(" ", query)
    q = _UNIXHOME.sub(" ", q)
    q = _EMAIL.sub(" ", q)
    q = _PHONE.sub(" ", q)
    q = _LONGNUM.sub(" ", q)
    for name in names:
        n = name.strip()
        if len(n) > 1:
            q = re.sub(rf"\b{re.escape(n)}\b", " ", q, flags=re.IGNORECASE)
    return " ".join(q.split())


def fold(s: str) -> str:
    """Lower-case, accents removed (for comparisons only)."""
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))


_QUOTES = str.maketrans({"\u201c": '"', "\u201d": '"', "\u201e": '"', "\u2018": "'", "\u2019": "'",
                         "\u00ab": '"', "\u00bb": '"', "\u2032": "'", "\u00a0": " "})
_ZERO_WIDTH = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")


def norm_quote(s: str) -> str:
    """Whitespace + quote-mark normalisation for the verbatim-quote check (03/04 §3)."""
    s = _ZERO_WIDTH.sub("", s.translate(_QUOTES))
    return " ".join(s.split())


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    return [p.strip() for p in parts if len(p.strip()) >= 24]


def key_sentences(text: str, query: str, *, max_sentences: int = 3, max_chars: int = 480) -> list[str]:
    """The most informative sentences for `query`, in original order (keyContent.ts keySentences)."""
    qk = set(extract_keywords(query, 12))
    scored = []
    for i, s in enumerate(_sentences(text)):
        kws = extract_keywords(s, 20)
        overlap = sum(1 for k in kws if k in qk)
        scored.append((overlap * 4 + min(len(kws), 12) + (2 if i == 0 else 0), i, s))
    picked: list[tuple[int, str]] = []
    chars = 0
    for _score, i, s in sorted(scored, key=lambda x: (-x[0], x[1])):
        if len(picked) >= max_sentences:
            break
        if chars + len(s) > max_chars:
            continue
        picked.append((i, s))
        chars += len(s)
    return [s for _, s in sorted(picked)]


def stem(word: str) -> str:
    """Crude suffix-tolerant stem: the first 6 letters, accents removed ("pythonban" → "python",
    "előtagot" → "elotag"). Hungarian agglutination makes whole-word matching too strict."""
    f = fold(word)
    return f[:6] if len(f) > 6 else f


def keyword_overlap(query: str, text: str) -> int:
    """How many of the query's keywords occur in `text` (accent- and suffix-tolerant)."""
    t = fold(text)
    return sum(1 for k in extract_keywords(query, 12) if stem(k) in t)
