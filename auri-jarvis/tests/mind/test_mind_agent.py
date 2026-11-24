"""Agent loop + Mind routing (M2) with a scripted fake LLM — no Ollama, no side effects."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import pytest

from auri_jarvis.contracts import GUEST, Event, JarvisPrefs, TurnRequest, UserContext
from auri_jarvis.mind.agent import NO_ACTION
from auri_jarvis.mind.core import JarvisMind
from auri_jarvis.mind.ollama_provider import LLMChunk, LLMStats, ToolCall
from auri_jarvis.tools.apps import AppCatalog
from auri_jarvis.tools.builtin import ToolServices
from auri_jarvis.tools.platform import RecordingPlatform

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
USER = UserContext(tier="user", user_id="u-1", prefs=JarvisPrefs(address="Teszt"), profile={"name": "Teszt Elek"})


def text(s: str) -> list[LLMChunk]:
    words = s.split(" ")
    return [LLMChunk(content=w if i == 0 else " " + w) for i, w in enumerate(words)]


def call(tool: str, /, **args) -> list[LLMChunk]:
    return [LLMChunk(tool_calls=[ToolCall(tool, args)])]


class ScriptedProvider:
    """Each chat_stream() call plays the next scripted round, then a `done` chunk."""

    model = "fake:1b"

    def __init__(self, *rounds: list[LLMChunk]) -> None:
        self.rounds = list(rounds)
        self.calls: list[dict] = []
        self.closed_early = 0

    async def chat_stream(self, messages, tools=None, opts=None):
        self.calls.append({"messages": [dict(m) for m in messages], "tools": tools})
        chunks = self.rounds.pop(0) if self.rounds else text("Rendben.")
        finished = False
        try:
            for ch in chunks:
                await asyncio.sleep(0)
                yield ch
            finished = True
            yield LLMChunk(done=True, stats=LLMStats(model=self.model, first_token_ms=7, eval_tokens=3))
        finally:
            if not finished:
                self.closed_early += 1  # the consumer closed the stream (barge-in)

    async def warmup(self, messages, tools=None, model=None):
        return LLMStats(model=self.model)

    async def aclose(self):
        pass


def make(*rounds: list[LLMChunk]):
    events: list[Event] = []
    prov = ScriptedProvider(*rounds)
    svc = ToolServices(platform=RecordingPlatform(), apps=AppCatalog.load(CONFIG_DIR / "apps.yaml"))
    mind = JarvisMind(
        {"llm": {"max_tool_rounds": 3}, "paths": {"config_dir": str(CONFIG_DIR)}},
        events.append,
        provider=prov,  # type: ignore[arg-type]
        services=svc,
        clock=lambda: datetime(2026, 11, 21, 10, 0),
    )
    return mind, prov, svc.platform, events


async def ask(mind: JarvisMind, said: str, events: list[Event], user: UserContext = USER, turn: int = 1) -> str:
    req = TurnRequest(turn_id=turn, user=user, channel="voice", text=said)
    return "".join([d async for d in mind.handle(req, events.append)])


def types(events: list[Event]) -> list[str]:
    return [e.type for e in events]


# ── agent loop ───────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_tool_call_then_answer_and_verbatim_session():
    mind, prov, plat, ev = make(call("set_volume", level=20), text("Rendben, húsz százalékon van."))
    out = await ask(mind, "legyen egy kicsit csendesebb, mondjuk húsz", ev)
    assert out.strip() == "Rendben, húsz százalékon van."
    assert plat.volume == 20
    tool_ev = [e for e in ev if e.type == "tool"]
    assert tool_ev and tool_ev[0].data["status"] == "ok"
    # Round 2 got the tool result; the tool schemas were offered in round 1.
    assert prov.calls[0]["tools"] and prov.calls[1]["messages"][-1]["role"] == "tool"
    # Next turn replays the whole tool exchange verbatim (cache resume).
    await ask(mind, "köszi", ev, turn=2)
    second = prov.calls[-1]["messages"]
    assert second[: len(prov.calls[1]["messages"])] == prov.calls[1]["messages"]


@pytest.mark.asyncio
async def test_hallucination_guard_blocks_claim_without_tool():
    mind, prov, plat, ev = make(text("Megnyitottam a Photoshopot a jobb monitoron."))
    out = await ask(mind, "csináld meg azt a dolgot", ev)
    assert "Megnyitottam" not in out and out.strip() == NO_ACTION
    assert plat.calls == []


@pytest.mark.asyncio
async def test_claim_is_fine_after_a_successful_tool():
    mind, prov, plat, ev = make(call("open_app", name="chrome"), text("Megnyitottam a Chrome-ot."))
    out = await ask(mind, "kéne egy böngésző", ev)
    assert out.strip() == "Megnyitottam a Chrome-ot."


@pytest.mark.asyncio
async def test_failed_tool_then_claim_is_blocked():
    mind, prov, plat, ev = make(call("open_app", name="photoshop"), text("Megnyitottam."))
    out = await ask(mind, "nyisd meg a fotósopot", ev)
    assert out.strip() == NO_ACTION


@pytest.mark.asyncio
async def test_tool_rounds_are_capped():
    rounds = [call("get_time") for _ in range(5)]
    mind, prov, plat, ev = make(*rounds)
    await ask(mind, "mennyi az idő most pontosan, többször is nézd meg", ev)
    assert len(prov.calls) == 4  # 3 tool rounds + 1 final round without tools
    assert prov.calls[-1]["tools"] is None


# ── confirmation flow (DoD M2: confirm never runs without an explicit yes) ───
@pytest.mark.asyncio
async def test_confirm_flow_yes_runs_once():
    mind, prov, plat, ev = make(call("pc_power", action="lock"))
    q = await ask(mind, "zárd le a gépet", ev)
    assert "Biztosan zároljam" in q and plat.calls == []
    assert any(e.type == "mind.expects_reply" for e in ev)
    yes = await ask(mind, "igen", ev, turn=2)
    assert yes == "Zároltam a gépet." and plat.names() == ["lock"]
    again = await ask(mind, "igen", ev, turn=3)  # no pending action any more → normal turn
    assert plat.names() == ["lock"] and again


@pytest.mark.asyncio
async def test_confirm_flow_no_and_other_topic_cancel():
    mind, prov, plat, ev = make(call("pc_power", action="sleep"))
    await ask(mind, "altasd el a gépet", ev)
    assert await ask(mind, "nem", ev, turn=2) == "Rendben, nem csinálom."
    mind2, prov2, plat2, ev2 = make(call("close_app", name="chrome"), text("A főváros Canberra."))
    await ask(mind2, "zárd be a chrome-ot", ev2)
    await ask(mind2, "mi Ausztrália fővárosa?", ev2, turn=2)  # not a yes → pending dropped
    assert await ask(mind2, "igen", ev2, turn=3) and plat2.calls == []


@pytest.mark.asyncio
async def test_pending_confirmation_never_crosses_identities():
    mind, prov, plat, ev = make(call("pc_power", action="lock"))
    await ask(mind, "zárd le a gépet", ev)
    await mind.on_identity_change(GUEST)
    await ask(mind, "igen", ev, user=GUEST, turn=2)
    assert plat.calls == []


# ── fast-path routing ────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_fastpath_runs_tool_without_llm():
    mind, prov, plat, ev = make()
    out = await ask(mind, "Hangerő 30", ev)
    assert out == "Hangerő 30 százalék." and prov.calls == []
    assert ev[0] == Event("route", {"path": "fastpath", "intent": "set_volume"}, ev[0].t)
    assert types(ev)[-2:] == ["reply.delta", "reply.done"]


@pytest.mark.asyncio
async def test_fastpath_guest_denied_and_cancel_is_silent():
    mind, prov, plat, ev = make()
    out = await ask(mind, "nyisd meg a vs code-ot", ev, user=GUEST)
    assert "be kell jelentkezned" in out and plat.calls == []
    assert await ask(mind, "mégse", ev, user=GUEST, turn=2) == ""


@pytest.mark.asyncio
async def test_regression_sentences_go_to_the_llm():
    mind, prov, plat, ev = make(text("Auri vagyok."), text("Nézzük meg együtt."))
    await ask(mind, "ki vagy?", ev)
    await ask(mind, "de a brain miért nem tud jól válaszolni?", ev, turn=2)
    assert len(prov.calls) == 2 and plat.calls == []


# ── barge-in closes the model stream at once ─────────────────────────────────
@pytest.mark.asyncio
async def test_barge_in_closes_the_llm_stream_immediately():
    mind, prov, plat, ev = make(text("Első mondat. Második mondat. Harmadik mondat."))
    gen = mind.handle(TurnRequest(turn_id=1, user=USER, channel="voice", text="mesélj"), ev.append)
    assert (await gen.__anext__()).startswith("Első")
    await gen.aclose()
    assert prov.closed_early == 1  # not left running until garbage collection
