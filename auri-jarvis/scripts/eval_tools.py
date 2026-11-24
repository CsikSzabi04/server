"""eval_tools.py — which local model calls our tools correctly in Hungarian? (AI-2 / M2)

For each candidate model: the 30 commands of tests/fixtures/eval/tools_hu.yaml go through
the REAL Mind prompt (persona + fictional logged-in profile + seed + the fixed tool schemas,
warmed exactly like JarvisMind) on the LLM path — the fast-path is bypassed on purpose,
because this measures the model. Only the FIRST round is judged (tool name + arguments, or
"no tool" for chat questions); no tool is executed. Then the 5 chat questions are answered
and saved for human scoring.

DoD M2: accuracy ≥ 85 %. Winner = highest accuracy, then lowest first-token median.

Usage (from auri-jarvis/):
  .venv\\Scripts\\python scripts\\eval_tools.py                    # gemma4:e2b gemma4:e4b qwen3.5:4b
  .venv\\Scripts\\python scripts\\eval_tools.py --models gemma4:e2b --only 1-5
Results: table on stdout, JSON + chat answers (Markdown) in data/mind/eval/.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # run as a plain script from auri-jarvis/

from auri_jarvis.mind import fastpath  # noqa: E402
from auri_jarvis.mind import prompts as P  # noqa: E402
from auri_jarvis.mind.hu_text import digitize, norm, parse_when  # noqa: E402
from auri_jarvis.mind.ollama_provider import ChatOptions, LLMError, OllamaProvider, ToolCall  # noqa: E402
from auri_jarvis.tools.apps import AppCatalog  # noqa: E402
from auri_jarvis.tools.builtin import build_registry  # noqa: E402

CANDIDATES = ["gemma4:e2b", "gemma4:e4b", "qwen3.5:4b"]
FIXTURE = ROOT / "tests" / "fixtures" / "eval" / "tools_hu.yaml"
PROFILE = {  # fictional (privacy rule)
    "name": "Minta Máté",
    "nickname": "Máté",
    "about": "Fejlesztő, saját projekteken dolgozik; három monitort használ (bal, közép, jobb).",
    "tone": "Magyarul, röviden.",
    "interests": ["webfejlesztés", "zene"],
}
APPS = AppCatalog.load(ROOT / "config" / "apps.yaml")


def _same(expected: Any, got: Any, key: str, now: datetime) -> bool:
    if isinstance(expected, dict):
        if "any" in expected:
            return any(_same(e, got, key, now) for e in expected["any"])
        if "contains" in expected:
            return isinstance(got, str) and norm(expected["contains"]) in norm(got)
        if "when" in expected:
            want = datetime.fromisoformat(expected["when"])
            return isinstance(got, str) and parse_when(got, now) == want
    if isinstance(expected, bool) or isinstance(got, bool):
        return bool(expected) == bool(got) if isinstance(got, bool | str) else False
    if isinstance(expected, int):
        try:
            return int(got) == expected
        except (TypeError, ValueError):
            return False
    if isinstance(expected, str):
        if not isinstance(got, str):
            return False
        if key in ("name", "app"):
            hit = APPS.resolve(got)
            return norm(got) == norm(expected) or (hit is not None and hit.entry.id == expected)
        return norm(got) == norm(expected)
    return expected == got


def judge(item: dict, calls: list[ToolCall], now: datetime, text: str = "") -> tuple[bool, str]:
    got = calls[0] if calls else None
    for exp in item["expect"]:
        if exp.get("tool") is None:
            if got is None and norm(exp.get("text_contains", "")) in norm(text):
                return True, "—"
            continue
        if got is None or got.name != exp["tool"]:
            continue
        if all(_same(v, got.arguments.get(k), k, now) for k, v in (exp.get("args") or {}).items()):
            return True, f"{got.name}({got.arguments})"
    shown = f"{got.name}({got.arguments})" if got else "nincs eszköz"
    return False, shown


async def eval_model(
    p: OllamaProvider, model: str, items: list[dict], chat: list[str], now: datetime, *, cold: bool = False
) -> dict:
    tools = build_registry().schemas()
    system = P.build_system_prompt(P.load_persona(), tier="user", address="Máté", profile=PROFILE)
    # Other sessions may be using Ollama (a live daemon): only unload on request (--cold).
    for loaded in await p.loaded_models() if cold else []:
        await p.unload(loaded.get("name"))
    t0 = time.perf_counter()
    for msgs in P.warm_sequence(system):
        await p.warmup(msgs, tools, model=model)
    warm_ms = int((time.perf_counter() - t0) * 1000)
    print(f"  warmup {warm_ms} ms", flush=True)

    ctx_now = f"{now:%Y-%m-%d %H:%M}, szombat"
    rows = []
    for i, item in enumerate(items, 1):
        # Same input path as JarvisMind._run_llm: digitize → <kontextus> + <kérés>.
        msgs = P.build_messages(system, [], P.build_user_message(digitize(item["say"]), {"idő": ctx_now}))
        text, calls, stats = await p.chat(msgs, tools, ChatOptions(model=model, num_predict=160))
        good, shown = judge(item, calls, now, text)
        # End-to-end = what the real Mind does: the fast-path first, the LLM only if it misses.
        intent = fastpath.match(item["say"], APPS)
        if intent is not None and intent.name != "cancel" and build_registry().get(intent.name):
            e2e, e2e_shown = judge(item, [ToolCall(intent.name, intent.args)], now)
            e2e_shown = "fast-path: " + e2e_shown
        else:
            e2e, e2e_shown = good, shown
        rows.append({"i": i, "say": item["say"], "ok": good, "got": shown, "e2e_ok": e2e, "e2e_got": e2e_shown,
                     "text": text.strip()[:160], "first_ms": stats.first_token_ms, "total_ms": stats.total_ms})  # fmt: skip
        mark = ("✅" if good else "❌") + ("⚡" if e2e_shown.startswith("fast-path") else " ")
        print(f"  {i:02d} {mark} {stats.first_token_ms:>5} ms  {item['say'][:48]:48} → {shown[:70]}", flush=True)

    answers = []
    for q in chat:
        msgs = P.build_messages(system, [], P.build_user_message(q, {"idő": ctx_now}))
        text, calls, stats = await p.chat(msgs, tools, ChatOptions(model=model, num_predict=160))
        answers.append({"q": q, "a": text.strip() or f"(eszközt hívott: {[c.name for c in calls]})",
                        "first_ms": stats.first_token_ms})  # fmt: skip
    if cold:
        await p.unload(model)

    firsts = [r["first_ms"] for r in rows if r["first_ms"] is not None]
    acc = sum(r["ok"] for r in rows) / len(rows)
    return {
        "model": model,
        "accuracy": round(acc * 100, 1),
        "correct": sum(r["ok"] for r in rows),
        "e2e_accuracy": round(sum(r["e2e_ok"] for r in rows) / len(rows) * 100, 1),
        "e2e_correct": sum(r["e2e_ok"] for r in rows),
        "n": len(rows),
        "first_median_ms": statistics.median(firsts) if firsts else None,
        "warmup_ms": warm_ms,
        "rows": rows,
        "chat": answers,
    }


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", default=CANDIDATES)
    ap.add_argument("--only", help="subset of items, e.g. 1-5")
    ap.add_argument("--cold", action="store_true", help="unload all models first (disturbs other users of Ollama)")
    args = ap.parse_args()

    fx = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    now = datetime.fromisoformat(fx["now"])
    items = fx["items"]
    if args.only:
        a, b = (int(x) for x in args.only.split("-"))
        items = items[a - 1 : b]
    cfg = yaml.safe_load((ROOT / "config" / "mind.yaml").read_text(encoding="utf-8")) or {}
    p = OllamaProvider(cfg.get("llm", {}))

    results = []
    for model in args.models:
        print(f"\n== {model}", flush=True)
        try:
            results.append(await eval_model(p, model, items, fx.get("chat", []), now, cold=args.cold))
        except LLMError as e:
            print("  hiba:", e.user_message, e.detail)
            results.append({"model": model, "error": e.user_message})
    await p.aclose()

    ok = [r for r in results if "error" not in r]
    print(
        "\n| modell | csak LLM | végponttól végpontig (fast-path + LLM) | 1. eszköz/token medián | bemelegítés |"
        "\n|---|---|---|---|---|"
    )
    for r in ok:
        print(f"| {r['model']} | {r['correct']}/{r['n']} = {r['accuracy']} % | {r['e2e_correct']}/{r['n']} = "
              f"{r['e2e_accuracy']} % | {r['first_median_ms'] / 1000:.2f} s | {r['warmup_ms'] / 1000:.1f} s |")  # fmt: skip
    if ok:
        best = sorted(ok, key=lambda r: (-r["accuracy"], r["first_median_ms"] or 1e9))[0]
        verdict = "✅ teljesíti" if best["accuracy"] >= 85 else "❌ NEM éri el"
        print(f"\nNyertes (csak LLM): {best['model']} ({best['accuracy']} %, {verdict} a 85 %-os kaput; "
              f"végponttól végpontig {best['e2e_accuracy']} %).")  # fmt: skip

    out_dir = ROOT / "data" / "mind" / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (out_dir / f"eval_tools_{stamp}.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    md = ["# Csevegési minőség — pontozd 1–5-ig (5 = természetes, helyes magyar)\n"]
    for r in ok:
        md.append(f"\n## {r['model']}\n")
        for a in r["chat"]:
            md.append(f"- **{a['q']}**\n  > {a['a']}\n  Pont: __\n")
    (out_dir / f"chat_{stamp}.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nJSON + csevegés: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
