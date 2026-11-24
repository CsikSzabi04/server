"""P2 research: SSRF-safe fetcher, robots.txt, providers, breaker/cache/rate limit — httpx.MockTransport only."""

import httpx
import pytest

from auri_core.research.fetch import SafeFetcher, check_url, is_public_ip
from auri_core.research.search import (
    CircuitBreaker,
    DuckDuckGoHtml,
    ResilientSearch,
    SearchCache,
    Searxng,
    TokenBucket,
    parse_ddg_html,
)
from auri_core.research.types import SearchResult

DNS = {"docs.example": ["93.184.216.34"], "evil.example": ["10.0.0.5"], "down.example": ["93.184.216.35"],
       "mixed.example": ["93.184.216.36", "127.0.0.1"]}


async def resolver(host):
    if host not in DNS:
        raise OSError("no such host")
    return DNS[host]


@pytest.mark.parametrize(("ip", "ok"), [
    ("8.8.8.8", True), ("127.0.0.1", False), ("10.1.2.3", False), ("172.16.0.1", False), ("192.168.1.1", False),
    ("169.254.169.254", False), ("100.64.0.1", False), ("0.0.0.0", False), ("224.0.0.1", False),
    ("192.0.2.1", False), ("::1", False), ("::", False), ("::ffff:127.0.0.1", False), ("::ffff:8.8.8.8", True),
    ("::7f00:1", False), ("fe80::1", False), ("fc00::1", False), ("2002:7f00:1::", False),
    ("64:ff9b::7f00:1", False), ("2001:db8::1", False), ("2001:4860:4860::8888", True), ("garbage", False),
])
def test_is_public_ip(ip, ok):
    assert is_public_ip(ip) is ok


async def test_check_url_rules():
    assert await check_url("https://docs.example/x", resolver) is None
    for bad in ["ftp://docs.example/", "http://u:p@docs.example/", "http://docs.example:8080/", "http://localhost/",
                "http://printer.local/", "http://127.0.0.1/", "http://[::1]/", "https://evil.example/",
                "https://mixed.example/", "https://nosuch.example/", "http://[::ffff:7f00:1]/"]:
        assert await check_url(bad, resolver) is not None, bad


PAGE = "<html><head><title>Docs</title></head><body><main><p>" + "Useful documentation text. " * 20 + "</p></main></body></html>"


def make_fetcher(seen, **kw):
    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(str(req.url))
        url = str(req.url)
        if url == "https://docs.example/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
        if url == "https://down.example/robots.txt":
            return httpx.Response(503)
        if url == "https://docs.example/page":
            return httpx.Response(200, html=PAGE)
        if url == "https://docs.example/redir":
            return httpx.Response(302, headers={"location": "https://evil.example/steal"})
        if url == "https://docs.example/hop":
            return httpx.Response(301, headers={"location": "/page"})
        if url == "https://docs.example/bin":
            return httpx.Response(200, content=b"\x00\x01", headers={"content-type": "application/octet-stream"})
        if url == "https://docs.example/big":
            return httpx.Response(200, html="<p>" + "x" * 50_000 + "</p>")
        if url == "https://docs.example/loop":
            return httpx.Response(302, headers={"location": "/loop"})
        return httpx.Response(404)

    sleeps = []

    async def sleep(s):
        sleeps.append(s)

    f = SafeFetcher(transport=httpx.MockTransport(handler), resolver=resolver, sleep=sleep,
                    clock=lambda: 1000.0, **kw)
    return f, sleeps


async def test_fetch_page_robots_redirects_and_limits():
    seen = []
    f, sleeps = make_fetcher(seen, max_bytes=2000)
    ok = await f.fetch("https://docs.example/page")
    assert ok.page is not None and "Useful documentation" in ok.page.text and ok.page.title == "Docs"
    assert (await f.fetch("https://docs.example/hop")).page.final_url == "https://docs.example/page"
    assert (await f.fetch("https://docs.example/private/x")).reason == "a robots.txt tiltja"
    assert "https://docs.example/private/x" not in seen
    evil = await f.fetch("https://docs.example/redir")
    assert evil.page is None and "nem nyilvános" in evil.reason and not any("evil" in u for u in seen)
    assert (await f.fetch("https://docs.example/bin")).reason == "nem szöveges tartalom"
    big = await f.fetch("https://docs.example/big")
    assert big.page is not None and len(big.page.text) < 2100
    assert (await f.fetch("https://docs.example/loop")).reason == "túl sok átirányítás"
    assert (await f.fetch("https://docs.example/missing")).reason == "HTTP 404"
    assert (await f.fetch("https://down.example/a")).reason == "a webhely robots.txt-je nem érhető el"
    assert seen.count("https://docs.example/robots.txt") == 1  # cached for the day
    assert sleeps and all(abs(s - 2.0) < 1e-9 for s in sleeps)  # ≥ 2 s between hits on one host
    await f.aclose()


