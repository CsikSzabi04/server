"""Piper TTS kept IN-PROCESS (models load once).

Measured on the target PC (Ryzen 5 5500): spawning piper.exe per sentence costs
0.7–2.3 s (it reloads the 63 MB model every time). In-process: the very first
synthesis is slow (~1.7 s, onnxruntime warm-up) — hence `warmup()` — after that
the first audio of a sentence is ready in ~60–90 ms.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import numpy as np

log = logging.getLogger("auri.voice.piper")


class PiperEngine:
    def __init__(self, voices: dict[str, Path]) -> None:
        self._paths = {lang: Path(p) for lang, p in voices.items() if p}
        self._voices: dict[str, object] = {}
        self._lock = threading.Lock()  # one synthesis at a time (onnxruntime session)

    def has(self, lang: str) -> bool:
        return lang in self._paths and self._paths[lang].is_file()

    def _voice(self, lang: str):
        if lang not in self._voices:
            from piper import PiperVoice

            path = self._paths.get(lang) if self.has(lang) else next((p for p in self._paths.values() if p.is_file()), None)
            if path is None:
                raise FileNotFoundError("No Piper voice model found — run the Piper voice download (spec §10).")
            t = time.perf_counter()
            self._voices[lang] = PiperVoice.load(path)
            log.info("Piper voice %s loaded in %.2fs", path.name, time.perf_counter() - t)
        return self._voices[lang]

    def warmup(self, langs: tuple[str, ...] = ("hu",)) -> float:
        """Load + run one tiny synthesis so the first real sentence is fast. Returns seconds."""
        t = time.perf_counter()
        for lang in langs:
            for _ in self.synthesize("Igen." if lang == "hu" else "Yes.", lang):
                pass
        return time.perf_counter() - t

    def synthesize(self, text: str, lang: str = "hu") -> Iterator[tuple[np.ndarray, int]]:
        """Yield (float32 mono audio, sample_rate) pieces for `text`."""
        with self._lock:
            voice = self._voice(lang)
            for chunk in voice.synthesize(text):
                pcm = np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                yield pcm, int(chunk.sample_rate)
