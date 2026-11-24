"""Offline doubles for the research lane (no network). Fictional data only."""

from __future__ import annotations

from .html import html_to_page
from .types import FetchOutcome, SearchResult


class FakeSearch:
    """Scripted results: {query substring: [SearchResult, ...]}; `default` for anything else."""

    name = "fake"

    def __init__(self, results: dict[str, list[SearchResult]] | None = None,
                 default: list[SearchResult] | None = None, *, offline: bool = False) -> None:
        self.results = results or {}
        self.default = default or []
        self.offline = offline
        self.last_offline = False
        self.queries: list[str] = []

    async def search(self, query: str, k: int = 6) -> list[SearchResult]:
        self.queries.append(query)
        self.last_offline = self.offline
        if self.offline:
            return []
        for key, hits in self.results.items():
            if key.lower() in query.lower():
                return hits[:k]
        return self.default[:k]


class FakeFetcher:
    """{url: html} → PageDoc via the real HTML extractor; unknown URL → a failed fetch."""

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.fetched: list[str] = []

    async def fetch(self, url: str) -> FetchOutcome:
        self.fetched.append(url)
        html = self.pages.get(url)
        if html is None:
            return FetchOutcome(None, "HTTP 404")
        return FetchOutcome(html_to_page(html, url=url, fetched_at="2026-01-01T00:00:00+00:00"))
