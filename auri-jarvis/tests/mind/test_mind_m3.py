"""M3 (AI-2): onboarding dialogue, tier gates, routines + clap triggers. Fictional data only,
no Ollama, side effects mocked (RecordingPlatform)."""

from __future__ import annotations

import dataclasses
from datetime import datetime
from pathlib import Path

import pytest

from auri_jarvis.contracts import GUEST, Event, JarvisPrefs, TurnRequest, UserContext
from auri_jarvis.mind import onboarding as ob
from auri_jarvis.mind.core import JarvisMind
from auri_jarvis.mind.ollama_provider import LLMChunk, LLMStats
from auri_jarvis.tools.apps import AppCatalog
from auri_jarvis.tools.builtin import ToolServices
from auri_jarvis.tools.platform import RecordingPlatform
from auri_jarvis.tools.timers import TimerService

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
NEW_USER = UserContext(tier="user", user_id="u-1", display_name="Teszt", profile={"name": "Teszt Elek"})
ROUTINE = {"music_url": None, "apps": [{"app": "vscode", "monitor": 2, "fullscreen": False}],
           "urls": [{"url": "https://example.com", "monitor": 1}]}  # fmt: skip
DONE_USER = UserContext(
    tier="user",
    user_id="u-2",
    prefs=JarvisPrefs(
        address="Elemér", welcome_routine=ROUTINE, onboarded=True, answered=("address", "wake_word", "voice", "welcome_routine")
    ),
)


class SilentProvider:
    model = "fake:1b"

    def __init__(self) -> None:
        self.calls = 0

    async def chat_stream(self, messages, tools=None, opts=None):
        self.calls += 1
        yield LLMChunk(content="Rendben.")
        yield LLMChunk(done=True, stats=LLMStats(model=self.model))

    async def warmup(self, messages, tools=None, model=None):
        return LLMStats()

    async def aclose(self):
        pass


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 21, 8, 0)

    def __call__(self) -> datetime:
        return self.now


def make(clock: Clock | None = None):
    events: list[Event] = []
    plat = RecordingPlatform()
    svc = ToolServices(platform=plat, apps=AppCatalog.load(CONFIG_DIR / "apps.yaml"), timers=TimerService(None, events.append))
    prov = SilentProvider()
    mind = JarvisMind({"paths": {"config_dir": str(CONFIG_DIR)}}, events.append, provider=prov, services=svc,  # type: ignore[arg-type]
                      clock=clock or Clock())  # fmt: skip
    return mind, plat, events, prov


async def say(mind, text, user, events, turn=1) -> str:
    req = TurnRequest(turn_id=turn, user=user, channel="voice", text=text)
    return "".join([c async for c in mind.handle(req, events.append)])


async def trigger(mind, trig, user, events, text="") -> str:
    req = TurnRequest(turn_id=0, user=user, channel="trigger", trigger=trig, text=text)
    return "".join([c async for c in mind.handle(req, events.append)])


def proposed(events) -> list[dict]:
    return [e.data for e in events if e.type == "prefs.proposed"]


def apply(user: UserContext, partials: list[dict]) -> UserContext:
    """What AI-3 does with prefs.proposed (union of `answered`; all 4 → onboarded)."""
    p = user.prefs
    for d in partials:
        changes = {k: v for k, v in d.items() if k not in ("answered", "onboarded")}
        answered = tuple(dict.fromkeys([*p.answered, *d.get("answered", ())]))
        onboarded = d.get("onboarded", len(answered) == 4)
        p = dataclasses.replace(p, **changes, answered=answered, onboarded=onboarded)
    return dataclasses.replace(user, prefs=p)


# ── tier gates ───────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_guest_is_never_asked_anything():
    mind, plat, ev, _ = make()
    assert await trigger(mind, "login", GUEST, ev) == ""
    assert not [e for e in ev if e.type in ("onboarding", "prefs.proposed", "mind.expects_reply")]
    assert await say(mind, "állítsuk be újra", GUEST, ev) == "Ehhez be kell jelentkezned."
    assert proposed(ev) == []


@pytest.mark.asyncio
async def test_onboarded_user_is_not_asked_again():
    mind, plat, ev, _ = make()
    assert await trigger(mind, "login", DONE_USER, ev) == ""
    assert not [e for e in ev if e.type == "onboarding"]


