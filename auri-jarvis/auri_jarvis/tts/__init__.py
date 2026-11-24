"""Text-to-speech + playback (AI-1 VOICE). Contract factory: create_mouth(cfg, emit) -> Mouth."""

from __future__ import annotations

from typing import Any


def create_mouth(cfg: dict[str, Any], emit):  # -> contracts.Mouth
    """Build Auri's mouth (Piper in-process now; ElevenLabs premium layer in M4)."""
    from .mouth import AuriMouth

    mouth = AuriMouth(cfg, emit)
    mouth.start()
    return mouth
