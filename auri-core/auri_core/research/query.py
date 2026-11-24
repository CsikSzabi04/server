"""Query building + ranking (03/01 §3): ports of queryExpansion.ts, bilingual.ts, devFocus.ts,
dedup.ts, rerank.ts, relevance.ts, mergeSearches.ts. Pure, offline."""

from __future__ import annotations

import math
import re

from ..lang import detect_lang
from .text import extract_keywords, norm_url, redact_for_search, text_similar
from .trust import domain_trust, host_of
from .types import SearchResult

HU_EN = {
    "függvény": "function", "osztály": "class", "metódus": "method", "változó": "variable", "tömb": "array",
    "objektum": "object", "ciklus": "loop", "feltétel": "condition", "hiba": "error", "kivétel": "exception",
    "hibakeresés": "debugging", "fordítás": "compile", "telepítés": "install", "telepíteni": "install",
    "csomag": "package", "könyvtár": "library", "keretrendszer": "framework", "adatbázis": "database",
    "lekérdezés": "query", "tábla": "table", "kiszolgáló": "server", "kliens": "client", "böngésző": "browser",
    "hálózat": "network", "fájl": "file", "mappa": "folder", "karakterlánc": "string", "szám": "number",
    "visszatérés": "return", "paraméter": "parameter", "argumentum": "argument", "öröklődés": "inheritance",
    "felület": "interface", "esemény": "event", "üzenet": "message", "kód": "code", "programozás": "programming",
    "fejlesztés": "development", "verzió": "version", "gyors": "fast", "lassú": "slow", "biztonság": "security",
    "teljesítmény": "performance", "példa": "example", "oktatóanyag": "tutorial", "dokumentáció": "documentation",
    "hogyan": "how to", "miért": "why", "lista": "list", "listát": "list", "rendezni": "sort", "rendezés": "sort",
    "előtag": "prefix", "előtagot": "prefix", "szöveg": "string", "szótár": "dictionary",
}
_PROG = re.compile(
    r"\b(code|coding|program|programming|function|class|method|api|sdk|library|framework|compile|runtime|debug|"
    r"error|exception|stack ?trace|install|npm|pip|cargo|git|deploy|docker|kubernetes|database|sql|query|endpoint|"
    r"async|await|promise|component|hook|css|html|javascript|typescript|python|pythonban|java|rust|golang|react|"
    r"vue|angular|node|regex|algorithm|array|object|json|http|rest|graphql|frontend|backend|függvény|osztály|"
    r"metódus|kód|programoz\w*|hiba|fordít\w*|telepít\w*|adatbázis|lekérdezés|string|lista\w*)\b",
    re.IGNORECASE,
)
_CODE_HINT = re.compile(r"[{}();=>]|```|\bfunction\b|\bconst\b|\bimport\b|\bclass\b|</?[a-z]+>", re.IGNORECASE)
_ERROR_LINE = re.compile(r"\b[A-Z]\w*(?:Error|Exception)\b|\bTS\d{4}\b|\bERR_[A-Z_]+\b")
_DEV_DOMAINS = (
    "stackoverflow.com", "stackexchange.com", "github.com", "gitlab.com", "developer.mozilla.org", "devdocs.io",
    "npmjs.com", "pypi.org", "crates.io", "pkg.go.dev", "docs.python.org", "nodejs.org", "react.dev", "vuejs.org",
    "angular.io", "typescriptlang.org", "rust-lang.org", "go.dev", "learn.microsoft.com", "docs.oracle.com",
    "baeldung.com", "geeksforgeeks.org", "freecodecamp.org", "css-tricks.com", "web.dev", "developer.chrome.com",
    "digitalocean.com", "dev.to",
)


def is_programming_query(q: str) -> bool:
    return bool(_PROG.search(q))


def to_englishish(q: str) -> str:
    out = []
    for tok in q.lower().split():
        out.append(HU_EN.get(re.sub(r"[.,!?;:()]", "", tok), tok))
    return " ".join(out)


