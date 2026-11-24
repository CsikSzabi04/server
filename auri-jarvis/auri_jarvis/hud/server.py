"""auri_jarvis.hud.server — FastAPI HUD server: WebSocket events + REST + web/dist (owner: AI-3).

Security (spec §8 — "localhost is not automatically safe"):
1. Binds to 127.0.0.1 only (refuses any other host).
2. Host header allowlist (DNS rebinding) → 403.
3. Origin allowlist when an Origin header is present (WS + REST) → 403. Browsers always send
   Origin on WebSocket and cross-origin requests; non-browser local tools may omit it but still
   need the token.
4. Token: random per start (or JARVIS_HUD_TOKEN / hud.dev_token); injected into the served
   index.html as <meta name="jarvis-token">; required on WS (`?token=`) and REST
   (`X-Jarvis-Token`) → 401. Compared in constant time. Never logged (access log is off).
5. No CORS headers at all → other origins cannot read responses.
6. Inbound WS messages: ≤ 64 KB, ≤ 30/s per connection, whitelisted types only.

Wire format: {"type", "data", "t"} (JARVIS_BUILD §2.3). On connect the client gets `hello`,
then the sticky snapshot (state, identity, …), then `options`, then the live stream.
"""

from __future__ import annotations

import asyncio
import contextlib
import html
import json
import logging
import secrets
import socket
import time
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from .. import __version__
from ..bus import Bus, event_from_dict, event_to_dict
from ..config import get
from ..contracts import Event
from . import sysinfo

log = logging.getLogger(__name__)

LOOPBACK = {"127.0.0.1", "localhost", "::1"}
HUD_TYPES = frozenset(
    {"hello", "ptt", "command", "stop", "mute", "auth", "logout", "prefs.set", "voice.sample", "proposal.answer"}
)
MAX_MSG_BYTES = 64 * 1024
MAX_MSGS_PER_S = 30


def make_token(cfg: Mapping[str, Any]) -> str:
    env_tok = str(cfg.get("env", {}).get("JARVIS_HUD_TOKEN") or "")
    dev_tok = get(cfg, "hud.dev_token")
    tok = env_tok or (str(dev_tok) if dev_tok else "") or secrets.token_urlsafe(24)
    if len(tok) < 16:
        raise ValueError("A HUD-token legalább 16 karakter legyen (JARVIS_HUD_TOKEN / hud.dev_token).")
    return tok


class GuardMiddleware:
    """Host + Origin allowlist for every HTTP and WebSocket request (pure ASGI)."""

    def __init__(self, app: ASGIApp, allowed_hosts: set[str], allowed_origins: set[str]) -> None:
        self.app = app
        self.allowed_hosts = {h.lower() for h in allowed_hosts}
        self.allowed_origins = {o.lower().rstrip("/") for o in allowed_origins}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
            host = headers.get("host", "").lower()
            origin = headers.get("origin")
            reason = None
            if host not in self.allowed_hosts:
                reason = "host"
            elif origin is not None and origin.lower().rstrip("/") not in self.allowed_origins:
                reason = "origin"
            if reason:
                log.warning("hud: rejected %s request (%s not allowed)", scope["type"], reason)
                await _deny(scope, receive, send, 403, f"forbidden ({reason})")
                return
        await self.app(scope, receive, send)


