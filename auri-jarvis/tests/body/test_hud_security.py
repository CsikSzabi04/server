"""M2 security gates (spec §8, JARVIS_BUILD §7.3) against a REAL uvicorn server on 127.0.0.1:
foreign Origin → 403 · wrong Host → 403 · no/wrong token → 401 · never 0.0.0.0 ·
plus WS hello/snapshot/options, message whitelist, token injection, path traversal."""

from __future__ import annotations

import asyncio
import json
import socket
from pathlib import Path
from typing import Any

import httpx
import pytest
from websockets.asyncio.client import connect

from auri_jarvis.bus import Bus
from auri_jarvis.contracts import GUEST, Event
from auri_jarvis.hud.server import HudServer

TOKEN = "test-token-0123456789abcdef"


class StubOrch:
    def __init__(self) -> None:
        self.user = GUEST
        self.hud: list[Event] = []
        self.texts: list[str] = []
        self.routines: list[str] = []

    async def handle_hud(self, ev: Event) -> None:
        self.hud.append(ev)

    def submit_text(self, text: str) -> None:
        self.texts.append(text)

    def submit_routine(self, name: str) -> None:
        self.routines.append(name)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
async def hud(tmp_path: Path):
    port = free_port()
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(
        "<!doctype html><html><head><title>x</title></head><body>HUD</body></html>", encoding="utf-8"
    )
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("do not serve", encoding="utf-8")
    cfg: dict[str, Any] = {
        "hud": {
            "host": "127.0.0.1",
            "port": port,
            "allowed_origins": ["http://localhost:5173"],
            "allowed_hosts": [],
            "web_dist": str(dist),
        },
        "env": {},
        "paths": {"root": str(tmp_path), "config_dir": str(tmp_path / "config")},
        "llm": {"base_url": "http://127.0.0.1:1"},
    }
    bus = Bus()
    bus.attach()
    bus.emit(Event("state", {"state": "idle"}))
    orch = StubOrch()
    server = HudServer(cfg, bus, orch, token=TOKEN)
    await server.start()
    try:
        yield server, bus, orch, port
    finally:
        await server.stop()


async def raw_status(port: int, path: str, *, host: str, origin: str | None = None, ws: bool = False) -> int:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    lines = [f"GET {path} HTTP/1.1", f"Host: {host}"]
    if origin:
        lines.append(f"Origin: {origin}")
    if ws:
        lines += [
            "Upgrade: websocket",
            "Connection: Upgrade",
            "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==",
            "Sec-WebSocket-Version: 13",
        ]
    writer.write(("\r\n".join(lines) + "\r\n\r\n").encode())
    await writer.drain()
    status_line = await asyncio.wait_for(reader.readline(), 5)
    writer.close()
    return int(status_line.split()[1])


async def test_never_binds_all_interfaces(hud):
    server, *_ = hud
    addrs = {s.getsockname()[0] for srv in server._server.servers for s in srv.sockets}
    assert addrs == {"127.0.0.1"}
    with pytest.raises(ValueError, match=r"127.0.0.1"):
        HudServer({"hud": {"host": "0.0.0.0"}, "env": {}, "paths": {"root": "."}}, Bus(), StubOrch(), token=TOKEN)


async def test_rest_requires_token(hud):
    _, _, orch, port = hud
    base = f"http://127.0.0.1:{port}"
    async with httpx.AsyncClient() as c:
        assert (await c.get(f"{base}/health")).status_code == 401
        assert (await c.get(f"{base}/health", headers={"X-Jarvis-Token": "wrong"})).status_code == 401
        r = await c.get(f"{base}/health", headers={"X-Jarvis-Token": TOKEN})
        assert r.status_code == 200 and r.json()["ok"] is True and r.json()["state"] == "idle"
        assert (await c.post(f"{base}/command", json={"text": "hány óra"})).status_code == 401
        r = await c.post(f"{base}/command", json={"text": "hány óra"}, headers={"X-Jarvis-Token": TOKEN})
        assert r.status_code == 200 and orch.texts == ["hány óra"]
        r = await c.post(f"{base}/routine", json={"name": "munka"}, headers={"X-Jarvis-Token": TOKEN})
        assert r.status_code == 200 and orch.routines == ["munka"]
        r = await c.post(f"{base}/command", content=b'{"text":"h\xe1ny"}', headers={"X-Jarvis-Token": TOKEN})
        assert r.status_code == 400  # non-UTF-8 body → 400, not 500
        r = await c.post(f"{base}/command", content=b"x" * 70_000, headers={"X-Jarvis-Token": TOKEN})
        assert r.status_code == 400  # oversized body
        r = await c.post(f"{base}/say", json={"text": ""}, headers={"X-Jarvis-Token": TOKEN})
        assert r.status_code == 400
        assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


