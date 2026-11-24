"""Search providers + resilience (03/01 §4–7).

- DuckDuckGoHtml: keyless, the `ddgSearch` of web/api/search.ts (POST html.duckduckgo.com/html/).
- Searxng: optional local meta-search (GET /search?format=json), URL from AURI_CORE_SEARXNG_URL.
- ResilientSearch: cache → token bucket → per-provider circuit breaker (exponential back-off,
  "soft failure" = 0 hits for several different queries) → next provider → stale cache → nothing.
Neither provider needs a key; queries are redacted by the caller before they get here.
"""

from __future__ import annotations

import html as _html
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import unquote

import httpx

from .trust import ttl_days_for_query
from .types import SearchAdapter, SearchResult

USER_AGENT = "Mozilla/5.0 (compatible; AuriCore/1; local assistant)"
_SNIP = re.compile(r'<a[^>]*class="result__snippet"[^>]*>([\s\S]*?)</a>')
_LINK = re.compile(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>')
_TAG = re.compile(r"<[^>]+>")


def _clean(s: str) -> str:
    return " ".join(_html.unescape(_TAG.sub("", s)).split())


def _real_url(href: str) -> str:
    """DDG wraps results in //duckduckgo.com/l/?uddg=<encoded url>."""
    m = re.search(r"[?&]uddg=([^&]+)", href)
    if m:
        return unquote(m.group(1))
    if href.startswith("//"):
        return "https:" + href
    return href if href.startswith("http") else ""


def parse_ddg_html(page: str, k: int = 6) -> list[SearchResult]:
    snippets = [_clean(m.group(1)) for m in _SNIP.finditer(page)]
    out: list[SearchResult] = []
    for i, m in enumerate(_LINK.finditer(page)):
        if len(out) >= k:
            break
        url, title = _real_url(_html.unescape(m.group(1))), _clean(m.group(2))
        if url and title:
            out.append(SearchResult(title, url, snippets[i] if i < len(snippets) else "", "ddg"))
    return out


class DuckDuckGoHtml:
    name = "ddg"
    URL = "https://html.duckduckgo.com/html/"

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None, timeout_s: float = 9.0) -> None:
        self._client = httpx.AsyncClient(transport=transport, timeout=timeout_s, headers={"user-agent": USER_AGENT})

    async def search(self, query: str, k: int = 6) -> list[SearchResult]:
        r = await self._client.post(self.URL, data={"q": query[:256]})
        if r.status_code >= 400:
            raise httpx.HTTPStatusError(f"ddg {r.status_code}", request=r.request, response=r)
        return parse_ddg_html(r.text, min(k, 10))

    async def aclose(self) -> None:
        await self._client.aclose()


class Searxng:
    """Local SearXNG; enable the JSON format in its settings.yml (03/01 §4)."""

    name = "searxng"

    def __init__(self, base_url: str | None = None, *, transport: httpx.AsyncBaseTransport | None = None,
                 timeout_s: float = 9.0) -> None:
        self.base_url = (base_url or os.environ.get("AURI_CORE_SEARXNG_URL") or "").rstrip("/")
        self._client = httpx.AsyncClient(transport=transport, timeout=timeout_s, headers={"user-agent": USER_AGENT})

    async def search(self, query: str, k: int = 6) -> list[SearchResult]:
        if not self.base_url:
            raise RuntimeError("searxng not configured")
        r = await self._client.get(f"{self.base_url}/search", params={"q": query[:256], "format": "json"})
        r.raise_for_status()
        out = []
        for item in (r.json().get("results") or [])[:k]:
            url, title = str(item.get("url") or ""), _clean(str(item.get("title") or ""))
            if url.startswith(("http://", "https://")) and title:
                out.append(SearchResult(title, url, _clean(str(item.get("content") or "")), "searxng"))
        return out

    async def aclose(self) -> None:
        await self._client.aclose()


# ───────────────────────────── resilience ─────────────────────────────

Clock = Callable[[], float]


