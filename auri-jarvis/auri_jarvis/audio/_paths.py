"""Filesystem locations used by the VOICE zone (AI-1). No heavy imports here."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # .../auri-jarvis
VOICE_DATA = ROOT / "data" / "voice"  # AI-1's private data folder (gitignored)


def resolve(p: str | Path) -> Path:
    """Resolve a config path relative to the auri-jarvis project root."""
    path = Path(p).expanduser()
    return path if path.is_absolute() else ROOT / path
