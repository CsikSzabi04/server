"""M4 (BODY): warm-up status, per-source acknowledgement (earcon), waiting for Ollama,
single instance, tray colour logic + menu → loop dispatch (no real tray icon is created)."""

from __future__ import annotations

import asyncio
import io
import sys
import threading
import time
from typing import Any

import pytest

from auri_jarvis.__main__ import SingleInstance, wait_for_ollama
from auri_jarvis.bus import Bus
from auri_jarvis.contracts import Event, WakeEvent
from auri_jarvis.fakes import EchoMind, FakeEars, FakeMouth
from auri_jarvis.orchestrator import Orchestrator
from auri_jarvis.tray import COLORS, Tray, make_icon

CFG: dict[str, Any] = {
    "core": {
        "follow_up_s": 0,
        "idle_tick_s": 0,
        "listen_start_timeout_s": 0.2,
        "ack_phrase": "Igen?",
        "ack_by_source": {"hotkey": "phrase", "wakeword": "earcon", "hud": "none"},
    },
}


class SlowMind(EchoMind):
    def __init__(self, fail: bool = False) -> None:
        super().__init__()
        self.fail = fail

    async def warmup(self) -> None:
        await asyncio.sleep(0.05)
        if self.fail:
            raise RuntimeError("no model")
        self.warmed_up = True


class EarconMouth(FakeMouth):
    def __init__(self) -> None:
        super().__init__(out=io.StringIO())
        self.earcons: list[str] = []
        self.ready_calls = 0

    async def earcon(self, name: str) -> None:
        self.earcons.append(name)

    def wait_ready(self, timeout: float | None = None) -> bool:
        self.ready_calls += 1
        time.sleep(0.02)
        return True


async def build(mind=None, mouth=None):
    bus = Bus()
    bus.attach()
    events: list[Event] = []
    bus.on("*", events.append)
    ears = FakeEars(read_stream=False)
    orch = Orchestrator(CFG, bus, ears, mouth or EarconMouth(), mind or SlowMind())
    return orch, bus, ears, events


async def test_warmup_events_loading_then_ready_and_pre_warmup():
    orch, bus, ears, events = await build()
    order: list[str] = []

    async def pre() -> None:
        order.append("pre")

    orch.pre_warmup = pre
    await orch.start(warmup=True)
    for _ in range(100):
        await asyncio.sleep(0.02)
        if orch.warm == {"mind": "ready", "voice": "ready"}:
            break
    await bus.drain()
    warm = [e.data for e in events if e.type == "warmup"]
    assert warm[0]["mind"] == "loading" and warm[-1]["mind"] == "ready" and warm[-1]["voice"] == "ready"
    assert order == ["pre"] and orch.mind.warmed_up and orch.mouth.ready_calls == 1
    assert bus.last("warmup").data["mind"] == "ready"  # sticky → a late HUD sees it
    await orch.stop()


async def test_warmup_failure_is_reported_and_daemon_keeps_running():
    orch, bus, ears, events = await build(mind=SlowMind(fail=True))
    await orch.start(warmup=True)
    for _ in range(100):
        await asyncio.sleep(0.02)
        if orch.warm["mind"] != "loading":
            break
    await bus.drain()
    assert orch.warm["mind"] == "error"
    assert any(e.type == "error" and e.data["where"] == "mind.warmup" for e in events)
    orch.submit_text("szia")  # a turn still works
    assert await orch.wait_idle(5)
    assert orch.mind.requests
    await orch.stop()


async def test_ack_by_source_earcon_phrase_none():
    orch, bus, ears, events = await build()
    mouth: EarconMouth = orch.mouth  # type: ignore[assignment]
    await orch.start(warmup=False)
    for src in ("wakeword", "hotkey", "hud"):
        orch.on_wake(WakeEvent(source=src))  # type: ignore[arg-type]
        await asyncio.sleep(0.05)
        assert await orch.wait_idle(5)
    assert mouth.earcons == ["wake"]  # wakeword → earcon
    assert mouth.said.count("Igen?") == 1  # hotkey → phrase; hud → none
    await orch.stop()


