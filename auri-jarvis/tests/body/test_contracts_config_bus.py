"""M0: contracts import, config loading/merging/secrets, bus threading + throttling."""

from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path

import pytest

from auri_jarvis import config as C
from auri_jarvis.bus import Bus, event_from_dict, event_to_dict
from auri_jarvis.contracts import (
    FRAME_SAMPLES,
    GUEST,
    SAMPLE_RATE,
    Event,
    JarvisPrefs,
    Transcript,
    TurnRequest,
    UserContext,
    WakeEvent,
)

# ── contracts ────────────────────────────────────────────────────────────────


def test_contract_constants_and_guest_defaults():
    assert SAMPLE_RATE == 16_000 and FRAME_SAMPLES == 1_280
    assert GUEST.tier == "guest" and GUEST.user_id is None
    p = GUEST.prefs
    assert (p.address, p.wake_word, p.voice, p.welcome_routine, p.onboarded) == ("you", "hey_auri", "daniel", None, False)


def test_contract_dataclasses_are_frozen():
    with pytest.raises(AttributeError):
        GUEST.prefs.voice = "george"  # type: ignore[misc]
    req = TurnRequest(turn_id=1, user=UserContext(tier="user", user_id="u"), channel="hud_text", text="szia")
    assert req.transcript is None and req.trigger is None
    assert WakeEvent(source="hotkey").t > 0
    Transcript(raw="a", text="a", lang="hu", confidence=1.0, engine="text", speech_ms=0, stt_ms=0)


def test_contract_text_is_verbatim_from_jarvis_build(project_root: Path):
    """contracts.py must match the code block in JARVIS_BUILD.md §2.1 byte for byte."""
    board = (project_root.parent / "JARVIS_BUILD.md").read_text(encoding="utf-8")
    start = board.index('```python\n"""auri_jarvis.contracts')
    block = board[start + len("```python\n") : board.index("```", start + 10)]
    src = (project_root / "auri_jarvis" / "contracts.py").read_text(encoding="utf-8")
    assert src == block


# ── config ───────────────────────────────────────────────────────────────────


def test_load_config_real_repo_files():
    cfg = C.load_config(environ={})
    assert "jarvis.yaml" in cfg["paths"]["loaded"]
    assert C.get(cfg, "hud.host") == "127.0.0.1"
    assert C.get(cfg, "hud.port") == 8790
    assert C.get(cfg, "guest_defaults.wake_word") == "hey_auri"


def test_missing_required_file_is_clear_error(tmp_path: Path):
    (tmp_path / "config").mkdir()
    with pytest.raises(C.ConfigError, match=r"jarvis.yaml"):
        C.load_config(tmp_path, environ={})


def test_optional_files_missing_is_ok(tmp_config: Path):
    cfg = C.load_config(tmp_config, environ={})
    assert set(cfg["paths"]["missing"]) == {"audio.yaml", "mind.yaml"}


def test_bad_yaml_reports_file_and_line(tmp_config: Path):
    (tmp_config / "config" / "audio.yaml").write_text("audio:\n  a: [1, 2\n", encoding="utf-8")
    with pytest.raises(C.ConfigError, match=r"audio\.yaml.*sor"):
        C.load_config(tmp_config, environ={})


def test_merge_substitution_and_secret_masking(tmp_config: Path):
    (tmp_config / "config" / "audio.yaml").write_text(
        "audio:\n  input_device: ${JARVIS_INPUT_DEVICE:-auto}\ntts:\n  key: ${ELEVENLABS_API_KEY}\n", encoding="utf-8"
    )
    (tmp_config / "config" / "mind.yaml").write_text("llm:\n  model: qwen3.5:4b\n", encoding="utf-8")
    (tmp_config / ".env").write_text("ELEVENLABS_API_KEY=sk_test_secret_123456\nSUPABASE_URL=https://x.supabase.co\n")
    cfg = C.load_config(tmp_config, environ={})
    assert cfg["audio"]["input_device"] == "auto"
    assert cfg["llm"]["model"] == "qwen3.5:4b"
    assert cfg["identity"]["supabase_url"] == "https://x.supabase.co"
    key = cfg["env"]["ELEVENLABS_API_KEY"]
    assert isinstance(key, C.Secret) and str(key) == "sk_test_secret_123456"
    assert f"Bearer {key}" == "Bearer sk_test_secret_123456"  # usable as a real value
    assert "sk_test_secret" not in repr(cfg)  # …but never leaks via repr
    assert isinstance(cfg["tts"]["key"], C.Secret)  # substituted secret stays masked
    assert C.describe(cfg)["env"]["ELEVENLABS_API_KEY"] == "***"


