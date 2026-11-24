"""auri_jarvis.hud.window — open the HUD as a Chrome app window on monitor 3 (owner: AI-3).

A separate Chrome profile (`data/body/chrome-hud`) makes the position/size flags stick (an
already running Chrome would otherwise ignore them) and keeps the HUD's storage apart from
the user's normal browser.
"""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..config import data_path, get
from .sysinfo import monitors

log = logging.getLogger(__name__)


def chrome_args(cfg: Mapping[str, Any], url: str) -> list[str] | None:
    chrome = get(cfg, "hud.chrome_path")
    if not chrome or not Path(chrome).is_file():
        log.warning("HUD window: Chrome not found (%s)", chrome)
        return None
    win = get(cfg, "hud.window", {}) or {}
    x, y = int(win.get("x", 1920)), int(win.get("y", 209))
    w, h = int(win.get("width", 1152)), int(win.get("height", 864))
    want = int(win.get("monitor", 3))
    mons = monitors()
    if mons:  # follow the real layout if it differs from the config
        m = next((m for m in mons if m["n"] == want), mons[-1])
        x, y, w, h = m["x"], m["y"], m["width"], m["height"]
    profile = data_path(cfg, "body", "chrome-hud")
    profile.mkdir(parents=True, exist_ok=True)
    return [
        str(chrome),
        f"--app={url}",
        f"--user-data-dir={profile}",
        f"--window-position={x},{y}",
        f"--window-size={w},{h}",
        "--no-first-run",
        "--no-default-browser-check",
    ]


def open_hud_window(cfg: Mapping[str, Any], url: str) -> subprocess.Popen[bytes] | None:
    args = chrome_args(cfg, url)
    if args is None:
        return None
    try:
        return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    except OSError as e:
        log.warning("HUD window: cannot start Chrome: %s", e)
        return None
