"""Interruptible speech playback queue (barge-in: stop() silences within one block).

The output callback only copies queued samples. Optional ducking lowers other apps'
audio (music) while Auri speaks and restores it afterwards.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import deque

import numpy as np

log = logging.getLogger("auri.voice.player")

BLOCK = 1024  # ~46 ms at 22.05 kHz → stop() takes effect within one block
LEVEL_EVERY_S = 1 / 15  # HUD level events ~15 Hz


class AudioPlayer:
    def __init__(self, device: int | str | None = None, rate: int = 22_050, emit=None, ducker=None, output=None) -> None:
        self.device = None if device in (None, "", "default") else device
        self.rate = rate
        self._emit = emit
        self._ducker = ducker
        self._q: deque[np.ndarray] = deque()
        self._cur: np.ndarray | None = None
        self._lock = threading.Lock()
        self._busy = False
        self._level = 0.0
        self._last_level_emit = 0.0
        self._stream = None
        self._output = output  # test hook: callable(np.ndarray) instead of a sound device
        self._restore_timer: threading.Timer | None = None

    def start(self) -> None:
        if self._stream is not None or self._output is not None:
            return
        import sounddevice as sd

        self._stream = sd.OutputStream(
            device=self.device, samplerate=self.rate, channels=1, dtype="float32", blocksize=BLOCK, callback=self._callback
        )
        self._stream.start()

    def close(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    # ── queue ──────────────────────────────────────────────────────────────
    def enqueue(self, pcm: np.ndarray, rate: int) -> None:
        if rate != self.rate:
            import soxr

            pcm = soxr.resample(pcm, rate, self.rate).astype(np.float32)
        with self._lock:
            was_idle = not self._busy
            self._q.append(pcm.astype(np.float32, copy=False))
            self._busy = True
        if was_idle:
            self._on_speaking(True)
        if self._output is not None:  # synchronous test output
            self._drain_to_output()

    def stop(self) -> None:
        with self._lock:
            self._q.clear()
            self._cur = None
            was_busy, self._busy = self._busy, False
        self._level = 0.0
        if was_busy:
            self._on_speaking(False)

    @property
    def speaking(self) -> bool:
        return self._busy

    @property
    def out_level(self) -> float:
        return self._level

    async def wait_idle(self, poll_s: float = 0.02) -> None:
        while self._busy:  # noqa: ASYNC110 — set by the audio thread; asyncio.Event is not thread-safe
            await asyncio.sleep(poll_s)

    # ── audio thread ───────────────────────────────────────────────────────
    def _next_block(self, n: int) -> np.ndarray:
        out = np.zeros(n, dtype=np.float32)
        filled = 0
        with self._lock:
            while filled < n:
                if self._cur is None or len(self._cur) == 0:
                    if not self._q:
                        break
                    self._cur = self._q.popleft()
                take = min(n - filled, len(self._cur))
                out[filled : filled + take] = self._cur[:take]
                self._cur = self._cur[take:]
                filled += take
            finished = self._busy and filled < n and not self._q and (self._cur is None or len(self._cur) == 0)
            if finished:
                self._busy = False
        self._level = float(np.sqrt(np.mean(np.square(out)))) if filled else 0.0
        self._maybe_emit_level()
        if finished:
            self._on_speaking(False)
        return out

    def _callback(self, outdata, frames, time_info, status) -> None:
        outdata[:, 0] = self._next_block(frames)

    def _drain_to_output(self) -> None:
        while self._busy:
            self._output(self._next_block(BLOCK))

    def _maybe_emit_level(self) -> None:
        now = time.monotonic()
        if self._emit is not None and now - self._last_level_emit >= LEVEL_EVERY_S:
            self._last_level_emit = now
            try:
                from ..contracts import Event  # AI-3's contract

                self._emit(Event("level", {"source": "out", "rms": round(self._level, 4)}))
            except Exception:
                pass

    def _on_speaking(self, on: bool) -> None:
        if self._ducker is None:
            return
        if self._restore_timer is not None:
            self._restore_timer.cancel()
            self._restore_timer = None
        if on:
            self._ducker.duck()
        else:  # small hangover so music doesn't "pump" between sentences
            self._restore_timer = threading.Timer(0.6, self._ducker.restore)
            self._restore_timer.daemon = True
            self._restore_timer.start()
