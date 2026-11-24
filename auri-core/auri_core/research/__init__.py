"""auri_core.research — P2: search → read → extract → verify → corroborate → store (owner: AI-1).

Entry point: `research(question, *, llm, scheduler, store, search, fetcher, …) -> ResearchResult`.
Real adapters: `ResilientSearch([DuckDuckGoHtml(), Searxng()])`, `SafeFetcher()`; offline doubles in
`research.fakes`. Spec: ideas_for_brain/thinking/03-web-szorfozes/.
"""

from .fetch import SafeFetcher, check_url, is_public_ip
from .html import html_to_page
from .pipeline import research
from .search import DuckDuckGoHtml, ResilientSearch, Searxng
from .trust import TrustOverrides
from .types import Claim, FetchOutcome, PageDoc, ResearchResult, SearchAdapter, SearchResult, SourceInfo

__all__ = [
    "Claim", "DuckDuckGoHtml", "FetchOutcome", "PageDoc", "ResearchResult", "ResilientSearch", "SafeFetcher",
    "SearchAdapter", "SearchResult", "Searxng", "SourceInfo", "TrustOverrides", "check_url", "html_to_page",
    "is_public_ip", "research",
]
