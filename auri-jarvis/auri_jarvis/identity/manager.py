"""auri_jarvis.identity.manager — who is signed in (spec 5.11, owner: AI-3).

Login bridge: the HUD (signed in with the AuriGPT account) sends its Supabase access token over
the WebSocket; we verify it here:

  GET {SUPABASE_URL}/auth/v1/user            apikey: anon key · Authorization: Bearer <token>
  GET {SUPABASE_URL}/rest/v1/profiles?user_id=eq.<id>&select=*   (same headers → RLS: own row only)

Local cache `data/body/identity.db` (SQLite): user_id, display name, profile, prefs,
prefs_updated_at, verified_at, and which user was signed in last. NEVER the access token, a
refresh token or a password.

Prefs merge: Supabase `profiles.prefs.jarvis` (+ its `updated_at`) vs the local copy — the newer
wins. If the local copy is newer (changed offline), `consume_push()` tells the orchestrator to
emit `prefs.changed`, so the HUD writes it back to Supabase.

Offline: if Supabase is unreachable and the token's `sub` belongs to a user verified within
`identity.offline_grace_days` (7), the cached user is accepted; otherwise → guest.
At startup `initial_user()` returns the last signed-in user (within the grace period), so the
daemon starts with the user's own settings even before the HUD connects / without network.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import dataclasses
import json
import logging
import sqlite3
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import httpx

from ..config import data_path, get
from ..contracts import Emit, JarvisPrefs, UserContext
from .prefs import prefs_from_dict, prefs_to_dict

log = logging.getLogger(__name__)

PROFILE_FIELDS = ("name", "nickname", "language", "tone", "about", "interests")
DAY = 86_400.0


class AuthError(RuntimeError):
    """Login could not be verified. The message is user-facing (Hungarian), never contains the token."""


def jwt_sub(token: str) -> str | None:
    """The unverified `sub` claim of a JWT (used ONLY to look up the offline cache)."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        sub = json.loads(base64.urlsafe_b64decode(payload)).get("sub")
        return sub if isinstance(sub, str) and 0 < len(sub) <= 64 else None
    except (IndexError, ValueError, AttributeError):
        return None


