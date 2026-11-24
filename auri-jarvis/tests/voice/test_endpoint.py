"""Endpointing state machine (pure) + Silero VAD on real speech fixtures."""
import wave
from pathlib import Path

import numpy as np
import pytest

from auri_jarvis.audio.vad import CHUNK, CHUNK_MS, EndpointConfig, EndpointLogic

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "audio"


def run_logic(probs: list[float], cfg: EndpointConfig | None = None, max_ms: int = 15_000):
    logic = EndpointLogic(cfg or EndpointConfig(), max_ms=max_ms)
    for i, p in enumerate(probs):
        done = logic.feed(np.full(CHUNK, float(i), np.float32), p)
        if done is not None:
            return done, i
    return None, len(probs)


def ms(n: int) -> int:
    return n // CHUNK_MS


def test_short_blip_does_not_start_an_utterance():
    done, _ = run_logic([0.0] * 20 + [0.9] * ms(150) + [0.0] * 60)
    assert done is None


def test_utterance_ends_after_700ms_silence_and_keeps_preroll():
    probs = [0.0] * 30 + [0.9] * ms(1000) + [0.0] * ms(900)
    done, at = run_logic(probs)
    assert done is not None and done.reason == "silence"
    end_chunk = 30 + ms(1000) + ms(700)  # silence counter reaches 700 ms here
    assert abs(at - end_chunk) <= 1
    first_sample = done.pcm[0]  # chunks are filled with their own index → preroll start is visible
    assert first_sample < 30  # preroll from before the speech start is included


def test_brief_pause_inside_a_sentence_does_not_end_it():
    probs = [0.0] * 10 + [0.9] * ms(600) + [0.1] * ms(400) + [0.9] * ms(600) + [0.0] * ms(800)
    done, _ = run_logic(probs)
    assert done is not None and done.speech_ms >= 1500


def test_max_length_cuts_endless_speech():
    done, _ = run_logic([0.9] * ms(3000), max_ms=2000)
    assert done is not None and done.reason == "max_len"


def _read(name: str) -> np.ndarray:
    with wave.open(str(FIX / name), "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def test_silero_endpoints_real_speech_fixtures():
    pytest.importorskip("pysilero_vad")
    import threading

    from auri_jarvis.audio.capture import AudioCapture
    from auri_jarvis.audio.vad import Endpointer

    for name, (lo, hi) in {"hu_open_chrome_16k.wav": (1500, 3500),
                           "hu_two_parts_pause_16k.wav": (2500, 4800)}.items():
        cap = AudioCapture(device=None)
        cap.start_worker_only()
        ep = Endpointer(EndpointConfig())
        result: dict = {}
        t = threading.Thread(target=lambda ep=ep, cap=cap, result=result: result.update(
            u=ep.capture(cap.subscribe, max_s=15, start_timeout_s=3, cancel=threading.Event())))
        t.start()
        audio = _read(name)
        for i in range(0, len(audio), 1280):
            cap.push(audio[i:i + 1280])
        t.join(timeout=10)
        cap.stop()
        u = result.get("u")
        assert u is not None, name
        assert u.reason == "silence", name
        assert lo <= u.speech_ms <= hi, (name, u.speech_ms)  # one utterance, pause not split
