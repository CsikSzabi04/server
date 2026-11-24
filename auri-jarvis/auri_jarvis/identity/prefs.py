"""auri_jarvis.identity.prefs — validate / merge / (de)serialize JarvisPrefs (owner: AI-3).

Both roads into the prefs go through `validate_partial()`:
  `prefs.proposed` (AI-2 onboarding)  and  `prefs.set` (HUD form)
Unknown keys or bad values raise PrefsError (Hungarian, user-facing message).

`welcome_routine` schema (spec 5.11 / JARVIS_BUILD M3):
  {"music_url": "https://…" | "spotify:…" | None,
   "apps": [{"app": "<apps.yaml id>", "monitor": 1-3, "fullscreen": bool}],   ≤ 8
   "urls": [{"url": "https://…", "monitor": 1-3}]}                            ≤ 8
App ids are only format-checked here; the routine runner (AI-2) re-checks the allowlist.
"""

from __future__ import annotations

import dataclasses
import re
import unicodedata
from collections.abc import Mapping
from typing import Any, get_args

from ..contracts import GUEST, JarvisPrefs, PrefKey, UserContext, VoiceName, WakeWord

WAKE_WORDS: tuple[str, ...] = get_args(WakeWord)
VOICES: tuple[str, ...] = get_args(VoiceName)
PREF_KEYS: tuple[str, ...] = get_args(PrefKey)
_PARTIAL_KEYS = frozenset({*PREF_KEYS, "answered", "onboarded"})
_APP_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,39}$")
MAX_ADDRESS = 40
MAX_ITEMS = 8
MAX_URL = 500


class PrefsError(ValueError):
    pass


