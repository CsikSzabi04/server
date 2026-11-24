"""python -m auri_jarvis — daemon entry point (owner: AI-3).

python -m auri_jarvis              voice mode: real Ears/Mouth (AI-1) + Mind (AI-2) + HUD
python -m auri_jarvis --text       stdin/stdout instead of mic/speaker; real Mind if present,
                                   else EchoMind (--echo forces EchoMind)
python -m auri_jarvis --selftest   environment check (Ollama + models, mic, Piper voices,
                                   STT model, key *presence*, free port) — spends no credits
--no-hud                           don't start the HUD server
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import importlib
import logging
import logging.handlers
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import __version__
from .bus import Bus
from .config import ConfigError, data_path, get, install_log_redaction, load_config
from .contracts import Emit
from .fakes import EchoMind, FakeEars, FakeMouth
from .orchestrator import Orchestrator
from .timing import TimingLog

log = logging.getLogger("auri_jarvis")

FACTORIES = {
    "ears": ("auri_jarvis.audio", "create_ears", "AI-1"),
    "mouth": ("auri_jarvis.tts", "create_mouth", "AI-1"),
    "mind": ("auri_jarvis.mind", "create_mind", "AI-2"),
}


def _safe_console() -> None:
    """Never crash on a ✓ or an accented letter. A real Windows console already speaks Unicode;
    pipes/redirects default to cp1250 → switch those to UTF-8.
    pythonw.exe (the Start-menu/desktop shortcut) has no console: stdout/stderr are None, and any
    library that touches them (uvicorn's isatty(), tqdm progress bars) would crash the daemon
    silently → point them at os.devnull instead."""
    import os

    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115 — lives as long as the process
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if stream is None:
            continue
        with contextlib.suppress(AttributeError, ValueError, OSError):
            if not stream.isatty():
                stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
            elif stream is not sys.stdin:
                stream.reconfigure(errors="replace")  # type: ignore[union-attr]


def setup_logging(cfg: dict[str, Any], *, console_level: str | None = None) -> Path:
    level = str(console_level or get(cfg, "core.log_level", "INFO")).upper()
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for h in list(root.handlers):
        root.removeHandler(h)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S")
    if sys.stderr is not None:  # pythonw.exe (autostart) has no console
        console = logging.StreamHandler(sys.stderr)
        console.setLevel(level)
        console.setFormatter(fmt)
        root.addHandler(console)
    log_file = data_path(cfg, "body", "logs", "jarvis.log")
    try:
        fh = logging.handlers.RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
        root.addHandler(fh)
    except OSError as e:
        log.warning("file log disabled: %s", e)
    install_log_redaction()
    for noisy in ("httpx", "httpcore", "uvicorn.access", "asyncio", "comtypes"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return log_file


def load_factory(kind: str) -> Callable[[dict[str, Any], Emit], Any] | None:
    """Return the AI-1/AI-2 factory, or None if their package does not exist yet.
    An ImportError *inside* their package (e.g. a missing dependency) is re-raised."""
    module, name, _owner = FACTORIES[kind]
    try:
        mod = importlib.import_module(module)
    except ModuleNotFoundError as e:
        if e.name and (e.name == module or module.startswith(e.name + ".")):
            return None
        raise
    fn = getattr(mod, name, None)
    return fn if callable(fn) else None


def build_parts(cfg: dict[str, Any], emit: Emit, args: argparse.Namespace, on_eof: Callable[[], None]):
    notes: list[str] = []
    if args.text:
        ears: Any = FakeEars(on_eof=on_eof)
        mouth: Any = FakeMouth()
    else:
        missing = [k for k in ("ears", "mouth") if load_factory(k) is None]
        if missing:
            owners = ", ".join(f"{FACTORIES[k][0]}.{FACTORIES[k][1]} ({FACTORIES[k][2]})" for k in missing)
            raise SystemExit(f"Hangmód nem indítható: még nincs kész: {owners}. Próbáld: python -m auri_jarvis --text")
        ears = load_factory("ears")(cfg, emit)  # type: ignore[misc]
        mouth = load_factory("mouth")(cfg, emit)  # type: ignore[misc]
    mind_factory = None if args.echo else load_factory("mind")
    if mind_factory is None:
        if not args.text and not args.echo:
            raise SystemExit("Hangmód nem indítható: az auri_jarvis.mind.create_mind (AI-2) még nincs kész. Próbáld: --text")
        mind: Any = EchoMind()
        notes.append("EchoMind (visszhang + idő)" + ("" if args.echo else " — az AI-2 Mind még nincs kész"))
    else:
        mind = mind_factory(cfg, emit)
        notes.append("valódi Mind (AI-2)")
    return ears, mouth, mind, notes


def build_identity(cfg: dict[str, Any], bus: Bus) -> Any:
    try:
        from .identity.manager import IdentityManager
    except ImportError:
        return None
    return IdentityManager(cfg, emit=bus.emit)


async def wait_for_ollama(cfg: dict[str, Any], *, timeout_s: float | None = None, period_s: float = 2.0) -> None:
    """Spec 5.10: after an autostart Ollama may come up later — poll /api/tags with retries."""
    import httpx

    base = str(get(cfg, "llm.base_url", "http://127.0.0.1:11434")).rstrip("/")
    limit = float(timeout_s if timeout_s is not None else get(cfg, "core.ollama_wait_s", 60))
    deadline = asyncio.get_running_loop().time() + limit
    tries = 0
    async with httpx.AsyncClient(timeout=2.0) as client:
        while True:
            tries += 1
            try:
                (await client.get(f"{base}/api/tags")).raise_for_status()
                if tries > 1:
                    log.info("Ollama is up after %d tries", tries)
                return
            except httpx.HTTPError:
                if asyncio.get_running_loop().time() >= deadline:
                    raise RuntimeError(f"Az Ollama nem érhető el ({base}) {limit:.0f} s után sem.") from None
                await asyncio.sleep(period_s)


class SingleInstance:
    """Voice mode owns the microphone: a second daemon must not start (autostart + manual start).
    Windows named mutex in the user's session; elsewhere a no-op."""

    NAME = "Local\\AuriJarvisDaemon"

    def __init__(self) -> None:
        self.handle: int | None = None

    def acquire(self) -> bool:
        if sys.platform != "win32":
            return True
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        self.handle = kernel32.CreateMutexW(None, False, self.NAME)
        return bool(self.handle) and kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS

    def release(self) -> None:
        if self.handle and sys.platform == "win32":
            import ctypes

            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(self.handle))  # type: ignore[attr-defined]
            self.handle = None


