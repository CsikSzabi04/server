"""JarvisMind (M1) against a fake provider — no Ollama needed."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import pytest

from auri_jarvis.contracts import GUEST, Event, JarvisPrefs, TurnRequest, UserContext
from auri_jarvis.mind import create_mind
from auri_jarvis.mind import prompts as P
from auri_jarvis.mind.core import JarvisMind, hu_now
from auri_jarvis.mind.ollama_provider import LLMChunk, LLMError, LLMStats
from auri_jarvis.tools.apps import AppCatalog
from auri_jarvis.tools.builtin import ToolServices
from auri_jarvis.tools.platform import RecordingPlatform

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
K = 1 + len(P.SEED)  # system + the fixed seed demo: session turns start at index K

ALEX = UserContext(
    tier="user",
    user_id="u-1",
    display_name="Teszt",
    prefs=JarvisPrefs(address="Teszt", onboarded=True),
    profile={"name": "Teszt Elek", "about": "Fejlesztő."},
)
BOB = UserContext(
    tier="user",
    user_id="u-2",
    prefs=JarvisPrefs(address="you"),
    profile={"name": "Bob"},
)


class FakeProvider:
    model = "fake:1b"

    def __init__(self, reply: str = "Szia! Itt vagyok.", error: LLMError | None = None) -> None:
        self.reply = reply
        self.error = error
        self.calls: list[list[dict]] = []
        self.warmups: list[list[dict]] = []

    async def chat_stream(self, messages, tools=None, opts=None):
        self.calls.append(messages)
        if self.error:
            raise self.error
        words = self.reply.split(" ")
        for i, w in enumerate(words):
            yield LLMChunk(content=w if i == 0 else " " + w)
            await asyncio.sleep(0)
        yield LLMChunk(
            done=True,
            stats=LLMStats(model=self.model, first_token_ms=12, eval_tokens=len(words)),
        )

    async def warmup(self, messages, tools=None, model=None):
        self.warmups.append(messages)
        return LLMStats(model=self.model)

    async def aclose(self):
        pass


class Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def make(provider: FakeProvider | None = None, clock: Clock | None = None):
    events: list[Event] = []
    prov = provider or FakeProvider()
    mind = JarvisMind(
        {
            "llm": {"max_session_turns": 3, "carry_turns": 1, "session_idle_s": 300},
            "paths": {"config_dir": str(CONFIG_DIR)},
        },
        events.append,
        provider=prov,  # type: ignore[arg-type]
        services=ToolServices(platform=RecordingPlatform(), apps=AppCatalog.load(CONFIG_DIR / "apps.yaml")),
        clock=clock or Clock(datetime(2026, 11, 20, 22, 15)),
    )
    return mind, prov, events


def req(text: str, user: UserContext = GUEST, channel: str = "voice", turn: int = 1, **kw) -> TurnRequest:
    return TurnRequest(turn_id=turn, user=user, channel=channel, text=text, **kw)  # type: ignore[arg-type]


async def run(mind: JarvisMind, r: TurnRequest, events: list[Event]) -> str:
    return "".join([d async for d in mind.handle(r, events.append)])


@pytest.mark.asyncio
async def test_streams_and_emits_route_delta_done_in_order():
    mind, _prov, ev = make()
    out = await run(mind, req("szia"), ev)
    assert out == "Szia! Itt vagyok."
    types = [e.type for e in ev]
    assert types[0] == "route" and ev[0].data["path"] == "llm"
    assert types[-1] == "reply.done" and set(types[1:-1]) == {"reply.delta"}
    done = ev[-1].data
    assert done["text"] == out and done["model"] == "fake:1b" and done["llm_first_ms"] == 12


@pytest.mark.asyncio
async def test_time_goes_into_user_tail_not_system():
    mind, prov, ev = make()
    await run(mind, req("mit csináljak ma este?"), ev)  # (not a fast-path command)
    msgs = prov.calls[0]
    assert "2026-11-20 22:15, péntek" in msgs[-1]["content"]
    assert "2026" not in msgs[0]["content"]
    assert msgs[-1]["content"].endswith("<kérés>mit csináljak ma este?</kérés>")


@pytest.mark.asyncio
async def test_system_prefix_identical_across_turns():
    mind, prov, ev = make()
    await run(mind, req("egy", user=ALEX), ev)
    await run(mind, req("kettő", user=ALEX, turn=2), ev)
    assert prov.calls[0][0]["content"].encode() == prov.calls[1][0]["content"].encode()


@pytest.mark.asyncio
async def test_guest_prefix_has_no_profile_user_prefix_has_it():
    mind, prov, ev = make()
    await run(mind, req("szia"), ev)
    await run(mind, req("szia", user=ALEX, turn=2), ev)
    guest_sys, user_sys = prov.calls[0][0]["content"], prov.calls[1][0]["content"]
    assert "Teszt Elek" not in guest_sys and "Vendéggel beszélsz" in guest_sys
    assert "Teszt Elek" in user_sys and "„Teszt”" in user_sys


@pytest.mark.asyncio
async def test_identity_change_rebuilds_prefix_and_rewarms():
    mind, prov, _ev = make()
    await mind.on_identity_change(ALEX)
    await asyncio.sleep(0.01)
    assert prov.warmups and "Teszt Elek" in prov.warmups[-1][0]["content"]
    assert prov.warmups[-2][-1] == {"role": "user", "content": P.SEED_REQUEST}


@pytest.mark.asyncio
async def test_turn_extends_the_warmed_prefix():
    mind, prov, ev = make()
    await mind.warmup()
    await run(mind, req("szia"), ev)
    seed, probe = prov.warmups[-2:]  # warm_sequence: seed request, then a throwaway probe turn
    assert prov.calls[-1][: len(seed)] == seed
    assert prov.calls[-1][:K] == probe[:K]  # shares system + seed exchange with the probe
    assert probe[-1] == {"role": "user", "content": P.WARM_PROBE}


@pytest.mark.asyncio
async def test_guest_history_cleared_on_identity_change():
    mind, prov, ev = make()
    await run(mind, req("a titkom: kék"), ev)
    await mind.on_identity_change(ALEX)
    await mind.on_identity_change(GUEST)
    await run(mind, req("mi a titkom?", turn=2), ev)
    assert all("kék" not in m["content"] for m in prov.calls[-1])


def _requests(msgs: list[dict]) -> list[str]:
    """The <kérés> texts of the session turns (seed excluded)."""
    return [m["content"].split("<kérés>")[1].split("</kérés>")[0] for m in msgs[K:] if m["role"] == "user"]


@pytest.mark.asyncio
async def test_session_is_append_only_and_verbatim():
    mind, prov, ev = make()
    await run(mind, req("egy", user=ALEX), ev)
    await run(mind, req("kettő", user=ALEX, turn=2), ev)
    first, second = prov.calls
    # The previous request (incl. its <kontextus>) is re-sent byte-for-byte.
    assert second[: len(first)] == first
    assert second[len(first)] == {"role": "assistant", "content": "Szia! Itt vagyok."}


@pytest.mark.asyncio
async def test_identity_switch_drops_all_conversation_state():
    """Privacy rule: nothing of the previous identity survives a switch — not even its own
    session when it comes back (memory "privacy-personal-data-rule")."""
    mind, prov, ev = make()
    for i in range(2):
        await run(mind, req(f"alex-{i}", user=ALEX, turn=i), ev)
    assert _requests(prov.calls[-1]) == ["alex-0", "alex-1"]
    await run(mind, req("bob-0", user=BOB, turn=9), ev)
    assert _requests(prov.calls[-1]) == ["bob-0"]  # never sees Alex's turns
    await run(mind, req("alex-2", user=ALEX, turn=10), ev)
    assert _requests(prov.calls[-1]) == ["alex-2"]


@pytest.mark.asyncio
async def test_session_resets_after_idle_gap():
    clock = Clock(datetime(2026, 11, 20, 10, 0))
    mind, prov, ev = make(clock=clock)
    await run(mind, req("régi téma", user=ALEX), ev)
    clock.now = datetime(2026, 11, 20, 10, 6)  # > session_idle_s (300 s)
    await run(mind, req("új téma", user=ALEX, turn=2), ev)
    assert _requests(prov.calls[-1]) == ["új téma"]


@pytest.mark.asyncio
async def test_long_session_carries_only_last_turns():
    mind, prov, ev = make()  # max_session_turns 3, carry_turns 1
    for i in range(4):
        await run(mind, req(f"k{i}", user=ALEX, turn=i), ev)
    assert _requests(prov.calls[-1]) == ["k2", "k3"]


@pytest.mark.asyncio
async def test_guest_history_cleared_at_day_change():
    clock = Clock(datetime(2026, 11, 20, 23, 59))
    mind, prov, ev = make(clock=clock)
    await run(mind, req("tegnapi kérés"), ev)
    clock.now = datetime(2026, 11, 21, 0, 1)
    await run(mind, req("mai kérés", turn=2), ev)
    assert all("tegnapi" not in m["content"] for m in prov.calls[-1])


@pytest.mark.asyncio
async def test_llm_error_is_spoken_in_hungarian_and_reported():
    err = LLMError("no_server", "Nem érem el az Ollamát. Fut a háttérben?", "connect refused")
    mind, _prov, ev = make(FakeProvider(error=err))
    out = await run(mind, req("szia"), ev)
    assert out == err.user_message
    errs = [e for e in ev if e.type == "error"]
    assert errs and errs[0].data == {"where": "mind", "message": err.user_message}
    assert "refused" not in str([e.data for e in ev])  # technical detail never leaks
    assert ev[-1].type == "reply.done"


@pytest.mark.asyncio
async def test_trigger_channel_says_nothing():
    mind, prov, ev = make()
    out = await run(mind, req("", channel="trigger", trigger="clap2"), ev)
    assert out == "" and not prov.calls
    assert ev == [ev[0]] and ev[0].data == {"path": "trigger", "intent": "clap2"}


@pytest.mark.asyncio
async def test_empty_text_says_nothing():
    mind, prov, ev = make()
    assert await run(mind, req("   "), ev) == "" and not prov.calls


@pytest.mark.asyncio
async def test_barge_in_keeps_partial_answer_marked():
    mind, prov, ev = make(FakeProvider(reply="Egy. Kettő. Három."))
    gen = mind.handle(req("számolj"), ev.append)
    assert await gen.__anext__() == "Egy. "  # sentence by sentence
    await gen.aclose()  # the orchestrator stops consuming (barge-in)
    assert "reply.done" not in [e.type for e in ev]
    await run(mind, req("és tovább?", turn=2), ev)
    hist = [m["content"] for m in prov.calls[-1][K:] if m["role"] == "assistant"]
    assert hist == ["Egy. …"]


def test_factory_and_hu_now(tmp_path):
    cfg = {"llm": {}, "tools": {"dry_run": True}, "paths": {"config_dir": str(CONFIG_DIR), "data_dir": str(tmp_path)}}
    mind = create_mind(cfg, lambda e: None)
    assert isinstance(mind, JarvisMind)
    assert hu_now(datetime(2026, 11, 22, 8, 5)) == "2026-11-22 08:05, vasárnap"
