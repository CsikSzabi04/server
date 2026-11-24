"""Fast-path (AI-2, spec 5.5 + Appendix B): common commands without the LLM, < 100 ms.

Rules that keep it safe:
- Every pattern matches the WHOLE (cleaned) utterance — never a substring. So "hány óra
  alatt tanulható meg a Python?" is not a time request, and "ki vagy?" / "de a brain miért
  nem tud jól válaszolni?" never hit anything (the AuriGPT BRAIN substring bug, 2026-11-20).
- Entities must resolve with confidence (numbers via hu_text, apps via AppCatalog with a
  fuzzy threshold + margin). Unsure → None → the LLM decides.
- Patterns are accent-tolerant (STT sometimes drops accents) but number words keep theirs.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..tools.apps import AppCatalog
from .hu_text import extract_monitor, norm, parse_duration, parse_number

_ACCENTS = {"a": "aá", "á": "aá", "e": "eé", "é": "eé", "i": "ií", "í": "ií", "o": "oóöő", "ó": "oó",
            "ö": "oöő", "ő": "oöő", "u": "uúüű", "ú": "uú", "ü": "uüű", "ű": "uüű"}  # fmt: skip


def _tolerant(pattern: str) -> str:
    """Accented vowels in a literal pattern → character classes ("hány" → "h[aá]ny")."""
    out = []
    for ch in pattern:
        if ch in "áéíóöőúüű":
            out.append(f"[{_ACCENTS[ch]}]")
        else:
            out.append(ch)
    return "".join(out)


def _rx(pattern: str) -> re.Pattern[str]:
    return re.compile("^" + _tolerant(pattern) + "$", re.IGNORECASE)


@dataclass(frozen=True)
class Intent:
    name: str  # tool name, or "cancel"
    args: dict[str, Any] = field(default_factory=dict)


_WAKE = re.compile(_tolerant(r"^(?:(?:hey|hé|hej)\s+)?(?:auri|jarvis)\b[,!.\s]*"), re.IGNORECASE)
_POLITE_HEAD = re.compile(_tolerant(r"^(?:kérlek|légyszi|légy szíves|légyszíves|please)\b[,\s]*"), re.IGNORECASE)
_POLITE_TAIL = re.compile(_tolerant(r"[,\s]+(?:kérlek|légyszi|légy szíves|please)$"), re.IGNORECASE)


def clean(text: str) -> str:
    t = " ".join(text.strip().split())
    t = _WAKE.sub("", t)
    t = t.strip(" .!?…")
    t = _POLITE_HEAD.sub("", t)
    t = _POLITE_TAIL.sub("", t)
    return t.strip(" ,.!?…").lower()


# ── grammar ──────────────────────────────────────────────────────────────────
CANCEL = _rx(r"(?:mégse|állj|elég|csend|csönd|hallgass|stop|cancel|hagyd|semmi)")
TIME = _rx(
    r"(?:mondd meg,?\s*)?(?:hány óra(?: van)?(?: most)?|mennyi (?:az )?idő(?: van)?(?: most)?|mennyi az óra"
    r"|milyen nap van(?: ma)?|hányadika van(?: ma)?|what time is it|what'?s the time)"
)
VOL_LEVEL = _rx(
    r"(?:(?:állítsd|tedd|vedd)\s+(?:a\s+)?hangerőt\s+|(?:a\s+)?hangerő(?:t)?\s+(?:legyen\s+)?)"
    r"(?P<n>[\w%-]+?)(?:\s*(?:százalék|%)\w*)?(?:\s*(?:ra|re))?"
)
VOL_UP = _rx(
    r"(?:hangosabban|hangosíts|hangosítsd(?: fel)?|hangosabbra|hangerő fel|feljebb a hangot"
    r"|vedd fel a hangerőt|turn it up|volume up)(?: egy kicsit| kicsit| még)?"
)
VOL_DOWN = _rx(
    r"(?:halkabban|halkíts|halkítsd(?: le)?|halkabbra|hangerő le|lejjebb a hangot"
    r"|vedd le a hangerőt|turn it down|volume down)(?: egy kicsit| kicsit| még)?"
)
VOL_MUTE = _rx(r"(?:némítsd(?: le)?|némíts|némítás|kapcsold ki a hangot|mute)")
VOL_UNMUTE = _rx(r"(?:némítás ki|hang vissza|kapcsold vissza a hangot|unmute)")
VOL_MAX = _rx(
    r"(?:teljes hangerő|maximális hangerő|max hangerő|hangerő (?:a )?maximumra"
    r"|(?:tekerd|vedd|állítsd) (?:fel )?a hangerőt (?:a )?maximumra)"
)
MEDIA_NEXT = _rx(r"(?:következő|kövi|next)(?: (?:szám|dal|zene|track|song|videó))?")
MEDIA_PREV = _rx(r"(?:előző|previous)(?: (?:szám|dal|zene|track|song|videó))?")
MEDIA_TOGGLE = _rx(
    r"(?:szünet|pause|play|állítsd meg a (?:zenét|videót)|állítsd le a zenét|folytasd a (?:zenét|lejátszást|videót)"
    r"|indítsd (?:el )?a zenét)"
)
TIMER_A = _rx(r"(?:(?:állíts be|indíts|tegyél|rakj)\s+)?(?:egy\s+)?(?:időzítőt?|timert?)\s+(?P<dur>.+?)")
TIMER_B = _rx(r"(?:(?:állíts be|indíts|kérek)\s+)?(?:egy\s+)?(?P<dur>.+?(?:perces|másodperces|órás))\s+(?:időzítő\w*|timer\w*)")
TIMER_C = _rx(r"(?:szólj|jelezz|ébressz(?: fel)?)\s+(?P<dur>.+?)\s+múlva(?:,?\s*(?:hogy\s+)?(?P<label>.+))?")
OPEN = _rx(
    r"(?:nyisd(?: meg| fel| ki)?|nyiss meg|indítsd(?: el)?|dobd fel|hozd (?:fel|elő)|open|launch|nincs meg)\s+(?P<target>.+)"
)
MOVE = _rx(r"(?:tedd|rakd|vidd|helyezd|told)(?: át)?\s+(?P<target>.+)")
FULLSCREEN = re.compile(_tolerant(r"\s*,?\s*(?:teljes képernyő(?:n|re|s)?|fullscreen)\s*"), re.IGNORECASE)
REMEMBER = _rx(r"(?:jegyezd (?:fel|meg)|emlékezz rá|ne felejtsd el|remember)(?:,)?(?: hogy)?\s+(?P<fact>.{3,})")
FORGET = _rx(r"(?:felejtsd el|töröld (?:az )?emlékeid közül|forget)(?:,)?(?: hogy)?\s+(?P<what>.{3,})")
RECALL = _rx(r"(?:mit tudsz rólam|mire emlékszel(?: rólam)?|mit jegyeztél (?:fel|meg)(?: rólam)?|mit tudsz még rólam)")


def _restore_case(original: str, lowered_part: str) -> str:
    """`clean()` lower-cases; a remembered fact should keep its capitals ("Bodri")."""
    i = original.lower().rfind(lowered_part)
    return original[i : i + len(lowered_part)] if i >= 0 else lowered_part


def _level(token: str) -> int | None:
    n = parse_number(token)
    return n if n is not None and 0 <= n <= 100 else None


def match(text: str, apps: AppCatalog | None = None, routine_phrases: Mapping[str, str] | None = None) -> Intent | None:
    """Utterance → Intent, or None (= let the LLM handle it).
    `routine_phrases`: normalised whole-utterance phrase → routine id (from routines.yaml)."""
    t = clean(text)
    if not t or len(t) > 120:
        return None
    if CANCEL.match(t):
        return Intent("cancel")
    if TIME.match(t):
        return Intent("get_time")
    if routine_phrases and (rid := routine_phrases.get(norm(t))):
        return Intent("run_routine", {"name": rid})
    if RECALL.match(t):
        return Intent("recall")
    if m := REMEMBER.match(t):
        return Intent("remember", {"fact": _restore_case(text, m.group("fact"))})
    if m := FORGET.match(t):
        return Intent("forget", {"what": _restore_case(text, m.group("what"))})

    if VOL_MAX.match(t):
        return Intent("set_volume", {"level": 100})
    if VOL_UNMUTE.match(t):
        return Intent("set_volume", {"change": "unmute"})
    if VOL_MUTE.match(t):
        return Intent("set_volume", {"change": "mute"})
    if VOL_UP.match(t):
        return Intent("set_volume", {"change": "up"})
    if VOL_DOWN.match(t):
        return Intent("set_volume", {"change": "down"})
    if m := VOL_LEVEL.match(t):
        lvl = _level(m.group("n"))
        return Intent("set_volume", {"level": lvl}) if lvl is not None else None

    if MEDIA_NEXT.match(t):
        return Intent("media_control", {"action": "next"})
    if MEDIA_PREV.match(t):
        return Intent("media_control", {"action": "previous"})
    if MEDIA_TOGGLE.match(t):
        return Intent("media_control", {"action": "play_pause"})

    for rx in (TIMER_C, TIMER_B, TIMER_A):
        if m := rx.match(t):
            secs = parse_duration(m.group("dur"))
            if not secs:
                return None
            args: dict[str, Any] = {"seconds": secs}
            label = (m.groupdict().get("label") or "").strip()
            if label:
                args["label"] = label[:80]
            return Intent("set_timer", args)

    if apps is not None:
        if m := OPEN.match(t):
            return _open(m.group("target"), apps, from_nincs=t.startswith("nincs meg"))
        if m := MOVE.match(t):
            return _move(m.group("target"), apps)
    return None


def _open(target: str, apps: AppCatalog, *, from_nincs: bool) -> Intent | None:
    full = bool(FULLSCREEN.search(target))
    target = FULLSCREEN.sub(" ", target)
    monitor, rest = extract_monitor(target)
    if not rest or len(rest.split()) > 4:
        return None
    hit = apps.resolve(rest)
    if hit is None or (from_nincs and hit.score < 95):  # "nincs meg" is only a mishearing if the app is certain
        return None
    args: dict[str, Any] = {"name": hit.entry.id}
    if monitor:
        args["monitor"] = monitor
    if full:
        args["fullscreen"] = True
    return Intent("open_app", args)


def _move(target: str, apps: AppCatalog) -> Intent | None:
    monitor, rest = extract_monitor(target)
    if monitor is None or not rest or len(rest.split()) > 4:
        return None
    hit = apps.resolve(rest, kind="app")
    if hit is None:
        return None
    return Intent("move_window", {"app": hit.entry.id, "monitor": monitor})
