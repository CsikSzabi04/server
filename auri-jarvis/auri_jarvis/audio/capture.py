"""ONE shared 16 kHz mono microphone stream for every "ear" (wake word, clap, VAD, STT).

The PortAudio callback only copies samples into a queue (never any logic there), so a
busy CPU (LLM inference) cannot cause input overflows. A worker thread resamples if
needed, cuts 80 ms frames, keeps a ring buffer and fans the frames out to subscribers.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable

import numpy as np

SAMPLE_RATE = 16_000  # == contracts.SAMPLE_RATE
FRAME_SAMPLES = 1_280  # == contracts.FRAME_SAMPLES (80 ms)

log = logging.getLogger("auri.voice.capture")

FrameCallback = Callable[[np.ndarray], None]


class RingBuffer:
    """Fixed-size float32 ring of the most recent samples."""

    def __init__(self, seconds: float, rate: int = SAMPLE_RATE) -> None:
        self._buf = np.zeros(int(seconds * rate), dtype=np.float32)
        self._pos = 0
        self._filled = 0
        self._lock = threading.Lock()

    def write(self, x: np.ndarray) -> None:
        with self._lock:
            n, size = len(x), len(self._buf)
            if n >= size:
                self._buf[:] = x[-size:]
                self._pos, self._filled = 0, size
                return
            end = self._pos + n
            if end <= size:
                self._buf[self._pos : end] = x
            else:
                k = size - self._pos
                self._buf[self._pos :] = x[:k]
                self._buf[: n - k] = x[k:]
            self._pos = end % size
            self._filled = min(size, self._filled + n)

    def recent(self, n: int) -> np.ndarray:
        with self._lock:
            n = min(n, self._filled)
            start = (self._pos - n) % len(self._buf)
            if start + n <= len(self._buf):
                return self._buf[start : start + n].copy()
            return np.concatenate([self._buf[start:], self._buf[: (start + n) % len(self._buf)]])


class AudioCapture:
    """Microphone → 80 ms frames at 16 kHz → subscribers (implements the AudioSource idea)."""

    def __init__(self, device: int | None, *, ring_seconds: float = 10.0) -> None:
        self.device = device
        self._ring = RingBuffer(ring_seconds)
        self._subs: list[FrameCallback] = []
        self._subs_lock = threading.Lock()
        self._q: queue.Queue[np.ndarray | None] = queue.Queue(maxsize=500)
        self._stream = None
        self._worker: threading.Thread | None = None
        self._resampler = None
        self._frame_lock = threading.Lock()  # ring write + subscriber snapshot are atomic
        self._pending = np.zeros(0, dtype=np.float32)
        self._level = 0.0
        self.input_rate = SAMPLE_RATE
        self.last_frame_t = time.monotonic()  # watchdog: a dead microphone stops delivering

    # ── public API ──────────────────────────────────────────────────────────
    def start(self) -> None:
        if self._stream is not None:
            return
        self._open_stream()
        self._worker = threading.Thread(target=self._run, name="auri-capture", daemon=True)
        self._worker.start()
        self._stream.start()

    def reopen(self, device: int | None) -> None:
        """Re-open the input stream (device lost / changed) — subscribers and ring stay."""
        if self._stream is not None:
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self.device = device
        self._resampler = None
        self._open_stream()
        self.last_frame_t = time.monotonic()
        self._stream.start()

    def _open_stream(self) -> None:
        import sounddevice as sd

        try:  # MME and most drivers resample to 16 kHz for us
            self._stream = sd.InputStream(
                device=self.device,
                channels=1,
                dtype="float32",
                samplerate=SAMPLE_RATE,
                blocksize=FRAME_SAMPLES,
                callback=self._callback,
            )
            self.input_rate = SAMPLE_RATE
        except Exception as e:  # device refuses 16 kHz → native rate + our own resampler
            import soxr

            rate = int(sd.query_devices(self.device, "input")["default_samplerate"])
            log.info("16 kHz refused (%s) — capturing at %d Hz and resampling", e, rate)
            self._resampler = soxr.ResampleStream(rate, SAMPLE_RATE, 1, dtype="float32")
            self._stream = sd.InputStream(
                device=self.device,
                channels=1,
                dtype="float32",
                samplerate=rate,
                blocksize=int(rate * 0.08),
                callback=self._callback,
            )
            self.input_rate = rate

    def stop(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None
        self._q.put(None)
        if self._worker is not None:
            self._worker.join(timeout=2)
            self._worker = None

    def subscribe(self, cb: FrameCallback) -> Callable[[], None]:
        with self._subs_lock:
            self._subs.append(cb)

        def unsubscribe() -> None:
            with self._subs_lock:
                if cb in self._subs:
                    self._subs.remove(cb)

        return unsubscribe

    def subscribe_with_history(self, cb: FrameCallback, seconds: float) -> tuple[np.ndarray, Callable[[], None]]:
        """Atomically: the last `seconds` of audio + a subscription for everything after it
        (no gap, no duplicated frame). Used to catch a command spoken right after the wake word."""
        with self._frame_lock:
            history = self._ring.recent(int(max(0.0, seconds) * SAMPLE_RATE))
            unsubscribe = self.subscribe(cb)
        return history, unsubscribe

    def recent(self, seconds: float) -> np.ndarray:
        return self._ring.recent(int(seconds * SAMPLE_RATE))

    @property
    def level(self) -> float:
        return self._level

    # ── internals ───────────────────────────────────────────────────────────
    def _callback(self, indata, frames, time_info, status) -> None:  # PortAudio thread
        if status:
            log.debug("input status: %s", status)
        try:
            self._q.put_nowait(indata[:, 0].copy())
        except queue.Full:
            pass  # drop rather than block the audio thread

    def push(self, samples: np.ndarray) -> None:
        """Feed 16 kHz samples directly (file sources and tests)."""
        self._q.put(np.asarray(samples, dtype=np.float32))

    def start_worker_only(self) -> None:
        """Start frame processing without a microphone (for push())."""
        if self._worker is None:
            self._worker = threading.Thread(target=self._run, name="auri-capture", daemon=True)
            self._worker.start()

    def _run(self) -> None:
        while True:
            chunk = self._q.get()
            self.last_frame_t = time.monotonic()
            if chunk is None:
                return
            if self._resampler is not None:
                chunk = self._resampler.resample_chunk(chunk)
            self._pending = np.concatenate([self._pending, chunk])
            while len(self._pending) >= FRAME_SAMPLES:
                frame, self._pending = self._pending[:FRAME_SAMPLES], self._pending[FRAME_SAMPLES:]
                with self._frame_lock:
                    self._ring.write(frame)
                    with self._subs_lock:
                        subs = list(self._subs)
                self._level = float(np.sqrt(np.mean(np.square(frame))))
                for cb in subs:
                    try:
                        cb(frame)
                    except Exception:  # one bad ear must not deafen the others
                        log.exception("frame subscriber failed")
