"""STT engines. Both take 16 kHz mono float32 numpy audio (never file paths: the
faster-whisper 1.2.1 + av 19 combination crashes on file decoding — measured).

  ParakeetStt  — default: nemo-parakeet-tdt-0.6b-v3 int8 via onnx-asr (~0.2 s per command)
  WhisperStt   — "accurate" mode: faster-whisper large-v3-turbo int8 (~7.5 s, near-perfect HU)
Models load lazily (and can be warmed up in a background thread).
"""

from __future__ import annotations

import logging
import threading
import time

import numpy as np

from .lang import guess_lang

log = logging.getLogger("auri.voice.stt")


class ParakeetStt:
    name = "parakeet"

    def __init__(self, model: str = "nemo-parakeet-tdt-0.6b-v3", quantization: str | None = "int8") -> None:
        self._model_name, self._quant = model, quantization
        self._model = None
        self._lock = threading.Lock()

    def load(self) -> None:
        with self._lock:
            if self._model is None:
                import onnx_asr

                t = time.perf_counter()
                self._model = onnx_asr.load_model(self._model_name, quantization=self._quant)
                log.info("Parakeet loaded in %.1fs", time.perf_counter() - t)

    def transcribe(self, pcm: np.ndarray) -> tuple[str, str]:
        self.load()
        if len(pcm) < 1600:  # < 0.1 s — nothing to say
            return "", "hu"
        text = str(self._model.recognize(pcm.astype(np.float32), sample_rate=16_000)).strip()
        return text, guess_lang(text)


class WhisperStt:
    name = "whisper"

    def __init__(self, model: str = "large-v3-turbo", language: str | None = "hu", hotwords: str = "", threads: int = 6) -> None:
        # threads=6 = the Ryzen 5 5500's physical cores; the library default (fewer threads)
        # measured ~10–11.5 s instead of ~7.5 s per command.
        self._model_name, self._language, self._hotwords, self._threads = model, language, hotwords, threads
        self._model = None
        self._lock = threading.Lock()

    def load(self) -> None:
        with self._lock:
            if self._model is None:
                from faster_whisper import WhisperModel

                t = time.perf_counter()
                self._model = WhisperModel(self._model_name, device="cpu", compute_type="int8", cpu_threads=self._threads)
                log.info("Whisper %s loaded in %.1fs", self._model_name, time.perf_counter() - t)

    def transcribe(self, pcm: np.ndarray) -> tuple[str, str]:
        self.load()
        if len(pcm) < 1600:
            return "", self._language or "hu"
        segs, info = self._model.transcribe(
            pcm.astype(np.float32),
            language=self._language,
            beam_size=1,
            without_timestamps=True,
            initial_prompt=self._hotwords or None,
            vad_filter=False,
        )
        text = " ".join(s.text.strip() for s in segs).strip()
        return text, info.language or guess_lang(text)
