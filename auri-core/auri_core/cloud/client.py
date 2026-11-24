"""Cloud fallback: masking, providers (Groq → Gemini if paid), 429, breaker, quotas, audit (08/03 §1–6)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import socket
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from .. import privacy
from ..config import Config
from ..store import now_iso

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_MODEL = "gemini-2.5-flash"
PROVIDER_DAILY = {"groq": 1000, "gemini": 250}  # free-tier estimates (08/03 §5); the Core stops at 80%
STOP_AT = 0.8
BREAKER_FAILS, BREAKER_OPEN_S = 3, 600.0
MAX_WAIT_S = 30.0
AUDIT_DAYS = 30


@dataclass(frozen=True)
class CloudPayload:
    messages: list[dict[str, str]]
    purpose: str
    sha256: str
    redactions: int

    @property
    def text(self) -> str:
        return "\n".join(m["content"] for m in self.messages)


@dataclass(frozen=True)
class CloudRefusal:
    reason: str  # Hungarian, for the user (no content, no key)
    kind: str  # off | background | guest | personal | secret | quota | unavailable | cap


@dataclass(frozen=True)
class CloudAnswer:
    text: str
    provider: str
    model: str
    provenance: str  # "cloud:<provider>:<model>" — a cloud answer is always a hypothesis (08/03 §7)


class RateLimited(Exception):
    def __init__(self, retry_after_s: float | None) -> None:
        super().__init__("429")
        self.retry_after_s = retry_after_s


class ProviderError(Exception):
    pass


# ── masking (08/03 §4) ───────────────────────────────────────────────────────────────────────
_HOME = re.compile(r"(?i)\b([A-Z]:\\Users\\|/home/|/Users/)[^\\/\s\"'<>]+")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def _mask(text: str, host: str) -> tuple[str, int]:
    n = 0

    def sub(rx: re.Pattern[str], repl: Callable[[re.Match[str]], str] | str, s: str) -> str:
        nonlocal n
        out, k = rx.subn(repl, s)
        n += k
        return out

    text = sub(_HOME, lambda m: m.group(1) + "<HOME>", text)
    text = sub(_EMAIL, "<EMAIL>", text)
    text = sub(_IPV4, "<IP>", text)
    if host and len(host) >= 3:
        text = sub(re.compile(re.escape(host), re.I), "<HOST>", text)
    return text, n


def prepare_payload(messages: list[dict[str, str]], *, purpose: str, names: list[str] | None = None,
                    host: str | None = None) -> CloudPayload | CloudRefusal:
    """Personal data or a secret → NOT sent (never "mask and send"); else paths/e-mails/IPs/host masked."""
    text = "\n".join(str(m.get("content", "")) for m in messages)
    if privacy.has_secret(text) or privacy.DECLARED_SECRET.search(text):
        return CloudRefusal("titoknak látszó adat van a kérésben (kulcs, token, kártyaszám…), ezért nem küldöm a felhőbe", "secret")
    if privacy.is_personal(text, names or []):
        return CloudRefusal("személyes adat van a kérésben, ezért nem küldöm a felhőbe", "personal")
    host = host if host is not None else (os.environ.get("COMPUTERNAME") or socket.gethostname() or "")
    out, total = [], 0
    for m in messages:
        c, k = _mask(str(m.get("content", "")), host)
        total += k
        out.append({"role": str(m.get("role", "user")), "content": c})
    body = "\n".join(m["content"] for m in out)
    return CloudPayload(out, purpose, hashlib.sha256(body.encode()).hexdigest(), total)


# ── providers ────────────────────────────────────────────────────────────────────────────────
@dataclass
class Provider:
    name: str
    model: str
    key: str = field(repr=False)
    call: Callable[[httpx.AsyncClient, Provider, CloudPayload, float], Awaitable[str]]


def _retry_after(r: httpx.Response) -> float | None:
    v = r.headers.get("retry-after")
    try:
        return float(v) if v is not None else None
    except ValueError:
        return None


def _check(r: httpx.Response) -> None:
    if r.status_code == 429:
        raise RateLimited(_retry_after(r))
    if r.status_code >= 400:
        raise ProviderError(f"HTTP {r.status_code}")  # never the body: it may echo the request


async def _groq(client: httpx.AsyncClient, p: Provider, pl: CloudPayload, timeout_s: float) -> str:
    r = await client.post(GROQ_URL, headers={"Authorization": f"Bearer {p.key}"}, timeout=timeout_s,
                          json={"model": p.model, "messages": pl.messages, "temperature": 0.2, "max_tokens": 2048})
    _check(r)
    return str(r.json()["choices"][0]["message"]["content"] or "")


async def _gemini(client: httpx.AsyncClient, p: Provider, pl: CloudPayload, timeout_s: float) -> str:
    system = "\n".join(m["content"] for m in pl.messages if m["role"] == "system")
    contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                for m in pl.messages if m["role"] != "system"]
    body: dict[str, Any] = {"contents": contents, "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    r = await client.post(GEMINI_URL.format(model=p.model), headers={"x-goog-api-key": p.key}, json=body, timeout=timeout_s)
    _check(r)
    parts = r.json()["candidates"][0]["content"]["parts"]
    return "".join(str(x.get("text", "")) for x in parts)


# ── the client ───────────────────────────────────────────────────────────────────────────────
class CloudClient:
    def __init__(self, cfg: Config, store: Any, *, transport: httpx.AsyncBaseTransport | None = None,
                 sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep, clock: Callable[[], float] = time.monotonic,
                 host: str | None = None) -> None:
        self.cfg, self.store, self.sleep, self.clock, self.host = cfg, store, sleep, clock, host
        self._http = httpx.AsyncClient(transport=transport, timeout=60.0)
        self._fails: dict[str, int] = {}
        self._open_until: dict[str, float] = {}
        self.providers: list[Provider] = []
        if cfg.groq_api_key:
            self.providers.append(Provider("groq", cfg.cloud_model or GROQ_MODEL, cfg.groq_api_key, _groq))
        if cfg.gemini_api_key and cfg.gemini_paid:  # free tier never (EEA terms, same rule as the web chat proxy)
            self.providers.append(Provider("gemini", GEMINI_MODEL, cfg.gemini_api_key, _gemini))

    @property
    def enabled(self) -> bool:
        return self.cfg.cloud_mode != "off" and bool(self.providers)

    async def aclose(self) -> None:
        await self._http.aclose()

    # quotas (store table cloud_quota)
    def _day(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%d")

    def _calls(self, key: str) -> tuple[int, str | None]:
        r = self.store.db.execute("SELECT calls, exhausted_until FROM cloud_quota WHERE day=? AND key=?", (self._day(), key)).fetchone()
        return (int(r[0]), r[1]) if r else (0, None)

    def _bump(self, key: str, *, exhausted_until: str | None = None) -> None:
        self.store.db.execute(
            "INSERT INTO cloud_quota(day, key, calls, exhausted_until) VALUES (?,?,?,?) ON CONFLICT(day, key) DO UPDATE SET "
            "calls = calls + excluded.calls, exhausted_until = COALESCE(excluded.exhausted_until, exhausted_until)",
            (self._day(), key, 0 if exhausted_until else 1, exhausted_until))

    def _usable(self, p: Provider) -> bool:
        if self._open_until.get(p.name, 0.0) > self.clock():
            return False
        calls, until = self._calls(f"provider:{p.name}")
        if until and until > now_iso():
            return False
        return calls < PROVIDER_DAILY.get(p.name, 100) * STOP_AT

    def _audit(self, p: Provider, pl: CloudPayload, ok: bool) -> None:
        self.store.db.execute("INSERT INTO cloud_audit VALUES (?,?,?,?,?,?,?,?,?)",
                              (now_iso(), p.name, p.model, pl.purpose, len(pl.text), pl.redactions, pl.sha256, pl.text, int(ok)))
        cutoff = (datetime.now(UTC) - timedelta(days=AUDIT_DAYS)).isoformat()
        self.store.db.execute("DELETE FROM cloud_audit WHERE at < ?", (cutoff,))

    async def chat(self, messages: list[dict[str, str]], *, purpose: str, interactive: bool, user_id: str | None,
                   background: bool = False, names: list[str] | None = None) -> CloudAnswer | CloudRefusal:
        if background:
            return CloudRefusal("háttérmunka soha nem használ felhőt", "background")
        if self.cfg.cloud_mode == "off":
            return CloudRefusal("a felhős segítség ki van kapcsolva", "off")
        if user_id is None:
            return CloudRefusal("vendég nevében a Core nem hív felhőt", "guest")
        if not self.providers:
            return CloudRefusal("nincs beállított felhős szolgáltató (kulcs az auri-core/.env-ben)", "unavailable")
        ukey = "user:" + hashlib.sha256(user_id.encode()).hexdigest()[:16]
        if self._calls(ukey)[0] >= self.cfg.cloud_daily_cap:
            return CloudRefusal(f"a mai felhős keret ({self.cfg.cloud_daily_cap} hívás) elfogyott", "cap")
        pl = prepare_payload(messages, purpose=purpose, names=names, host=self.host)
        if isinstance(pl, CloudRefusal):
            return pl
        for p in self.providers:
            if not self._usable(p):
                continue
            for attempt in (1, 2):
                try:
                    text = await p.call(self._http, p, pl, 60.0)
                except RateLimited as e:
                    if interactive and attempt == 1 and e.retry_after_s is not None and e.retry_after_s <= MAX_WAIT_S:
                        await self.sleep(e.retry_after_s)  # one wait, live requests only
                        continue
                    tomorrow = (datetime.now(UTC) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                    self._bump(f"provider:{p.name}", exhausted_until=tomorrow.isoformat())
                    break
                except (ProviderError, httpx.HTTPError, KeyError, IndexError, ValueError, json.JSONDecodeError):
                    self._fails[p.name] = self._fails.get(p.name, 0) + 1
                    if self._fails[p.name] >= BREAKER_FAILS:
                        self._open_until[p.name] = self.clock() + BREAKER_OPEN_S
                        self._fails[p.name] = 0
                    self._audit(p, pl, False)
                    break
                self._fails[p.name] = 0
                self._bump(f"provider:{p.name}")
                self._bump(ukey)
                self._audit(p, pl, True)
                return CloudAnswer(text, p.name, p.model, f"cloud:{p.name}:{p.model}")
        return CloudRefusal("most egyik felhős szolgáltató sem érhető el (kvóta vagy hiba)", "quota")

    def audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.store.db.execute("SELECT * FROM cloud_audit ORDER BY at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
