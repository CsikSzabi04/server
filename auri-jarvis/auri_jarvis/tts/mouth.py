"""Auri's mouth — implements contracts.Mouth.

Pipeline:  LLM deltas → SentenceSplitter → clean_for_tts → TTS (thread) → AudioPlayer.
A reader task and a speaker task are decoupled by a queue, so the LLM stream keeps
flowing while a sentence is being synthesised, and sentence N+1 is synthesised while
sentence N plays. stop() (barge-in) bumps a generation counter → in-flight work is
abandoned and the player goes silent within one audio block.

Voices (spec 5.7): "daniel" / "george" = ElevenLabs premium, "piper" = local only.
`tts.mode`: premium = every sentence premium · hybrid = only signature phrases premium ·
local = never. Premium is used only with a key, within the monthly credit budget and while
the service answers; any failure → that sentence is spoken by local Piper (speech never fails).
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections.abc import AsyncIterator
from typing import Any

from ..audio._paths import VOICE_DATA, resolve
from ..audio.player import AudioPlayer
from ..stt.lang import guess_lang
from .cache import TtsCache, cache_key
from .credits import CreditLedger
from .piper_tts import PiperEngine
from .splitter import SentenceSplitter
from .textclean import clean_for_tts

log = logging.getLogger("auri.voice.mouth")

SAMPLE_TEXT = {
    "daniel": "Szia! Így szólok, ha engem választasz.",
    "george": "Szia! Így szólok, ha engem választasz.",
    "piper": "Szia! Ez a helyi, ingyenes hangom.",
}
_DEFAULT_VOICES = {"hu": "models/piper/hu_HU-imre-medium.onnx", "en": "models/piper/en_GB-alan-medium.onnx"}
_DEFAULT_EL_VOICES = {"daniel": "onwK4e9ZLuTAKqWW03F9", "george": "JBFqnCBsd6RMkjVDRZzb"}
# Short fixed phrases (acks) rendered once → they play with ~0 ms latency.
ACKS = ("Igen?", "Hallgatlak.", "Máris.", "Kész.", "Rendben.", "Nem értettem, megismételnéd?")
CIRCUIT_OPEN_S = 60.0  # after a premium failure, use Piper for a minute (offline → no repeated delays)


def _earcon_pcm(name: str = "wake"):
    """Two soft rising tones (~160 ms) — generated, no file, no credits."""
    import numpy as np

    rate, tones = 22_050, ((880.0, 0.07), (1320.0, 0.09)) if name == "wake" else ((660.0, 0.12),)
    parts = []
    for freq, dur in tones:
        t = np.arange(int(rate * dur)) / rate
        env = np.minimum(1.0, np.minimum(t, dur - t) / 0.01)  # 10 ms fade in/out → no clicks
        parts.append(0.22 * env * np.sin(2 * np.pi * freq * t))
    return np.concatenate(parts).astype(np.float32)


class AuriMouth:
    def __init__(self, cfg: dict[str, Any], emit=None, *, output=None, el_client=None, data_dir=None) -> None:
        tts = cfg.get("tts") or {}
        audio = cfg.get("audio") or {}
        env = cfg.get("env") or {}
        piper_cfg = tts.get("piper") or {}
        el_cfg = tts.get("elevenlabs") or {}
        self._emit = emit
        self._engine = PiperEngine(
            {
                "hu": resolve(piper_cfg.get("voice_hu", _DEFAULT_VOICES["hu"])),
                "en": resolve(piper_cfg.get("voice_en", _DEFAULT_VOICES["en"])),
            }
        )
        ducker = None
        if tts.get("duck_music", True) and output is None:
            from ..audio.ducking import Ducker

            ducker = Ducker(float(tts.get("duck_level", 0.3)))
        self._player = AudioPlayer(audio.get("output_device"), rate=22_050, emit=emit, ducker=ducker, output=output)
        self._voice: str = str(tts.get("default_voice", "daniel"))
        self._mode: str = str(tts.get("mode", "premium"))
        self._max_chars = int(tts.get("max_sentence_chars", 220))
        # premium layer (optional)
        self._el = None
        key = str(env.get("ELEVENLABS_API_KEY") or "")
        if key and self._mode != "local":
            from .elevenlabs import ElevenLabsTts

            voices = {**_DEFAULT_EL_VOICES, **(el_cfg.get("voices") or {})}
            if env.get("ELEVENLABS_VOICE_ID"):  # .env override for the default premium voice
                voices[self._voice if self._voice in voices else "daniel"] = str(env["ELEVENLABS_VOICE_ID"])
            self._el = ElevenLabsTts(
                key,
                voices,
                model=str(env.get("ELEVENLABS_MODEL_ID") or el_cfg.get("live_model", "eleven_flash_v2_5")),
                client=el_client,
                first_byte_timeout_s=float(el_cfg.get("first_byte_timeout_s", 2.0)),
            )
        data = resolve(data_dir) if data_dir is not None else VOICE_DATA  # tests use a temp dir
        self._ledger = CreditLedger(data / "credits.json", int(el_cfg.get("monthly_credit_budget", 2000)))
        self._cache = TtsCache(data / "tts_cache")
        self._circuit_open_until = 0.0
        self._gen = 0
        self._warned = False
        self.last_first_audio_ms: int | None = None  # for benchmarks / AI-3 timing
        self.last_engine: str = "piper"
        self._warm = threading.Event()

    # ── lifecycle ──────────────────────────────────────────────────────────
    def start(self) -> None:
        self._player.start()
        threading.Thread(target=self._warmup, name="auri-tts-warmup", daemon=True).start()

    def _warmup(self) -> None:
        try:
            s = self._engine.warmup(("hu",))
            for phrase in ACKS:  # premium acks cost credits once, then live on disk forever
                self._render(phrase, signature=True)
            log.info("TTS warm-up + %d acks done (piper %.2fs, voice %s)", len(ACKS), s, self._voice)
        except Exception as e:
            log.warning("TTS warm-up failed: %s", e)
        finally:
            self._warm.set()

    def wait_ready(self, timeout: float | None = None) -> bool:
        return self._warm.wait(timeout)

    # ── contract: Mouth ────────────────────────────────────────────────────
    async def say(self, text: str, *, signature: bool = False) -> None:
        if signature:  # fixed phrase: synthesise once, replay instantly afterwards
            gen, started = self._gen, time.perf_counter()
            pieces = await asyncio.to_thread(self._render, text, True)
            if gen != self._gen:
                return
            self.last_first_audio_ms = int((time.perf_counter() - started) * 1000)
            for pcm, rate in pieces:
                self._player.enqueue(pcm, rate)
            await self._player.wait_idle()
            return

        async def one() -> AsyncIterator[str]:
            yield text

        await self.say_stream(one())

    async def say_stream(self, chunks: AsyncIterator[str]) -> None:
        gen = self._gen
        started = time.perf_counter()
        self.last_first_audio_ms = None
        sentences: asyncio.Queue[str | None] = asyncio.Queue()
        splitter = SentenceSplitter(max_chars=self._max_chars)

        async def reader() -> None:
            try:
                async for delta in chunks:
                    if gen != self._gen:
                        break
                    for s in splitter.feed(delta):
                        await sentences.put(s)
                if gen == self._gen:
                    for s in splitter.flush():
                        await sentences.put(s)
            finally:
                await sentences.put(None)

        async def speaker() -> None:
            while True:
                s = await sentences.get()
                if s is None or gen != self._gen:
                    return
                await asyncio.to_thread(self._speak_sentence, s, gen, started)

        await asyncio.gather(reader(), speaker())
        if gen == self._gen:
            await self._player.wait_idle()

    async def earcon(self, name: str = "wake") -> None:
        """Short non-verbal 'I'm listening' sound (optional, not in the contract). Used after a
        spoken wake word: unlike "Igen?" the microphone cannot mistake it for words."""
        self._player.enqueue(_earcon_pcm(name), 22_050)
        await self._player.wait_idle()

    async def play_sample(self, voice: str) -> None:
        previous = self._voice
        self._voice = voice
        try:
            await self.say(SAMPLE_TEXT.get(voice, SAMPLE_TEXT["piper"]), signature=True)
        finally:
            self._voice = previous

    def stop(self) -> None:
        self._gen += 1
        self._player.stop()

    def set_voice(self, voice: str) -> None:
        self._voice = voice
        if voice in ("daniel", "george") and self._el is None and not self._warned:
            self._warned = True
            log.info("Premium voice %r selected but no ElevenLabs key / mode=local → local Piper.", voice)

    @property
    def speaking(self) -> bool:
        return self._player.speaking

    @property
    def out_level(self) -> float:
        return self._player.out_level

    # ── engine choice ──────────────────────────────────────────────────────
    def _use_premium(self, text: str, signature: bool) -> bool:
        if self._el is None or not self._el.has_voice(self._voice):
            return False
        if self._mode == "hybrid" and not signature:
            return False
        if time.monotonic() < self._circuit_open_until:
            return False
        return self._ledger.allows(text)

    def _key(self, engine: str, text: str, lang: str) -> str:
        if engine == "el":
            return cache_key("el", self._el.voices[self._voice], self._el.model, text)
        return cache_key("piper", lang, "medium", text)

    def _premium_failed(self, err: Exception) -> None:
        self._circuit_open_until = time.monotonic() + CIRCUIT_OPEN_S
        log.warning("ElevenLabs failed (%s) — local Piper for %ds", err, int(CIRCUIT_OPEN_S))
        self._emit_event("error", {"where": "tts.elevenlabs", "message": str(err)[:200]})

    def _book(self, cost: int) -> None:
        used = self._ledger.add(cost)
        self._emit_event("tts.credits", {"used_month": used, "budget": self._ledger.budget, "mode": self._mode})

    def _emit_event(self, type_: str, data: dict) -> None:
        if self._emit is None:
            return
        try:
            from ..contracts import Event

            self._emit(Event(type_, data))
        except Exception:
            pass

    # ── synthesis (worker threads) ─────────────────────────────────────────
    def _render(self, text: str, signature: bool = False) -> list:
        """Whole-phrase audio (cached; signature phrases persist on disk)."""
        lang = guess_lang(text)
        clean = clean_for_tts(text, lang)
        if self._use_premium(clean, signature):
            key = self._key("el", clean, lang)
            hit = self._cache.get(key)
            if hit is not None:
                self.last_engine = "elevenlabs(cache)"
                return hit
            try:
                pieces = list(self._el.synthesize(clean, self._voice, lang))
                self._book(self._el.last_cost)
                self._cache.put(key, pieces, persistent=signature)
                self.last_engine = "elevenlabs"
                return pieces
            except Exception as e:
                self._premium_failed(e)
        key = self._key("piper", clean, lang)
        hit = self._cache.get(key)
        if hit is None:
            hit = list(self._engine.synthesize(clean, lang))
            self._cache.put(key, hit, persistent=False)  # Piper is free + fast: memory only
        self.last_engine = "piper"
        return hit

    def _speak_sentence(self, sentence: str, gen: int, started: float) -> None:
        lang = guess_lang(sentence)
        text = clean_for_tts(sentence, lang)
        if not text:
            return

        def play(pieces_iter) -> list:
            got = []
            for pcm, rate in pieces_iter:
                if gen != self._gen:
                    return got  # barge-in happened
                if self.last_first_audio_ms is None:
                    self.last_first_audio_ms = int((time.perf_counter() - started) * 1000)
                self._player.enqueue(pcm, rate)
                got.append((pcm, rate))
            return got

        if self._use_premium(text, signature=False):
            key = self._key("el", text, lang)
            hit = self._cache.get(key)
            if hit is not None:
                self.last_engine = "elevenlabs(cache)"
                play(hit)
                return
            got: list = []
            try:
                got = play(self._el.synthesize(text, self._voice, lang))  # streamed: plays as it arrives
                self._book(self._el.last_cost)
                if gen == self._gen:
                    self._cache.put(key, got, persistent=False)
                self.last_engine = "elevenlabs"
                return
            except Exception as e:
                self._premium_failed(e)
                if got:  # part of the sentence was already spoken — don't repeat it
                    return
        try:
            self.last_engine = "piper"
            play(self._engine.synthesize(text, lang))
        except Exception as e:
            log.error("TTS failed for a sentence: %s", e)
            self._emit_event("error", {"where": "tts", "message": str(e)[:200]})