def _clean_text(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")  # no control chars
    return " ".join(s.split())


def _check_url(u: Any, *, allow_spotify: bool) -> str:
    if not isinstance(u, str):
        raise PrefsError("Az URL szöveg legyen.")
    u = u.strip()
    if len(u) > MAX_URL:
        raise PrefsError("Túl hosszú URL.")
    low = u.lower()
    if low.startswith(("http://", "https://")) and len(u) > len("https://"):
        if any(c.isspace() for c in u):
            raise PrefsError("Az URL nem tartalmazhat szóközt.")
        return u
    if allow_spotify and low.startswith("spotify:") and len(u) > len("spotify:"):
        return u
    allowed = "http(s) vagy spotify:" if allow_spotify else "http(s)"
    raise PrefsError(f"Csak {allowed} cím engedélyezett: {u[:60]}")


def _check_monitor(m: Any) -> int:
    if isinstance(m, bool) or not isinstance(m, (int, float)) or int(m) != m or not 1 <= int(m) <= 3:
        raise PrefsError("A monitor 1, 2 vagy 3 lehet.")
    return int(m)


def validate_routine(r: Any) -> dict[str, Any] | None:
    if r is None or r is False:
        return None
    if not isinstance(r, Mapping):
        raise PrefsError("A rutin objektum legyen (vagy null).")
    extra = set(r) - {"music_url", "apps", "urls"}
    if extra:
        raise PrefsError(f"Ismeretlen rutin-mező: {', '.join(sorted(extra))}")
    music = r.get("music_url")
    out: dict[str, Any] = {
        "music_url": None if music in (None, "") else _check_url(music, allow_spotify=True),
        "apps": [],
        "urls": [],
    }
    apps = r.get("apps") or []
    urls = r.get("urls") or []
    if not isinstance(apps, list) or not isinstance(urls, list):
        raise PrefsError("Az 'apps' és az 'urls' lista legyen.")
    if len(apps) > MAX_ITEMS or len(urls) > MAX_ITEMS:
        raise PrefsError(f"Legfeljebb {MAX_ITEMS} app és {MAX_ITEMS} URL lehet a rutinban.")
    for a in apps:
        if not isinstance(a, Mapping) or set(a) - {"app", "monitor", "fullscreen"}:
            raise PrefsError("Rutin-app: {app, monitor, fullscreen}.")
        app = a.get("app")
        if not isinstance(app, str) or not _APP_ID.match(app):
            raise PrefsError(f"Érvénytelen app-azonosító: {str(app)[:40]}")
        out["apps"].append(
            {"app": app, "monitor": _check_monitor(a.get("monitor", 2)), "fullscreen": bool(a.get("fullscreen", False))}
        )
    for u in urls:
        if not isinstance(u, Mapping) or set(u) - {"url", "monitor"}:
            raise PrefsError("Rutin-URL: {url, monitor}.")
        out["urls"].append({"url": _check_url(u.get("url"), allow_spotify=False), "monitor": _check_monitor(u.get("monitor", 1))})
    return out


def validate_partial(data: Any) -> dict[str, Any]:
    """Validate a partial prefs update. Returns the cleaned dict (only the given keys)."""
    if not isinstance(data, Mapping):
        raise PrefsError("A beállítás objektum legyen.")
    extra = set(data) - _PARTIAL_KEYS
    if extra:
        raise PrefsError(f"Ismeretlen beállítás: {', '.join(sorted(extra))}")
    out: dict[str, Any] = {}
    if "address" in data:
        a = data["address"]
        if a is None:
            a = ""
        if not isinstance(a, str):
            raise PrefsError("A megszólítás szöveg legyen.")
        a = _clean_text(a)
        if len(a) > MAX_ADDRESS:
            raise PrefsError(f"A megszólítás legfeljebb {MAX_ADDRESS} karakter.")
        out["address"] = a or "you"
    if "wake_word" in data:
        if data["wake_word"] not in WAKE_WORDS:
            raise PrefsError(f"Az ébresztőszó csak {' / '.join(WAKE_WORDS)} lehet.")
        out["wake_word"] = data["wake_word"]
    if "voice" in data:
        if data["voice"] not in VOICES:
            raise PrefsError(f"A hang csak {' / '.join(VOICES)} lehet.")
        out["voice"] = data["voice"]
    if "welcome_routine" in data:
        out["welcome_routine"] = validate_routine(data["welcome_routine"])
    if "answered" in data:
        ans = data["answered"]
        if not isinstance(ans, (list, tuple)) or any(k not in PREF_KEYS for k in ans):
            raise PrefsError(f"Az 'answered' csak ezeket tartalmazhatja: {', '.join(PREF_KEYS)}")
        out["answered"] = tuple(dict.fromkeys(ans))
    if "onboarded" in data:
        if not isinstance(data["onboarded"], bool):
            raise PrefsError("Az 'onboarded' igaz/hamis érték.")
        out["onboarded"] = data["onboarded"]
    return out


def apply_partial(prefs: JarvisPrefs, clean: Mapping[str, Any]) -> JarvisPrefs:
    """Merge an already-validated partial into prefs. `answered` is a union; `onboarded`
    turns True by itself once all 4 questions are answered (an explicit value wins).
    An explicit `onboarded: False` means "set up again": `answered` restarts from what is given."""
    changes = {k: v for k, v in clean.items() if k not in ("answered", "onboarded")}
    if clean.get("onboarded") is False:
        answered = tuple(dict.fromkeys(clean.get("answered", ())))
    else:
        answered = tuple(dict.fromkeys((*prefs.answered, *clean.get("answered", ()))))
    onboarded = clean.get("onboarded", prefs.onboarded or set(PREF_KEYS) <= set(answered))
    return dataclasses.replace(prefs, **changes, answered=answered, onboarded=onboarded)


def prefs_to_dict(p: JarvisPrefs) -> dict[str, Any]:
    d = dataclasses.asdict(p)
    d["answered"] = list(p.answered)
    return d


def prefs_from_dict(d: Any, base: JarvisPrefs | None = None) -> JarvisPrefs:
    """Lenient load (Supabase / local cache): invalid fields are dropped, not fatal."""
    prefs = base or JarvisPrefs()
    if not isinstance(d, Mapping):
        return prefs
    clean: dict[str, Any] = {}
    for key in (*PREF_KEYS, "answered", "onboarded"):
        if key in d:
            try:
                clean.update(validate_partial({key: d[key]}))
            except PrefsError:
                continue
    return dataclasses.replace(prefs, **clean)  # a stored snapshot: set as-is, no merge rules


def guest_prefs(cfg: Mapping[str, Any] | None = None) -> JarvisPrefs:
    """Guest defaults from jarvis.yaml `guest_defaults` (fixed by the user: you · hey_auri ·
    daniel · no routine). Never onboarded, never asks."""
    gd = (cfg or {}).get("guest_defaults") or {}
    base = JarvisPrefs()
    try:
        clean = validate_partial({k: gd[k] for k in PREF_KEYS if k in gd})
    except PrefsError:
        clean = {}
    return dataclasses.replace(apply_partial(base, clean), answered=(), onboarded=False)


def guest_user(cfg: Mapping[str, Any] | None = None) -> UserContext:
    prefs = guest_prefs(cfg)
    return GUEST if prefs == GUEST.prefs else UserContext(tier="guest", prefs=prefs)