async def _start_hud(cfg: dict[str, Any], bus: Bus, orch: Orchestrator, *, open_window: bool) -> Any:
    from .hud.server import HudServer

    hud = HudServer(cfg, bus, orch)
    try:
        await hud.start(open_window=open_window)
    except RuntimeError as e:
        log.error("%s — a daemon HUD nélkül fut tovább.", e)
        return None
    return hud


async def run(cfg: dict[str, Any], args: argparse.Namespace) -> int:
    loop = asyncio.get_running_loop()
    bus = Bus()
    bus.attach(loop)
    stop = asyncio.Event()

    def on_eof() -> None:
        loop.call_soon_threadsafe(stop.set)

    ears, mouth, mind, notes = build_parts(cfg, bus.emit, args, on_eof)
    identity = build_identity(cfg, bus)
    timing = TimingLog(data_path(cfg, "body", "timing.jsonl"))
    orch = Orchestrator(cfg, bus, ears, mouth, mind, timing_log=timing, identity=identity, ack=not args.text)
    if not isinstance(mind, EchoMind):
        orch.pre_warmup = lambda: wait_for_ollama(cfg)
    hud = None
    tray = None
    try:
        if identity is not None:
            await identity.start()
            identity.on_lock = orch.logout  # only used when identity.guest_on_lock is true
            cached = identity.initial_user()
            if cached is not None:
                orch.user = cached  # start with the last user's own settings (offline grace)
        await orch.start()
        if not args.no_hud:
            hud = await _start_hud(cfg, bus, orch, open_window=not args.text and not args.no_window)
        if not args.text and not args.no_tray and get(cfg, "core.tray", True):
            from .tray import Tray

            def open_hud() -> None:
                if hud is not None:
                    from .hud.window import open_hud_window

                    open_hud_window(cfg, hud.url)

            tray = Tray(bus, orch, loop, on_quit=stop.set, open_hud=open_hud if hud is not None else None)
            tray.start()
        if args.text:
            print(f"Auri J.A.R.V.I.S. {__version__} — szöveges mód · {', '.join(notes)}")
            if hud is not None:
                print(f"HUD: {hud.url}")
            print("Írj egy sort és Enter. Kilépés: Ctrl+C (vagy Ctrl+Z, Enter).", flush=True)
        else:
            log.info("Auri J.A.R.V.I.S. %s online · %s", __version__, ", ".join(notes))
        await stop.wait()  # EOF on stdin (--text); Ctrl+C cancels this task instead
        await orch.wait_idle(timeout_s=60.0)  # let the last reply finish
        return 0
    finally:
        if tray is not None:
            tray.stop()
        await orch.stop()
        if hud is not None:
            await hud.stop()
        if identity is not None:
            with contextlib.suppress(Exception):
                await identity.stop()
        s = timing.summary().get("total_ms")
        if s:
            log.info("timing total_ms: n=%d median=%.0f p90=%.0f", s["n"], s["median"], s["p90"])


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m auri_jarvis", description="Auri J.A.R.V.I.S. daemon")
    p.add_argument("--text", action="store_true", help="stdin/stdout instead of microphone/speaker")
    p.add_argument("--echo", action="store_true", help="use EchoMind even if the real Mind exists")
    p.add_argument("--selftest", action="store_true", help="check the environment and exit")
    p.add_argument("--no-hud", action="store_true", help="do not start the HUD server")
    p.add_argument("--no-window", action="store_true", help="start the HUD server but don't open the Chrome window")
    p.add_argument("--no-tray", action="store_true", help="no system tray icon (voice mode)")
    p.add_argument("--config-dir", type=Path, default=None, help="directory with jarvis/audio/mind.yaml")
    p.add_argument("--log-level", default=None, help="console log level (default: core.log_level)")
    p.add_argument("--version", action="version", version=f"auri-jarvis {__version__}")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _safe_console()
    args = parse_args(argv)
    try:
        cfg = load_config(config_dir=args.config_dir)
    except ConfigError as e:
        print(f"Konfigurációs hiba: {e}", file=sys.stderr)
        return 2
    if args.selftest:
        from .selftest import run_selftest

        setup_logging(cfg, console_level=args.log_level or "WARNING")
        return run_selftest(cfg)
    setup_logging(cfg, console_level=args.log_level or ("WARNING" if args.text else None))
    lock = SingleInstance()
    if not args.text and not lock.acquire():
        msg = "Már fut egy Auri J.A.R.V.I.S. daemon (hangmód) — a második nem indul el."
        log.error(msg)
        if sys.stderr is not None:
            print(msg, file=sys.stderr)
        return 3
    try:
        return asyncio.run(run(cfg, args))
    except KeyboardInterrupt:
        if sys.stdout is not None:
            print("\nViszlát.", flush=True)
        return 0
    except SystemExit as e:
        if isinstance(e.code, str):
            log.error("%s", e.code)
            if sys.stderr is not None:
                print(e.code, file=sys.stderr)
            return 2
        raise
    except Exception:
        # Without a console (pythonw) an uncaught error leaves no trace at all — put it in jarvis.log.
        log.exception("Auri J.A.R.V.I.S. összeomlott")
        return 1
    finally:
        lock.release()


if __name__ == "__main__":
    sys.exit(main())