async def test_fetch_timeout_is_a_reason_not_a_crash():
    def handler(req):
        raise httpx.ConnectTimeout("slow", request=req)

    f = SafeFetcher(transport=httpx.MockTransport(handler), resolver=resolver, respect_robots=False)
    assert (await f.fetch("https://docs.example/page")).reason == "időtúllépés"


DDG = """<div><a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fdocs.python.org%2F3%2F&amp;rut=x">
Python <b>docs</b></a><a class="result__snippet" href="x">The &quot;official&quot; docs</a></div>
<div><a class="result__a" href="https://example.org/b">Second</a><a class="result__snippet">two</a></div>"""


async def test_ddg_and_searxng_adapters():
    assert parse_ddg_html(DDG)[0] == SearchResult("Python docs", "https://docs.python.org/3/", 'The "official" docs', "ddg")
    bodies = []

    def ddg(req):
        bodies.append(req.content.decode())
        return httpx.Response(200, text=DDG)

    hits = await DuckDuckGoHtml(transport=httpx.MockTransport(ddg)).search("python docs", 1)
    assert len(hits) == 1 and bodies == ["q=python+docs"]

    def sx(req):
        assert req.url.params["format"] == "json"
        return httpx.Response(200, json={"results": [{"url": "https://a.example/", "title": "A", "content": "c"},
                                                     {"url": "javascript:x", "title": "bad"}]})

    out = await Searxng("http://127.0.0.1:8888", transport=httpx.MockTransport(sx)).search("q")
    assert out == [SearchResult("A", "https://a.example/", "c", "searxng")]
    with pytest.raises(RuntimeError):
        await Searxng("").search("q")


class Prov:
    def __init__(self, name, script):
        self.name, self.script, self.calls = name, list(script), 0

    async def search(self, query, k=6):
        self.calls += 1
        r = self.script.pop(0) if self.script else []
        if isinstance(r, Exception):
            raise r
        return r


HIT = [SearchResult("t", "https://a.example/", "s")]


async def test_breaker_backoff_fallback_and_cache():
    now = [0.0]
    a = Prov("ddg", [OSError("down")] * 6)
    b = Prov("searxng", [HIT, HIT, HIT, HIT])
    rs = ResilientSearch([a, b], clock=lambda: now[0], bucket=TokenBucket(capacity=100, clock=lambda: now[0]))
    for i in range(3):
        assert await rs.search(f"q{i}") == HIT  # fell back to the second provider
    assert a.calls == 3 and not rs.breakers["ddg"].allowed()
    await rs.search("q3")
    assert a.calls == 3  # open: not even tried
    await rs.search("q0")
    assert b.calls == 4  # q0 came from the cache
    now[0] = 61.0
    assert rs.breakers["ddg"].allowed()  # half-open probe
    await rs.search("q4")
    assert a.calls == 4 and rs.breakers["ddg"].cooldown_s == 120.0  # failed probe → doubled back-off


def test_breaker_soft_failure_bucket_and_cache_ttl():
    br = CircuitBreaker(clock=lambda: 0.0)
    for q in ("a", "b", "c"):
        br.empty(q)
    assert not br.allowed()
    tb = TokenBucket(capacity=2, window_s=60, clock=lambda: 0.0)
    assert tb.allow() and tb.allow() and not tb.allow()
    t = [0.0]
    c = SearchCache(clock=lambda: t[0])
    c.put("latest node version", HIT)
    c.put("what is a closure", HIT)
    t[0] = 3601
    assert c.get("latest node version") is None and c.get("latest node version", allow_stale=True) == HIT
    assert c.get("What is  a closure") == HIT


async def test_offline_after_rate_limit_without_cache():
    rs = ResilientSearch([Prov("ddg", [HIT])], bucket=TokenBucket(capacity=1, clock=lambda: 0.0))
    assert await rs.search("first") == HIT and not rs.last_offline
    assert await rs.search("second") == [] and rs.last_offline
