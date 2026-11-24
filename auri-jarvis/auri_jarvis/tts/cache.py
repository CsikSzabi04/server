"""TTS audio cache (spec 5.7): signature phrases are kept on disk forever (a premium phrase
costs credits only once); everything else lives in a small in-memory LRU."""

from __future__ import annotations

import hashlib
import threading
from collections import OrderedDict
from pathlib import Path

import numpy as np

Pieces = list[tuple[np.ndarray, int]]


def cache_key(engine: str, voice: str, model: str, text: str) -> str:
    return hashlib.sha256(f"{engine}|{voice}|{model}|{text}".encode()).hexdigest()[:32]


class TtsCache:
    def __init__(self, directory: Path, mem_items: int = 64) -> None:
        self.dir = Path(directory)
        self._mem: OrderedDict[str, Pieces] = OrderedDict()
        self._max = mem_items
        self._lock = threading.Lock()

    def get(self, key: str) -> Pieces | None:
        with self._lock:
            if key in self._mem:
                self._mem.move_to_end(key)
                return self._mem[key]
        path = self.dir / f"{key}.npz"
        if path.is_file():
            try:
                with np.load(path) as z:
                    pieces = [(z["pcm"].astype(np.float32), int(z["rate"]))]
            except (OSError, ValueError, KeyError):
                return None
            self._remember(key, pieces)
            return pieces
        return None

    def put(self, key: str, pieces: Pieces, *, persistent: bool) -> None:
        if not pieces:
            return
        self._remember(key, pieces)
        if persistent:
            rate = pieces[0][1]
            pcm = np.concatenate([p for p, _ in pieces]).astype(np.float32)
            self.dir.mkdir(parents=True, exist_ok=True)
            tmp = self.dir / f"{key}.tmp.npz"
            np.savez_compressed(tmp, pcm=pcm, rate=np.int32(rate))
            tmp.replace(self.dir / f"{key}.npz")

    def _remember(self, key: str, pieces: Pieces) -> None:
        with self._lock:
            self._mem[key] = pieces
            self._mem.move_to_end(key)
            while len(self._mem) > self._max:
                self._mem.popitem(last=False)
