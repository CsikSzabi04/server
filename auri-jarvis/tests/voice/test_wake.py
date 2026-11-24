"""Clap detector 2.0, "Hey Auri" transcript matching, wake-phrase stripping, WakeHub logic."""
import wave
from pathlib import Path

import numpy as np
import pytest

from auri_jarvis.audio.clap import ClapDetector
from auri_jarvis.wake.engines import matches_hey_auri
from auri_jarvis.wake.hub import WakeHub, strip_wake_phrase

SR = 16_000
FIX = Path(__file__).resolve().parents[1] / "fixtures" / "audio"
rng = np.random.default_rng(42)


def room(sec: float, level: float = 0.002) -> np.ndarray:
    return rng.normal(0, level, int(SR * sec)).astype(np.float32)


def burst(kind: str = "clap", amp: float = 0.5, tau_ms: float = 12, dur_ms: int = 120) -> np.ndarray:
    t = np.arange(int(SR * dur_ms / 1000)) / SR
    env = np.exp(-t / (tau_ms / 1000))
    env[:32] *= np.linspace(0, 1, 32)  # 2 ms attack
    src = rng.normal(0, 1, len(t)) if kind in ("clap", "door") else np.sin(2 * np.pi * 80 * t)
    x = env * src
    return (amp * x / np.max(np.abs(x))).astype(np.float32)


def events(audio: np.ndarray) -> list[str]:
    det, out = ClapDetector(), []
    for i in range(0, len(audio), 1280):
        ev = det.feed(audio[i:i + 1280])
        if ev:
            out.append(ev)
    return out


def claps(gaps_ms: list[int], **kw) -> np.ndarray:
    parts = [room(1.0), burst(**kw)]
    for g in gaps_ms:
        parts += [room(g / 1000 - 0.12), burst(**kw)]
    return np.concatenate([*parts, room(1.2)])


# ── claps ──────────────────────────────────────────────────────────────────
def test_double_and_triple_clap():
    assert events(claps([300])) == ["clap2"]
    assert events(claps([250, 250])) == ["clap3"]


def test_quiet_far_clap_still_counts():
    assert events(claps([350], amp=0.08)) == ["clap2"]


def test_not_a_double_clap():
    assert events(claps([])) == []  # single clap
    assert events(claps([1000])) == []  # too slow → two singles
    echo = np.concatenate([room(1), burst(dur_ms=60), burst(dur_ms=60), room(1.2)])  # 60 ms apart < gap_min
    assert events(echo) == []


def test_thumps_and_doors_are_rejected():
    assert events(claps([300], kind="thump", tau_ms=40)) == []  # desk knock: low frequency
    assert events(claps([300], kind="door", tau_ms=150, dur_ms=400)) == []  # slow decay


def _read(name: str) -> np.ndarray:
    with wave.open(str(FIX / name), "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def test_speech_is_not_a_clap():
    for name in ("hu_open_chrome_16k.wav", "hu_two_parts_pause_16k.wav"):
        assert events(_read(name)) == [], name


# ── "Hey Auri" in a transcript (STT-wake) ──────────────────────────────────
@pytest.mark.parametrize("text", [
    "Hey Auri.", "Hei Hauri.", "Hé, Auri!", "Auri kapcsolt be a zenét.", "Helyeüri, hány óra van?",
    "hey owry what time is it", "Hej Orri, nyisd meg",
    # measured Parakeet outputs for "Hey Auri" spoken by Hungarian voices
    "Hey Audi.", "Hey Oli.", "Hei ja Uri!", "Helyeúri, hány óra van?", "Helye, óri, nyisd meg a böngészőt.",
    "Hey Juri, Nis meg a Böngi.", "Eh auri.", "Hei, oli hän uudervan.", "Hey Aori.", "Aurik kapcsolt be a zenét.",
])
def test_matches_hey_auri(text):
    assert matches_hey_auri(text)


@pytest.mark.parametrize("text", [
    "Hely, nyisd megad Ramaut!",  # measured miss: the name is gone — must NOT match
    "Laura, gyere ide.", "Az aurora szép.", "Hey Siri", "Hé, Ottó!", "hány óra van", "",
    "Hey, how are you doing?", "Hey Jervis, nice to meet you.", "Hej, de jó ez a zene!",
    "Óra van a falon.", "Úri módon viselkedett.", "Audi A4-et vett.", "Oli ma nem jön.", "Hely van még?",
])
def test_does_not_match_other_speech(text):
    assert not matches_hey_auri(text)


# ── stripping the wake phrase from the command ────────────────────────────
def test_strip_wake_phrase():
    assert strip_wake_phrase("Hey Auri, hány óra van?") == "Hány óra van?"
    assert strip_wake_phrase("Auri, nyisd meg a Chrome-ot.") == "Nyisd meg a Chrome-ot."
    assert strip_wake_phrase("Hey Jarvis what's the time") == "What's the time"
    assert strip_wake_phrase("Hey Auri") == ""
    for keep in ["Hány óra van?", "Hey, mi újság?", "Laura, gyere ide."]:
        assert strip_wake_phrase(keep) == keep


# ── WakeHub: suppression + refractory, with a fake engine ─────────────────
class FakeEngine:
    def __init__(self, fire_on: set[int]):
        self.n, self.fire_on = 0, fire_on

    def feed(self, frame):
        self.n += 1
        return 0.9 if self.n in self.fire_on else None

    def reset(self):
        pass


def run_hub(fire_on: set[int], suppressed_frames: set[int] = frozenset(), frames: int = 60):
    import time

    got = []
    hub = WakeHub({"clap": {"enabled": False}, "refractory_s": 1.0}, lambda s, w, c: got.append((s, w)))
    hub._engine, hub._engine_word = FakeEngine(fire_on), "hey_auri"
    hub.start()
    for i in range(1, frames + 1):
        while not hub._q.empty():
            time.sleep(0.001)
        hub.suppressed = i in suppressed_frames
        hub.feed(np.zeros(1280, np.float32))
    while not hub._q.empty():
        time.sleep(0.005)
    time.sleep(0.05)
    hub.stop()
    return got


def test_hub_fires_once_per_utterance_and_respects_suppression():
    assert run_hub({5, 6, 7}) == [("wakeword", "hey_auri")]  # refractory swallows the repeats
    assert run_hub({5}, suppressed_frames={5}) == []  # Auri was speaking / mic muted
