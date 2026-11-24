"""Safe page fetching (03/02 §2, §6) — the Python twin of web/api/_guard.ts `publicUrl`/`safeFetch`.

Public http(s) hosts only: no credentials in the URL, only ports 80/443, no localhost/.local/.internal,
and EVERY resolved address must be public (loopback, private, link-local, CGNAT, multicast, reserved,
documentation, and IPv6 forms that embed such an IPv4 address are refused). Every redirect hop is
re-checked (≤ 5). 7 s timeout, ≤ 2 MB raw body, text/html | text/plain | XML only, robots.txt
(24 h cache, 5xx → skip the host), ≥ 2 s between requests to the same host, no cookies, no forms.
Known limit: the address is checked, then httpx resolves again (DNS-rebinding window), as in the web.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
import time
import urllib.robotparser
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit

import httpx

from .html import html_to_page
from .search import USER_AGENT
from .trust import TrustOverrides, blocked
from .types import FetchOutcome

Resolver = Callable[[str], Awaitable[list[str]]]
MAX_BYTES = 2_000_000
_OK_TYPES = ("text/html", "text/plain", "application/xhtml+xml", "application/xml", "text/xml")
_CGNAT = ipaddress.ip_network("100.64.0.0/10")
_NAT64 = ipaddress.ip_network("64:ff9b::/96")
_BAD_SUFFIX = (".localhost", ".local", ".internal", ".lan", ".home", ".corp", ".intranet")


def is_public_ip(raw: str) -> bool:
    try:
        ip = ipaddress.ip_address(raw.split("%")[0])
    except ValueError:
        return False  # unparseable → refuse
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return is_public_ip(str(ip.ipv4_mapped))
        if ip.sixtofour is not None:
            return is_public_ip(str(ip.sixtofour))
        if ip.teredo is not None:
            return False
        if ip in _NAT64:
            return is_public_ip(str(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)))
        if int(ip) >> 32 == 0:  # ::a.b.c.d (IPv4-compatible), ::, ::1
            return False
    elif ip in _CGNAT:
        return False
    bad = ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved
    return not bad and not ip.is_unspecified and ip.is_global


async def system_resolver(host: str) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return sorted({str(i[4][0]) for i in infos})


async def check_url(url: str, resolver: Resolver = system_resolver) -> str | None:
    """None if the server may fetch `url`; else the (Hungarian) reason."""
    try:
        u = urlsplit(url)
        port = u.port
    except ValueError:
        return "érvénytelen cím"
    if u.scheme not in ("http", "https"):
        return "csak http(s) cím tölthető le"
    if u.username or u.password:
        return "felhasználónév a címben"
    if port not in (None, 80, 443):
        return "nem szabványos port"
    host = (u.hostname or "").lower().strip("[]")
    if not host or host == "localhost" or host.endswith(_BAD_SUFFIX):
        return "helyi vagy belső cím"
    try:
        ipaddress.ip_address(host.split("%")[0])
        return None if is_public_ip(host) else "nem nyilvános IP-cím"
    except ValueError:
        pass
    try:
        addrs = await resolver(host)
    except (OSError, UnicodeError):
        return "a név nem oldható fel"
    if not addrs or not all(is_public_ip(a) for a in addrs):
        return "a név nem nyilvános címre mutat"
    return None


class SafeFetcher:
    """`Fetcher` implementation. One per research session (it remembers robots.txt and host timing)."""

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        resolver: Resolver = system_resolver,
        timeout_s: float = 7.0,
        max_bytes: int = MAX_BYTES,
        max_redirects: int = 5,
        host_delay_s: float = 2.0,
        respect_robots: bool = True,
        overrides: TrustOverrides | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._client = httpx.AsyncClient(
            transport=transport, timeout=httpx.Timeout(timeout_s), follow_redirects=False,
            headers={"user-agent": USER_AGENT, "accept": "text/html,text/plain;q=0.9,*/*;q=0.1"},
        )
        self.resolver = resolver
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects
        self.host_delay_s = host_delay_s
        self.respect_robots = respect_robots
        self.overrides = overrides
        self.clock, self.sleep = clock, sleep
        self._robots: dict[str, tuple[float, urllib.robotparser.RobotFileParser | None, float]] = {}
        self._last: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self.requests = 0

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _polite(self, host: str, delay: float) -> None:
        lock = self._locks.setdefault(host, asyncio.Lock())
        async with lock:
            last = self._last.get(host)
            if last is not None:
                wait = delay - (self.clock() - last)
                if wait > 0:
                    await self.sleep(wait)
            self._last[host] = self.clock()

    async def _robots_for(self, scheme: str, host: str) -> tuple[urllib.robotparser.RobotFileParser | None, float, bool]:
        """(parser | None = allow all, crawl delay, host usable)."""
        cached = self._robots.get(host)
        if cached and self.clock() - cached[0] < 86400:
            return cached[1], cached[2], cached[1] is not None or cached[2] >= 0
        rp: urllib.robotparser.RobotFileParser | None = None
        delay = self.host_delay_s
        try:
            await self._polite(host, self.host_delay_s)
            self.requests += 1
            r = await self._client.get(f"{scheme}://{host}/robots.txt")
            if r.status_code >= 500:
                self._robots[host] = (self.clock(), None, -1.0)  # 5xx → skip the host today (03/02 §6)
                return None, -1.0, False
            if r.status_code == 200:
                rp = urllib.robotparser.RobotFileParser()
                rp.parse(r.text[:200_000].splitlines())
                cd = rp.crawl_delay(USER_AGENT) or rp.crawl_delay("*")
                if cd:
                    delay = max(delay, min(float(cd), 30.0))
        except httpx.HTTPError:
            self._robots[host] = (self.clock(), None, -1.0)
            return None, -1.0, False
        self._robots[host] = (self.clock(), rp, delay)
        return rp, delay, True

    async def fetch(self, url: str) -> FetchOutcome:
        current = url
        try:
            for _hop in range(self.max_redirects + 1):
                if blocked(current, self.overrides):
                    return FetchOutcome(None, "tiltólistás webhely")
                if reason := await check_url(current, self.resolver):
                    return FetchOutcome(None, reason)
                u = urlsplit(current)
                host = (u.hostname or "").lower()
                delay = self.host_delay_s
                if self.respect_robots:
                    rp, delay, usable = await self._robots_for(u.scheme, host)
                    if not usable:
                        return FetchOutcome(None, "a webhely robots.txt-je nem érhető el")
                    if rp is not None and not rp.can_fetch(USER_AGENT, current):
                        return FetchOutcome(None, "a robots.txt tiltja")
                await self._polite(host, delay)
                self.requests += 1
                async with self._client.stream("GET", current) as r:
                    if 300 <= r.status_code < 400:
                        loc = r.headers.get("location")
                        if not loc:
                            return FetchOutcome(None, "átirányítás cél nélkül")
                        current = urljoin(current, loc)
                        continue
                    if r.status_code != 200:
                        return FetchOutcome(None, f"HTTP {r.status_code}")
                    ctype = r.headers.get("content-type", "").lower()
                    if not any(t in ctype for t in _OK_TYPES):
                        return FetchOutcome(None, "nem szöveges tartalom")
                    body = bytearray()
                    async for chunk in r.aiter_bytes():
                        body.extend(chunk)
                        if len(body) >= self.max_bytes:
                            del body[self.max_bytes:]
                            break
                    charset = r.charset_encoding or "utf-8"
                try:
                    text = bytes(body).decode(charset, errors="replace")
                except LookupError:
                    text = bytes(body).decode("utf-8", errors="replace")
                page = html_to_page(text, url=url, final_url=current, content_type=ctype,
                                    fetched_at=datetime.now(UTC).isoformat(timespec="seconds"))
                return FetchOutcome(page)
            return FetchOutcome(None, "túl sok átirányítás")
        except httpx.TimeoutException:
            return FetchOutcome(None, "időtúllépés")
        except httpx.HTTPError:
            return FetchOutcome(None, "nem sikerült letölteni")
