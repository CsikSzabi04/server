"""Who is calling (01/03 §4, §6): `X-Auri-User: <Supabase access token>` → signed-in user, else guest.

The token is checked the Jarvis M3 way (`GET {SUPABASE_URL}/auth/v1/user`); a missing, bad or
unverifiable token means **guest** (reads T0 only, writes nothing). The refresh token is never asked
for. Verified tokens are cached by their SHA-256 for a short time; the token itself is never stored.
T1 = one SQLite file per user under `users_dir`, named by a hash of the user id.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from ..config import Config
from ..store import SqliteKnowledgeStore

CACHE_S = 300.0
BAD_CACHE_S = 60.0  # a rejected token is not re-checked on every request


@dataclass(frozen=True)
class Identity:
    user_id: str | None = None

    @property
    def guest(self) -> bool:
        return self.user_id is None


GUEST = Identity()


def user_db_name(user_id: str) -> str:
    return hashlib.sha256(f"auri-core-t1:{user_id}".encode()).hexdigest()[:32] + ".db"


class Verifier:
    def __init__(self, cfg: Config, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.cfg = cfg
        self.transport = transport
        self._cache: dict[str, tuple[str | None, float]] = {}
        self._client: httpx.AsyncClient | None = None  # kept open: TLS to Supabase once, not per request

    @property
    def configured(self) -> bool:
        return bool(self.cfg.supabase_url and self.cfg.supabase_anon_key)

    async def identify(self, token: str | None) -> Identity:
        if not token or not self.configured:
            return GUEST
        key = hashlib.sha256(token.encode()).hexdigest()
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[1] < (CACHE_S if hit[0] else BAD_CACHE_S):
            return Identity(hit[0])
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=5.0, transport=self.transport)
        try:
            r = await self._client.get(f"{self.cfg.supabase_url}/auth/v1/user",
                                       headers={"apikey": self.cfg.supabase_anon_key, "Authorization": f"Bearer {token}"})
            uid = r.json().get("id") if r.status_code == 200 else None
            definite = r.status_code in (200, 401, 403)
        except (httpx.HTTPError, ValueError):
            uid, definite = None, False  # network trouble: guest now, but ask again next time
        if not isinstance(uid, str) or not uid:
            if definite:
                self._cache[key] = (None, time.monotonic())
            return GUEST
        self._cache[key] = (uid, time.monotonic())
        return Identity(uid)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


class UserStores:
    """T1 stores, opened lazily, one per signed-in user. Guests never get one."""

    def __init__(self, users_dir: Path) -> None:
        self.users_dir = users_dir
        self._open: dict[str, SqliteKnowledgeStore] = {}

    def path(self, user_id: str) -> Path:
        return self.users_dir / user_db_name(user_id)

    def get(self, ident: Identity, *, create: bool = True) -> SqliteKnowledgeStore | None:
        if ident.user_id is None:
            return None
        s = self._open.get(ident.user_id)
        if s is None:
            p = self.path(ident.user_id)
            if not create and not p.exists():
                return None
            self.users_dir.mkdir(parents=True, exist_ok=True)
            s = self._open[ident.user_id] = SqliteKnowledgeStore(p)
        return s

    def delete(self, ident: Identity) -> bool:
        """Account deletion (01/03 §6): the user's T1 file goes too."""
        if ident.user_id is None:
            return False
        s = self._open.pop(ident.user_id, None)
        if s is not None:
            s.close()
        p = self.path(ident.user_id)
        existed = p.exists()
        for suffix in ("", "-wal", "-shm"):
            Path(f"{p}{suffix}").unlink(missing_ok=True)
        return existed

    def close(self) -> None:
        for s in self._open.values():
            s.close()
        self._open.clear()


def tier_of(item: dict[str, Any], tier: str) -> dict[str, Any]:
    return {**item, "tier": tier}
