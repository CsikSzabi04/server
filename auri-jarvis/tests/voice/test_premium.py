"""ElevenLabs premium layer with a MOCKED service (no network, no credits spent)."""
import asyncio
import json

import numpy as np
import pytest

httpx = pytest.importorskip("httpx")
pytest.importorskip("auri_jarvis.contracts")

from auri_jarvis.audio._paths import ROOT  # noqa: E402
from auri_jarvis.tts.mouth import AuriMouth  # noqa: E402

PIPER_OK = (ROOT / "models/piper/hu_HU-imre-medium.onnx").is_file()


def fake_service(calls: list, *, status: int = 200, cost: int = 10, seconds: float = 0.4):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if status != 200:
            return httpx.Response(status, text='{"detail": "quota_exceeded"}')
        t = np.arange(int(22_050 * seconds)) / 22_050
        pcm = (np.sin(2 * np.pi * 220 * t) * 8000).astype("<i2").tobytes()
        return httpx.Response(200, headers={"character-cost": str(cost)}, content=pcm)

    return httpx.Client(transport=httpx.MockTransport(handler))


def make_mouth(tmp_path, calls, *, mode="premium", budget=8000, **svc):
    events, played = [], []
    cfg = {"tts": {"duck_music": False, "mode": mode, "default_voice": "daniel",
                   "elevenlabs": {"monthly_credit_budget": budget}},
           "env": {"ELEVENLABS_API_KEY": "test-key-not-real"}}
    m = AuriMouth(cfg, events.append, output=played.append, el_client=fake_service(calls, **svc), data_dir=tmp_path)
    return m, events, played


async def stream(*parts):
    for p in parts:
        yield p


def test_premium_streams_sentences_and_books_credits(tmp_path):
    calls: list = []
    m, events, played = make_mouth(tmp_path, calls)
    asyncio.run(m.say_stream(stream("Szia, Auri vagyok. ", "Miben segíthetek?")))
    assert len(calls) == 2 and m.last_engine == "elevenlabs"
    req = calls[0]
    assert req.headers["xi-api-key"] == "test-key-not-real"
    assert req.url.params["output_format"] == "pcm_22050"
    assert "onwK4e9ZLuTAKqWW03F9" in req.url.path  # Daniel
    body = json.loads(req.content)
    assert body["text"] == "Szia, Auri vagyok." and body["language_code"] == "hu"
    assert sum(len(b) for b in played) / 22_050 > 0.7
    assert json.loads((tmp_path / "credits.json").read_text())["used"] == 20
    assert any(e.type == "tts.credits" and e.data["used_month"] == 20 for e in events)


def test_same_sentence_is_not_paid_twice(tmp_path):
    calls: list = []
    m, _, _ = make_mouth(tmp_path, calls)
    asyncio.run(m.say("Kész vagyok."))
    asyncio.run(m.say("Kész vagyok."))
    assert len(calls) == 1 and m.last_engine == "elevenlabs(cache)"


def test_signature_phrases_persist_on_disk_across_restarts(tmp_path):
    calls: list = []
    m, _, _ = make_mouth(tmp_path, calls, mode="hybrid")
    asyncio.run(m.say("Üdv itthon.", signature=True))
    assert len(calls) == 1 and list((tmp_path / "tts_cache").glob("*.npz"))
    m2, _, played = make_mouth(tmp_path, calls, mode="hybrid")  # fresh process, empty memory
    asyncio.run(m2.say("Üdv itthon.", signature=True))
    assert len(calls) == 1 and played  # served from disk — 0 credits


@pytest.mark.skipif(not PIPER_OK, reason="Piper voice not downloaded")
def test_hybrid_speaks_live_replies_locally(tmp_path):
    calls: list = []
    m, _, played = make_mouth(tmp_path, calls, mode="hybrid")
    asyncio.run(m.say_stream(stream("Ez egy élő válasz.")))
    assert calls == [] and m.last_engine == "piper" and played


@pytest.mark.skipif(not PIPER_OK, reason="Piper voice not downloaded")
def test_service_error_falls_back_to_piper_and_stops_retrying(tmp_path):
    calls: list = []
    m, events, played = make_mouth(tmp_path, calls, status=429)
    asyncio.run(m.say_stream(stream("Első mondat. ", "Második mondat.")))
    assert len(calls) == 1  # failed once → circuit open → the 2nd sentence did not retry
    assert m.last_engine == "piper" and sum(len(b) for b in played) > 22_050  # still spoke both
    assert any(e.type == "error" and e.data["where"] == "tts.elevenlabs" for e in events)


@pytest.mark.skipif(not PIPER_OK, reason="Piper voice not downloaded")
def test_monthly_budget_switches_to_piper(tmp_path):
    calls: list = []
    m, _, _ = make_mouth(tmp_path, calls, budget=12, cost=10)
    asyncio.run(m.say("Szia."))  # estimate 3 ≤ 12 → premium, books 10
    asyncio.run(m.say("Ez már túl sok lenne a keretből."))  # estimate 16 > 12 - 10 → local
    assert len(calls) == 1 and m.last_engine == "piper"


def test_local_mode_or_missing_key_never_calls_the_service(tmp_path):
    calls: list = []
    m, _, _ = make_mouth(tmp_path, calls, mode="local")
    assert m._el is None
    cfg = {"tts": {"duck_music": False}, "env": {}}
    assert AuriMouth(cfg, None, output=lambda b: None, data_dir=tmp_path)._el is None