def test_process_env_overrides_dotenv(tmp_config: Path):
    (tmp_config / ".env").write_text("JARVIS_INPUT_DEVICE=3\n")
    cfg = C.load_config(tmp_config, environ={"JARVIS_INPUT_DEVICE": "DGM20", "UNRELATED": "x"})
    assert cfg["env"]["JARVIS_INPUT_DEVICE"] == "DGM20"
    assert "UNRELATED" not in cfg["env"]


def test_reserved_key_rejected(tmp_config: Path):
    (tmp_config / "config" / "mind.yaml").write_text("env:\n  x: 1\n")
    with pytest.raises(C.ConfigError, match="foglalt"):
        C.load_config(tmp_config, environ={})


def test_log_redaction(caplog: pytest.LogCaptureFixture):
    C.register_secret("supersecretvalue42")
    handler = logging.StreamHandler()
    logger = logging.getLogger("redact-test")
    logger.addHandler(handler)
    C.install_log_redaction(logger)
    try:
        rec = logging.LogRecord("redact-test", logging.INFO, __file__, 1, "key=%s", ("supersecretvalue42",), None)
        for f in handler.filters:
            f.filter(rec)
        assert "supersecretvalue42" not in rec.getMessage() and "***" in rec.getMessage()
    finally:
        logger.removeHandler(handler)


# ── bus ──────────────────────────────────────────────────────────────────────


async def test_bus_dispatch_from_threads_in_order():
    bus = Bus()
    bus.attach()
    got: list[int] = []
    bus.on("x", lambda ev: got.append(ev.data["i"]))
    q = bus.subscribe_queue()

    def worker():
        for i in range(50):
            bus.emit(Event("x", {"i": i}))

    th = threading.Thread(target=worker)
    th.start()
    th.join()
    await bus.drain()
    assert got == list(range(50))
    assert q.qsize() == 50


async def test_bus_pending_before_attach_and_async_handlers():
    bus = Bus()
    bus.emit(Event("early", {"n": 1}))
    seen: list[str] = []

    async def ah(ev: Event) -> None:
        await asyncio.sleep(0)
        seen.append(ev.type)

    bus.on("*", ah)
    bus.attach()
    await bus.drain()
    assert seen == ["early"]


async def test_bus_level_throttle_and_sticky():
    bus = Bus(level_hz=15)
    bus.attach()
    q = bus.subscribe_queue()
    for i in range(100):
        bus.emit(Event("level", {"source": "mic", "rms": 0.1 + i * 0.05}))
    bus.emit(Event("state", {"state": "idle"}))
    bus.emit(Event("state", {"state": "listening"}))
    await bus.drain()
    levels = [e for e in list(q._queue) if e.type == "level"]
    assert 1 <= len(levels) <= 3 and bus.dropped_levels >= 97
    assert bus.last("state").data["state"] == "listening"
    assert [e.type for e in bus.snapshot()] == ["state"]


async def test_bus_handler_exception_does_not_break_others():
    bus = Bus()
    bus.attach()
    ok: list[bool] = []
    bus.on("e", lambda ev: 1 / 0)
    bus.on("e", lambda ev: ok.append(True))
    bus.emit(Event("e"))
    await bus.drain()
    assert ok == [True]


async def test_bus_slow_queue_drops_oldest():
    bus = Bus()
    bus.attach()
    q = bus.subscribe_queue(maxsize=3)
    for i in range(10):
        bus.emit(Event("n", {"i": i}))
    await bus.drain()
    assert [e.data["i"] for e in list(q._queue)] == [7, 8, 9]


def test_event_json_roundtrip():
    ev = Event("identity", {"prefs": JarvisPrefs(), "tup": (1, 2)})
    d = event_to_dict(ev)
    assert d["data"]["prefs"]["wake_word"] == "hey_auri" and d["data"]["tup"] == [1, 2]
    back = event_from_dict({"type": "command", "data": {"text": "hi"}})
    assert back.type == "command" and back.data == {"text": "hi"}
    for bad in (None, [], {"type": ""}, {"type": "x", "data": []}, {"type": "x" * 100}):
        with pytest.raises(ValueError):
            event_from_dict(bad)
