"""ElevenLabs premium voice (spec 5.7) — streamed raw PCM at 22.05 kHz (= the player's rate).

Only the TEXT to be spoken is sent (never microphone audio). The key comes from .env
(cfg["env"]["ELEVENLABS_API_KEY"], a masked Secret). Measured with this key (2026-11-20):
flash v2.5 ≈ 0.4 credits/character; the key has no user_read / voices_read permission, so
the remaining quota cannot be queried — usage is booked locally (see credits.py).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

import numpy as np

log = logging.getLogger("auri.voice.elevenlabs")

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"


class ElevenLabsError(RuntimeError):
    pass


class ElevenLabsTts:
    def __init__(
        self,
        api_key: str,
        voices: dict[str, str],
        *,
        model: str = "eleven_flash_v2_5",
        rate: int = 22_050,
        first_byte_timeout_s: float = 2.0,
        client=None,
    ) -> None:
        import httpx

        self._key = str(api_key)
        self.voices = dict(voices)
        self.model = model
        self.rate = rate
        self._timeout = httpx.Timeout(connect=3.0, read=first_byte_timeout_s, write=5.0, pool=3.0)
        self._client = client or httpx.Client()
        self.last_cost = 0

    def has_voice(self, voice: str) -> bool:
        return bool(self._key) and voice in self.voices

    def synthesize(self, text: str, voice: str, lang: str = "hu") -> Iterator[tuple[np.ndarray, int]]:
        """Yield float32 PCM pieces as they stream in. Raises ElevenLabsError on any failure."""
        import httpx

        body = {"text": text, "model_id": self.model, "language_code": lang}
        try:
            with self._client.stream(
                "POST",
                API.format(voice_id=self.voices[voice]),
                params={"output_format": f"pcm_{self.rate}"},
                headers={"xi-api-key": self._key, "Content-Type": "application/json"},
                json=body,
                timeout=self._timeout,
            ) as r:
                if r.status_code != 200:
                    detail = r.read().decode("utf-8", "replace")[:200]
                    raise ElevenLabsError(f"HTTP {r.status_code}: {detail}")
                self.last_cost = int(r.headers.get("character-cost") or 0)
                leftover = b""
                for chunk in r.iter_bytes(4096):
                    data = leftover + chunk
                    n = len(data) // 2 * 2
                    leftover = data[n:]
                    if n:
                        yield np.frombuffer(data[:n], dtype="<i2").astype(np.float32) / 32768.0, self.rate
        except httpx.HTTPError as e:  # timeout, DNS, connection reset … → caller falls back to Piper
            raise ElevenLabsError(type(e).__name__) from e
