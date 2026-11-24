"""auri_jarvis.contracts — the shared language of the three AIs.

Owner: AI-3 (BODY). AI-1 and AI-2 only IMPORT from here. Changes only via a request in
JARVIS_BUILD.md §6 (integration queue), announced in §4 (status log).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Literal, Protocol

import numpy as np

SAMPLE_RATE = 16_000   # Hz, mono, float32 in [-1.0, 1.0]
FRAME_SAMPLES = 1_280  # 80 ms


# ── Events: internal bus == HUD WebSocket JSON (1:1) — types listed in §2.3 ──
@dataclass
class Event:
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    t: float = field(default_factory=time.time)


Emit = Callable[[Event], None]  # thread-safe; may be called from any thread


# ── Identity (produced by AI-3, read by everyone) ────────────────────────────
WakeWord = Literal["hey_auri", "hey_jarvis"]
VoiceName = Literal["daniel", "george", "piper"]
Tier = Literal["guest", "user"]
PrefKey = Literal["address", "wake_word", "voice", "welcome_routine"]


@dataclass(frozen=True)
class JarvisPrefs:
    address: str = "you"                          # "you" or "" = no name, no title
    wake_word: WakeWord = "hey_auri"
    voice: VoiceName = "daniel"
    welcome_routine: dict[str, Any] | None = None  # None = no "Üdv itthon" routine
    answered: tuple[PrefKey, ...] = ()            # which onboarding questions the user answered
    onboarded: bool = False                       # True once all 4 are answered (or skipped)


@dataclass(frozen=True)
class UserContext:
    tier: Tier
    user_id: str | None = None
    display_name: str | None = None
    prefs: JarvisPrefs = field(default_factory=JarvisPrefs)
    profile: dict[str, Any] = field(default_factory=dict)  # Supabase `profiles` row: name, about, tone, interests…


GUEST = UserContext(tier="guest")  # guest defaults: "you" · hey_auri · daniel · no routine


# ── Ears (AI-1): capture + wake + VAD + STT ──────────────────────────────────
WakeSource = Literal["hotkey", "wakeword", "clap2", "clap3", "hud", "followup"]


@dataclass(frozen=True)
class WakeEvent:
    source: WakeSource
    word: WakeWord | None = None
    confidence: float = 1.0
    t: float = field(default_factory=time.monotonic)


@dataclass(frozen=True)
class Transcript:
    raw: str            # engine output
    text: str           # lexicon-corrected (what the Mind sees)
    lang: str           # "hu" | "en" | ...
    confidence: float
    engine: str         # "parakeet" | "whisper" | "text"
    speech_ms: int      # length of captured speech
    stt_ms: int         # transcription time


class Ears(Protocol):
    def start(self, on_wake: Callable[[WakeEvent], None]) -> None: ...
    def stop(self) -> None: ...
    def set_wake_word(self, word: WakeWord) -> None: ...
    def set_suppressed(self, on: bool) -> None: ...  # e.g. while Auri speaks (half duplex)

    async def listen(
        self, *, max_s: float = 15.0, accurate: bool = False, start_timeout_s: float = 4.0
    ) -> Transcript | None: ...
    # Waits for speech (VAD), captures until end-of-speech, transcribes.
    # None = no speech within start_timeout_s, or cancelled.

    @property
    def level(self) -> float: ...  # current mic RMS (HUD)


# ── Mouth (AI-1): TTS + playback ─────────────────────────────────────────────
class Mouth(Protocol):
    async def say(self, text: str, *, signature: bool = False) -> None: ...
    # signature=True: fixed/characteristic phrase → premium voice + permanent cache

    async def say_stream(self, chunks: AsyncIterator[str]) -> None: ...
    # Raw LLM deltas in; Mouth splits into sentences, cleans, synthesizes, plays in order.

    async def play_sample(self, voice: VoiceName) -> None: ...  # onboarding question 3
    def stop(self) -> None: ...                                  # barge-in: silence now
    def set_voice(self, voice: VoiceName) -> None: ...

    @property
    def speaking(self) -> bool: ...

    @property
    def out_level(self) -> float: ...


# ── Mind (AI-2): LLM + fast-path + tools + memory + onboarding ───────────────
Trigger = Literal["clap2", "clap3", "login", "timer", "hud_button"]


@dataclass(frozen=True)
class TurnRequest:
    turn_id: int
    user: UserContext
    channel: Literal["voice", "hud_text", "trigger"]
    text: str = ""                     # empty on the "trigger" channel
    transcript: Transcript | None = None
    trigger: Trigger | None = None
    wake: WakeEvent | None = None


class Mind(Protocol):
    def handle(self, req: TurnRequest, emit: Emit) -> AsyncIterator[str]: ...
    # Async generator of text deltas to speak (may yield nothing).
    # Side information via emit(): route, tool, reply.delta, reply.done,
    # mind.expects_reply, prefs.proposed, onboarding, voice.sample, say, proposal.

    async def on_identity_change(self, user: UserContext) -> None: ...
    async def on_hud_event(self, ev: Event, user: UserContext) -> None: ...  # e.g. proposal.answer
    async def idle_tick(self, idle_s: float, user: UserContext) -> None: ...  # dream phase
    async def warmup(self) -> None: ...


# ── Factories (each AI exports exactly these; AI-3 wires them) ───────────────
#   auri_jarvis.audio.create_ears(cfg: dict, emit: Emit) -> Ears      [AI-1]
#   auri_jarvis.tts.create_mouth(cfg: dict, emit: Emit) -> Mouth      [AI-1]
#   auri_jarvis.mind.create_mind(cfg: dict, emit: Emit) -> Mind       [AI-2]
#   cfg = merged config dict (jarvis.yaml + audio.yaml + mind.yaml + .env), see config.py
