"""OS side effects behind one interface (AI-2). Tools never touch Win32/COM directly, so
unit tests run with `RecordingPlatform` (no real app, window, volume or lock — rule 8).

The real implementation is `platform_win.WindowsPlatform` (ctypes + pycaw), created by
`default_platform()` only on Windows.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

MediaAction = Literal["play_pause", "next", "previous", "stop"]
WindowMode = Literal["normal", "maximized", "fullscreen"]


class Platform(Protocol):
    def start_app(self, path: str, args: list[str]) -> None: ...
    def open_url(self, url: str, *, browser_path: str | None, app_window: bool) -> None: ...
    def place_window(self, exe_name: str, monitor: int, mode: WindowMode, *, wait_s: float) -> bool: ...
    def close_app(self, exe_name: str) -> int: ...  # number of windows asked to close
    def is_running(self, exe_name: str) -> bool: ...
    def media_key(self, action: MediaAction) -> None: ...
    def get_volume(self) -> tuple[int, bool]: ...  # (0..100, muted)
    def set_volume(self, level: int | None = None, mute: bool | None = None) -> tuple[int, bool]: ...
    def lock(self) -> None: ...
    def sleep(self) -> None: ...
    def clipboard_text(self) -> str | None: ...
    def monitor_count(self) -> int: ...
    def screenshot_png(self, monitor: int, max_width: int) -> bytes | None: ...  # never written to disk


@dataclass
class RecordingPlatform:
    """In-memory platform for tests / dry runs: records every call, performs nothing."""

    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    volume: int = 40
    muted: bool = False
    running: set[str] = field(default_factory=set)
    clipboard: str | None = None
    monitors: int = 3
    window_found: bool = True

    def _rec(self, name: str, **kw: Any) -> None:
        self.calls.append((name, kw))

    def names(self) -> list[str]:
        return [c[0] for c in self.calls]

    def start_app(self, path: str, args: list[str]) -> None:
        self._rec("start_app", path=path, args=list(args))

    def open_url(self, url: str, *, browser_path: str | None, app_window: bool) -> None:
        self._rec("open_url", url=url, browser_path=browser_path, app_window=app_window)

    def place_window(self, exe_name: str, monitor: int, mode: WindowMode, *, wait_s: float) -> bool:
        self._rec("place_window", exe_name=exe_name, monitor=monitor, mode=mode)
        return self.window_found

    def close_app(self, exe_name: str) -> int:
        self._rec("close_app", exe_name=exe_name)
        return 1 if exe_name.lower() in {r.lower() for r in self.running} else 0

    def is_running(self, exe_name: str) -> bool:
        return exe_name.lower() in {r.lower() for r in self.running}

    def media_key(self, action: MediaAction) -> None:
        self._rec("media_key", action=action)

    def get_volume(self) -> tuple[int, bool]:
        return self.volume, self.muted

    def set_volume(self, level: int | None = None, mute: bool | None = None) -> tuple[int, bool]:
        self._rec("set_volume", level=level, mute=mute)
        if level is not None:
            self.volume = max(0, min(100, level))
        if mute is not None:
            self.muted = mute
        return self.volume, self.muted

    def lock(self) -> None:
        self._rec("lock")

    def sleep(self) -> None:
        self._rec("sleep")

    def clipboard_text(self) -> str | None:
        self._rec("clipboard_text")
        return self.clipboard

    def monitor_count(self) -> int:
        return self.monitors

    def screenshot_png(self, monitor: int, max_width: int) -> bytes | None:
        self._rec("screenshot_png", monitor=monitor, max_width=max_width)
        return b"\x89PNG\r\n\x1a\nFAKE"


def default_platform() -> Platform:
    if sys.platform == "win32":
        from .platform_win import WindowsPlatform

        return WindowsPlatform()
    return RecordingPlatform()  # non-Windows: no side effects (development only)
