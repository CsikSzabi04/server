"""M3: login verification against a mocked Supabase, local cache, offline grace, prefs merge,
persistence across restarts, and that no token is ever stored."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from auri_jarvis.identity.manager import AuthError, IdentityManager, jwt_sub
from auri_jarvis.identity.prefs import apply_partial, validate_partial

URL = "https://proj.supabase.co"
ANON = "anon-public-key-123456"
UID = "11111111-2222-3333-4444-555555555555"


def make_jwt(sub: str) -> str:
    def b64(d: dict[str, Any]) -> str:
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")

    return f"{b64({'alg': 'HS256'})}.{b64({'sub': sub, 'exp': 1})}.c2lnbmF0dXJl"


TOKEN = make_jwt(UID)


class FakeSupabase:
    def __init__(self) -> None:
        self.profile: dict[str, Any] = {"user_id": UID, "name": "Teszt Elek", "nickname": "Elek", "tone": "laza", "prefs": {}}
        self.down = False
        self.calls: list[httpx.Request] = []

    def handler(self, req: httpx.Request) -> httpx.Response:
        self.calls.append(req)
        if self.down:
            raise httpx.ConnectError("offline", request=req)
        assert req.headers["apikey"] == ANON
        if req.headers.get("authorization") != f"Bearer {TOKEN}":
            return httpx.Response(401, json={"msg": "invalid JWT"})
        if req.url.path == "/auth/v1/user":
            return httpx.Response(200, json={"id": UID, "email": "elek@example.com", "user_metadata": {}})
        if req.url.path == "/rest/v1/profiles":
            assert req.url.params["user_id"] == f"eq.{UID}"
            return httpx.Response(200, json=[self.profile])
        return httpx.Response(404)


def cfg(tmp_path: Path, *, configured: bool = True, grace_days: float = 7) -> dict[str, Any]:
    return {
        "env": {"SUPABASE_URL": URL if configured else "", "SUPABASE_ANON_KEY": ANON if configured else ""},
        "identity": {"offline_grace_days": grace_days, "verify_timeout_s": 2},
        "paths": {"data_dir": str(tmp_path / "data")},
    }


async def manager(tmp_path: Path, sb: FakeSupabase, **kw: Any) -> IdentityManager:
    clock = kw.pop("clock", None)
    m = IdentityManager(cfg(tmp_path, **kw), transport=httpx.MockTransport(sb.handler), now=clock or (lambda: 1_000_000.0))
    await m.start()
    return m


def test_jwt_sub():
    assert jwt_sub(TOKEN) == UID
    assert jwt_sub("garbage") is None and jwt_sub("a.b.c") is None


async def test_not_configured_is_clear_error(tmp_path: Path):
    m = await manager(tmp_path, FakeSupabase(), configured=False)
    with pytest.raises(AuthError, match="SUPABASE_URL"):
        await m.verify(TOKEN)
    await m.stop()


async def test_first_login_profile_and_not_onboarded(tmp_path: Path):
    sb = FakeSupabase()
    m = await manager(tmp_path, sb)
    u = await m.verify(TOKEN)
    assert u.tier == "user" and u.user_id == UID and u.display_name == "Elek"
    assert u.profile == {"name": "Teszt Elek", "nickname": "Elek", "tone": "laza"}
    assert u.prefs.onboarded is False and u.prefs.wake_word == "hey_auri"  # → Auri asks the 4 questions
    assert m.initial_user().user_id == UID
    assert not m.consume_push(UID)
    await m.stop()


async def test_onboarding_is_offered_only_at_the_very_first_login(tmp_path: Path):
    """👤 2026-11-24: the form + spoken questions come ONCE in total, never again by themselves."""
    sb = FakeSupabase()
    m = await manager(tmp_path, sb)
    first = await m.verify(TOKEN)
    assert first.prefs.onboarded is False  # the one and only time
    import dataclasses

    partly = dataclasses.replace(
        first, prefs=apply_partial(first.prefs, validate_partial({"address": "Szabi", "answered": ["address"]}))
    )
    await m.save_prefs(partly)  # answered 1 of 4, then closed the HUD
    again = await m.verify(TOKEN)  # next login (HUD reopened / daemon restarted)
    assert again.prefs.onboarded is True and again.prefs.address == "Szabi"
    assert again.prefs.wake_word == "hey_auri"  # unanswered → default kept
    assert m.consume_push(UID) is True  # → the HUD writes it to Supabase (every device)
    assert (await m.verify(TOKEN)).prefs.onboarded is True
    await m.stop()


async def test_onboarding_not_offered_again_on_a_new_device(tmp_path: Path):
    sb = FakeSupabase()
    sb.profile["prefs"] = {"jarvis": {"answered": [], "onboarded": False, "updated_at": 10}}  # seen elsewhere
    m = await manager(tmp_path, sb)
    u = await m.verify(TOKEN)
    assert u.prefs.onboarded is True
    await m.stop()


async def test_bad_token_is_rejected(tmp_path: Path):
    m = await manager(tmp_path, FakeSupabase())
    with pytest.raises(AuthError, match="Érvénytelen"):
        await m.verify(make_jwt("someone-else"))
    assert m.initial_user() is None
    await m.stop()


async def test_remote_newer_prefs_win(tmp_path: Path):
    sb = FakeSupabase()
    m = await manager(tmp_path, sb)
    u = await m.verify(TOKEN)
    await m.save_prefs(u)  # local copy at t=1_000_000
    sb.profile["prefs"] = {"jarvis": {"voice": "george", "wake_word": "hey_jarvis", "onboarded": True, "updated_at": 2_000_000}}
    u2 = await m.verify(TOKEN)
    assert (u2.prefs.voice, u2.prefs.wake_word, u2.prefs.onboarded) == ("george", "hey_jarvis", True)
    assert not m.consume_push(UID)
    await m.stop()


async def test_local_newer_prefs_win_and_request_push(tmp_path: Path):
    sb = FakeSupabase()
    sb.profile["prefs"] = {"jarvis": {"voice": "george", "updated_at": 10}, "other": "keep"}
    m = await manager(tmp_path, sb)
    u = await m.verify(TOKEN)
    assert u.prefs.voice == "george"
    import dataclasses

    changed = dataclasses.replace(u, prefs=apply_partial(u.prefs, validate_partial({"voice": "piper"})))
    await m.save_prefs(changed)  # offline change at t=1_000_000 > 10
    u2 = await m.verify(TOKEN)
    assert u2.prefs.voice == "piper"
    assert m.consume_push(UID) is True and m.consume_push(UID) is False
    await m.stop()


async def test_offline_grace_and_expiry(tmp_path: Path):
    sb = FakeSupabase()
    now = [1_000_000.0]
    m = await manager(tmp_path, sb, clock=lambda: now[0])
    await m.verify(TOKEN)
    sb.down = True
    now[0] += 6 * 86_400  # 6 days later, offline → cached user accepted
    u = await m.verify(TOKEN)
    assert u.user_id == UID and u.display_name == "Elek"
    now[0] += 2 * 86_400  # 8 days after the last real verification → guest
    with pytest.raises(AuthError, match="vendég"):
        await m.verify(TOKEN)
    assert m.initial_user() is None
    await m.stop()


async def test_offline_unknown_user_is_guest(tmp_path: Path):
    sb = FakeSupabase()
    sb.down = True
    m = await manager(tmp_path, sb)
    with pytest.raises(AuthError):
        await m.verify(TOKEN)
    await m.stop()


async def test_persistence_across_restart_and_logout(tmp_path: Path):
    sb = FakeSupabase()
    m = await manager(tmp_path, sb)
    u = await m.verify(TOKEN)
    import dataclasses

    u = dataclasses.replace(
        u, prefs=apply_partial(u.prefs, validate_partial({"wake_word": "hey_jarvis", "answered": ["wake_word"]}))
    )
    await m.save_prefs(u)
    await m.stop()

    m2 = await manager(tmp_path, sb)  # daemon restart
    again = m2.initial_user()
    assert again is not None and again.prefs.wake_word == "hey_jarvis" and again.prefs.answered == ("wake_word",)
    await m2.logout()
    assert m2.initial_user() is None  # next start = guest
    await m2.stop()


async def test_token_is_never_stored(tmp_path: Path):
    m = await manager(tmp_path, FakeSupabase())
    await m.verify(TOKEN)
    await m.stop()
    blob = b"".join(p.read_bytes() for p in (tmp_path / "data" / "body").glob("identity.db*"))
    assert TOKEN.encode() not in blob and TOKEN.split(".")[1].encode() not in blob
    assert ANON.encode() not in blob