class IdentityManager:
    def __init__(
        self,
        cfg: Mapping[str, Any],
        emit: Emit | None = None,
        *,
        db_path: Path | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.cfg = cfg
        self.emit = emit
        env = cfg.get("env", {})
        self.url = str(env.get("SUPABASE_URL") or get(cfg, "identity.supabase_url", "") or "").rstrip("/")
        self.anon_key = str(env.get("SUPABASE_ANON_KEY") or "")
        self.timeout = float(get(cfg, "identity.verify_timeout_s", 5.0))
        self.grace_s = float(get(cfg, "identity.offline_grace_days", 7)) * DAY
        self.guest_on_lock = bool(get(cfg, "identity.guest_on_lock", False))
        self.db_path = db_path or data_path(cfg, "body", "identity.db")
        self._transport = transport
        self._now = now
        self._db: sqlite3.Connection | None = None
        self._push: set[str] = set()
        self._lock_task: asyncio.Task[None] | None = None
        self.on_lock: Callable[[], Any] | None = None

    @property
    def configured(self) -> bool:
        return bool(self.url and self.anon_key)

    # ── lifecycle ────────────────────────────────────────────────────────────
    async def start(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.db_path, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                display_name TEXT,
                profile_json TEXT NOT NULL DEFAULT '{}',
                prefs_json TEXT NOT NULL DEFAULT '{}',
                prefs_updated_at REAL NOT NULL DEFAULT 0,
                verified_at REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
            """
        )
        self._db.commit()
        if self.guest_on_lock:
            self._lock_task = asyncio.create_task(self._watch_lock())

    async def stop(self) -> None:
        if self._lock_task is not None:
            self._lock_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._lock_task
        if self._db is not None:
            self._db.close()
            self._db = None

    # ── cache ────────────────────────────────────────────────────────────────
    def _row(self, user_id: str) -> dict[str, Any] | None:
        assert self._db is not None, "IdentityManager.start() first"
        cur = self._db.execute(
            "SELECT user_id, display_name, profile_json, prefs_json, prefs_updated_at, verified_at FROM users WHERE user_id=?",
            (user_id,),
        )
        r = cur.fetchone()
        if r is None:
            return None
        return {
            "user_id": r[0],
            "display_name": r[1],
            "profile": json.loads(r[2] or "{}"),
            "prefs": json.loads(r[3] or "{}"),
            "prefs_updated_at": float(r[4] or 0),
            "verified_at": float(r[5] or 0),
        }

    def _meta(self, key: str) -> str | None:
        assert self._db is not None
        r = self._db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return r[0] if r else None

    def _set_meta(self, key: str, value: str | None) -> None:
        assert self._db is not None
        if value is None:
            self._db.execute("DELETE FROM meta WHERE key=?", (key,))
        else:
            self._db.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value)
            )
        self._db.commit()

    def _store(self, user: UserContext, *, prefs_updated_at: float, verified_at: float | None) -> None:
        assert self._db is not None and user.user_id
        self._db.execute(
            """INSERT INTO users(user_id, display_name, profile_json, prefs_json, prefs_updated_at, verified_at)
               VALUES(?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET display_name=excluded.display_name, profile_json=excluded.profile_json,
                 prefs_json=excluded.prefs_json, prefs_updated_at=excluded.prefs_updated_at,
                 verified_at=CASE WHEN excluded.verified_at > 0 THEN excluded.verified_at ELSE users.verified_at END""",
            (
                user.user_id,
                user.display_name,
                json.dumps(user.profile, ensure_ascii=False),
                json.dumps(prefs_to_dict(user.prefs), ensure_ascii=False),
                prefs_updated_at,
                verified_at or 0,
            ),
        )
        self._db.commit()

    def _user_from_row(self, row: Mapping[str, Any]) -> UserContext:
        return UserContext(
            tier="user",
            user_id=row["user_id"],
            display_name=row["display_name"],
            prefs=prefs_from_dict(row["prefs"]),
            profile=dict(row["profile"]),
        )

    def _fresh(self, row: Mapping[str, Any]) -> bool:
        return self._now() - float(row["verified_at"]) <= self.grace_s

    def initial_user(self) -> UserContext | None:
        """The last signed-in user if verified within the grace period, else None (= guest)."""
        uid = self._meta("last_user_id")
        row = self._row(uid) if uid else None
        if row is None or not self._fresh(row):
            return None
        return self._user_from_row(row)

    def prefs_updated_at(self, user_id: str) -> float | None:
        row = self._row(user_id)
        return row["prefs_updated_at"] if row else None

    def consume_push(self, user_id: str | None) -> bool:
        """True once if the local prefs were newer than Supabase at the last login."""
        if user_id and user_id in self._push:
            self._push.discard(user_id)
            return True
        return False

    # ── IdentityBackend (orchestrator) ───────────────────────────────────────
    async def verify(self, access_token: str) -> UserContext:
        if not self.configured:
            raise AuthError("A bejelentkezés nincs beállítva: SUPABASE_URL és SUPABASE_ANON_KEY kell az auri-jarvis/.env-be.")
        headers = {"apikey": self.anon_key, "Authorization": f"Bearer {access_token}"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
                r = await client.get(f"{self.url}/auth/v1/user", headers=headers)
                if r.status_code in (401, 403):
                    raise AuthError("Érvénytelen vagy lejárt bejelentkezés — jelentkezz be újra a HUD-on.")
                r.raise_for_status()
                auth_user = r.json()
                user_id = auth_user.get("id")
                if not isinstance(user_id, str) or not user_id:
                    raise AuthError("A Supabase nem adott felhasználó-azonosítót.")
                pr = await client.get(
                    f"{self.url}/rest/v1/profiles",
                    params={"user_id": f"eq.{user_id}", "select": "*"},
                    headers={**headers, "Accept": "application/json"},
                )
                rows = pr.json() if pr.status_code == 200 else []
        except AuthError:
            raise
        except (httpx.TransportError, httpx.HTTPStatusError, ValueError) as e:
            return self._offline(access_token, e)

        profile_row = rows[0] if isinstance(rows, list) and rows and isinstance(rows[0], dict) else {}
        return self._login(user_id, auth_user, profile_row)

    def _offline(self, token: str, err: Exception) -> UserContext:
        sub = jwt_sub(token)
        row = self._row(sub) if sub else None
        if row is not None and self._fresh(row):
            log.warning("identity: Supabase unreachable (%s) — offline grace for a cached user", type(err).__name__)
            self._set_meta("last_user_id", row["user_id"])
            return self._user_from_row(row)
        raise AuthError("Nem sikerült ellenőrizni a bejelentkezést (nincs kapcsolat a Supabase-zel) — vendég mód.") from err

    def _login(self, user_id: str, auth_user: Mapping[str, Any], profile_row: Mapping[str, Any]) -> UserContext:
        profile = {k: profile_row.get(k) for k in PROFILE_FIELDS if profile_row.get(k) not in (None, "", [])}
        meta = auth_user.get("user_metadata") if isinstance(auth_user.get("user_metadata"), dict) else {}
        email = auth_user.get("email") if isinstance(auth_user.get("email"), str) else ""
        display = profile.get("nickname") or profile.get("name") or meta.get("name") or (email.split("@")[0] if email else None)

        remote_prefs_raw = (profile_row.get("prefs") or {}).get("jarvis") if isinstance(profile_row.get("prefs"), dict) else None
        remote_ts = 0.0
        if isinstance(remote_prefs_raw, dict):
            with contextlib.suppress(TypeError, ValueError):
                remote_ts = float(remote_prefs_raw.get("updated_at") or 0)
        local = self._row(user_id)
        local_ts = local["prefs_updated_at"] if local else 0.0

        if isinstance(remote_prefs_raw, dict) and remote_ts >= local_ts:
            prefs, ts = prefs_from_dict(remote_prefs_raw), remote_ts
        elif local is not None:
            prefs, ts = prefs_from_dict(local["prefs"]), local_ts
            if local_ts > remote_ts:
                self._push.add(user_id)  # local is newer → the HUD should write it to Supabase
        else:
            prefs, ts = JarvisPrefs(), 0.0  # first login: not onboarded → Auri asks the 4 questions
        first_login = local is None and not isinstance(remote_prefs_raw, dict)
        if not first_login and not prefs.onboarded:
            # 👤 The onboarding (HUD form + the spoken questions) is offered ONCE, at the very first
            # login — never again automatically. Unanswered questions keep their defaults; the ⚙
            # button still opens the form. Saved locally and pushed to Supabase (all devices).
            prefs = dataclasses.replace(prefs, onboarded=True)
            ts = self._now()
            self._push.add(user_id)

        user = UserContext(tier="user", user_id=user_id, display_name=display, prefs=prefs, profile=profile)
        self._store(user, prefs_updated_at=ts, verified_at=self._now())
        self._set_meta("last_user_id", user_id)
        log.info("identity: signed in (user verified)")
        return user

    async def save_prefs(self, user: UserContext) -> float:
        ts = self._now()
        if user.user_id:
            self._store(user, prefs_updated_at=ts, verified_at=None)
        return ts

    async def logout(self) -> None:
        self._set_meta("last_user_id", None)

    # ── optional: guest when Windows locks ───────────────────────────────────
    async def _watch_lock(self, period_s: float = 3.0) -> None:
        was_locked = False
        while True:
            await asyncio.sleep(period_s)
            locked = _workstation_locked()
            if locked and not was_locked and self.on_lock is not None:
                with contextlib.suppress(Exception):
                    res = self.on_lock()
                    if asyncio.iscoroutine(res):
                        await res
            was_locked = locked


def _workstation_locked() -> bool:
    """Windows: the input desktop can't be opened while the session is locked."""
    try:
        import ctypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        h = user32.OpenInputDesktop(0, False, 0x0100)  # DESKTOP_SWITCHDESKTOP
        if not h:
            return True
        user32.CloseDesktop(h)
        return False
    except (AttributeError, OSError):
        return False