def error_query(text: str) -> str | None:
    """Error-message mode (03/01 §3): the error line's core in quotes, no paths/line numbers."""
    for line in text.splitlines():
        m = _ERROR_LINE.search(line)
        if not m:
            continue
        core = redact_for_search(line[m.start():])
        core = re.sub(r"\(?\b(?:line|sor)\s*\d+\)?|:\d+(?::\d+)?", " ", core)
        core = " ".join(core.split())[:120].rstrip(" .:")
        if len(core) > 8:
            return f'"{core}"'
    return None


def expand_query(question: str, *, max_variants: int = 3, names: tuple[str, ...] = ()) -> list[str]:
    """Deduped search variants, best first: keyword core, (error mode), dev/EN variants (≤ max_variants)."""
    clean = redact_for_search(question, names)
    kw = extract_keywords(clean, 8)
    core = " ".join(kw) if kw else clean
    variants: list[str] = []

    def add(v: str) -> None:
        v = " ".join(v.split())[:256]
        if v and v.lower() not in (x.lower() for x in variants):
            variants.append(v)

    if eq := error_query(question):
        add(eq)
    add(core)
    if detect_lang(question) == "hu":
        en = " ".join(extract_keywords(to_englishish(clean), 8)) or to_englishish(clean)
        add(en)
    if is_programming_query(question):
        add(f"{core} documentation")
        add(f"{core} code example")
    else:
        if clean != core:
            add(clean)
        add(f"{core} how to")
    return variants[: max(1, max_variants)]


def dedupe_hits(hits: list[SearchResult], sim_threshold: float = 0.82) -> list[SearchResult]:
    out: list[SearchResult] = []
    seen: set[str] = set()
    for h in hits:
        key = norm_url(h.url)
        if key in seen:
            continue
        if any(text_similar(o.snippet or o.title, h.snippet or h.title) >= sim_threshold for o in out):
            continue
        seen.add(key)
        out.append(h)
    return out


def _trigrams(s: str) -> set[str]:
    t = f" {s.lower()} "
    return {t[i : i + 3] for i in range(len(t) - 2)}


def _fuzzy(a: str, b: str) -> float:
    if a == b:
        return 1.0
    A, B = _trigrams(a), _trigrams(b)
    if not A or not B:
        return 0.0
    inter = len(A & B)
    return inter / (len(A) + len(B) - inter)


def _dev_bonus(h: SearchResult) -> float:
    host = host_of(h.url)
    dev = 1.0 if any(host == d or host.endswith("." + d) for d in _DEV_DOMAINS) else 0.0
    return dev * 2 + (1.0 if _CODE_HINT.search(h.snippet) else 0.0)


def rerank_smart(query: str, hits: list[SearchResult], top: int = 6, *, dev: bool = False) -> list[SearchResult]:
    """TF-IDF over the hit set + trigram fuzzy match + domain trust (relevance.ts rerankSmart);
    `dev=True` adds the devFocus bias (dev domains, code-bearing snippets)."""
    q_terms = extract_keywords(query, 14)
    hit_terms = [set(extract_keywords(f"{h.title} {h.snippet}", 24)) for h in hits]
    n = len(hits) or 1
    df = {t: sum(1 for ht in hit_terms if t in ht) for t in q_terms}

    def idf(t: str) -> float:
        return math.log((n + 1) / (df.get(t, 0) + 1)) + 1

    scored = []
    for i, (h, ht) in enumerate(zip(hits, hit_terms, strict=True)):
        s = 0.0
        for t in q_terms:
            if t in ht:
                s += idf(t) * 3
            else:
                best = max((_fuzzy(t, w) for w in ht), default=0.0)
                if best >= 0.5:
                    s += best * idf(t) * 1.5
        s += domain_trust(h.url) * 2 + (_dev_bonus(h) if dev else 0.0)
        scored.append((s, i, h))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [h for _, _, h in scored[:top]]


def merge_results(question: str, results: list[list[SearchResult]], top: int = 6) -> list[SearchResult]:
    """mergeSearches.ts: flatten variant results, dedupe, rerank (dev bias for programming questions)."""
    flat = [h for r in results for h in r]
    return rerank_smart(question, dedupe_hits(flat), top, dev=is_programming_query(question))
