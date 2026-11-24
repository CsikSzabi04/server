"""Fast-path + Hungarian text helpers (M2). Pure, no Ollama, no side effects."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import pytest

from auri_jarvis.mind import hu_text as H
from auri_jarvis.mind.fastpath import Intent, match
from auri_jarvis.tools.apps import AppCatalog

APPS = AppCatalog.load(Path(__file__).resolve().parents[2] / "config" / "apps.yaml")


@pytest.mark.parametrize(
    ("token", "value"),
    [
        ("25", 25), ("25-re", 25), ("30%", 30), ("huszonöt", 25), ("huszonötre", 25),
        ("Huszöt", 25),  # Parakeet misspelling (AI-1 note) — must not become 20
        ("harmincra", 30), ("ötvenet", 50), ("húszat", 20), ("harminckét", 32), ("tizenkettő", 12),
        ("két", 2), ("hat", 6), ("hét", 7), ("öt", 5), ("száz", 100),
        ("hát", None), ("het", None), ("valami", None),
    ],
)  # fmt: skip
def test_parse_number(token, value):
    assert H.parse_number(token) == value


@pytest.mark.parametrize(
    ("text", "secs"),
    [
        ("25 perc", 1500), ("huszonöt percre", 1500), ("Huszöt percre", 1500), ("fél óra", 1800),
        ("másfél óra", 5400), ("negyed óra múlva", 900), ("egy óra tíz perc", 4200), ("90 másodperc", 90),
        ("hét perc", 420), ("szólj, ha kész", None), ("hát perc", None),
    ],
)  # fmt: skip
def test_parse_duration(text, secs):
    assert H.parse_duration(text) == secs


def test_extract_monitor_and_name_candidates():
    assert H.extract_monitor("nyisd meg a VS Code-ot a középső monitoron") == (2, "nyisd meg a vs code-ot")
    assert H.extract_monitor("tedd a chrome-ot a kettesen")[0] == 2
    assert H.extract_monitor("a bal oldali képernyőre")[0] == 1
    assert H.extract_monitor("semmi")[0] is None
    assert H.name_candidates("a VS Code-ot") == ["vs code"]
    assert "figma" in H.name_candidates("a figmát")


def test_parse_when():
    now = datetime(2026, 11, 21, 10, 0)
    assert H.parse_when("18:30", now) == datetime(2026, 11, 21, 18, 30)
    assert H.parse_when("9-kor", now) == datetime(2026, 11, 22, 9, 0)  # already past → tomorrow
    assert H.parse_when("holnap 9-kor", now) == datetime(2026, 11, 22, 9, 0)
    assert H.parse_when("este 8-kor", now) == datetime(2026, 11, 21, 20, 0)
    assert H.parse_when("fél óra múlva", now) == datetime(2026, 11, 21, 10, 30)
    assert H.parse_when("2026-11-22 07:15", now) == datetime(2026, 11, 22, 7, 15)
    assert H.parse_when("valamikor", now) is None


@pytest.mark.parametrize(
    ("utterance", "expected"),
    [
        ("Hány óra van?", Intent("get_time")),
        ("Auri, mennyi az idő?", Intent("get_time")),
        ("Hangerő 30", Intent("set_volume", {"level": 30})),
        ("Állítsd a hangerőt harminc százalékra", Intent("set_volume", {"level": 30})),
        ("hangosabban", Intent("set_volume", {"change": "up"})),
        ("halkítsd le egy kicsit", Intent("set_volume", {"change": "down"})),
        ("némítsd", Intent("set_volume", {"change": "mute"})),
        ("Következő szám", Intent("media_control", {"action": "next"})),
        ("szünet", Intent("media_control", {"action": "play_pause"})),
        ("Időzítő 25 perc", Intent("set_timer", {"seconds": 1500})),
        ("huszöt perces időzítő", Intent("set_timer", {"seconds": 1500})),
        ("Szólj tíz perc múlva, hogy vegyem ki a pizzát", Intent("set_timer", {"seconds": 600, "label": "vegyem ki a pizzát"})),
        ("Nyisd meg a VS Code-ot a középső monitoron", Intent("open_app", {"name": "vscode", "monitor": 2})),
        ("nyisd meg a krómot", Intent("open_app", {"name": "chrome"})),
        ("Indítsd el a böngészőt teljes képernyőn", Intent("open_app", {"name": "brave", "fullscreen": True})),
        ("nincs meg a vs code-ot", Intent("open_app", {"name": "vscode"})),  # Parakeet's "nyisd meg"
        ("kérlek nyisd meg a figmát", Intent("open_app", {"name": "figma"})),
        ("Dobd fel a YouTube-ot.", Intent("open_app", {"name": "youtube"})),
        ("tedd a vs code-ot a bal monitorra", Intent("move_window", {"app": "vscode", "monitor": 1})),
        ("Mégse", Intent("cancel")),
    ],
)
def test_fastpath_hits(utterance, expected):
    assert match(utterance, APPS) == expected


@pytest.mark.parametrize(
    "utterance",
    [
        "ki vagy?",  # ⊃ "agy" — the AuriGPT BRAIN substring bug (2026-11-20)
        "de a brain miért nem tud jól válaszolni?",  # ⊃ "rain"
        "Hány óra alatt lehet megtanulni a Pythont?",  # starts like a time request
        "folytasd",  # could mean "keep talking" → ambiguous → LLM
        "szólj, ha kész a build",  # no duration
        "hát",
        "nyisd meg a fájlt amit tegnap szerkesztettem",  # unknown target
        "nincs meg a kulcsom",  # real Hungarian, not a mishearing
        "hangerő mennyi most?",
        "",
    ],
)
def test_fastpath_misses_go_to_the_llm(utterance):
    assert match(utterance, APPS) is None


def test_fastpath_is_fast():
    samples = ["Hány óra van?", "Nyisd meg a VS Code-ot a középső monitoron", "Szólj tíz perc múlva", "ki vagy?"] * 25
    t0 = time.perf_counter()
    for s in samples:
        match(s, APPS)
    per_ms = (time.perf_counter() - t0) / len(samples) * 1000
    assert per_ms < 100  # DoD M2 (measured ~0.05 ms)
