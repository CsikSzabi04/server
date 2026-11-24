"""Wake-word engines (spec 5.1). All share one tiny interface:

  engine.feed(frame16k_float32_1280) -> float | None   # confidence when the word was heard
  engine.reset()

KwsWake   — sherpa-onnx open-vocabulary keyword spotter (zipformer, ~3 M params). NO training:
            keywords are BPE token strings (precomputed in config/audio.yaml, so no
            sentencepiece at runtime). Used for "Hey Auri" v1/A and as a "Hey Jarvis" fallback.
OwwWake   — openWakeWord pre-trained model ("hey_jarvis"; later our own "hey_auri" v2).
            ⚠️ pre-trained oWW models are CC BY-NC-SA 4.0 (non-commercial).
SttWake   — "Hey Auri" v1/B: Silero segments → Parakeet on the first ≤ 2.5 s → phonetic
            fuzzy match. Fallback only (measured ~3/5 on synthetic speech).
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Iterable
from pathlib import Path

import numpy as np

log = logging.getLogger("auri.voice.wake")


class KwsWake:
    def __init__(
        self,
        model_dir: Path,
        keywords: Iterable[str],
        keywords_file: Path,
        *,
        threshold: float = 0.25,
        score: float = 1.0,
        threads: int = 1,
        label: str = "WAKE",
    ) -> None:
        import sherpa_onnx

        d = Path(model_dir)
        pick = lambda stem: str(next(d.glob(f"{stem}-*.int8.onnx")))  # noqa: E731
        keywords_file.parent.mkdir(parents=True, exist_ok=True)
        keywords_file.write_text("".join(f"{k.strip()} @{label}\n" for k in keywords if k.strip()), "utf-8")
        self._kws = sherpa_onnx.KeywordSpotter(
            tokens=str(d / "tokens.txt"),
            encoder=pick("encoder"),
            decoder=pick("decoder"),
            joiner=pick("joiner"),
            keywords_file=str(keywords_file),
            num_threads=threads,
            keywords_score=score,
            keywords_threshold=threshold,
            num_trailing_blanks=1,
            provider="cpu",
        )
        self._stream = self._kws.create_stream()

    def feed(self, frame: np.ndarray) -> float | None:
        self._stream.accept_waveform(16_000, frame)
        hit = None
        while self._kws.is_ready(self._stream):
            self._kws.decode_stream(self._stream)
            if self._kws.get_result(self._stream):
                hit = 1.0
                self._kws.reset_stream(self._stream)
        return hit

    def reset(self) -> None:
        self._stream = self._kws.create_stream()


class OwwWake:
    def __init__(self, model: Path, melspec: Path, embedding: Path, *, threshold: float = 0.5) -> None:
        from openwakeword.model import Model

        self._m = Model(
            wakeword_models=[str(model)],
            inference_framework="onnx",
            melspec_model_path=str(melspec),
            embedding_model_path=str(embedding),
        )
        self._key = next(iter(self._m.models))
        self.threshold = threshold

    def feed(self, frame: np.ndarray) -> float | None:
        score = float(self._m.predict((np.clip(frame, -1, 1) * 32767).astype(np.int16))[self._key])
        return score if score >= self.threshold else None

    def reset(self) -> None:
        self._m.reset()


# ── STT-based wake (fallback) ───────────────────────────────────────────────
# Measured with Parakeet on Hungarian voices (2026-11-20): "Auri" comes out as Auri, Audi, Oli,
# Uri/úri/óri, Juri, "ja Uri", Aori, Ori — and glued to the greeting: "Helyeúri", "Hely, óri".
_GREETING = {"hey", "hei", "hej", "he", "hé", "hi", "hay", "ej", "eh", "hely", "helye", "helló", "hello", "szia"}
_AURI = re.compile(r"^h?(a|o)u?w?r+(i|y|ee|ie)$")  # canonical spellings: auri, ori, owry, hauri…
_FILLER = {"ja", "a"}  # "Hei ja Uri"


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _phonetic(word: str) -> str:
    """Rough Hungarian/English sound-alike key: Auri, Ori, Óri, Úri, Juri, Owry → 'ori'."""
    w = _fold(word)
    w = re.sub(r"^[jh](?=[aeiouy])", "", w)
    for a, b in (("au", "o"), ("ao", "o"), ("ou", "o"), ("ow", "o"), ("u", "o"), ("y", "i"), ("ee", "i")):
        w = w.replace(a, b)
    return re.sub(r"(.)\1+", r"\1", w)


def _is_auri_name(word: str, *, after_greeting: bool) -> bool:
    if _AURI.match(_fold(word)) or _fold(word).startswith("auri"):
        return True
    if not after_greeting:  # without "hey" only the real name counts (keeps false wakes low)
        return False
    from rapidfuzz.distance import Levenshtein

    key = _phonetic(word)
    return 2 <= len(key) <= 5 and Levenshtein.distance(key, "ori") <= 1


def matches_hey_auri(transcript: str) -> bool:
    """Does an utterance START with "(hey) Auri" (incl. measured mishearings)? Pure function."""
    words = re.findall(r"[a-z]+", _fold(transcript))[:4]
    if not words:
        return False
    first = words[0]
    greetings = sorted({_fold(g) for g in _GREETING}, key=len, reverse=True)
    if first not in greetings:  # glued: "helyeuri", "heiauri", "helyorni"
        for g in greetings:
            if first.startswith(g) and len(first) > len(g) + 1 and _is_auri_name(first[len(g) :], after_greeting=True):
                return True
        return _is_auri_name(first, after_greeting=False)
    rest = words[1:]
    if rest and rest[0] in _FILLER and len(rest) > 1:
        rest = rest[1:]
    return bool(rest) and _is_auri_name(rest[0], after_greeting=True)


class SttWake:
    def __init__(self, stt, *, max_s: float = 2.5) -> None:
        from ..audio.vad import EndpointConfig, EndpointLogic, SileroVad

        self._stt = stt
        self._vad = SileroVad()
        self._cfg = EndpointConfig(start_ms=200, end_silence_ms=300, preroll_ms=250)
        self._logic_cls = EndpointLogic
        self._max_ms = int(max_s * 1000)
        self._logic = EndpointLogic(self._cfg, max_ms=self._max_ms)
        self._buf = np.zeros(0, np.float32)
        self.last_transcript = ""
        self._samples = 0  # stream position
        self._prev: tuple[int, str] | None = None  # (end sample, text) of the previous segment

    def feed(self, frame: np.ndarray) -> float | None:
        self._buf = np.concatenate([self._buf, frame])
        hit = None
        while len(self._buf) >= 512:
            chunk, self._buf = self._buf[:512], self._buf[512:]
            self._samples += 512
            utt = self._logic.feed(chunk, self._vad.prob(chunk))
            if utt is not None:
                self._logic = self._logic_cls(self._cfg, max_ms=self._max_ms)
                text, _ = self._stt.transcribe(utt.pcm)
                self.last_transcript = text
                # "Hé, … Auri!" — a pause after the greeting splits it into two segments:
                # also try the previous segment + this one if they were < 1 s apart.
                joined = None
                if self._prev is not None and self._samples - self._prev[0] - len(utt.pcm) < 16_000:
                    joined = f"{self._prev[1]} {text}"
                if matches_hey_auri(text) or (joined is not None and matches_hey_auri(joined)):
                    hit = 0.8
                    self._prev = None
                else:
                    self._prev = (self._samples, text)
        return hit

    def reset(self) -> None:
        self._logic = self._logic_cls(self._cfg, max_ms=self._max_ms)
        self._buf = np.zeros(0, np.float32)
        self._vad.reset()
        self._prev = None
