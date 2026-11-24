"""Prefs validation (5.11), state machine (4.2), timing math."""

from __future__ import annotations

import pytest

from auri_jarvis.contracts import Event, JarvisPrefs
from auri_jarvis.identity.prefs import (
    PrefsError,
    apply_partial,
    guest_prefs,
    guest_user,
    prefs_from_dict,
    prefs_to_dict,
    validate_partial,
)
from auri_jarvis.state import State, StateMachine
from auri_jarvis.timing import TurnTiming, percentile, summarize

# ── prefs ────────────────────────────────────────────────────────────────────


def test_guest_defaults_match_user_decision():
    g = guest_user({"guest_defaults": {"address": "you", "wake_word": "hey_auri", "voice": "daniel", "welcome_routine": None}})
    assert g.tier == "guest"
    assert (g.prefs.address, g.prefs.wake_word, g.prefs.voice, g.prefs.welcome_routine) == ("you", "hey_auri", "daniel", None)
    assert g.prefs.onboarded is False and g.prefs.answered == ()
    assert guest_prefs(None) == JarvisPrefs()


def test_validate_partial_happy_path():
    clean = validate_partial(
        {
            "address": "  Szabi\x07 ",
            "wake_word": "hey_jarvis",
            "voice": "george",
            "welcome_routine": {
                "music_url": "spotify:playlist:abc",
                "apps": [{"app": "vscode", "monitor": 2, "fullscreen": True}],
                "urls": [{"url": "https://claude.ai/new", "monitor": 1}],
            },
            "answered": ["address", "wake_word", "address"],
        }
    )
    assert clean["address"] == "Szabi"
    assert clean["answered"] == ("address", "wake_word")
    assert clean["welcome_routine"]["apps"][0] == {"app": "vscode", "monitor": 2, "fullscreen": True}


@pytest.mark.parametrize(
    "bad",
    [
        {"voice": "morgan"},
        {"wake_word": "ok_google"},
        {"unknown": 1},
        {"address": "x" * 41},
        {"welcome_routine": {"music_url": "javascript:alert(1)"}},
        {"welcome_routine": {"urls": [{"url": "file:///C:/x", "monitor": 1}]}},
        {"welcome_routine": {"apps": [{"app": "rm -rf", "monitor": 1}]}},
        {"welcome_routine": {"apps": [{"app": "vscode", "monitor": 4}]}},
        {"welcome_routine": {"apps": [{"app": "vscode", "monitor": True}]}},
        {"welcome_routine": {"shell": "x"}},
        {"answered": ["address", "password"]},
        {"onboarded": "yes"},
        "not a dict",
    ],
)
def test_validate_partial_rejects(bad):
    with pytest.raises(PrefsError):
        validate_partial(bad)


def test_apply_partial_onboarded_after_all_four():
    p = JarvisPrefs()
    p = apply_partial(p, validate_partial({"address": "uram", "answered": ["address"]}))
    assert p.address == "uram" and not p.onboarded
    p = apply_partial(p, validate_partial({"voice": "piper", "answered": ["wake_word", "voice", "welcome_routine"]}))
    assert p.onboarded and p.voice == "piper"
    p = apply_partial(p, validate_partial({"onboarded": False}))  # "állítsuk be újra"
    assert not p.onboarded


def test_prefs_roundtrip_and_lenient_load():
    p = apply_partial(JarvisPrefs(), validate_partial({"voice": "george", "answered": ["voice"]}))
    d = prefs_to_dict(p)
    assert d["answered"] == ["voice"]
    assert prefs_from_dict(d) == p
    # junk from a remote profile is dropped, not fatal
    q = prefs_from_dict({"voice": "nope", "wake_word": "hey_jarvis", "address": 5})
    assert q.voice == "daniel" and q.wake_word == "hey_jarvis" and q.address == "you"
    assert prefs_from_dict(None) == JarvisPrefs()


# ── state machine ────────────────────────────────────────────────────────────


def test_state_machine_emits_and_tolerates_unexpected():
    events: list[Event] = []
    sm = StateMachine(events.append)
    assert sm.set(State.LISTENING)
    assert not sm.set(State.LISTENING)  # no duplicate event
    sm.set(State.THINKING)
    sm.set(State.SPEAKING)
    sm.set(State.LISTENING, follow_up=True)
    sm.set(State.IDLE)
    assert [e.data["state"] for e in events] == ["listening", "thinking", "speaking", "listening", "idle"]
    assert events[3].data["follow_up"] is True
    assert sm.unexpected == []
    sm.set(State.SPEAKING)
    sm.set(State.TRANSCRIBING)  # unexpected, but applied
    assert sm.state == State.TRANSCRIBING and sm.unexpected == [(State.SPEAKING, State.TRANSCRIBING)]


# ── timing ───────────────────────────────────────────────────────────────────


def test_turn_timing_fields():
    t = TurnTiming(turn=7, channel="voice", t0=100.0)
    t.mark("ack", 100.2)
    t.mark("mind_start", 101.0)
    t.mark("llm_first", 102.5)
    t.mark("llm_first", 109.0)  # first call wins
    t.mark("tts_first", 102.9)
    t.mark("end", 105.0)
    t.speech_ms, t.stt_ms = 1500, 210
    r = t.result()
    assert r["wake_ack_ms"] == 200 and r["llm_first_ms"] == 1500 and r["tts_first_ms"] == 400
    assert r["total_ms"] == 2900 and r["turn_ms"] == 5000 and r["stt_ms"] == 210


def test_summarize_median_p90():
    recs = [{"total_ms": v} for v in range(1, 21)] + [{"total_ms": None}]
    s = summarize(recs)["total_ms"]
    assert s["n"] == 20 and s["median"] == 10.5 and s["p90"] == 18
    assert percentile([5.0], 90) == 5.0
