"""Source trust (03/03): class A–F, the trust score, TTL, registrable domain, independence.

Ported from web/src/autolearn/trust.ts + devFocus.ts; the class table and the score are 03/03 §2–3.
All coefficients are starting estimates (to be calibrated, 03/03 §3).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from .text import text_similar
from .types import PageKind, SourceClass

PRIOR: dict[str, float] = {"A": 0.90, "B": 0.85, "C": 0.70, "D": 0.60, "E": 0.40, "F": 0.10}

# A: official docs, language specs, RFCs (trust.ts HIGH list)
_A = (
    "developer.mozilla.org", "nodejs.org", "react.dev", "reactjs.org", "typescriptlang.org", "w3.org",
    "whatwg.org", "python.org", "docs.python.org", "rust-lang.org", "go.dev", "golang.org",
    "developer.apple.com", "developer.android.com", "learn.microsoft.com", "docs.microsoft.com",
    "kubernetes.io", "postgresql.org", "sqlite.org", "tailwindcss.com", "getbootstrap.com",
    "developer.chrome.com", "web.dev", "rfc-editor.org", "ietf.org", "vuejs.org", "angular.dev",
    "docs.oracle.com", "pkg.go.dev", "docs.rs", "fastapi.tiangolo.com", "docs.pydantic.dev",
)
# C: Q&A
_C = ("stackoverflow.com", "stackexchange.com", "superuser.com", "serverfault.com", "askubuntu.com")
# D: known professional sites + code hosts (a random repo is not "the library's own repo", 03/03 §2)
_D = (
    "wikipedia.org", "github.com", "gitlab.com", "npmjs.com", "pypi.org", "crates.io", "freecodecamp.org",
    "css-tricks.com", "smashingmagazine.com", "digitalocean.com", "baeldung.com", "devdocs.io",
    "geeksforgeeks.org", "realpython.com",
)
# F: content farms / mirrors (grey list; extendable by overrides)
_F = ("w3schools.blog", "codegrepper.com", "stackoom.com", "itecnote.com", "programmerah.com")

# Second-level suffixes and hosting platforms where each sub-domain is a separate site.
_MULTI_LABEL = (
    "co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au", "co.jp", "co.nz", "com.br", "co.in",
    "github.io", "gitlab.io", "pages.dev", "vercel.app", "netlify.app", "herokuapp.com", "blogspot.com",
    "wordpress.com", "readthedocs.io",
)

VOLATILE = re.compile(
    r"\b(price|cost|ár|árak|news|hír|today|latest|legújabb|20\d\d|version|verzió|release|kiadás)\b", re.IGNORECASE
)


@dataclass
class TrustOverrides:
    """trust_overrides.yaml equivalent (03/03 §6): boost → class, grey → F, block → never fetched."""

    boost: dict[str, SourceClass] = field(default_factory=dict)
    grey: set[str] = field(default_factory=set)
    block: set[str] = field(default_factory=set)


def host_of(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").removeprefix("www.").lower()
    except ValueError:
        return ""


def _in(host: str, domains: tuple[str, ...] | set[str]) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


def registrable_domain(url_or_host: str) -> str:
    """eTLD+1 heuristic (no public-suffix list): docs.python.org → python.org; x.github.io stays."""
    host = host_of(url_or_host) if "/" in url_or_host else url_or_host.lower().removeprefix("www.")
    labels = [p for p in host.split(".") if p]
    if len(labels) <= 2:
        return host
    for suffix in _MULTI_LABEL:
        n = suffix.count(".") + 1
        if ".".join(labels[-n:]) == suffix:
            return ".".join(labels[-(n + 1):])
    return ".".join(labels[-2:])


def page_kind(url: str) -> PageKind:
    host = host_of(url)
    if _in(host, _C):
        return "qa"
    if _in(host, ("github.com", "gitlab.com", "raw.githubusercontent.com")):
        return "repo"
    if _in(host, _A) or host.startswith("docs.") or ".readthedocs." in host or "/docs/" in url:
        return "docs"
    if _in(host, ("medium.com", "dev.to", "hashnode.dev", "substack.com")) or "/blog/" in url:
        return "blog"
    return "other"


def source_class(url: str, overrides: TrustOverrides | None = None) -> SourceClass:
    host = host_of(url)
    o = overrides or TrustOverrides()
    if not host:
        return "F"
    for d, cls in o.boost.items():
        if _in(host, (d,)):
            return cls
    if _in(host, o.grey) or _in(host, _F):
        return "F"
    if _in(host, _A):
        return "A"
    if _in(host, _C):
        return "C"
    if _in(host, _D):
        return "D"
    return "E"


def domain_trust(url: str) -> float:
    """trust.ts domainTrust: 1 official docs, 0.65 known good, 0.4 unknown, 0.3 no host."""
    host = host_of(url)
    if not host:
        return 0.3
    if _in(host, _A):
        return 1.0
    if _in(host, _C) or _in(host, _D):
        return 0.65
    return 0.4


def blocked(url: str, overrides: TrustOverrides | None = None) -> bool:
    return bool(overrides) and _in(host_of(url), overrides.block)  # type: ignore[union-attr]


def trust_score(
    cls: SourceClass,
    *,
    age_days: float = 0.0,
    ttl_days: float = 180.0,
    version_match: str = "unknown",
    independent_agreeing: int = 0,
    contradicted_by_higher: bool = False,
    sandbox: str = "not_run",
    suspicious: bool = False,
) -> float:
    """03/03 §3 `trust()`, verbatim. independent_agreeing excludes the source itself."""
    s = PRIOR[cls]
    if age_days > ttl_days:
        s *= 0.7
    if version_match == "no":
        s *= 0.5
    s += min(0.15, 0.08 * independent_agreeing)
    if contradicted_by_higher:
        s -= 0.3
    if sandbox == "passed":
        s = max(s, 0.9)
    if sandbox == "failed":
        s = min(s, 0.2)
    if suspicious:
        s = min(s, 0.2)
    return max(0.0, min(1.0, s))


def ttl_days_for_query(query: str) -> int:
    """trust.ts ttlDaysForQuery: volatile topic → 3 days, else 180."""
    return 3 if VOLATILE.search(query) else 180


def independent_count(refs: list[tuple[str, str]], *, copy_threshold: float = 0.82) -> int:
    """Number of independent sources among (domain, page_text) pairs: distinct registrable domains
    whose texts are not copies of each other (textSimilar < 0.82, 03/03 §5)."""
    kept: list[tuple[str, str]] = []
    for domain, text in refs:
        if any(d == domain for d, _ in kept):
            continue
        if any(text_similar(text[:4000], t[:4000]) >= copy_threshold for _, t in kept):
            continue
        kept.append((domain, text))
    return len(kept)
