"""NK14 measurements (a)–(h) (owner: AI-3). Real Ollama, run by hand, when the user is idle:

    .venv\\Scripts\\python scripts\\measure_llm.py [--model gemma4:e2b] [--n 20] [--only a,b,c]

Prints one JSON line per measurement (median, p90, n, model) — copy the numbers as new rows
into ideas_for_brain/thinking/00-alapok/03-tenyek-es-meresek.md.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auri_core.config import load_config
from auri_core.llm import OllamaClient, parse_json
from auri_core.scheduler import Priority, Scheduler

LONG = "You are a careful Python tutor. " + " ".join(f"Rule {i}: write clear, tested, typed code." for i in range(60))
SCHEMA = {"type": "object", "properties": {"code": {"type": "string"}, "why": {"type": "string"}}, "required": ["code", "why"]}


def p90(xs: list[float]) -> float:
    return sorted(xs)[max(0, round(0.9 * len(xs)) - 1)] if xs else 0.0


def out(name: str, model: str, **kw: object) -> None:
    print(json.dumps({"m": name, "model": model, **kw}, ensure_ascii=False), flush=True)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=load_config().models.code)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--only", default="a,b,c,d,e,f,g,h")
    a = ap.parse_args()
    only, m, cfg = set(a.only.split(",")), a.model, load_config()
    c, s = OllamaClient(cfg), Scheduler()
    msgs = [{"role": "system", "content": LONG}, {"role": "user", "content": "Say OK."}]

    async with s.lease(Priority.TASK, m) as lz:
        await c.chat(lz, msgs, num_predict=1)  # warm load
        if "a" in only or "b" in only:  # (a) cold prefill tok/s, (b) warm re-send of the same prompt
            cold, warm = [], []
            for i in range(3):
                r = await c.chat(lz, [{"role": "system", "content": f"[{i}{time.time()}] " + LONG}, msgs[1]], num_predict=1)
                cold.append(r.stats.prompt_tokens / max(r.stats.prompt_ms, 1) * 1000)
                r2 = await c.chat(lz, msgs, num_predict=1)
                warm.append(r2.stats.prompt_ms)
            out("a_prefill_tok_s", m, median=statistics.median(cold), n=3, prompt_tokens=r.stats.prompt_tokens)
            out("b_warm_prompt_ms", m, median=statistics.median(warm), n=3)
        if "c" in only:  # (c) valid-JSON rate with a schema
            ok = 0
            for i in range(a.n):
                data, _ = await c.chat_json(lz, [{"role": "user", "content": f"Write a Python function #{i} that reverses a string. JSON."}], schema=SCHEMA, num_predict=300)
                ok += isinstance(data, dict) and {"code", "why"} <= data.keys()
            out("c_json_valid_rate", m, rate=ok / a.n, n=a.n)
        if "d" in only:  # (d) does a per-request num_thread reload the model?
            r = await c.chat(lz, msgs, num_predict=1, options={"num_thread": 2})
            r2 = await c.chat(lz, msgs, num_predict=1)
            out("d_num_thread_reload", m, load_ms_with=r.stats.load_ms, load_ms_after=r2.stats.load_ms)
        if "e" in only:  # (e) after cancelling a stream, when is the lane free?
            free = []
            for _ in range(3):
                n = 0
                async for _ch in c.chat_stream(lz, [{"role": "user", "content": "Count to 500."}], num_predict=800):
                    n += 1
                    if n >= 5:
                        break
                t0 = time.perf_counter()
                r = await c.chat(lz, msgs, num_predict=1)
                free.append((time.perf_counter() - t0) * 1000 - r.stats.prompt_ms)
            out("e_after_cancel_extra_ms", m, median=statistics.median(free), p90=p90(free), n=3)
    if "f" in only:  # (f) two models at once: second model's first token while the first generates
        other = cfg.models.roles
        async with s.lease(Priority.TASK, m) as l1:
            await c.chat(l1, msgs, num_predict=1)
        solo = await _first_token(c, s, other)
        async def gen() -> None:
            async with Scheduler().lease(Priority.TASK, m) as l2:  # deliberate second lane, measurement only
                await c.chat(l2, [{"role": "user", "content": "Write 300 words."}], num_predict=400)
        t = asyncio.create_task(gen())
        await asyncio.sleep(2)
        both = await _first_token(c, Scheduler(), other)
        await t
        out("f_parallel_first_token_ms", other, solo=solo, with_other_generating=both)
    if "g" in only:
        async with s.lease(Priority.BACKGROUND, cfg.models.embed) as le:
            v = await c.embed(le, ["árvíztűrő tükörfúrógép"])
        out("g_embed_dim", cfg.models.embed, dim=len(v[0]) if v else 0)
    if "h" in only:
        async with s.lease(Priority.TASK, cfg.models.roles) as lr:
            await c.chat(lr, msgs, num_predict=1)
        ps = {x.get("name"): x for x in await c.loaded_models()}
        x = next((v for k, v in ps.items() if k and k.startswith(cfg.models.roles)), {})
        out("h_ram_bytes", cfg.models.roles, size=x.get("size"), size_vram=x.get("size_vram"))
    await c.aclose()
    return 0


async def _first_token(c: OllamaClient, s: Scheduler, model: str) -> int | None:
    async with s.lease(Priority.TASK, model) as lz:
        r = await c.chat(lz, [{"role": "user", "content": "Say OK."}], num_predict=2)
    return r.stats.first_token_ms


if __name__ == "__main__":
    _ = parse_json
    raise SystemExit(asyncio.run(main()))