@dataclass
class CircuitBreaker:
    """3 consecutive failures → open; cooldown 60 s, doubling on each re-open up to 30 min; then one
    half-open probe. 0 hits for `soft_limit` different queries in a row counts as a failure (blocked)."""

    fail_threshold: int = 3
    base_cooldown_s: float = 60.0
    max_cooldown_s: float = 1800.0
    soft_limit: int = 3
    clock: Clock = time.monotonic
    fails: int = 0
    opens: int = 0
    opened_at: float | None = None
    _empty_queries: set[str] = field(default_factory=set)

    @property
    def cooldown_s(self) -> float:
        return min(self.max_cooldown_s, self.base_cooldown_s * 2 ** max(0, self.opens - 1))

    def allowed(self) -> bool:
        return self.opened_at is None or self.clock() - self.opened_at >= self.cooldown_s

    def success(self) -> None:
        self.fails, self.opens, self.opened_at = 0, 0, None
        self._empty_queries.clear()

    def failure(self) -> None:
        self.fails += 1
        if self.opened_at is not None or self.fails >= self.fail_threshold:  # half-open probe failed, or tripped
            self.opens += 1
            self.opened_at = self.clock()
            self.fails = 0

    def empty(self, query: str) -> None:
        self._empty_queries.add(query.lower())
        if len(self._empty_queries) >= self.soft_limit:
            self._empty_queries.clear()
            self.fails = self.fail_threshold - 1
            self.failure()


@dataclass
class TokenBucket:
    """rateLimit.ts: `capacity` requests per `window_s`, continuous refill."""

    capacity: int = 12
    window_s: float = 60.0
    clock: Clock = time.monotonic
    tokens: float = -1.0
    updated: float = 0.0

    def allow(self) -> bool:
        now = self.clock()
        if self.tokens < 0:
            self.tokens, self.updated = float(self.capacity), now
        self.tokens = min(self.capacity, self.tokens + (now - self.updated) / self.window_s * self.capacity)
        self.updated = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


@dataclass
class SearchCache:
    """In-memory TTL cache of hit lists (03/01 §7): volatile topic 1 h, stable 7 days, negative 1 h.
    The SQLite `search_cache` table is AI-3's store; this keeps the same keys and TTLs."""

    max_entries: int = 200
    clock: Clock = time.time
    entries: dict[str, tuple[list[SearchResult], float, float]] = field(default_factory=dict)

    @staticmethod
    def key(query: str) -> str:
        return " ".join(query.lower().split())

    def get(self, query: str, *, allow_stale: bool = False) -> list[SearchResult] | None:
        e = self.entries.get(self.key(query))
        if e is None:
            return None
        hits, at, ttl = e
        return hits if allow_stale or self.clock() - at <= ttl else None

    def put(self, query: str, hits: list[SearchResult]) -> None:
        if not hits:
            ttl = 3600.0
        else:
            ttl = 3600.0 if ttl_days_for_query(query) <= 3 else 7 * 86400.0
        self.entries[self.key(query)] = (list(hits), self.clock(), ttl)
        if len(self.entries) > self.max_entries:
            for k, _ in sorted(self.entries.items(), key=lambda kv: kv[1][1])[: len(self.entries) - self.max_entries]:
                del self.entries[k]


class ResilientSearch:
    """The pipeline's one search entry: cache → rate limit → providers in order (each behind its own
    breaker) → stale cache. `last_offline` tells the caller that no provider answered (03/01 §6)."""

    name = "resilient"

    def __init__(self, providers: list[SearchAdapter], *, cache: SearchCache | None = None,
                 bucket: TokenBucket | None = None, clock: Clock = time.monotonic) -> None:
        self.providers = providers
        self.cache = cache or SearchCache()
        self.bucket = bucket or TokenBucket(clock=clock)
        self.breakers = {p.name: CircuitBreaker(clock=clock) for p in providers}
        self.last_offline = False
        self.provider_calls = 0

    async def search(self, query: str, k: int = 6) -> list[SearchResult]:
        self.last_offline = False
        if (hit := self.cache.get(query)) is not None:
            return hit[:k]
        if not self.bucket.allow():
            stale = self.cache.get(query, allow_stale=True)
            self.last_offline = stale is None
            return (stale or [])[:k]
        answered = False
        for p in self.providers:
            br = self.breakers[p.name]
            if not br.allowed():
                continue
            self.provider_calls += 1
            try:
                hits = await p.search(query, k)
            except Exception:  # network down, blocked, HTML changed — never the caller's problem
                br.failure()
                continue
            answered = True
            if hits:
                br.success()
                self.cache.put(query, hits)
                return hits[:k]
            br.empty(query)
        if answered:
            self.cache.put(query, [])  # negative cache, 1 h
            return []
        stale = self.cache.get(query, allow_stale=True)
        self.last_offline = stale is None
        return (stale or [])[:k]
