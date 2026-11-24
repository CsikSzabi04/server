"""Audio input side (AI-1 VOICE). Contract factory: create_ears(cfg, emit) -> Ears."""

from __future__ import annotations

from typing import Any


def create_ears(cfg: dict[str, Any], emit):  # -> contracts.Ears
    """Build Auri's ears. Call `.start(on_wake)` to open the microphone."""
    from .ears import AuriEars

    return AuriEars(cfg, emit)