async def _deny(scope: Scope, receive: Receive, send: Send, status: int, text: str) -> None:
    body = text.encode()
    if scope["type"] == "http":
        await send({"type": "http.response.start", "status": status, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": body})
        return
    # websocket: answer the upgrade with a real HTTP status if the server supports it
    msg = await receive()  # websocket.connect
    if msg.get("type") != "websocket.connect":
        return
    if "websocket.http.response" in scope.get("extensions", {}):
        await send({"type": "websocket.http.response.start", "status": status, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "websocket.http.response.body", "body": body})
    else:
        await send({"type": "websocket.close", "code": 1008})


def create_app(cfg: Mapping[str, Any], bus: Bus, orch: Any, token: str, *, web_dist: Path | None = None) -> FastAPI:
    port = int(get(cfg, "hud.port", 8790))
    hosts = set(get(cfg, "hud.allowed_hosts", []) or []) | {f"127.0.0.1:{port}", f"localhost:{port}"}
    origins = set(get(cfg, "hud.allowed_origins", []) or []) | {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
    if web_dist is None:
        web_dist = (Path(cfg["paths"]["root"]) / str(get(cfg, "hud.web_dist", "../web/dist"))).resolve()

    app = FastAPI(title="Auri J.A.R.V.I.S. HUD", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.clients = 0

    def authorized(value: str | None) -> bool:
        return bool(value) and secrets.compare_digest(str(value), token)

    def require(request: Request) -> Response | None:
        if not authorized(request.headers.get("x-jarvis-token")):
            return PlainTextResponse("unauthorized", status_code=401)
        return None

    async def body_json(request: Request) -> dict[str, Any] | None:
        raw = await request.body()
        if len(raw) > MAX_MSG_BYTES:
            return None
        try:
            data = json.loads(raw or b"{}")
        except ValueError:  # JSONDecodeError and UnicodeDecodeError (non-UTF-8 body)
            return None
        return data if isinstance(data, dict) else None

    # ── REST ────────────────────────────────────────────────────────────────
    @app.get("/health")
    async def health(request: Request) -> Response:
        if (deny := require(request)) is not None:
            return deny
        st = bus.last("state")
        return JSONResponse(
            {
                "ok": True,
                "version": __version__,
                "state": st.data.get("state") if st else None,
                "tier": orch.user.tier,
                "clients": app.state.clients,
            }
        )

    @app.post("/say")
    async def say(request: Request) -> Response:
        if (deny := require(request)) is not None:
            return deny
        data = await body_json(request)
        text = (data or {}).get("text")
        if not isinstance(text, str) or not text.strip() or len(text) > 2000:
            return JSONResponse({"ok": False, "error": "text (1–2000 karakter) kell"}, status_code=400)
        bus.emit(Event("say", {"text": text.strip(), "signature": bool((data or {}).get("signature", False))}))
        return JSONResponse({"ok": True})

    @app.post("/command")
    async def command(request: Request) -> Response:
        if (deny := require(request)) is not None:
            return deny
        data = await body_json(request)
        text = (data or {}).get("text")
        if not isinstance(text, str) or not text.strip() or len(text) > 2000:
            return JSONResponse({"ok": False, "error": "text (1–2000 karakter) kell"}, status_code=400)
        orch.submit_text(text)
        return JSONResponse({"ok": True})

    @app.post("/routine")
    async def routine(request: Request) -> Response:
        if (deny := require(request)) is not None:
            return deny
        data = await body_json(request)
        name = (data or {}).get("name")
        if not isinstance(name, str) or not name.strip() or len(name) > 64:
            return JSONResponse({"ok": False, "error": "name kell"}, status_code=400)
        orch.submit_routine(name.strip())
        return JSONResponse({"ok": True})

    # ── WebSocket ───────────────────────────────────────────────────────────
    @app.websocket("/events")
    async def events(ws: WebSocket) -> None:
        if not authorized(ws.query_params.get("token")):
            log.warning("hud: websocket without a valid token rejected")
            if "websocket.http.response" in ws.scope.get("extensions", {}):
                await ws.send_denial_response(PlainTextResponse("unauthorized", status_code=401))
            else:
                await ws.close(code=4401)
            return
        await ws.accept()
        q = bus.subscribe_queue()
        app.state.clients += 1
        try:
            await ws.send_json({"type": "hello", "data": {"version": __version__}, "t": time.time()})
            for ev in bus.snapshot():
                await ws.send_json(event_to_dict(ev))
            await ws.send_json(event_to_dict(options_event(cfg)))
            sender = asyncio.create_task(_pump(ws, q))
            try:
                await _receive_loop(ws, orch)
            finally:
                sender.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await sender
        except WebSocketDisconnect:
            pass
        finally:
            bus.unsubscribe_queue(q)
            app.state.clients -= 1

    # ── static HUD (web/dist) with the token injected ───────────────────────
    index_cache: dict[str, Any] = {}

    def index_html() -> str | None:
        f = web_dist / "index.html"
        if not f.is_file():
            return None
        mtime = f.stat().st_mtime
        if index_cache.get("mtime") != mtime:
            src = f.read_text(encoding="utf-8")
            meta = f'<meta name="jarvis-token" content="{html.escape(token, quote=True)}">'
            index_cache.update(mtime=mtime, html=src.replace("<head>", "<head>\n    " + meta, 1))
        return index_cache["html"]

    def no_store(resp: Response) -> Response:
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        return resp

    @app.get("/{path:path}")
    async def static(path: str) -> Response:
        if path and not path.endswith("/"):
            target = (web_dist / path).resolve()
            if target.is_file() and web_dist in target.parents and target.name != "index.html":
                return FileResponse(target)
            if "." in Path(path).name:  # a missing asset — don't hand out the SPA page
                return PlainTextResponse("not found", status_code=404)
        page = index_html()
        if page is None:
            return no_store(
                HTMLResponse(
                    "<!doctype html><meta charset=utf-8><title>Auri HUD</title>"
                    "<body style='background:#04070d;color:#cfeefe;font-family:monospace;padding:2em'>"
                    "<h2>Auri HUD — nincs web build</h2><p>cd web &amp;&amp; npm run build</p>",
                    status_code=503,
                )
            )
        return no_store(HTMLResponse(page))

    return GuardMiddleware(app, hosts, origins)  # type: ignore[return-value]


def options_event(cfg: Mapping[str, Any]) -> Event:
    return Event("options", {"apps": sysinfo.app_options(cfg), "monitors": sysinfo.monitors()})


async def _pump(ws: WebSocket, q: asyncio.Queue[Event]) -> None:
    while True:
        ev = await q.get()
        await ws.send_json(event_to_dict(ev))


async def _receive_loop(ws: WebSocket, orch: Any) -> None:
    window_start, count = time.monotonic(), 0
    while True:
        raw = await ws.receive_text()
        now = time.monotonic()
        if now - window_start >= 1.0:
            window_start, count = now, 0
        count += 1
        if count > MAX_MSGS_PER_S:
            continue  # flood → drop silently
        if len(raw) > MAX_MSG_BYTES:
            await _send_error(ws, "hud", "túl nagy üzenet")
            continue
        try:
            ev = event_from_dict(json.loads(raw))
        except (ValueError, json.JSONDecodeError) as e:
            await _send_error(ws, "hud", f"hibás üzenet: {e}")
            continue
        if ev.type not in HUD_TYPES:
            await _send_error(ws, "hud", f"ismeretlen üzenettípus: {ev.type[:40]}")
            continue
        try:
            await orch.handle_hud(ev)
        except Exception:
            log.exception("hud: handling %s failed", ev.type)
            await _send_error(ws, "hud", f"{ev.type} feldolgozása sikertelen")


async def _send_error(ws: WebSocket, where: str, message: str) -> None:
    with contextlib.suppress(Exception):
        await ws.send_json({"type": "error", "data": {"where": where, "message": message}, "t": time.time()})


def _port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(
            socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE if hasattr(socket, "SO_EXCLUSIVEADDRUSE") else socket.SO_REUSEADDR, 1
        )
        try:
            s.bind((host, port))
        except OSError:
            return False
    return True


class _EmbeddedServer(uvicorn.Server):
    """uvicorn inside our loop: leave SIGINT to asyncio.run (no signal capturing)."""

    @contextlib.contextmanager
    def capture_signals(self) -> Iterator[None]:
        yield


class HudServer:
    def __init__(self, cfg: Mapping[str, Any], bus: Bus, orch: Any, *, token: str | None = None, port: int | None = None) -> None:
        self.cfg, self.bus, self.orch = cfg, bus, orch
        self.host = str(get(cfg, "hud.host", "127.0.0.1"))
        if self.host not in LOOPBACK:
            raise ValueError(f"A HUD csak 127.0.0.1-en figyelhet (hud.host = {self.host}).")
        if self.host == "localhost":
            self.host = "127.0.0.1"
        self.port = int(port if port is not None else get(cfg, "hud.port", 8790))
        self.token = token or make_token(cfg)
        self.app = create_app(cfg, bus, orch, self.token)
        self._server: _EmbeddedServer | None = None
        self._task: asyncio.Task[None] | None = None
        self._stats_task: asyncio.Task[None] | None = None
        self.window = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/#jarvis"

    async def start(self, *, open_window: bool = False) -> None:
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
            # Our root logger (setup_logging) already writes the log file. uvicorn's own dictConfig
            # calls sys.stdout.isatty() — under pythonw.exe (Start-menu shortcut) stdout is None and
            # the HUD, then the whole daemon, died silently before any window opened.
            log_config=None,
            access_log=False,  # the WS URL carries the token — never log it
            lifespan="off",
            ws="websockets-sansio",
            ws_max_size=MAX_MSG_BYTES,
            server_header=False,
            proxy_headers=False,
        )
        if not _port_free(self.host, self.port):
            raise RuntimeError(f"A HUD-szerver nem indult el: 127.0.0.1:{self.port} foglalt (fut már egy daemon?)")
        self._server = _EmbeddedServer(config)
        self._task = asyncio.create_task(self._serve_guarded())
        deadline = time.monotonic() + 10
        while not self._server.started:
            if self._task.done():
                exc = self._task.exception() if not self._task.cancelled() else None
                raise RuntimeError(f"A HUD-szerver nem indult el (127.0.0.1:{self.port} foglalt?)") from exc
            if time.monotonic() > deadline:
                raise RuntimeError("A HUD-szerver indítása időtúllépés.")
            await asyncio.sleep(0.02)
        log.info("HUD listening on http://127.0.0.1:%d", self.port)
        self._stats_task = asyncio.create_task(self._stats_loop())
        if open_window and get(self.cfg, "hud.open_on_start", True):
            from .window import open_hud_window

            self.window = open_hud_window(self.cfg, self.url)

    async def _serve_guarded(self) -> None:
        """uvicorn calls sys.exit() on a startup failure; inside a task that SystemExit would
        tear down the whole asyncio loop (= the daemon). Turn it into a normal error."""
        assert self._server is not None
        try:
            await self._server.serve()
        except SystemExit as e:
            raise RuntimeError(f"uvicorn exited ({e.code})") from None

    async def stop(self) -> None:
        if self._stats_task is not None:
            self._stats_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._stats_task
        if self._server is not None:
            self._server.should_exit = True
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except (TimeoutError, asyncio.CancelledError, RuntimeError):
                self._task.cancel()

    async def _stats_loop(self, period_s: float = 5.0) -> None:
        import httpx

        base = str(get(self.cfg, "llm.base_url", "http://127.0.0.1:11434"))
        async with httpx.AsyncClient(timeout=1.5) as client:
            while True:
                if getattr(self.app, "app", self.app).state.clients > 0:  # GuardMiddleware wraps the app
                    try:
                        self.bus.emit(Event("stats", await sysinfo.stats(base, client)))
                    except Exception:
                        log.debug("stats failed", exc_info=True)
                await asyncio.sleep(period_s)
