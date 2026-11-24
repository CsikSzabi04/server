"""P1 measurement (01/03 §8 last point): after a Jarvis `/activity` signal, how fast does BACKGROUND
work give the single Ollama lane back?

    .venv\\Scripts\\python scripts\\measure_preempt.py [--n 5] [--after 5]

A BACKGROUND `ask()` streams from the real model; after `--after` deltas we POST /core/v1/activity
(as Jarvis would) and time: (1) signal → lane free (holder released), (2) signal → a VOICE lease granted.
Needs Ollama and an idle lane (do not run during a bench). Prints one JSON line per run + a summary.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import statistics
import sys
import time

import httpx

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))  # run from anywhere

from auri_core.ask import ask
from auri_core.config import load_config
from auri_core.contracts import AskRequest, Priority
from auri_core.llm import OllamaClient
from auri_core.scheduler import Scheduler
from auri_core.server import create_app

TOKEN = "m" * 40
PROMPT = "Írj egy hosszú, részletes magyarázatot a rendezési algoritmusokról, sok példával."


async def one(cfg, llm, after: int) -> dict:
    sched = Scheduler()
    app = create_app(cfg, token=TOKEN, llm=llm, scheduler=sched)
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=f"http://127.0.0.1:{cfg.server_port}")
    got = asyncio.Event()
    deltas = 0
    last = ""

    async def background() -> None:
        nonlocal deltas, last
        req = AskRequest(text=PROMPT, priority=Priority.BACKGROUND)
        async for ev in ask(req, llm=llm, scheduler=sched):
            last = ev.type if ev.type != "error" else f"error:{ev.data.get('kind')}"
            if ev.type == "delta":
                deltas += 1
                if deltas >= after:
                    got.set()
        got.set()

    task = asyncio.create_task(background())
    await asyncio.wait_for(got.wait(), timeout=300)
    t0 = time.perf_counter()
    r = await client.post("/core/v1/activity", headers={"Authorization": f"Bearer {TOKEN}"}, json={"source": "jarvis"})
    while sched.holder is not None:  # noqa: ASYNC110 — 1 ms polling is the measurement
        await asyncio.sleep(0.001)
    free_ms = (time.perf_counter() - t0) * 1000
    async with sched.lease(Priority.VOICE, cfg.models.code):
        voice_ms = (time.perf_counter() - t0) * 1000
    await task
    await client.aclose()
    valid = deltas >= after and r.json().get("preempted") is True  # the lane was really held mid-stream
    return {"valid": valid, "preempted": r.json().get("preempted"), "deltas_before": deltas, "lane_free_ms": round(free_ms, 1),
            "voice_lease_ms": round(voice_ms, 1), "background_end": last}


async def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--after", type=int, default=5)
    a = ap.parse_args(argv)
    cfg = dataclasses.replace(load_config(), runs_dir=load_config().data_dir / "runs")
    llm = OllamaClient(cfg)
    rows = []
    try:
        for _ in range(a.n):
            row = await one(cfg, llm, a.after)
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    finally:
        await llm.aclose()
    ok = [r for r in rows if r["valid"]]
    if not ok:
        print(json.dumps({"summary": True, "n": len(rows), "valid": 0,
                          "note": "érvénytelen: a háttérkérés nem streamelt (fut az Ollama?)"}, ensure_ascii=False))
        return 1
    free = [r["lane_free_ms"] for r in ok]
    voice = [r["voice_lease_ms"] for r in ok]
    print(json.dumps({"summary": True, "n": len(rows), "valid": len(ok), "lane_free_ms_median": statistics.median(free),
                      "lane_free_ms_max": max(free), "voice_lease_ms_median": statistics.median(voice),
                      "all_paused": all(r["background_end"] == "error:paused" for r in ok)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
