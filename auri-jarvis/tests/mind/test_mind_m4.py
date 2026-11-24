"""M4 (AI-2): long-term memory, dream phase, proposals, skills, dictation. Fictional data,
no Ollama (scripted LLM), no side effects (RecordingPlatform), in-memory / tmp SQLite."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import httpx
import numpy as np
import pytest

from auri_jarvis.contracts import GUEST, Event, JarvisPrefs, TurnRequest, UserContext
from auri_jarvis.memory.dream import Dreamer
from auri_jarvis.memory.embed import Embedder
from auri_jarvis.memory.redact import is_secret, mask
from auri_jarvis.memory.store import MemoryStore
from auri_jarvis.mind.core import JarvisMind
from auri_jarvis.mind.ollama_provider import LLMChunk, LLMStats
from auri_jarvis.skills.loader import SkillBook
from auri_jarvis.tools.apps import AppCatalog
from auri_jarvis.tools.builtin import ToolServices, build_registry
from auri_jarvis.tools.platform import RecordingPlatform
from auri_jarvis.tools.registry import ToolContext
from auri_jarvis.tools.timers import TimerService

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
USER = UserContext(tier="user", user_id="u-1", prefs=JarvisPrefs(address="Elek", onboarded=True,
                   answered=("address", "wake_word", "voice", "welcome_routine")))  # fmt: skip
USER2 = UserContext(tier="user", user_id="u-2", prefs=JarvisPrefs(onboarded=True))


class FakeLLM:
    """Scripted replies; records every request. `json_reply` answers format= requests."""

    model = "fake:1b"

    def __init__(self, reply: str = "Rendben.", json_reply: dict | None = None) -> None:
        self.reply = reply
        self.json_reply = json_reply or {"facts": []}
        self.calls: list[dict] = []

    async def chat_stream(self, messages, tools=None, opts=None):
        self.calls.append({"messages": [dict(m) for m in messages], "format": getattr(opts, "format", None)})
        text = json.dumps(self.json_reply, ensure_ascii=False) if getattr(opts, "format", None) else self.reply
        yield LLMChunk(content=text)
        yield LLMChunk(done=True, stats=LLMStats(model=self.model, prompt_tokens=10, eval_tokens=3))

    async def chat(self, messages, tools=None, opts=None):
        text = ""
        async for ch in self.chat_stream(messages, tools, opts):
            text += ch.content
        return text, [], LLMStats(model=self.model)

    async def warmup(self, messages, tools=None, model=None):
        return LLMStats()

    async def aclose(self):
        pass


class Clock:
    def __init__(self, t: float) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


def make(tmp_path: Path, llm: FakeLLM | None = None, store: MemoryStore | None = None):
    events: list[Event] = []
    llm = llm or FakeLLM()
    store = store or MemoryStore(":memory:")
    svc = ToolServices(platform=RecordingPlatform(), apps=AppCatalog.load(CONFIG_DIR / "apps.yaml"),
                       timers=TimerService(None, events.append), memory=store)  # fmt: skip
    mind = JarvisMind({"paths": {"config_dir": str(CONFIG_DIR), "data_dir": str(tmp_path)},
                       "memory": {"dream_idle_s": 600, "dream_every_s": 0, "dream_min_turns": 3}},
                      events.append, provider=llm, services=svc,  # type: ignore[arg-type]
                      clock=lambda: datetime(2026, 11, 21, 10, 0))  # fmt: skip
    return mind, llm, store, events


async def say(mind, text, user, events, turn=1) -> str:
    req = TurnRequest(turn_id=turn, user=user, channel="voice", text=text)
    return "".join([c async for c in mind.handle(req, events.append)])


def last_user_msg(llm: FakeLLM) -> str:
    return llm.calls[-1]["messages"][-1]["content"]


# ── store ────────────────────────────────────────────────────────────────────
def test_store_is_per_user_merges_and_refuses_secrets_and_guests():
    s = MemoryStore(":memory:")
    assert s.add_fact("u-1", "Szereti a rövid válaszokat", "preference") == (1, False)
    assert s.add_fact("u-1", "Szereti a rövid válaszokat.", "preference") == (1, True)
    assert s.facts("u-1")[0].mentions == 2
    assert s.add_fact("u-1", "A jelszava kutya123", "fact") is None
    assert s.add_fact("u-1", "Kártyaszám 4111 1111 1111 1111") is None
    s.add_fact("u-2", "Bob a teát szereti", "preference")
    assert [f.text for f, _ in s.search("u-1", "tea")] == []
    assert [f.text for f, _ in s.search("u-1", "miért ilyen rövidek a válaszaid")] == ["Szereti a rövid válaszokat"]
    with pytest.raises(ValueError):
        s.add_turn("", "voice", "x", "y")  # a guest is never stored


def test_merge_by_embedding_similarity():
    s = MemoryStore(":memory:")
    v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    s.add_fact("u-1", "Kávét iszik reggel", "preference", embedding=v)
    _, merged = s.add_fact("u-1", "Reggelente kávézik", "preference", embedding=v * 0.99 + 0.01)
    assert merged and len(s.facts("u-1")) == 1


def test_redaction():
    assert mask("A jelszavam: titok123") == "[kényes adat törölve]"
    assert mask("Hogyan állítsak be API kulcsot?") == "Hogyan állítsak be API kulcsot?"
    assert "[törölve]" in mask("A számlám 11773016-11111018-00000000")
    assert is_secret("api token: sk-abc123def456ghi789")


def test_proposals_need_the_users_answer():
    s = MemoryStore(":memory:")
    fid, _ = s.add_fact("u-1", "Mindig 25 perces időzítőt kér", "preference")
    pid = s.add_proposal("u-1", fid, "Felvegyem?")
    assert s.profile_facts("u-1") == []  # nothing changes until the user answers
    assert s.add_proposal("u-1", fid, "Felvegyem?") is None  # never proposed twice
    assert s.decide("u-2", pid, True) is False  # someone else can't decide it
    assert s.decide("u-1", pid, True) and s.profile_facts("u-1") == ["Mindig 25 perces időzítőt kér"]


# ── recall in the Mind ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_week_old_preference_is_used_spontaneously(tmp_path):
    clock = Clock(datetime(2026, 11, 14, 10, 0).timestamp())
    store = MemoryStore(":memory:", clock=clock)
    store.add_fact("u-1", "Szereti, ha röviden, egy mondatban válaszolok", "preference")
    store.add_fact("u-1", "A kutyája neve Bodri", "person")
    clock.t = datetime(2026, 11, 21, 10, 0).timestamp()  # one week later
    mind, llm, _, ev = make(tmp_path, store=store)
    await say(mind, "Mesélj a Holdról!", USER, ev)  # unrelated question
    assert "emlék: Szereti, ha röviden, egy mondatban válaszolok" in last_user_msg(llm)
    await say(mind, "Hogy hívják a kutyámat?", USER, ev, 2)
    assert "emlék: A kutyája neve Bodri" in last_user_msg(llm)


@pytest.mark.asyncio
async def test_guest_sees_no_memories_and_is_not_stored(tmp_path):
    store = MemoryStore(":memory:")
    store.add_fact("u-1", "Szereti, ha röviden válaszolok", "preference")
    mind, llm, _, ev = make(tmp_path, store=store)
    await say(mind, "Mesélj a Holdról!", GUEST, ev)
    assert "emlék" not in last_user_msg(llm)
    assert "Szereti" not in json.dumps(llm.calls[-1]["messages"], ensure_ascii=False)
    assert await say(mind, "mit tudsz rólam?", GUEST, ev, 2) == "Vendégként nem tárolok rólad semmit."
    assert "be kell jelentkezned" in await say(mind, "jegyezd meg, hogy a kedvenc színem a kék", GUEST, ev, 3)
    assert store.undreamed_turns("u-1") == [] and store.count_facts("u-1") == 1


@pytest.mark.asyncio
async def test_remember_recall_forget_by_voice(tmp_path):
    mind, llm, store, ev = make(tmp_path)
    assert await say(mind, "Jegyezd meg, hogy a kutyám neve Bodri", USER, ev) == "Megjegyeztem."
    assert "Bodri" in await say(mind, "mit tudsz rólam?", USER, ev, 2)
    assert "nem jegyzek meg" in await say(mind, "jegyezd meg, hogy a pinkódom 1234", USER, ev, 3)
    q = await say(mind, "Felejtsd el, hogy a kutyám neve Bodri", USER, ev, 4)
    assert "Biztosan elfelejtsem" in q and store.count_facts("u-1") == 1  # not before "igen"
    assert (await say(mind, "igen", USER, ev, 5)).startswith("Elfelejtettem")
    assert store.count_facts("u-1") == 0


@pytest.mark.asyncio
async def test_forget_everything_needs_confirmation(tmp_path):
    mind, llm, store, ev = make(tmp_path)
    await say(mind, "jegyezd meg, hogy szeretem a teát", USER, ev)
    await say(mind, "felejtsd el, hogy mindent", USER, ev, 2)
    assert store.count_facts("u-1") == 1
    assert "Mindent elfelejtettem" in await say(mind, "igen", USER, ev, 3)
    assert store.count_facts("u-1") == 0


@pytest.mark.asyncio
async def test_turns_are_kept_for_the_user_masked(tmp_path):
    mind, llm, store, ev = make(tmp_path)
    await say(mind, "A jelszavam: titok, de ez csak példa", USER, ev)
    await say(mind, "Mesélj valamit a csillagokról", USER, ev, 2)
    turns = store.undreamed_turns("u-1")
    assert [t.request for t in turns] == ["[kényes adat törölve]", "Mesélj valamit a csillagokról"]


# ── dream phase ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_dream_extracts_merges_and_proposes_only_after_repeats(tmp_path):
    llm = FakeLLM(json_reply={"facts": [{"text": "Mindig 25 perces időzítőt kér", "kind": "preference", "confidence": 0.8},
                                        {"text": "A jelszava titok", "kind": "fact"}]})  # fmt: skip
    mind, _, store, ev = make(tmp_path, llm=llm)
    for round_ in range(3):
        for i in range(3):
            await say(mind, f"Időzítő kéne, kör {round_}-{i}, huszonöt perc", USER, ev, i)
        await mind.idle_tick(900, USER)
    facts = store.facts("u-1")
    prefs = [f for f in facts if f.kind == "preference"]
    assert [f.text for f in prefs] == ["Mindig 25 perces időzítőt kér"]
    assert prefs[0].mentions == 3  # merged across the three dreams
    assert not any("jelszava" in f.text for f in facts)  # secrets never get in
    props = [e for e in ev if e.type == "proposal"]
    assert len(props) == 1 and "25 perces" in props[0].data["text"]
    assert store.profile_facts("u-1") == []  # NOT in the profile by itself
    assert llm.calls and any(c["format"] for c in llm.calls)  # structured output was used

    # accept on the HUD → it joins the static prefix of the next request
    await mind.on_hud_event(Event("proposal.answer", {"id": props[0].data["id"], "accept": True}), USER)
    await say(mind, "Mesélj a Holdról", USER, ev, 9)
    assert "Mindig 25 perces időzítőt kér" in llm.calls[-1]["messages"][0]["content"]


@pytest.mark.asyncio
async def test_dream_waits_for_idle_and_never_runs_for_guests(tmp_path):
    llm = FakeLLM(json_reply={"facts": [{"text": "Szereti a zenét", "kind": "preference"}]})
    mind, _, store, ev = make(tmp_path, llm=llm)
    for i in range(3):
        await say(mind, f"kérdés {i}", USER, ev, i)
    await mind.idle_tick(60, USER)  # not idle long enough
    await mind.idle_tick(900, GUEST)
    assert store.count_facts("u-1") == 0
    await mind.idle_tick(900, USER)
    assert store.count_facts("u-1") == 1


@pytest.mark.asyncio
async def test_rejected_proposal_stays_out(tmp_path):
    store = MemoryStore(":memory:")
    fid, _ = store.add_fact("u-1", "Mindig halkan hallgat zenét", "preference")
    pid = store.add_proposal("u-1", fid, "Felvegyem?")
    mind, llm, _, ev = make(tmp_path, store=store)
    await mind.on_hud_event(Event("proposal.answer", {"id": pid, "accept": False}), USER)
    await say(mind, "szia", USER, ev)
    assert "Mindig halkan" not in llm.calls[-1]["messages"][0]["content"]


# ── skills ───────────────────────────────────────────────────────────────────
def test_skill_loader_and_router():
    book = SkillBook.load(ROOT / "skills")
    assert {"napi-briefing", "projekt-statusz", "fokusz-mod", "jegyzet-diktalas"} <= set(book.skills)
    assert book.route("Auri, mi vár ma rám?").name == "napi-briefing"
    assert book.route("Hogy állnak a projektjeim?").name == "projekt-statusz"
    assert book.route("Szerintem a pomodoro technika jó, de mit gondolsz a hosszabb munkablokkokról?") is None
    assert book.get("napi briefing").name == "napi-briefing"


@pytest.mark.asyncio
async def test_skill_index_only_for_users_and_briefing_gets_real_data(tmp_path):
    mind, llm, store, ev = make(tmp_path)
    await say(mind, "szia", GUEST, ev)
    assert "napi-briefing" not in llm.calls[-1]["messages"][0]["content"]
    mind._services.timers.add("user:u-1", "reminder", datetime(2026, 11, 21, 18, 30).timestamp(), "edzés", persist=False)
    await say(mind, "mi vár ma rám?", USER, ev, 2)
    msgs = llm.calls[-1]["messages"]
    assert "napi-briefing" in msgs[0]["content"]  # skill index in the user's prefix
    tail = msgs[-1]["content"]
    assert "skill:" in tail and "briefing ma: ma 18:30 edzés" in tail


@pytest.mark.asyncio
async def test_use_skill_tool_returns_the_body(tmp_path):
    svc = ToolServices(platform=RecordingPlatform(), skills=SkillBook.load(ROOT / "skills"))
    res = await build_registry().call("use_skill", {"name": "fokusz-mod"}, ToolContext(USER, lambda e: None, svc))
    assert res.ok and "1500" in res.message
    denied = await build_registry().call("use_skill", {"name": "fokusz-mod"}, ToolContext(GUEST, lambda e: None, svc))
    assert denied.status == "denied"


@pytest.mark.asyncio
async def test_dictation_saves_a_note_in_accurate_mode(tmp_path):
    mind, llm, store, ev = make(tmp_path)
    assert await say(mind, "Jegyzetet szeretnék diktálni", USER, ev) == "Mondhatod, figyelek."
    exp = [e for e in ev if e.type == "mind.expects_reply"][-1]
    assert exp.data == {"timeout_s": 10, "accurate": True}
    assert await say(mind, "Holnap hívjam fel a szerelőt a kazán miatt.", USER, ev, 2) == "Feljegyeztem."
    notes = list((tmp_path / "mind" / "notes").rglob("2026-11-21.md"))
    assert notes and "kazán" in notes[0].read_text(encoding="utf-8")
    assert any(f.kind == "note" for f in store.facts("u-1"))
    assert llm.calls == []  # no LLM involved
    await say(mind, "diktálni szeretnék", USER, ev, 3)
    assert "kényes adat" in await say(mind, "a pinkódom 4321", USER, ev, 4)


# ── embeddings (mocked Ollama) ───────────────────────────────────────────────
@pytest.mark.asyncio
async def test_embedder_and_missing_model():
    def ok(req: httpx.Request) -> httpx.Response:
        n = len(json.loads(req.content)["input"])
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2, 0.3]] * n})

    e = Embedder({}, transport=httpx.MockTransport(ok))
    vecs = await e.embed(["a", "b"])
    assert vecs is not None and len(vecs) == 2 and vecs[0].dtype == np.float32
    await e.aclose()

    missing = Embedder({}, transport=httpx.MockTransport(lambda r: httpx.Response(404, json={"error": "not found"})))
    assert await missing.embed(["a"]) is None and missing.available is False
    await missing.aclose()


@pytest.mark.asyncio
async def test_dreamer_needs_enough_turns():
    store = MemoryStore(":memory:")
    d = Dreamer(store, FakeLLM(json_reply={"facts": [{"text": "x tény", "kind": "fact"}]}), None, min_turns=3)  # type: ignore[arg-type]
    store.add_turn("u-1", "voice", "egy", "a")
    assert (await d.run("u-1")).turns == 0
