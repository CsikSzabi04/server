"""Types of the research lane (P2). Kept here, not in contracts.py, until ask() wires them in."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from ..contracts import EndState

SourceClass = Literal["A", "B", "C", "D", "E", "F"]  # 03/03 §2
PageKind = Literal["docs", "qa", "repo", "blog", "other"]
ClaimKind = Literal["fact", "api", "snippet", "fix", "concept"]
ClaimStatus = Literal["verified", "probable", "hypothesis"]  # ellenőrzött · valószínű · hipotézis (03/03 §3)


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    provider: str = ""


class SearchAdapter(Protocol):
    """One search provider (03/01 §4). Never returns more than `k` results."""

    name: str

    async def search(self, query: str, k: int = 6) -> list[SearchResult]: ...


@dataclass
class Section:
    path: tuple[str, ...]  # heading trail h1 > h2 > h3
    text: str
    code: list[tuple[str, str]] = field(default_factory=list)  # (lang, code)


@dataclass
class PageDoc:
    """A fetched page, reduced to structured text (03/02 §3). Its text is DATA, never instructions."""

    url: str
    final_url: str
    title: str
    lang: str
    fetched_at: str
    content_hash: str
    kind: PageKind
    sections: list[Section]
    links: list[tuple[str, str]] = field(default_factory=list)  # (href, anchor text)
    suspicious: bool = False  # prompt-injection signs (03/02 §7)
    noindex: bool = False  # meta robots noindex/noai → never stored as knowledge (03/02 §6)

    @property
    def text(self) -> str:
        parts = []
        for s in self.sections:
            parts.append(s.text)
            parts.extend(code for _lang, code in s.code)
        return "\n".join(p for p in parts if p)


@dataclass(frozen=True)
class FetchOutcome:
    page: PageDoc | None
    reason: str | None = None  # why not (Hungarian, no secrets); None when page is set


class Fetcher(Protocol):
    async def fetch(self, url: str) -> FetchOutcome: ...


@dataclass(frozen=True)
class SourceRef:
    url: str
    domain: str  # registrable domain (independence key)
    source_class: SourceClass
    quote: str  # verbatim, verified to occur in the page text


@dataclass
class Claim:
    kind: ClaimKind
    key: str  # canonical key, e.g. "python:str.removeprefix"
    text: str  # in the answer language
    sources: list[SourceRef]
    status: ClaimStatus
    trust: float
    independent: int  # independent agreeing sources (distinct domains, not copies)
    code: str | None = None  # only if it occurs verbatim on a supporting page
    applies_to: str | None = None
    stored_id: str | None = None


@dataclass(frozen=True)
class SourceInfo:
    url: str
    domain: str
    title: str
    source_class: SourceClass
    trust: float
    suspicious: bool


@dataclass
class ResearchResult:
    question: str
    kind: Literal["answered", "partial", "give_up"]
    end_state: EndState
    answer: str  # composed from claims, with certainty labels + domains (answer language)
    claims: list[Claim] = field(default_factory=list)
    sources: list[SourceInfo] = field(default_factory=list)
    stored: list[str] = field(default_factory=list)  # knowledge item ids written this run
    from_memory: bool = False  # answered from verified store items, no web
    web_checked: bool = False  # False → the answer says so ("nem tudtam a neten ellenőrizni")
    reason_hu: str | None = None
    episode_id: str = ""
    lang: str = "en"
    llm_calls: int = 0
    searches: int = 0
    pages: int = 0
    tokens_out: int = 0
    wall_ms: int = 0
    rejected_claims: int = 0  # claims dropped by the quote check
    withheld: int = 0  # claims not stored (not verified, privacy gate, duplicates)