# ── the 4 questions ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_full_voice_onboarding_once():
    mind, plat, ev, prov = make()
    user = NEW_USER
    out = await trigger(mind, "login", user, ev)
    assert "Négy gyors kérdés" in out and out.endswith("Hogyan szólítsalak?")
    assert ev[-1] == Event("mind.expects_reply", {"timeout_s": ob.REPLY_WINDOW_S}, ev[-1].t)
    assert [e.data["step"] for e in ev if e.type == "onboarding"] == [1]

    out = await say(mind, "Szólíts Elemérnek", user, ev, 2)
    assert out.startswith("Rendben, Elemér.") and "Hey Auri vagy Hey Jarvis" in out
    assert proposed(ev)[-1] == {"address": "Elemér", "answered": ["address"]}
    user = apply(user, proposed(ev))

    ev.clear()
    out = await say(mind, "a hey jarvist kérem", user, ev, 3)
    assert out.startswith("Hey Jarvis lesz.") and out.endswith(ob.SAMPLES_INTRO)
    assert proposed(ev)[-1] == {"wake_word": "hey_jarvis", "answered": ["wake_word"]}
    # Order the user hears: this turn's text → sample 1 → sample 2 → the question → listen.
    order = [(e.type, e.data.get("voice") or e.data.get("text") or e.data.get("step")) for e in ev
             if e.type in ("reply.done", "voice.sample", "say", "mind.expects_reply")]  # fmt: skip
    assert [o[0] for o in order] == ["reply.done", "voice.sample", "voice.sample", "say", "mind.expects_reply"]
    assert order[1][1] == "daniel" and order[2][1] == "george" and "Melyik hang" in order[3][1]
    user = apply(user, proposed(ev))

    out = await say(mind, "a második", user, ev, 4)
    assert proposed(ev)[-1] == {"voice": "george", "answered": ["voice"]} and "rutint" in out
    user = apply(user, proposed(ev))

    out = await say(mind, "igen", user, ev, 5)
    assert out.endswith(ob.DONE) and "HUD-on" in out
    last = proposed(ev)[-1]
    assert last["answered"] == ["welcome_routine"] and last["welcome_routine"]["apps"]
    user = apply(user, proposed(ev))
    assert user.prefs.onboarded

    # Never asked again; the next turn is a normal one (LLM).
    await mind.on_identity_change(user)
    assert await trigger(mind, "login", user, ev) == ""
    await say(mind, "Mondj egy szót.", user, ev, 6)
    assert prov.calls == 1


@pytest.mark.asyncio
async def test_already_answered_questions_are_skipped():
    mind, plat, ev, _ = make()
    user = dataclasses.replace(NEW_USER, prefs=JarvisPrefs(answered=("address", "voice")))
    out = await trigger(mind, "login", user, ev)
    assert out.endswith("Hey Auri vagy Hey Jarvis?")
    out = await say(mind, "Hey Auri", user, ev, 2)
    assert "rutint" in out and "Melyik hang" not in out  # voice was answered on the HUD


@pytest.mark.asyncio
async def test_hud_answer_while_waiting_moves_on_out_of_turn():
    mind, plat, ev, _ = make()
    await trigger(mind, "login", NEW_USER, ev)  # asks the address
    ev.clear()
    hud_user = apply(NEW_USER, [{"address": "Elemér", "answered": ["address"]}])
    await mind.on_identity_change(hud_user)
    says = [e.data["text"] for e in ev if e.type == "say"]
    assert says == ["Melyik ébresztőszót szeretnéd: Hey Auri vagy Hey Jarvis?"]
    assert [e.data["step"] for e in ev if e.type == "onboarding"] == [2]


@pytest.mark.asyncio
async def test_later_finishes_with_defaults_and_no_routine_is_a_valid_answer():
    mind, plat, ev, _ = make()
    await trigger(mind, "login", NEW_USER, ev)
    assert await say(mind, "később", NEW_USER, ev, 2) == ob.LATER
    assert proposed(ev)[-1] == {"onboarded": True}

    mind2, _, ev2, _ = make()
    u = dataclasses.replace(NEW_USER, prefs=JarvisPrefs(answered=("address", "wake_word", "voice")))
    await trigger(mind2, "login", u, ev2)
    out = await say(mind2, "nem", u, ev2, 2)  # "nem" here = no routine, not "later"
    assert proposed(ev2)[-1] == {"welcome_routine": None, "answered": ["welcome_routine"]} and ob.DONE in out


@pytest.mark.asyncio
async def test_unclear_answer_is_asked_again_once_then_skipped():
    mind, plat, ev, _ = make()
    u = dataclasses.replace(NEW_USER, prefs=JarvisPrefs(answered=("address",)))
    await trigger(mind, "login", u, ev)
    out = await say(mind, "talán valami más", u, ev, 2)
    assert out.startswith("Ezt nem értettem.") and "Hey Jarvis" in out
    out = await say(mind, "fogalmam sincs", u, ev, 3)
    assert "kihagyom" in out and proposed(ev) == []