async def test_earcon_falls_back_to_phrase_without_mouth_support():
    orch, bus, ears, events = await build(mouth=FakeMouth(out=io.StringIO()))
    await orch.start(warmup=False)
    orch.on_wake(WakeEvent(source="wakeword", word="hey_auri"))
    await asyncio.sleep(0.05)
    assert await orch.wait_idle(5)
    assert orch.mouth.said == ["Igen?"]
    await orch.stop()


async def test_wait_for_ollama_retries_then_succeeds_or_times_out():
    hits = 0

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        nonlocal hits
        await reader.readuntil(b"\r\n\r\n")
        hits += 1
        status = b"503 Service Unavailable" if hits < 3 else b"200 OK"
        body = b'{"models":[]}'
        writer.write(
            b"HTTP/1.1 " + status + b"\r\nContent-Type: application/json\r\nContent-Length: %d\r\n\r\n" % len(body) + body
        )
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        await wait_for_ollama({"llm": {"base_url": f"http://127.0.0.1:{port}"}}, timeout_s=5, period_s=0.05)
        assert hits == 3
    finally:
        server.close()
        await server.wait_closed()
    with pytest.raises(RuntimeError, match="Ollama"):
        await wait_for_ollama({"llm": {"base_url": f"http://127.0.0.1:{port}"}}, timeout_s=0.2, period_s=0.05)


@pytest.mark.skipif(sys.platform != "win32", reason="named mutex is Windows-only")
def test_single_instance_mutex():
    a, b = SingleInstance(), SingleInstance()
    try:
        assert a.acquire() is True
        assert b.acquire() is False  # a second daemon would be refused
    finally:
        b.release()
        a.release()
    c = SingleInstance()
    assert c.acquire() is True
    c.release()


class FakeIcon:
    def __init__(self, name, icon, title, menu) -> None:
        self.icon, self.title, self.menu = icon, title, menu
        self.stopped = threading.Event()

    def run(self) -> None:
        self.stopped.wait(5)

    def stop(self) -> None:
        self.stopped.set()


class StubOrch:
    def __init__(self) -> None:
        self.wakes: list[str] = []
        self.mutes: list[bool] = []

    def on_wake(self, w: WakeEvent) -> None:
        self.wakes.append(w.source)

    def set_muted(self, on: bool) -> None:
        self.mutes.append(on)


async def test_tray_colours_and_menu_dispatch():
    bus = Bus()
    bus.attach()
    orch = StubOrch()
    quit_called = asyncio.Event()
    tray = Tray(bus, orch, asyncio.get_running_loop(), on_quit=quit_called.set, icon_factory=FakeIcon)
    tray.start()
    try:
        assert isinstance(tray.icon, FakeIcon) and tray.status() == "loading"
        bus.emit(Event("warmup", {"mind": "ready", "voice": "ready"}))
        bus.emit(Event("state", {"state": "listening"}))
        await bus.drain()
        assert tray.status() == "listening" and "listening" in tray.icon.title
        bus.emit(Event("mute", {"on": True}))
        await bus.drain()
        assert tray.status() == "muted"
        bus.emit(Event("error", {"where": "x", "message": "y"}))
        await bus.drain()
        assert tray.status() == "error"
        # menu actions run on the tray thread → land on the loop
        threading.Thread(target=tray.action_listen).start()
        threading.Thread(target=tray.action_mute).start()
        threading.Thread(target=tray.action_quit).start()
        await asyncio.wait_for(quit_called.wait(), 2)
        await asyncio.sleep(0.05)
        assert orch.wakes == ["hud"] and orch.mutes == [False]  # muted → toggles off
    finally:
        tray.stop()


def test_make_icon_sizes_and_colours():
    img = make_icon(COLORS["error"], 32)
    assert img.size == (32, 32) and img.getpixel((16, 16))[:3] == COLORS["error"]
