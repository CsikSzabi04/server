"""End-to-end VOICE pipeline on fixtures (no microphone, no speakers):
  Ears.listen(): frames → Silero endpointing → Parakeet → lexicon → contracts.Transcript
  Mouth.say_stream(): LLM-like deltas → sentences → Piper → player (test output hook)
Skipped automatically if the shared contract or the models are not available yet.
"""
import asyncio
import wave
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures" / "audio"
PIPER_HU = ROOT / "models" / "piper" / "hu_HU-imre-medium.onnx"


def _read(name: str) -> np.ndarray:
    with wave.open(str(FIX / name), "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def _listen_to(ears, cap, fixture: str, **kw):
    async def run():
        task = asyncio.create_task(ears.listen(max_s=10, start_timeout_s=3, **kw))
        await asyncio.sleep(0.3)  # listen() is subscribed now
        audio = _read(fixture)
        for i in range(0, len(audio), 1280):
            cap.push(audio[i:i + 1280])
        return await task

    return asyncio.run(run())


def test_ears_listen_transcribes_a_hungarian_command():
    """Real Silero + real Parakeet. (The fixture voice is synthetic Piper "imre": it
    pronounces "nyisd meg" / "Chrome-ot" so badly that even Whisper hears "nincs meg a
    C-Romeot" — so accuracy is benchmarked with the user's own voice in bench_stt.py,
    and this test uses the clearly pronounced timer sentence.)"""
    pytest.importorskip("auri_jarvis.contracts")
    pytest.importorskip("onnx_asr")
    from auri_jarvis.audio.capture import AudioCapture
    from auri_jarvis.audio.ears import AuriEars

    cap = AudioCapture(device=None)
    cap.start_worker_only()
    ears = AuriEars({"stt": {"lexicon": "config/lexicon.yaml"}}, lambda ev: None, capture=cap)
    ears._fast.load()  # model load is not part of the per-command latency
    tr = _listen_to(ears, cap, "hu_two_parts_pause_16k.wav")
    cap.stop()
    assert tr is not None
    assert tr.engine == "parakeet" and tr.lang == "hu"
    # Parakeet writes the number either as digits ("25 percre") or as a word ("huszonöt" —
    # sometimes misspelled "Huszöt"): the Mind's number parser must accept both.
    assert "időzítő" in tr.text.lower(), tr
    assert "25 perc" in tr.text or "husz" in tr.text.lower(), tr
    assert 2000 <= tr.speech_ms <= 4000  # one utterance despite the mid-sentence pause
    assert tr.stt_ms < 1500, tr.stt_ms


def test_ears_applies_the_lexicon_to_engine_output():
    pytest.importorskip("auri_jarvis.contracts")
    from auri_jarvis.audio.capture import AudioCapture
    from auri_jarvis.audio.ears import AuriEars

    class FakeEngine:  # deterministic stand-in returning a measured Parakeet mishearing
        name = "parakeet"

        def transcribe(self, pcm):
            return "Hei Hauri, nycs meg a vízkódot", "hu"

    cap = AudioCapture(device=None)
    cap.start_worker_only()
    ears = AuriEars({"stt": {"lexicon": "config/lexicon.yaml"}}, lambda ev: None, capture=cap)
    ears._fast = FakeEngine()
    tr = _listen_to(ears, cap, "hu_open_chrome_16k.wav")
    cap.stop()
    assert tr.raw == "Hei Hauri, nycs meg a vízkódot"
    # lexicon: "Hei Hauri" → "Hey Auri", "nycs meg" → "nyisd meg", "vízkódot" → "VS Code-ot";
    # then the wake phrase is stripped so the Mind only sees the command
    assert tr.text == "Nyisd meg a VS Code-ot"


def test_command_spoken_right_after_the_wake_word_is_not_lost():
    """'Hey Auri, hány óra van' in one breath: the command started BEFORE listen() was called
    (Auri was still acknowledging). listen() must recover it from the ring buffer."""
    pytest.importorskip("auri_jarvis.contracts")
    import time

    from auri_jarvis.audio.capture import AudioCapture
    from auri_jarvis.audio.ears import AuriEars

    heard = {}

    class FakeEngine:
        name = "parakeet"

        def transcribe(self, pcm):
            heard["seconds"] = len(pcm) / 16_000
            return "Hey Auri, igen? Hány óra van?", "hu"  # incl. our own ack via the speakers

    cap = AudioCapture(device=None)
    cap.start_worker_only()
    ears = AuriEars({"wake": {"command_history_s": 6}}, lambda ev: None, capture=cap)
    ears._fast = FakeEngine()
    audio = _read("hu_two_parts_pause_16k.wav")
    cap.push(audio)  # the whole utterance happened already …
    time.sleep(0.3)
    ears._last_wake_word_t = time.monotonic() - len(audio) / 16_000  # … right after the wake word
    tr = asyncio.run(ears.listen(start_timeout_s=1.0))
    cap.stop()
    assert tr is not None, "the command spoken before listen() was lost"
    assert tr.text == "Hány óra van?"  # wake phrase stripped
    assert heard["seconds"] > 2.0  # the full command, not just its tail


def test_ears_listen_returns_none_when_nobody_speaks():
    pytest.importorskip("auri_jarvis.contracts")
    from auri_jarvis.audio.capture import AudioCapture
    from auri_jarvis.audio.ears import AuriEars

    cap = AudioCapture(device=None)
    cap.start_worker_only()
    ears = AuriEars({}, lambda ev: None, capture=cap)

    async def run():
        task = asyncio.create_task(ears.listen(start_timeout_s=0.8))
        await asyncio.sleep(0.2)
        cap.push(np.random.default_rng(0).normal(0, 0.003, 16_000).astype(np.float32))  # room noise
        return await task

    assert asyncio.run(run()) is None
    cap.stop()


@pytest.mark.skipif(not PIPER_HU.is_file(), reason="Piper voice not downloaded")
def test_mouth_streams_sentences_fast_and_stops_on_barge_in():
    pytest.importorskip("piper")
    from auri_jarvis.tts.mouth import AuriMouth

    played: list[np.ndarray] = []
    mouth = AuriMouth({"tts": {"duck_music": False}}, None, output=played.append)
    mouth.start()
    assert mouth.wait_ready(60)

    async def deltas():
        for d in ["Má", "ris, uram. Megnyitom ", "a Chrome-ot a középső ", "monitoron. Kész."]:
            yield d
            await asyncio.sleep(0.01)

    # the ack is pre-rendered during warm-up → plays (almost) instantly
    asyncio.run(mouth.say("Igen?", signature=True))
    # (< 80 ms even under heavy CPU load; a fresh synthesis takes ~170 ms)
    assert mouth.last_first_audio_ms is not None and mouth.last_first_audio_ms < 80, mouth.last_first_audio_ms
    played.clear()

    asyncio.run(mouth.say_stream(deltas()))
    seconds = sum(len(b) for b in played) / 22_050
    assert seconds > 3.0, seconds  # three sentences were spoken
    assert mouth.last_first_audio_ms is not None and mouth.last_first_audio_ms < 300, mouth.last_first_audio_ms

    # barge-in: stop() while the reply is still streaming → the rest is never synthesised
    played.clear()

    async def long_reply():
        yield "Első mondat. "
        yield "Második mondat. "
        await asyncio.sleep(0.4)  # first sentence(s) already spoken by now
        mouth.stop()
        for i in range(10):
            yield f"Ez a(z) {i + 3}. mondat, amit már nem szabad kimondani. "

    asyncio.run(mouth.say_stream(long_reply()))
    assert 0 < sum(len(b) for b in played) / 22_050 < 3.0
