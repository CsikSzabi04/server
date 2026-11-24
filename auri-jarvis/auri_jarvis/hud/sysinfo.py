"""auri_jarvis.hud.sysinfo — data for the HUD: monitors, app list, system stats (owner: AI-3).

Read-only helpers. `apps.yaml` belongs to AI-2 — we only READ the ids + display names for the
"Üdv itthon" routine editor (`options` event).
"""

from __future__ import annotations

import ctypes
import logging
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx
import yaml

log = logging.getLogger(__name__)


def monitors() -> list[dict[str, Any]]:
    """Monitors left→right, numbered 1.. (the user's layout: 1 = left, 2 = middle, 3 = right)."""
    if sys.platform != "win32":
        return []
    from ctypes import wintypes

    rects: list[tuple[int, int, int, int, bool]] = []
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", wintypes.RECT),
            ("rcWork", wintypes.RECT),
            ("dwFlags", wintypes.DWORD),
        ]

    proc_t = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

    def cb(hmon, _hdc, _rect, _lp):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            r = mi.rcMonitor
            rects.append((r.left, r.top, r.right - r.left, r.bottom - r.top, bool(mi.dwFlags & 1)))
        return 1

    try:
        user32.EnumDisplayMonitors(None, None, proc_t(cb), 0)
    except OSError as e:
        log.warning("monitors: %s", e)
        return []
    rects.sort(key=lambda r: (r[0], r[1]))
    names = {1: "bal", 2: "közép", 3: "jobb"} if len(rects) == 3 else {}
    return [
        {"n": i, "name": names.get(i, f"{i}."), "x": x, "y": y, "width": w, "height": h, "primary": p}
        for i, (x, y, w, h, p) in enumerate(rects, start=1)
    ]


def app_options(cfg: Mapping[str, Any]) -> list[dict[str, str]]:
    """[{id, name}] from AI-2's config/apps.yaml (read-only). Missing file → []."""
    path = Path(cfg["paths"]["config_dir"]) / "apps.yaml"
    if not path.is_file():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        log.warning("apps.yaml unreadable: %s", e)
        return []
    out = []
    apps = data.get("apps") if isinstance(data, Mapping) else None
    if isinstance(apps, Mapping):
        for app_id, spec in apps.items():
            name = None
            if isinstance(spec, Mapping):
                name = spec.get("name") or spec.get("display_name")
                if not name and isinstance(spec.get("aliases"), list) and spec["aliases"]:
                    name = str(spec["aliases"][0])
            out.append({"id": str(app_id), "name": str(name or app_id)})
    return out


async def stats(ollama_base: str, client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    import psutil

    out: dict[str, Any] = {
        "cpu": round(psutil.cpu_percent(interval=None)),
        "ram": round(psutil.virtual_memory().percent),
        "ollama": "offline",
    }
    try:
        own = client is None
        c = client or httpx.AsyncClient(timeout=1.5)
        try:
            r = await c.get(f"{ollama_base.rstrip('/')}/api/ps")
            r.raise_for_status()
            models = [m.get("name", "?") for m in r.json().get("models", [])]
            out["ollama"] = (", ".join(models) + " loaded") if models else "idle"
        finally:
            if own:
                await c.aclose()
    except Exception:
        pass
    return out
