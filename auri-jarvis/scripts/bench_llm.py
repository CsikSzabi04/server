"""bench_llm.py — first-token latency the way JarvisMind really runs (AI-2 / M0).

For each candidate model:
  1. STARTUP: unload everything, then warmup(system + seed request) = cold load + prefill
  2. INDEPENDENT questions (default 20): each a new session resuming from the warm seed
     → first token median / p90, prefill ms, tok/s  (DoD M1: median ≤ 2 s)
  3. SESSION: append-only follow-ups (default 5) → first token as a conversation grows
  4. MISS: the static prefix changed (different address) → one full re-prefill
  5. RAM of the loaded model (/api/ps), then unload it before the next model
Why this layout: see prompts.SEED_REQUEST (measured KV-cache resume behaviour).

The prefix is the real one from mind/prompts.py (persona + a sample logged-in profile)
plus a representative set of ~12 tool schemas (spec 5.6), because Ollama renders the
tool list into the cached prefix too.

Usage (from auri-jarvis/):
  py -3.12 scripts/bench_llm.py                         # default candidates, 20 warm runs
  py -3.12 scripts/bench_llm.py --models gemma2:2b --runs 5
Results: Markdown table on stdout + JSON in data/mind/bench/.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # run as a plain script from auri-jarvis/

from auri_jarvis.mind import prompts as P  # noqa: E402
from auri_jarvis.mind.ollama_provider import ChatOptions, LLMError, LLMStats, OllamaProvider  # noqa: E402

CANDIDATES = ["qwen3.5:4b", "gemma4:e4b", "gemma4:e2b"]

# A synthetic (non-personal) profile of realistic size for the logged-in prefix.
SAMPLE_PROFILE = {
    "name": "Minta Máté",
    "nickname": "Máté",
    "about": (
        "Mérnökinformatikus hallgató és full-stack fejlesztő. Saját SaaS-terméken és egy helyi "
        "AI-asszisztensen dolgozik, mellette egyetemre jár és oktatóvideókat készít. Szereti a "
        "horrorjátékokat, a sötét, üveghatású felületeket és a gyors, pontos válaszokat."
    ),
    "tone": "Magyarul, röviden, közvetlenül; egy ajánlás a lista helyett; őszinte kolléga.",
    "interests": [
        "webfejlesztés",
        "helyi AI",
        "SaaS",
        "horror és gaming",
        "írás",
        "kerékpározás",
    ],
}

QUESTIONS = [
    "Mondj egy mondatot a mai napról.",
    "Mi a különbség a RAM és az SSD között, röviden?",
    "Adj egy tippet, hogyan koncentráljak jobban.",
    "Mit javasolsz vacsorára, ha fáradt vagyok?",
    "Mi az a KV-cache, egy mondatban?",
    "Hogyan kezdjek bele egy új React-projektbe?",
    "Mondj egy rövid motiváló mondatot.",
    "Mi a fővárosa Ausztráliának?",
    "Hány perc egy pomodoro?",
    "Miért fontos a biztonsági mentés?",
]


def _fn(
    name: str,
    desc: str,
    props: dict[str, Any] | None = None,
    req: list[str] | None = None,
) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": props or {},
                "required": req or [],
            },
        },
    }


_S = {"type": "string"}
_I = {"type": "integer"}
BENCH_TOOLS = [
    _fn("get_time", "Aktuális idő és dátum."),
    _fn(
        "open_app",
        "Allowlistes alkalmazás megnyitása, opcionálisan egy monitoron.",
        {
            "name": _S,
            "monitor": {**_I, "enum": [1, 2, 3]},
            "fullscreen": {"type": "boolean"},
        },
        ["name"],
    ),
    _fn(
        "open_url",
        "Weboldal vagy URL-alias megnyitása Chrome-ban.",
        {"url_or_alias": _S, "monitor": _I, "app_window": {"type": "boolean"}},
        ["url_or_alias"],
    ),
    _fn(
        "move_window",
        "Egy app ablakának áthelyezése monitorra.",
        {
            "app": _S,
            "monitor": _I,
            "mode": {**_S, "enum": ["normal", "maximized", "fullscreen"]},
        },
        ["app", "monitor"],
    ),
    _fn(
        "media_control",
        "Médiavezérlés.",
        {"action": {**_S, "enum": ["play_pause", "next", "previous"]}},
        ["action"],
    ),
    _fn(
        "play_music",
        "Zene lejátszása keresőszóval vagy URI-val.",
        {"query_or_uri": _S},
        ["query_or_uri"],
    ),
    _fn(
        "set_volume",
        "Hangerő beállítása.",
        {"level": _I, "change": {**_S, "enum": ["up", "down", "mute", "unmute"]}},
    ),
    _fn("set_timer", "Időzítő indítása.", {"seconds": _I, "label": _S}, ["seconds"]),
    _fn(
        "set_reminder",
        "Emlékeztető egy időpontra.",
        {"when": _S, "text": _S},
        ["when", "text"],
    ),
    _fn("system_status", "CPU, RAM, lemez és Ollama állapota."),
    _fn("project_status", "Egy projekt git-állapota.", {"name": _S}),
    _fn("remember", "Tény megjegyzése a felhasználóról.", {"fact": _S}, ["fact"]),
    _fn("run_routine", "Rutin futtatása.", {"name": _S}, ["name"]),
    _fn(
        "use_skill",
        "Ritkább skill betöltése név szerint.",
        {"name": _S, "args": _S},
        ["name"],
    ),
]


def pct(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    k = max(0, min(len(s) - 1, round(p / 100 * (len(s) - 1))))
    return s[k]


def available_ram_bytes() -> int | None:
    """System-wide available RAM. On Windows the runner's model memory doesn't show up in
    any ollama process RSS (measured: 0.04 GB with gemma4 loaded), so the bench reports
    the drop in available RAM between "nothing loaded" and "model warm" instead."""
    try:
        import psutil
    except ImportError:
        return None
    return int(psutil.virtual_memory().available)


async def unload_all(p: OllamaProvider) -> None:
    for m in await p.loaded_models():
        try:
            await p.unload(m.get("name") or m.get("model"))
        except LLMError:
            pass
    for _ in range(50):  # wait until the runner really freed the RAM
        if not await p.loaded_models():
            return
        await asyncio.sleep(0.2)


def user_msg(question: str) -> str:
    return P.build_user_message(question, {"idő": time.strftime("%Y-%m-%d %H:%M")})


async def ask(
    p: OllamaProvider, model: str, system: str, history: list[tuple[str, str]], msg: str, tools: list | None, num_predict: int
) -> tuple[LLMStats, str]:
    msgs = P.build_messages(system, history, msg)
    text, _calls, stats = await p.chat(msgs, tools, ChatOptions(model=model, num_predict=num_predict))
    return stats, text


def summary(stats: list[LLMStats]) -> dict[str, float | None]:
    firsts = [float(s.first_token_ms) for s in stats if s.first_token_ms is not None]
    return {
        "first_median_ms": statistics.median(firsts) if firsts else None,
        "first_p90_ms": pct(firsts, 90),
        "prefill_median_ms": statistics.median([s.prompt_ms for s in stats]) if stats else None,
        "tok_per_s_median": statistics.median([s.tok_per_s for s in stats]) if stats else None,
    }


async def bench_model(p: OllamaProvider, model: str, runs: int, session_turns: int, tools: list | None, num_predict: int) -> dict:
    """Mirrors what JarvisMind does: warmup(seed) at startup, then turns that extend it."""
    persona = P.load_persona()
    system = P.build_system_prompt(persona, tier="user", address="Máté", profile=SAMPLE_PROFILE)
    system_miss = P.build_system_prompt(persona, tier="user", address="uram", profile=SAMPLE_PROFILE)

    # 1) startup: cold load + prefill of system + seed (+ probe), exactly like JarvisMind._warm
    await unload_all(p)
    ram_before = available_ram_bytes()
    t0 = time.perf_counter()
    warm_stats = [await p.warmup(m, tools, model=model) for m in P.warm_sequence(system)]
    cold = warm_stats[0]
    startup_ms = int((time.perf_counter() - t0) * 1000)
    print(f"  startup warmup {startup_ms} ms (load {cold.load_ms} + prefill {cold.prompt_ms} ms, {cold.prompt_tokens} tok)")

    # 2) independent questions (each = new session resuming from the seed)
    indep: list[LLMStats] = []
    sample = ""
    for i in range(runs):
        st, txt = await ask(p, model, system, [], user_msg(QUESTIONS[i % len(QUESTIONS)]), tools, num_predict)
        indep.append(st)
        sample = sample or txt.strip()
        print(f"  q{i + 1:02d} first={st.first_token_ms} ms prefill={st.prompt_ms} ms {st.tok_per_s:.1f} tok/s", flush=True)

    # 3) one growing session (append-only follow-ups)
    hist: list[tuple[str, str]] = []
    sess: list[LLMStats] = []
    for i in range(session_turns):
        msg = user_msg(QUESTIONS[(i + 3) % len(QUESTIONS)])
        st, txt = await ask(p, model, system, hist, msg, tools, num_predict)
        hist.append((msg, txt))
        sess.append(st)
        print(f"  s{i + 1:02d} first={st.first_token_ms} ms prefill={st.prompt_ms} ms ctx={st.prompt_tokens}", flush=True)

    # 4) the static prefix changed (e.g. a pref edit) → full re-prefill once
    miss, _ = await ask(p, model, system_miss, [], user_msg(QUESTIONS[0]), tools, num_predict)
    print(f"  miss first={miss.first_token_ms} ms prefill={miss.prompt_ms} ms", flush=True)

    ram = next((m for m in await p.loaded_models() if (m.get("name") or m.get("model")) == model), {})
    ram_after = available_ram_bytes()
    ram_gb = round((ram_before - ram_after) / 1e9, 2) if ram_before and ram_after else None
    await p.unload(model)

    return {
        "model": model,
        "prefix_tokens": cold.prompt_tokens,
        "startup_ms": startup_ms,
        "startup_load_ms": cold.load_ms,
        "startup_prefill_ms": cold.prompt_ms,
        "independent": {"runs": len(indep), **summary(indep)},
        "session": {"turns": len(sess), **summary(sess)},
        "miss_first_ms": miss.first_token_ms,
        "miss_prefill_ms": miss.prompt_ms,
        "ram_gb": ram_gb,  # drop in available system RAM (see available_ram_bytes)
        "ollama_ps_size_gb": round((ram.get("size") or 0) / 1e9, 2),
        "vram_gb": round((ram.get("size_vram") or 0) / 1e9, 2),
        "sample_answer": sample[:200],
        "runs_raw": {"independent": [asdict(s) for s in indep], "session": [asdict(s) for s in sess]},
    }


def table(rows: list[dict]) -> str:
    head = (
        "| modell | prefix tok | indulás (betöltés + prefill) | 1. token, független kérdés medián / p90 | "
        "1. token, munkamenet medián | tok/s | prefixváltás 1. token | RAM |\n|---|---|---|---|---|---|---|---|"
    )
    out = [head]
    for r in rows:
        if "error" in r:
            out.append(f"| {r['model']} | — | {r['error']} | | | | | |")
            continue
        ind, ses = r["independent"], r["session"]
        out.append(
            f"| {r['model']} | {r['prefix_tokens']} | {r['startup_ms'] / 1000:.1f} s "
            f"(betöltés {r['startup_load_ms'] / 1000:.1f} s) | {ind['first_median_ms'] / 1000:.2f} / "
            f"{ind['first_p90_ms'] / 1000:.2f} s | {ses['first_median_ms'] / 1000:.2f} s | "
            f"{ind['tok_per_s_median']:.1f} | {r['miss_first_ms'] / 1000:.1f} s | {r['ram_gb']} GB |"
        )
    return "\n".join(out)


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", default=CANDIDATES)
    ap.add_argument("--runs", type=int, default=20, help="independent questions")
    ap.add_argument("--session-turns", type=int, default=5, help="append-only follow-ups")
    ap.add_argument("--no-tools", action="store_true", help="prefix without tool schemas")
    ap.add_argument("--num-predict", type=int, default=None, help="default: llm.num_predict_voice")
    args = ap.parse_args()

    cfg = yaml.safe_load((ROOT / "config" / "mind.yaml").read_text(encoding="utf-8")) or {}
    llm = cfg.get("llm", {})
    num_predict = args.num_predict or int(llm.get("num_predict_voice", 160))
    p = OllamaProvider(llm)
    tools = None if args.no_tools else BENCH_TOOLS

    try:
        installed = set(await p.list_models())
    except LLMError as e:
        print(e.user_message)
        return 2

    rows: list[dict] = []
    for model in args.models:
        print(f"\n== {model}", flush=True)
        if model not in installed and f"{model}:latest" not in installed:
            rows.append({"model": model, "error": f"nincs letöltve (ollama pull {model})"})
            print("  " + rows[-1]["error"])
            continue
        try:
            rows.append(await bench_model(p, model, args.runs, args.session_turns, tools, num_predict))
        except LLMError as e:
            rows.append({"model": model, "error": e.user_message})
            print("  hiba:", e.user_message, e.detail)
    await p.aclose()

    print("\n" + table(rows))
    out_dir = ROOT / "data" / "mind" / "bench"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"bench_llm_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(
        json.dumps(
            {"tools": not args.no_tools, "num_predict": num_predict, "rows": rows},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nJSON: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
