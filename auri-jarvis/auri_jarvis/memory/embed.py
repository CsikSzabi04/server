"""Embeddings via Ollama (`embeddinggemma`, short keep_alive) — AI-2, spec 5.8.

Optional by design: every call has a tight timeout and returns None on any problem, so
recall silently falls back to full-text search (FTS5) instead of slowing a voice turn.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
import numpy as np

log = logging.getLogger(__name__)


def to_blob(vec: np.ndarray) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


def from_blob(blob: bytes | None) -> np.ndarray | None:
    if not blob:
        return None
    return np.frombuffer(blob, dtype=np.float32)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0 or a.shape != b.shape:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class Embedder:
    def __init__(self, cfg: dict[str, Any] | None = None, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        cfg = cfg or {}
        self.base_url = str(cfg.get("base_url") or "http://127.0.0.1:11434").rstrip("/")
        self.model = str(cfg.get("embed_model") or "embeddinggemma")
        self.keep_alive = cfg.get("embed_keep_alive", "5m")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=httpx.Timeout(30.0, connect=2.0), transport=transport)
        self.available = True  # flips to False after a hard failure (model missing)

    async def embed(self, texts: list[str], *, timeout_s: float | None = None) -> list[np.ndarray] | None:
        if not texts or not self.available:
            return None
        try:
            r = await self._client.post(
                "/api/embed",
                json={"model": self.model, "input": texts, "keep_alive": self.keep_alive},
                timeout=timeout_s,
            )
            if r.status_code == 404:
                self.available = False
                log.warning("embed model %s missing — recall uses full-text search only", self.model)
                return None
            r.raise_for_status()
            vecs = r.json().get("embeddings") or []
            if len(vecs) != len(texts):
                return None
            return [np.asarray(v, dtype=np.float32) for v in vecs]
        except (httpx.HTTPError, ValueError) as e:
            log.info("embed failed (%s) — falling back to FTS", type(e).__name__)
            return None

    async def aclose(self) -> None:
        await self._client.aclose()
