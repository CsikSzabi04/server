"""auri_jarvis.tray — system tray icon (pystray) (owner: AI-3, spec 5.9 / M4).

The dot's colour follows the daemon: idle cyan · listening light blue · thinking/acting orange ·
speaking bright cyan · muted grey · error red (warm-up failed or the HUD/daemon reported an
error in the last 30 s). Menu: Hallgatás (push-to-talk) · Némítás ✓ · HUD megnyitása · Kilépés.

pystray runs its own message loop on a background thread; every menu action is handed back to
the asyncio loop with `call_soon_threadsafe` (the orchestrator is loop-only).
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from PIL import Image, ImageDraw

from .bus import Bus
from .contracts import Event, WakeEvent

log = logging.getLogger(__name__)

COLORS: dict[str, tuple[int, int, int]] = {
    "idle": (31, 229, 255),
    "listening": (53, 200, 232),
    "transcribing": (255, 157, 47),
    "thinking": (255, 157, 47),
    "acting": (255, 157, 47),
    "speaking": (120, 245, 255),
    "muted": (110, 120, 130),
    "error": (255, 77, 77),
    "loading": (170, 140, 255),
}
ERROR_HOLD_S = 30.0


def make_icon(color: tuple[int, int, int], size: int = 64) -> Image.Image:
    """A HUD-style ring + core in the state colour (transparent background)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = size // 16
    d.ellipse((m, m, size - m, size - m), outline=(*color, 255), width=max(2, size // 12))
    c = size // 2
    r = size // 5
    d.ellipse((c - r, c - r, c + r, c + r), fill=(*color, 255))
    return img


class Tray:
    def __init__(
        self,
        bus: Bus,
        orch: Any,
        loop: asyncio.AbstractEventLoop,
        *,
        on_quit: Callable[[], None],
        open_hud: Callable[[], None] | None = None,
        icon_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.bus, self.orch, self.loop = bus, orch, loop
        self.on_quit, self.open_hud = on_quit, open_hud
        self._icon_factory = icon_factory
        self.state = "idle"
        self.muted = False
        self.loading = True
        self.last_error = 0.0
        self.icon: Any = None
        self._thread: threading.Thread | None = None
        self._unsubs: list[Callable[[], None]] = []
        self._tasks: set[asyncio.Future[Any]] = set()

    # ── colour logic (pure, tested) ─────────────────────────────────────────
    def status(self) -> str:
        if time.monotonic() - self.last_error < ERROR_HOLD_S:
            return "error"
        if self.muted:
            return "muted"
        if self.loading and self.state == "idle":
            return "loading"
        return self.state

    def on_event(self, ev: Event) -> None:
        if ev.type == "state":
            self.state = str(ev.data.get("state", "idle"))
        elif ev.type == "mute":
            self.muted = bool(ev.data.get("on"))
        elif ev.type == "warmup":
            self.loading = ev.data.get("mind") == "loading" or ev.data.get("voice") == "loading"
            if "error" in (ev.data.get("mind"), ev.data.get("voice")):
                self.last_error = time.monotonic()
        elif ev.type == "error":
            self.last_error = time.monotonic()
        self.refresh()

    def refresh(self) -> None:
        if self.icon is None:
            return
        st = self.status()
        try:
            self.icon.icon = make_icon(COLORS.get(st, COLORS["idle"]))
            self.icon.title = f"Auri J.A.R.V.I.S. — {st}"
        except Exception:  # the tray must never take the daemon down
            log.debug("tray refresh failed", exc_info=True)

    # ── menu actions (tray thread → loop) ────────────────────────────────────
    def _call(self, fn: Callable[[], Any]) -> None:
        def run() -> None:
            res = fn()
            if asyncio.iscoroutine(res):
                task = asyncio.ensure_future(res)
                self._tasks.add(task)  # keep a reference until done (no GC mid-flight)
                task.add_done_callback(self._tasks.discard)

        self.loop.call_soon_threadsafe(run)

    def action_listen(self, *_: Any) -> None:
        self._call(lambda: self.orch.on_wake(WakeEvent(source="hud")))

    def action_mute(self, *_: Any) -> None:
        self._call(lambda: self.orch.set_muted(not self.muted))

    def action_hud(self, *_: Any) -> None:
        if self.open_hud is not None:
            self._call(self.open_hud)

    def action_quit(self, *_: Any) -> None:
        self.loop.call_soon_threadsafe(self.on_quit)

    # ── lifecycle ────────────────────────────────────────────────────────────
    def _build(self) -> Any:
        import pystray

        menu = pystray.Menu(
            pystray.MenuItem("Hallgatás", self.action_listen, default=True),
            pystray.MenuItem("Némítás", self.action_mute, checked=lambda _item: self.muted),
            pystray.MenuItem("HUD megnyitása", self.action_hud, enabled=self.open_hud is not None),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Kilépés", self.action_quit),
        )
        factory = self._icon_factory or pystray.Icon
        return factory("auri-jarvis", make_icon(COLORS["loading"]), "Auri J.A.R.V.I.S.", menu)

    def start(self) -> None:
        for typ in ("state", "mute", "warmup", "error"):
            self._unsubs.append(self.bus.on(typ, self.on_event))
        try:
            self.icon = self._build()
        except Exception as e:
            log.warning("tray unavailable: %s", e)
            self.icon = None
            return
        self._thread = threading.Thread(target=self._run, name="tray", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            self.icon.run()
        except Exception:
            log.exception("tray loop crashed")

    def stop(self) -> None:
        for off in self._unsubs:
            off()
        self._unsubs.clear()
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                log.debug("tray stop failed", exc_info=True)
        if self._thread is not None:
            self._thread.join(timeout=3)
