"""scripts/smoke.py — synthetic turns through the real orchestrator (owner: AI-3).

    .venv\\Scripts\\python scripts\\smoke.py --n 20            # real Mind (Ollama), no audio
    .venv\\Scripts\\python scripts\\smoke.py --n 20 --echo     # EchoMind (plumbing only)
    .venv\\Scripts\\python scripts\\smoke.py --soak 2h         # M5 soak: turns every --every s

No microphone, no speaker, no ElevenLabs credit: FakeEars + a silent FakeMouth. Measures per
turn `llm_first_ms` (request → first text delta) and `total_ms` (request → first "audio"), and
reports n / median / p90. The soak also samples the process RSS + CPU every minute.
Results: data/body/smoke-<timestamp>.json (numbers only — no transcript text).
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from auri_jarvis.__main__ import load_factory, wait_for_ollama  # noqa: E402
from auri_jarvis.bus import Bus  # noqa: E402
from auri_jarvis.config import data_path, deep_merge, load_config  # noqa: E402
from auri_jarvis.fakes import EchoMind, FakeEars, FakeMouth  # noqa: E402
from auri_jarvis.orchestrator import Orchestrator  # noqa: E402
from auri_jarvis.timing import TimingLog, summarize  # noqa: E402

# generic, non-personal questions (guest-safe)
QUESTIONS = [
    "Hány óra van?",
    "Milyen nap van ma?",
    "Mondj egy rövid viccet!",
    "Mi a fővárosa Franciaországnak?",
    "Mennyi hét meg nyolc?",
    "Hogy vagy?",
    "Mit tudsz csinálni?",
    "Mi a különbség a kávé és a tea között, röviden?",
    "Ajánlj egy könyvet egy mondatban!",
    "Mondd meg egy szóban, milyen színű az ég.",
]


def parse_duration(s: str) -> float:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([smh]?)", s.strip().lower())
    if not m:
        raise argparse.ArgumentTypeError("pl. 90s, 30m, 2h")
    return float(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600}[m.group(2)]


async def run(args: argparse.Namespace) -> dict[str, Any]:
    cfg = deep_merge(load_config(), {"core": {"follow_up_s": 0, "idle_tick_s": 0}})
    bus = Bus()
    bus.attach()
    errors: list[dict[str, Any]] = []
    bus.on("error", lambda ev: errors.append(dict(ev.data)))
    factory = None if args.echo else load_factory("mind")
    mind = EchoMind() if factory is None else factory(cfg, bus.emit)
    timing = TimingLog(None)
    orch = Orchestrator(cfg, bus, FakeEars(read_stream=False), FakeMouth(out=io.StringIO()), mind, timing_log=timing, ack=False)
    if factory is not None:
        orch.pre_warmup = lambda: wait_for_ollama(cfg)
    t0 = time.monotonic()
    await orch.start(warmup=True)
    while orch.warm["mind"] == "loading" and time.monotonic() - t0 < 300:  # noqa: ASYNC110 — simple poll in a CLI script
        await asyncio.sleep(0.2)
    warm_s = time.monotonic() - t0
    print(f"mind: {'EchoMind' if factory is None else type(mind).__name__} · bemelegítés {warm_s:.1f} s ({orch.warm['mind']})")
    if orch.warm["mind"] != "ready":
        await orch.stop()
        print("A Mind nem melegedett be (fut az Ollama?) — nem mérek, mert a számok csak a hibaágat mutatnák.")
        return {"errors": 1, "aborted": True}

    samples: list[dict[str, float]] = []
    proc = None
    try:
        import psutil

        proc = psutil.Process(os.getpid())
        proc.cpu_percent(None)
    except Exception:
        pass

    deadline = time.monotonic() + args.soak if args.soak else None
    i = 0
    last_sample = 0.0
    while True:
        if deadline is None and i >= args.n:
            break
        if deadline is not None and time.monotonic() >= deadline:
            break
        q = QUESTIONS[i % len(QUESTIONS)]
        orch.submit_text(q)
        ok = await orch.wait_idle(timeout_s=180)
        i += 1
        rec = timing.records[-1] if timing.records else {}
        print(f"  #{i:3d} llm_first={rec.get('llm_first_ms')} ms  total={rec.get('total_ms')} ms{'' if ok else '  (TIMEOUT)'}")
        if proc is not None and time.monotonic() - last_sample >= 60:
            last_sample = time.monotonic()
            samples.append(
                {"t": round(time.monotonic() - t0), "rss_mb": proc.memory_info().rss / 2**20, "cpu": proc.cpu_percent(None)}
            )
        if deadline is not None:
            await asyncio.sleep(args.every)
    await orch.stop()

    summary = summarize(timing.records, ("llm_first_ms", "total_ms", "turn_ms"))
    result = {
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mind": "echo" if factory is None else type(mind).__name__,
        "model": cfg.get("llm", {}).get("model"),
        "turns": i,
        "warmup_s": round(warm_s, 1),
        "summary": summary,
        "errors": len(errors),
        "resources": samples,
    }
    out = data_path(cfg, "body", f"smoke-{time.strftime('%Y%m%d-%H%M%S')}.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nszakasz          n   medián     p90")
    for k, s in summary.items():
        print(f"  {k:13s} {s['n']:3d} {s['median']:7.0f} ms {s['p90']:6.0f} ms")
    print(f"hibák: {len(errors)} · eredmény: {out}")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description="Auri J.A.R.V.I.S. smoke / soak test (no audio, no credits)")
    p.add_argument("--n", type=int, default=20, help="number of turns (ignored with --soak)")
    p.add_argument("--echo", action="store_true", help="EchoMind instead of the real Mind")
    p.add_argument("--soak", type=parse_duration, default=None, help="run for a duration, e.g. 2h")
    p.add_argument("--every", type=float, default=20.0, help="seconds between soak turns")
    args = p.parse_args()
    for s in (sys.stdout, sys.stderr):
        if s is not None and not s.isatty():
            s.reconfigure(encoding="utf-8", errors="replace")
    res = asyncio.run(run(args))
    return 1 if res["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
