"""AI-2 Mind inside AI-3's REAL orchestrator (Bus + Orchestrator, Fake ears/mouth): the
onboarding round trip login → 4 spoken questions → prefs.proposed → orchestrator applies →
Mind.on_identity_change, and the order the user hears the voice samples. No Ollama, no audio."""

from __future__ import annotations

import asyncio
import io
from pathlib import Path
from typing import Any

from auri_jarvis.bus import Bus
from auri_jarvis.contracts import Event, UserContext
from auri_jarvis.fakes import FakeEars, FakeMouth
from auri_jarvis.mind.core import JarvisMind
from auri_jarvis.mind.ollama_provider import LLMChunk, LLMStats
from auri_jarvis.orchestrator import Orchestrator
from auri_jarvis.tools.apps import AppCatalog
from auri_jarvis.tools.builtin import ToolServices
from auri_jarvis.tools.platform import RecordingPlatform

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
CFG: dict[str, Any] = {
    "guest_defaults": {"address": "you", "wake_word": "hey_auri", "voice": "daniel", "welcome_routine": None},
    "core": {"follow_up_s": 0.3, "listen_start_timeout_s": 0.5, "idle_tick_s": 0, "ack_phrase": "Igen?"},
    "audio": {"full_duplex": False},
}


class NoLLM:
    model = "none"

    async def chat_stream(self, messages, tools=None, opts=None):
        yield LLMChunk(content="(LLM)")
        yield LLMChunk(done=True, stats=LLMStats())

    async def warmup(self, messages, tools=None, model=None):
        return LLMStats()

    async def aclose(self):
        pass


async def _listening(ears: FakeEars, timeout: float = 5.0) -> None:
    async def wait():
        while ears._waiting == 0:  # FakeEars: a listen() is waiting for a line
            await asyncio.sleep(0.01)

    await asyncio.wait_for(wait(), timeout)


async def test_onboarding_round_trip_through_the_real_orchestrator():
    bus = Bus()
    bus.attach()
    events: list[Event] = []
    bus.on("*", events.append)
    ears = FakeEars(read_stream=False)
    mouth = FakeMouth(out=io.StringIO())
    svc = ToolServices(platform=RecordingPlatform(), apps=AppCatalog.load(CONFIG_DIR / "apps.yaml"))
    mind = JarvisMind({"paths": {"config_dir": str(CONFIG_DIR)}}, bus.emit, provider=NoLLM(), services=svc)  # type: ignore[arg-type]
    orch = Orchestrator(CFG, bus, ears, mouth, mind)
    await orch.start(warmup=False)
    try:
        await orch.set_user(UserContext(tier="user", user_id="u-9", display_name="Teszt"), reason="login")
        for answer in ("Szólíts Elemérnek", "Hey Jarvis", "a második", "igen"):
            await _listening(ears)
            ears.feed(answer)
        await asyncio.sleep(0.2)
        await bus.drain()

        said = mouth.said
        assert said[0].startswith("Szia! Négy gyors kérdés") and said[0].endswith("Hogyan szólítsalak?")
        i = next(k for k, s in enumerate(said) if "Most két hangmintát hallasz" in s)
        assert said[i + 1 : i + 4] == [
            "[hangminta: daniel]",
            "[hangminta: george]",
            "Melyik hang tetszett jobban: az első, a második, vagy a helyi, ingyenes hang?",
        ]
        assert mouth.samples == ["daniel", "george"]
        assert said[-1].endswith("Kész, minden be van állítva.")

        p = orch.user.prefs  # applied by the orchestrator from our prefs.proposed
        assert (p.address, p.wake_word, p.voice) == ("Elemér", "hey_jarvis", "george")
        assert p.welcome_routine and p.welcome_routine["apps"]
        assert set(p.answered) == {"address", "wake_word", "voice", "welcome_routine"} and p.onboarded
        assert ears.wake_word == "hey_jarvis" and mouth.voice == "george"  # applied live
        assert not [e for e in events if e.type == "error"]
    finally:
        await orch.stop()
