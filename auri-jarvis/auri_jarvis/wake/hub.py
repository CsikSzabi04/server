"""WakeHub — runs the automatic wake detectors (wake word + claps) on their own thread.

The capture worker only enqueues frames here, so a slow detector (STT-wake transcribes a
segment) never stalls the microphone. Suppression (Auri speaking / HUD mute) silences
automatic wakes but keeps the detectors fed, so their state stays aligned. The hotkey is
handled elsewhere and is never suppressed.
"""

from __future__ import annotations

import logging
import queue
import re
import threading
import time
import unicodedata
from collections.abc import Callable
from typing import Any

import numpy as np

from ..audio._paths import VOICE_DATA, resolve
from ..audio.clap import ClapConfig, ClapDetector
from .engines import _AURI, _GREETING, KwsWake, OwwWake, SttWake

log = logging.getLogger("auri.voice.wakehub")


def build_engine(word: str, wake_cfg: dict[str, Any], stt=None):
    """Pick the detector for `word` per config: `wake.engine` (oww | kws | stt) forces one;
    `auto` follows `wake.engine_order[word]` (measured per word — see config/audio.yaml)."""
    mode = str(wake_cfg.get("engine", "auto"))
    oww, kws = wake_cfg.get("oww") or {}, wake_cfg.get("kws") or {}
    oww_model = (oww.get("models") or {}).get(word)
    if mode == "auto":
        default = ["oww", "stt"] if word == "hey_auri" else ["oww", "kws"]
        order_names = list((wake_cfg.get("engine_order") or {}).get(word, default))
    else:
        order_names = [mode]

    def make_oww():
        return OwwWake(
            resolve(oww_model), resolve(oww["melspec"]), resolve(oww["embedding"]), threshold=float(oww.get("threshold", 0.5))
        )

    def make_kws():
        return KwsWake(
            resolve(kws["model_dir"]),
            (kws.get("keywords") or {})[word],
            VOICE_DATA / f"kws_{word}.txt",
            threshold=float(kws.get("threshold", 0.25)),
            score=float(kws.get("score", 1.0)),
            label=word.upper(),
        )

    for name in order_names:
        try:
            if name == "oww" and oww_model and resolve(oww_model).is_file():
                return make_oww()
            if name == "kws" and (kws.get("keywords") or {}).get(word):
                return make_kws()
            if name == "stt" and word == "hey_auri" and stt is not None:
                return SttWake(stt, max_s=float((wake_cfg.get("stt_wake") or {}).get("max_s", 2.5)))
        except Exception as e:  # missing model files, bad config …
            log.warning("wake engine %s for %s unavailable: %s", name, word, e)
    log.warning("no wake engine for %s — only the hotkey (and claps) will wake Auri", word)
    return None


_LEAD = re.compile(r"^\W*(?:(?:hey|hei|hej|hé|he|hi|hay)\W+)?(?:\w+)\W*", re.IGNORECASE)


def strip_wake_phrase(text: str) -> str:
    """'Hey Auri, hány óra van?' → 'hány óra van?' (only if it really starts with the wake phrase)."""
    m = _LEAD.match(text)
    if not m:
        return text
    words = [unicodedata.normalize("NFD", w.lower()) for w in re.findall(r"\w+", m.group(0))]
    words = ["".join(c for c in w if unicodedata.category(c) != "Mn") for w in words]
    name = words[-1]
    greeting_ok = len(words) == 1 or words[0] in {"hey", "hei", "hej", "he", "hi", "hay"} | set(_GREETING)
    if greeting_ok and (_AURI.match(name) or name == "jarvis"):
        rest = text[m.end() :]
        return rest[:1].upper() + rest[1:] if rest else rest
    return text


class WakeHub:
    def __init__(self, wake_cfg: dict[str, Any], on_detect: Callable[[str, str | None, float], None], stt=None) -> None:
        self._cfg = wake_cfg
        self._on_detect = on_detect  # (source, word, confidence)
        self._stt = stt
        self._q: queue.Queue[np.ndarray | None] = queue.Queue(maxsize=200)
        self._word = "hey_auri"
        self._engine = None
        self._engine_word: str | None = None
        clap_cfg = wake_cfg.get("clap") or {}
        self._clap = ClapDetector(ClapConfig.from_cfg(clap_cfg)) if clap_cfg.get("enabled", True) else None
        self.suppressed = False
        self._refractory = float(wake_cfg.get("refractory_s", 1.5))
        self._last_fire = 0.0
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="auri-wake", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._q.put(None)

    def set_word(self, word: str) -> None:
        with self._lock:
            self._word = word

    def feed(self, frame: np.ndarray) -> None:  # called on the capture thread — must be cheap
        try:
            self._q.put_nowait(frame)
        except queue.Full:
            pass

    @property
    def engine_name(self) -> str:
        return type(self._engine).__name__ if self._engine is not None else "none"

    def _run(self) -> None:
        while True:
            frame = self._q.get()
            if frame is None:
                return
            with self._lock:
                word = self._word
            if self._engine_word != word:  # (re)build lazily on the wake thread
                self._engine = build_engine(word, self._cfg, self._stt)
                self._engine_word = word
                log.info("wake word %s → %s", word, self.engine_name)
            try:
                conf = self._engine.feed(frame) if self._engine is not None else None
                clap = self._clap.feed(frame) if self._clap is not None else None
            except Exception:
                log.exception("wake detector failed")
                continue
            if self.suppressed:
                continue
            now = time.monotonic()
            if now - self._last_fire < self._refractory:
                continue
            if conf is not None:
                self._last_fire = now
                self._on_detect("wakeword", word, conf)
            elif clap is not None:
                self._last_fire = now
                self._on_detect(clap, None, 1.0)
