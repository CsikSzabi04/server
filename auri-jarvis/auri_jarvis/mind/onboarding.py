"""Onboarding dialogue — the 4 questions (AI-2, spec 5.11; JARVIS_BUILD M3).

Only for a LOGGED-IN user whose prefs.onboarded is False; a guest is never asked anything.
Answers leave as `prefs.proposed` partials ({<key>: value, "answered": [<key>]}) — the same
shape the HUD form saves, so voice and form are interchangeable: AI-3 validates, merges
(`answered` is a union), saves and calls Mind.on_identity_change; once all 4 are answered
AI-3 turns `onboarded` on by itself. A question already answered (on the HUD, or before)
is never asked again.

The dialogue is a pure state machine: it returns what to say and the events to emit; the
Mind decides when it runs (login trigger, "állítsuk be újra", the follow-up answer turn).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..contracts import Event, PrefKey, UserContext
from .hu_text import norm

ORDER: tuple[PrefKey, ...] = ("address", "wake_word", "voice", "welcome_routine")
STEP = {k: i + 1 for i, k in enumerate(ORDER)}
QUESTION = {
    "address": "Hogyan szólítsalak?",
    "wake_word": "Melyik ébresztőszót szeretnéd: Hey Auri vagy Hey Jarvis?",
    "voice": "Melyik hang tetszett jobban: az első, a második, vagy a helyi, ingyenes hang?",
    "welcome_routine": "Kérsz „Üdv itthon” rutint? Igen vagy nem?",
}
OPTIONS: dict[str, list[str]] = {
    "address": [],
    "wake_word": ["Hey Auri", "Hey Jarvis"],
    "voice": ["Daniel", "George", "Helyi (Piper)"],
    "welcome_routine": ["Igen", "Nem"],
}
INTRO = "Szia! Négy gyors kérdés, hogy jól működjek nálad. Bármikor mondhatod, hogy később."
SAMPLES_INTRO = "Most két hangmintát hallasz."
DONE = "Kész, minden be van állítva."
LATER = "Rendben, alapértékekkel folytatjuk. Ha mégis beállítanád, mondd: állítsuk be újra."
ROUTINE_YES = "Rendben. A részleteket, vagyis a zenét, az appokat és a monitorokat a HUD-on tudod beállítani."
REPLY_WINDOW_S = 12.0

LATER_RX = re.compile(r"^(?:később|majd később|most nem|nem most|hagyjuk|kihagyom|skip|later)\b")
RESTART_RX = re.compile(
    r"^(?:(?:auri|jarvis)[, ]+)?(?:állítsuk be újra|kezdjük újra a beállítást|beállítás újra|újra a beállítást"
    r"|állítsunk be mindent újra|set up again)\b"
)
YES_RX = re.compile(r"^(?:igen|ja|aha|persze|kérek|kérem|mehet|legyen|oké|ok|yes|yeah|sure)\b")
NO_RX = re.compile(r"^(?:nem|ne|nem kérek|nincs rá szükség|no|nope)\b")
NO_ADDRESS_RX = re.compile(r"^(?:semmi|sehogy|sehogyan|mindegy|nem kell|ne szólíts|egyszerűen tegezz|tegezz|you)\b")
ADDRESS_PATTERNS = (
    re.compile(r"^(?:szólíts|hívj|nevezz)(?:\s+csak)?\s+(?P<n>.+?)$"),
    re.compile(r"^(?:a nevem|(?:én )?vagyok|legyen)\s+(?P<n>.+?)$"),
)
_NAME_SUFFIX = re.compile(r"(?:-?n[ae]k|-?k[ée]nt)$")


ANSWER_TTL_S = 60.0  # a reply later than this is a new request, not an answer


@dataclass
class OnboardingState:
    user_id: str
    current: PrefKey | None = None
    proposed: set[str] = field(default_factory=set)  # keys answered by voice in this run
    retried: bool = False
    fresh: bool = False  # "állítsuk be újra": the old `answered` no longer counts


def next_key(
    user: UserContext, extra_answered: set[str] | frozenset[str] = frozenset(), *, ignore_prefs: bool = False
) -> PrefKey | None:
    answered = (set() if ignore_prefs else set(user.prefs.answered)) | set(extra_answered)
    return next((k for k in ORDER if k not in answered), None)


def needs_onboarding(user: UserContext) -> bool:
    return user.tier == "user" and bool(user.user_id) and not user.prefs.onboarded and next_key(user) is not None


# ── answer parsers (None = didn't understand) ────────────────────────────────
def parse_address(text: str) -> str | None:
    t = text.strip().strip(".!?").strip()
    low = t.lower()
    if NO_ADDRESS_RX.match(low):
        return "you"
    if low in ("uram", "főnök", "főnököm"):
        return low
    name = None
    for rx in ADDRESS_PATTERNS:
        m = rx.match(low)
        if m:
            name = t[m.start("n") : m.end("n")]
            break
    if name is None:
        if len(t.split()) > 3:
            return None  # a sentence, not a name — ask again
        name = t
    name = _NAME_SUFFIX.sub("", name.strip(" ,.")).strip()
    if not name or len(name) > 40:
        return None
    if name.lower() == "uram":
        return "uram"
    return " ".join(w[:1].upper() + w[1:] for w in name.split())


def _has(text: str, stems: tuple[str, ...]) -> bool:
    """Any word equals a stem, or starts with a stem of ≥ 4 letters (Hungarian suffixes:
    "jarvist", "elsőt", "másodikat"). Short stems ("ori", "dani") must match whole words."""
    for w in norm(text).split():
        for s in stems:
            if w == s or (len(s) >= 4 and w.startswith(s)):
                return True
    return False


def parse_wake_word(text: str) -> str | None:
    jarvis = _has(text, ("jarvis", "dzsarvis", "masodik", "kettes", "ketto"))
    auri = _has(text, ("auri", "ori", "aury", "hauri", "elso", "egyes"))
    if jarvis and not auri:
        return "hey_jarvis"
    if auri and not jarvis:
        return "hey_auri"
    return None


def parse_voice(text: str) -> str | None:
    hits = {
        "daniel": _has(text, ("daniel", "denijel", "dani", "elso", "egyes")),
        "george": _has(text, ("george", "dzsordz", "gyorgy", "masodik", "kettes")),
        "piper": _has(text, ("helyi", "ingyenes", "piper", "offline", "harmadik", "harmas", "gepi")),
    }
    found = [k for k, v in hits.items() if v]
    return found[0] if len(found) == 1 else None


def parse_yes_no(text: str) -> bool | None:
    t = text.strip().lower()
    if NO_RX.match(t):
        return False
    if YES_RX.match(t):
        return True
    return None


# ── the dialogue ─────────────────────────────────────────────────────────────
@dataclass
class Turn:
    """What one onboarding step produces."""

    say: list[str] = field(default_factory=list)  # spoken now, in the turn
    events: list[Event] = field(default_factory=list)  # emitted AFTER the spoken text
    done: bool = False


def ask(key: PrefKey, *, intro: str | None = None) -> Turn:
    """The question for `key` (+ the voice samples before question 3)."""
    q = QUESTION[key]
    turn = Turn()
    if intro:
        turn.say.append(intro)
    ev = [Event("onboarding", {"step": STEP[key], "question": q, "options": OPTIONS[key]})]
    if key == "voice":
        # The samples queue behind the spoken text (shared speech lock), then the question
        # as a `say`, then we listen — so the order the user hears is intro → samples → question.
        turn.say.append(SAMPLES_INTRO)
        ev += [Event("voice.sample", {"voice": "daniel"}), Event("voice.sample", {"voice": "george"})]
        ev.append(Event("say", {"text": q}))
    else:
        turn.say.append(q)
    ev.append(Event("mind.expects_reply", {"timeout_s": REPLY_WINDOW_S}))
    turn.events = ev
    return turn


def start(user: UserContext, state: OnboardingState, *, intro: str = INTRO) -> Turn:
    key = next_key(user, state.proposed, ignore_prefs=state.fresh)
    if key is None:
        return Turn(done=True)
    state.current = key
    state.retried = False
    return ask(key, intro=intro)


def answer(user: UserContext, state: OnboardingState, text: str, *, default_welcome: dict[str, Any]) -> Turn | None:
    """Handle the reply to `state.current`. None = not an answer (the Mind continues normally)."""
    key = state.current
    if key is None:
        return None
    low = text.strip().lower().strip(".!?")
    if LATER_RX.match(low) and not (key == "welcome_routine" and NO_RX.match(low)):
        state.current = None
        return Turn(say=[LATER], events=[Event("prefs.proposed", {"onboarded": True})], done=True)

    value: Any
    ack = ""
    if key == "address":
        value = parse_address(text)
        if value is not None:
            ack = "Rendben." if value == "you" else f"Rendben, {value}."
    elif key == "wake_word":
        value = parse_wake_word(text)
        if value is not None:
            ack = "Hey Jarvis lesz." if value == "hey_jarvis" else "Hey Auri lesz."
    elif key == "voice":
        value = parse_voice(text)
        if value is not None:
            ack = {"daniel": "Az első hang marad.", "george": "A második hang lesz.", "piper": "A helyi hang lesz."}[value]
    else:
        yn = parse_yes_no(text)
        if yn is not None:  # value None = "no routine" is a valid answer, so return here
            ack = ROUTINE_YES if yn else "Rendben, rutin nélkül."
            return _accepted(user, state, key, default_welcome if yn else None, ack)
        value = None

    if value is None:
        if state.retried:  # second miss → leave it; it stays unanswered for next time
            state.current = None
            return Turn(say=["Ezt most kihagyom, később a HUD-on is beállíthatod."], done=True)
        state.retried = True
        return ask(key, intro="Ezt nem értettem.")
    return _accepted(user, state, key, value, ack)


def _accepted(user: UserContext, state: OnboardingState, key: PrefKey, value: Any, ack: str) -> Turn:
    state.proposed.add(key)
    events = [Event("prefs.proposed", {key: value, "answered": [key]})]
    nxt = next_key(user, state.proposed, ignore_prefs=state.fresh)
    if nxt is None:
        state.current = None
        return Turn(say=[ack, DONE], events=events, done=True)
    state.current = nxt
    state.retried = False
    follow = ask(nxt)
    return Turn(say=[ack, *follow.say], events=events + follow.events)
