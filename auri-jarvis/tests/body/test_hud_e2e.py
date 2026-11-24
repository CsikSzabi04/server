"""M2 end-to-end: real HudServer + real Orchestrator + fakes (FakeEars/FakeMouth/EchoMind).
A HUD WebSocket client types a command and sees state → reply.delta → reply.done → timing."""

from __future__ import annotations

import asyncio
import io
import json
import socket
from pathlib import Path
from typing import Any

from websockets.asyncio.client import connect

from auri_jarvis.bus import Bus
from auri_jarvis.fakes import EchoMind, FakeEars, FakeMouth
from auri_jarvis.hud.server import HudServer
from auri_jarvis.orchestrator import Orchestrator

TOKEN = "e2e-token-0123456789abcdef"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def recv_until(ws, pred, timeout=5.0) -> list[dict[str, Any]]:
    got: list[dict[str, Any]] = []
    async with asyncio.timeout(timeout):
        while True:
            msg = json.loads(await ws.recv())
            got.append(msg)
            if pred(msg):
                return got


async def test_hud_command_roundtrip(tmp_path: Path):
    port = free_port()
    cfg: dict[str, Any] = {
        "hud": {"host": "127.0.0.1", "port": port, "allowed_origins": [], "allowed_hosts": [], "web_dist": str(tmp_path)},
        "core": {"follow_up_s": 0, "idle_tick_s": 0},
        "env": {},
        "paths": {"root": str(tmp_path), "config_dir": str(tmp_path)},
        "llm": {"base_url": "http://127.0.0.1:1"},
    }
    bus = Bus()
    bus.attach()
    mouth = FakeMouth(out=io.StringIO())
    orch = Orchestrator(cfg, bus, FakeEars(read_stream=False), mouth, EchoMind())
    await orch.start(warmup=False)
    hud = HudServer(cfg, bus, orch, token=TOKEN)
    await hud.start()
    try:
        async with connect(f"ws://127.0.0.1:{port}/events?token={TOKEN}", origin=f"http://127.0.0.1:{port}") as ws:
            hello = await recv_until(ws, lambda m: m["type"] == "options")
            types = [m["type"] for m in hello]
            assert types[0] == "hello" and "state" in types and "identity" in types
            ident = next(m for m in hello if m["type"] == "identity")["data"]
            assert ident["tier"] == "guest" and ident["prefs"]["wake_word"] == "hey_auri"

            await ws.send(json.dumps({"type": "command", "data": {"text": "hány óra van"}}))
            stream = await recv_until(ws, lambda m: m["type"] == "timing")
            kinds = [m["type"] for m in stream]
            assert "reply.delta" in kinds and "reply.done" in kinds
            done = next(m for m in stream if m["type"] == "reply.done")["data"]
            assert done["text"].startswith("Ezt mondtad: hány óra van.")
            states = [m["data"]["state"] for m in stream if m["type"] == "state"]
            assert states[:2] == ["thinking", "speaking"]
            assert mouth.said and mouth.said[-1] == done["text"]

            # guest → prefs.set is refused with an error event
            await ws.send(json.dumps({"type": "prefs.set", "data": {"voice": "george"}}))
            err = await recv_until(ws, lambda m: m["type"] == "error")
            assert err[-1]["data"]["where"] == "prefs"
    finally:
        await hud.stop()
        await orch.stop()
