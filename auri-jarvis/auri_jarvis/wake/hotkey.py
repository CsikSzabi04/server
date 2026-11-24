"""Global push-to-talk hotkey (works even while Auri is speaking → barge-in)."""

from __future__ import annotations

import logging
from collections.abc import Callable

log = logging.getLogger("auri.voice.hotkey")


def to_pynput(combo: str) -> str:
    """'ctrl+alt+space' → '<ctrl>+<alt>+<space>' (single characters stay bare: 'ctrl+j')."""
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    return "+".join(p if len(p) == 1 else f"<{p}>" for p in parts)


class Hotkey:
    def __init__(self, combo: str, on_press: Callable[[], None]) -> None:
        self.combo = combo
        self._on_press = on_press
        self._listener = None

    def start(self) -> None:
        from pynput import keyboard

        try:
            self._listener = keyboard.GlobalHotKeys({to_pynput(self.combo): self._on_press})
            self._listener.start()
            log.info("Push-to-talk hotkey: %s", self.combo)
        except Exception as e:  # never let a bad hotkey string kill the ears
            log.warning("Hotkey %r unavailable: %s", self.combo, e)

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