async def test_foreign_origin_is_403(hud):
    _, _, orch, port = hud
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"http://127.0.0.1:{port}/command",
            json={"text": "lock pc"},
            headers={"X-Jarvis-Token": TOKEN, "Origin": "https://evil.example"},
        )
    assert r.status_code == 403 and orch.texts == []
    assert (
        await raw_status(port, f"/events?token={TOKEN}", host=f"127.0.0.1:{port}", origin="https://evil.example", ws=True) == 403
    )
    # allowed dev origin passes the guard
    assert await raw_status(port, "/", host=f"127.0.0.1:{port}", origin="http://localhost:5173") == 200


async def test_wrong_host_is_403_dns_rebinding(hud):
    _, _, _, port = hud
    assert await raw_status(port, "/", host=f"evil.example:{port}") == 403
    assert await raw_status(port, "/", host="127.0.0.1:9999") == 403
    assert await raw_status(port, f"/events?token={TOKEN}", host=f"attacker.test:{port}", ws=True) == 403
    assert await raw_status(port, "/", host=f"localhost:{port}") == 200


async def test_websocket_without_token_is_401(hud):
    _, _, _, port = hud
    assert await raw_status(port, "/events", host=f"127.0.0.1:{port}", origin=f"http://127.0.0.1:{port}", ws=True) == 401
    assert await raw_status(port, "/events?token=nope", host=f"127.0.0.1:{port}", ws=True) == 401
    assert await raw_status(port, f"/events?token={TOKEN}", host=f"127.0.0.1:{port}", ws=True) == 101


async def test_websocket_stream_and_inbound_whitelist(hud):
    _, bus, orch, port = hud
    uri = f"ws://127.0.0.1:{port}/events?token={TOKEN}"
    async with connect(uri, origin=f"http://127.0.0.1:{port}") as ws:
        first = [json.loads(await asyncio.wait_for(ws.recv(), 5)) for _ in range(3)]
        assert [m["type"] for m in first] == ["hello", "state", "options"]
        assert set(first[2]["data"]) == {"apps", "monitors"}
        bus.emit(Event("transcript", {"text": "szia"}))
        live = json.loads(await asyncio.wait_for(ws.recv(), 5))
        assert live == {"type": "transcript", "data": {"text": "szia"}, "t": live["t"]}
        await ws.send(json.dumps({"type": "command", "data": {"text": "hello"}}))
        await ws.send(json.dumps({"type": "say", "data": {"text": "internal only"}}))  # not a HUD type
        err = json.loads(await asyncio.wait_for(ws.recv(), 5))
        assert err["type"] == "error" and "ismeretlen" in err["data"]["message"]
        await ws.send("not json")
        err = json.loads(await asyncio.wait_for(ws.recv(), 5))
        assert err["type"] == "error"
        await asyncio.sleep(0.05)
    assert [e.type for e in orch.hud] == ["command"] and orch.hud[0].data == {"text": "hello"}


async def test_index_gets_token_and_traversal_blocked(hud):
    _, _, _, port = hud
    base = f"http://127.0.0.1:{port}"
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{base}/jarvis")
        assert r.status_code == 200 and f'<meta name="jarvis-token" content="{TOKEN}">' in r.text
        assert r.headers["cache-control"] == "no-store"
        assert (await c.get(f"{base}/assets/app.js")).text == "console.log(1)"
        assert (await c.get(f"{base}/assets/missing.js")).status_code == 404
        for p in ("/..%2Fsecret.txt", "/%2e%2e/secret.txt", "/assets/..%2F..%2Fsecret.txt"):
            r = await c.get(base + p)
            assert "do not serve" not in r.text


async def test_port_in_use_is_a_clean_error_not_a_dead_loop(hud):
    server, bus, orch, port = hud
    cfg = dict(server.cfg)
    second = HudServer(cfg, bus, orch, token=TOKEN, port=port)
    with pytest.raises(RuntimeError, match="foglalt"):
        await second.start()
    await asyncio.sleep(0.05)
    async with httpx.AsyncClient() as c:  # the loop and the first server are still alive
        r = await c.get(f"http://127.0.0.1:{port}/health", headers={"X-Jarvis-Token": TOKEN})
    assert r.status_code == 200