@pytest.mark.asyncio
async def test_command_during_the_address_question_is_not_taken_as_a_name():
    mind, plat, ev, _ = make()
    await trigger(mind, "login", NEW_USER, ev)
    out = await say(mind, "Hangerő 30", NEW_USER, ev, 2)
    assert out == "Hangerő 30 százalék." and proposed(ev) == []


@pytest.mark.asyncio
async def test_set_up_again_restarts_from_question_one():
    mind, plat, ev, _ = make()
    out = await say(mind, "Auri, állítsuk be újra", DONE_USER, ev)
    assert proposed(ev) == [{"onboarded": False}] and out.endswith("Hogyan szólítsalak?")
    out = await say(mind, "uram", DONE_USER, ev, 2)  # old prefs still say "answered": must not skip
    assert proposed(ev)[-1] == {"address": "uram", "answered": ["address"]} and "Hey Jarvis" in out


@pytest.mark.parametrize(
    ("text", "value"),
    [("Szólíts Elemérnek", "Elemér"), ("A nevem Teszt Elek", "Teszt Elek"), ("Elek", "Elek"), ("uram", "uram"),
     ("semmi, csak tegezz", "you"), ("mindegy", "you"), ("hát ezt most nem tudom pontosan megmondani", None)],
)  # fmt: skip
def test_parse_address(text, value):
    assert ob.parse_address(text) == value


@pytest.mark.parametrize(
    ("text", "wake", "voice"),
    [("Hey Jarvis", "hey_jarvis", None), ("az elsőt", "hey_auri", "daniel"), ("a második", "hey_jarvis", "george"),
     ("a helyi, ingyenes", None, "piper"), ("George", None, "george"), ("passz", None, None)],
)  # fmt: skip
def test_parse_choices(text, wake, voice):
    assert ob.parse_wake_word(text) == wake
    assert ob.parse_voice(text) == voice


# ── routines + clap triggers ─────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_double_clap_runs_welcome_once_a_day():
    clock = Clock()
    mind, plat, ev, _ = make(clock)
    out = await trigger(mind, "clap2", DONE_USER, ev)
    assert out.startswith("Üdv itthon, Elemér.")
    assert plat.names() == ["start_app", "place_window", "open_url", "place_window"]
    assert plat.calls[2][1]["url"] == "https://example.com"
    assert await trigger(mind, "clap2", DONE_USER, ev) == ""  # second double clap today → nothing
    clock.now = datetime(2026, 11, 22, 8, 0)
    assert (await trigger(mind, "clap2", DONE_USER, ev)).startswith("Üdv itthon")


@pytest.mark.asyncio
async def test_double_clap_without_routine_or_as_guest_does_nothing():
    mind, plat, ev, _ = make()
    assert await trigger(mind, "clap2", GUEST, ev) == ""
    assert await trigger(mind, "clap2", NEW_USER, ev) == ""
    assert plat.calls == []


@pytest.mark.asyncio
async def test_triple_clap_guest_only_says_sleep_mode_user_runs_alvas():
    mind, plat, ev, _ = make()
    assert await trigger(mind, "clap3", GUEST, ev) == "Alvó mód."
    assert plat.calls == []
    out = await trigger(mind, "clap3", DONE_USER, ev)
    assert out.startswith("Jó éjt.") and plat.names() == ["lock"]  # preconfirmed in routines.yaml


@pytest.mark.asyncio
async def test_hud_button_and_phrase_run_routines_for_users_only():
    mind, plat, ev, _ = make()
    assert "be kell jelentkezned" in await trigger(mind, "hud_button", GUEST, ev, text="munka")
    assert "be kell jelentkezned" in await say(mind, "munka mód", GUEST, ev)
    assert plat.calls == []
    out = await trigger(mind, "hud_button", DONE_USER, ev, text="munka")
    assert out.startswith("Fókusz mód.")
    assert plat.names() == ["start_app", "place_window", "set_volume"]
    assert plat.calls[1][1]["mode"] == "fullscreen" and plat.volume == 20
    out = await say(mind, "Üdv itthon!", DONE_USER, ev, 2)
    assert out.startswith("Üdv itthon, Elemér.")
    assert "Nincs beállítva" in await say(mind, "kezdjük a napot", NEW_USER, ev, 3)


@pytest.mark.asyncio
async def test_routine_url_step_only_http():
    mind, plat, ev, _ = make()
    bad = dataclasses.replace(DONE_USER, prefs=dataclasses.replace(
        DONE_USER.prefs, welcome_routine={"music_url": "spotify:playlist:x", "apps": [], "urls": []}))  # fmt: skip
    out = await trigger(mind, "clap2", bad, ev)
    assert "gond volt" in out and plat.calls == []
