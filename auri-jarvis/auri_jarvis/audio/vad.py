"""Voice activity detection + end-of-speech ("endpointing").

`EndpointLogic` is the pure decision state machine (unit-testable with plain
probability sequences); `SileroVad` scores 32 ms chunks (Silero via pysilero-vad,
no torch); `Endpointer` glues them to the live 16 kHz frame stream.
"""

from __future__ import annotations

import queue
import threading
import time
from collections import deque
from dataclasses import dataclass, field

import numpy as np

SAMPLE_RATE = 16_000
CHUNK = 512  # Silero chunk at 16 kHz = 32 ms
CHUNK_MS = CHUNK * 1000 // SAMPLE_RATE  # 32


@dataclass
class EndpointConfig:
    threshold: float = 0.5  # prob ≥ this = speech
    neg_threshold: float = 0.35  # prob < this = silence (hysteresis in between)
    start_ms: int = 250  # this much speech (leaky count) starts an utterance
    end_silence_ms: int = 700  # this much continuous silence ends it
    preroll_ms: int = 300  # audio kept from before the start (first syllable)
    tail_ms: int = 200  # silence kept after the end

    @classmethod
    def from_cfg(cls, vad: dict | None) -> EndpointConfig:
        vad = vad or {}
        return cls(**{k: type(getattr(cls, k))(vad[k]) for k in cls.__dataclass_fields__ if k in vad})


@dataclass
class Utterance:
    pcm: np.ndarray
    reason: str  # "silence" | "max_len"
    speech_ms: int


@dataclass
class EndpointLogic:
    """Feed (chunk, prob) pairs; returns an Utterance when one is complete."""

    cfg: EndpointConfig = field(default_factory=EndpointConfig)
    max_ms: int = 15_000

    def __post_init__(self) -> None:
        self._pre: deque[np.ndarray] = deque(maxlen=max(1, self.cfg.preroll_ms // CHUNK_MS + 1))
        self._started = False
        self._score = 0  # leaky speech counter (ms) before the start
        self._silence = 0  # continuous silence (ms) after the start
        self._chunks: list[np.ndarray] = []
        self._ms = 0

    @property
    def started(self) -> bool:
        return self._started

    def feed(self, chunk: np.ndarray, prob: float) -> Utterance | None:
        if not self._started:
            self._pre.append(chunk)
            self._score = self._score + CHUNK_MS if prob >= self.cfg.threshold else max(0, self._score - CHUNK_MS // 2)
            if self._score >= self.cfg.start_ms:
                self._started = True
                self._chunks = list(self._pre)
                self._ms = len(self._chunks) * CHUNK_MS
            return None
        self._chunks.append(chunk)
        self._ms += CHUNK_MS
        self._silence = self._silence + CHUNK_MS if prob < self.cfg.neg_threshold else 0
        if self._silence >= self.cfg.end_silence_ms:
            drop = max(0, (self._silence - self.cfg.tail_ms) // CHUNK_MS)
            return self._finish("silence", drop)
        if self._ms >= self.max_ms:
            return self._finish("max_len", 0)
        return None

    def _finish(self, reason: str, drop_tail_chunks: int) -> Utterance:
        chunks = self._chunks[: len(self._chunks) - drop_tail_chunks] if drop_tail_chunks else self._chunks
        pcm = np.concatenate(chunks) if chunks else np.zeros(0, np.float32)
        return Utterance(pcm=pcm, reason=reason, speech_ms=len(pcm) * 1000 // SAMPLE_RATE)


class SileroVad:
    """Silero speech probability for 512-sample chunks (pysilero-vad; no torch)."""

    def __init__(self) -> None:
        from pysilero_vad import SileroVoiceActivityDetector

        self._det = SileroVoiceActivityDetector()
        assert self._det.chunk_samples() == CHUNK

    def reset(self) -> None:
        self._det.reset()

    def prob(self, chunk: np.ndarray) -> float:
        pcm16 = (np.clip(chunk, -1.0, 1.0) * 32767).astype(np.int16)
        return float(self._det(pcm16.tobytes()))


class Endpointer:
    """Capture one utterance from a live frame stream (blocking; run in a worker thread)."""

    def __init__(self, cfg: EndpointConfig, vad: SileroVad | None = None) -> None:
        self.cfg = cfg
        self.vad = vad or SileroVad()

    def capture(
        self, subscribe, *, max_s: float, start_timeout_s: float, cancel: threading.Event, history: float = 0.0, capture=None
    ) -> Utterance | None:
        """`subscribe(cb) -> unsubscribe` delivers 16 kHz frames (e.g. AudioCapture.subscribe).
        With `history` > 0 and an AudioCapture, the last `history` seconds are processed first
        (atomically joined to the live stream) — a command spoken right after the wake word."""
        frames: queue.Queue[np.ndarray] = queue.Queue()
        if history > 0 and capture is not None:
            past, unsubscribe = capture.subscribe_with_history(frames.put, history)
        else:
            past, unsubscribe = np.zeros(0, np.float32), subscribe(frames.put)
        self.vad.reset()
        logic = EndpointLogic(self.cfg, max_ms=int(max_s * 1000))
        buf = past.astype(np.float32, copy=False)
        deadline = time.monotonic() + start_timeout_s

        def drain() -> Utterance | None:
            nonlocal buf
            while len(buf) >= CHUNK:
                chunk, buf = buf[:CHUNK], buf[CHUNK:]
                done = logic.feed(chunk, self.vad.prob(chunk))
                if done is not None:
                    return done
            return None

        try:
            done = drain()  # the history (if any) is processed right away
            if done is not None:
                return done
            while not cancel.is_set():
                if not logic.started and time.monotonic() > deadline:
                    return None  # nobody spoke
                try:
                    frame = frames.get(timeout=0.1)
                except queue.Empty:
                    continue
                buf = np.concatenate([buf, frame])
                done = drain()
                if done is not None:
                    return done
            return None  # cancelled
        finally:
            unsubscribe()
