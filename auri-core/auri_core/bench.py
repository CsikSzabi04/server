"""bench: measure Auri on the aurikod-hu task set (owner: AI-2).

Spec: ideas_for_brain/thinking/06-programozas/09-meres-es-benchmark.md (§3 metrics, §4 protocol,
§5 result format, §7 honesty). CLI (via `python -m auri_core bench …`):

    bench --mode model-only|+repair|+roles --split dev --lang py [--model gemma4:e2b] [--limit N] [--tasks id,id]
    bench --suite e5|research [--model …] [--limit N]        (P5 projects / P2 research: auri_core/evals.py)
          [--prompt-lang en|hu] [--resume <bench_id>]

* model-only: one generation, no repair (pass@1);  +repair: ≤ 3 repair rounds on VISIBLE feedback (javítással@3).
* The verdict always comes from the HIDDEN tests, run here on the final solution — the loop never sees them.
* No memory, no learning (a measurement must not change the store), temperature 0, fixed seed,
  BACKGROUND priority (the user's VOICE/CHAT always wins the Ollama lane).
* Every task result is appended to data/eval/<bench_id>/results.jsonl at once → a long run can resume.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from auri_core.contracts import CodeTask, Outcome, Priority, RunResult, SolveOptions

TASKSET_VERSION = "aurikod-hu-v1"
MODES = {"model-only": 0, "+repair": 3, "+roles": 3, "+cloud": 3}
METRIC = {"model-only": "pass1", "+repair": "pass_repair3", "+roles": "pass_roles3",  # +roles: P3 (evals.py)
          "+cloud": "pass_cloud"}  # +cloud: L4 rescue on top of a finished +repair run (cloud_bench.py)
INFRA_PREFIX = "infrastruktúra"  # solve / debate / research reason_hu for an unreachable Ollama, hash mismatch, …
INFRA_RETRY_S = (30, 60, 90)  # an Ollama restart takes ~15 s; after these the run stops (resume later)


def is_infra(row: dict[str, Any]) -> bool:
    """Not the model's failure: never counted as a fail — retried, dropped on --resume (06/09 §7)."""
    return str(row.get("reason_hu") or row.get("reason") or "").startswith(INFRA_PREFIX)


def load_resumable(path: Path) -> list[dict[str, Any]]:
    """Rows of an earlier run minus infrastructure failures (rewritten in place, so they run again)."""
    rows = _load_rows(path)
    keep = [r for r in rows if not is_infra(r)]
    if len(keep) != len(rows):
        print(f"{len(rows) - len(keep)} infrastruktúra-hibás sor eldobva, újrafut.", flush=True)
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keep), encoding="utf-8")
    return keep


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes out of n (06/09 §7)."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def _p90(xs: list[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    return s[min(len(s) - 1, math.ceil(0.9 * len(s)) - 1)]


def hidden_tests(task: CodeTask) -> dict[str, str]:
    """The hidden test file — read ONLY here (06/09 §8.1); never passed to the solving loop."""
    root = Path(task.root or "")
    return {task.files.hidden: (root / task.files.hidden).read_text(encoding="utf-8")}


def result_row(task: CodeTask, out: Outcome, hidden: RunResult | None, *, mode: str, bench_id: str) -> dict[str, Any]:
    ok = hidden is not None and hidden.status == "pass"
    return {
        "run_id": bench_id, "task_id": task.id, "split": task.split, "lang": task.lang, "level": task.level,
        "mode": mode, "model": out.model, "prompt_ver": out.prompt_ver, "taskset": TASKSET_VERSION,
        METRIC[mode]: ok,
        "outcome": out.kind, "end_state": str(out.end_state), "rounds": out.rounds, "no_progress": out.no_progress,
        "kb_hit": out.snippet_id if out.from_memory else None,
        "wall_ms": out.wall_ms, "gen_ms": out.gen_ms, "sandbox_ms": out.sandbox_ms + (hidden.duration_ms if hidden else 0),
        "tokens_out": out.tokens_out, "tokens_in": out.tokens_in, "llm_calls": out.llm_calls,
        "visible": out.last_run.status if out.last_run else None,
        "hidden": {"status": hidden.status if hidden else None, "passed": hidden.passed if hidden else 0,
                   "total": len(hidden.tests) if hidden else 0},
        # 06/09 §3: a success claim without a green run — must always be 0
        "false_done": out.kind == "pass" and (out.last_run is None or out.last_run.status != "pass"),
        "visible_pass_hidden_fail": out.kind == "pass" and not ok,
        "sandbox": hidden.sandbox if hidden else None, "env": asdict(hidden.env) if hidden else None,
        "solve_run_id": out.run_id, "reason_hu": out.reason_hu, "cloud_calls": 0,
    }


async def bench_task(task: CodeTask, *, mode: str, llm: Any, sandbox: Any, scheduler: Any, model: str | None,
                     prompt_lang: str = "en", runs_dir: Path | None = None, bench_id: str = "",
                     prompt_variant: str | None = None) -> dict[str, Any]:
    from auri_core.solve import solve  # AI-1's loop

    if mode == "+roles":  # P3: the debate protocol instead of the P0 loop
        from auri_core.evals import bench_roles_task

        return await bench_roles_task(task, llm=llm, sandbox=sandbox, scheduler=scheduler, model=model,
                                      prompt_lang=prompt_lang, runs_dir=runs_dir, bench_id=bench_id)
    opts = SolveOptions(repair_rounds=MODES[mode], use_memory=False, learn=False, model=model, temperature=0.0, seed=42,
                        prompt_lang=prompt_lang, prompt_variant=prompt_variant,  # type: ignore[arg-type]
                        priority=Priority.BACKGROUND)
    out = await solve(task, llm=llm, sandbox=sandbox, store=None, scheduler=scheduler, opts=opts, runs_dir=runs_dir)
    hidden = None
    if out.files:
        hidden = await sandbox.run_tests(out.files, hidden_tests(task), task.lang, task.limits.wall_s, mem_mb=task.limits.mem_mb)
    return result_row(task, out, hidden, mode=mode, bench_id=bench_id)


def summarize(rows: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    key = METRIC[mode]
    n = len(rows)
    k = sum(bool(r.get(key)) for r in rows)
    lo, hi = wilson(k, n)
    wall = [r["wall_ms"] / 1000 for r in rows]
    by_level: dict[str, Any] = {}
    for lvl in sorted({r["level"] for r in rows}):
        rs = [r for r in rows if r["level"] == lvl]
        kk = sum(bool(r.get(key)) for r in rs)
        by_level[f"L{lvl}"] = {"n": len(rs), "passed": kk, "rate": round(kk / len(rs), 3)}
    return {
        "mode": mode, "metric": key, "n": n, "passed": k, "rate": round(k / n, 3) if n else 0.0,
        "ci95": [round(lo, 3), round(hi, 3)], "by_level": by_level,
        "wall_s_median": round(statistics.median(wall), 1) if wall else 0.0, "wall_s_p90": round(_p90(wall), 1),
        "llm_calls_mean": round(statistics.mean(r["llm_calls"] for r in rows), 2) if rows else 0.0,
        "tokens_out_mean": round(statistics.mean(r["tokens_out"] for r in rows), 1) if rows else 0.0,
        "rounds_mean_passed": round(statistics.mean([r["rounds"] for r in rows if r.get(key)] or [0]), 2),
        "no_progress": sum(r["no_progress"] for r in rows),
        "false_done": sum(r["false_done"] for r in rows),
        "visible_pass_hidden_fail": sum(r["visible_pass_hidden_fail"] for r in rows),
    } | (_roles_extra(rows) if mode == "+roles" else {}) | (_cloud_extra(rows) if mode == "+cloud" else {})


def _roles_extra(rows: list[dict[str, Any]]) -> dict[str, Any]:
    from auri_core.evals import roles_extra

    return roles_extra(rows)


def _cloud_extra(rows: list[dict[str, Any]]) -> dict[str, Any]:
    from auri_core.cloud_bench import cloud_extra

    return cloud_extra(rows)


def markdown(meta: dict[str, Any], s: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    key = s["metric"]
    lines = [
        f"## Mérés: {meta['taskset']} · {meta['split']} · {meta['lang']} · {s['mode']} · {meta['model']}",
        "",
        f"- **{key}: {s['passed']}/{s['n']} = {s['rate']:.1%}** (95% Wilson: {s['ci95'][0]:.1%}–{s['ci95'][1]:.1%})",
        "- szintenként: " + ", ".join(f"{lv} {v['passed']}/{v['n']}" for lv, v in s["by_level"].items()),
        f"- falióra feladatonként: medián {s['wall_s_median']} s, p90 {s['wall_s_p90']} s; LLM-hívás átlag {s['llm_calls_mean']}",
        f"- hamis „kész”: **{s['false_done']}** (célérték 0) · látható zöld, rejtett piros: {s['visible_pass_hidden_fail']}"
        f" · nincs előrelépés: {s['no_progress']}",
        f"- bench_id: `{meta['bench_id']}` · prompt: {meta.get('prompt_lang')} {meta.get('prompt_variant') or 'v1'}"
        f" · sandbox: {meta.get('sandbox')}",
        *([f"- helyi +repair: {s['local_passed']}/{s['n']} · felhő ({meta.get('cloud_model')}, alap: {meta.get('base')}): "
           f"{s['cloud_tried']} próba, {s['cloud_answered']} válasz, **{s['cloud_rescued']} mentve**, "
           f"{s['cloud_refused']} nem válaszolt/elutasított"] if "cloud_rescued" in s else []),
        *([f"- Kritikus: pontosság {s['critic_accuracy']} ({s['critic_judged']} ítélet; hamis elfogadás {s['critic_false_accept']}, vaklárma {s['critic_false_alarm']}) · Kérdező: {s['kerdezo_used']} · visszaállítva zöldre: {s['reverted_to_green']}"] if "critic_judged" in s else []),
        "",
        "| feladat | szint | eredmény | körök | idő (s) | rejtett |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        h = r["hidden"]
        lines.append(f"| {r['task_id']} | L{r['level']} | {'✅' if r.get(key) else '❌'} {r['outcome']} | {r['rounds']} "
                     f"| {r['wall_ms'] / 1000:.0f} | {h['passed']}/{h['total']} |")
    return "\n".join(lines) + "\n"


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


async def _main_async(a: argparse.Namespace) -> int:
    if a.mode == "+cloud":  # no Ollama: only the tasks a finished +repair run failed go to the cloud
        from auri_core.cloud_bench import main_cloud

        return await main_cloud(a)
    from auri_core import config, llm, sandbox, scheduler, taskset

    cfg = config.load_config()
    tasks = list(taskset.iter_tasks(a.split, a.lang, a.tasks_dir))
    if a.tasks:
        wanted = set(a.tasks.split(","))
        tasks = [t for t in tasks if t.id in wanted]
    if a.limit:
        tasks = tasks[: a.limit]
    if not tasks:
        print("Nincs a szűrésnek megfelelő feladat.", file=sys.stderr)
        return 2
    variant = f"_{a.prompt_variant}" if a.prompt_variant else ""
    bench_id = a.resume or f"bench_{time.strftime('%Y%m%dT%H%M%S')}_{a.lang}_{a.mode.strip('+')}{variant}"
    out_dir = cfg.data_dir / "eval" / bench_id
    out_dir.mkdir(parents=True, exist_ok=True)
    results = out_dir / "results.jsonl"
    rows = load_resumable(results)
    done = {r["task_id"] for r in rows}
    model = a.model or cfg.models.code
    sb = sandbox.create_sandbox()
    meta = {"bench_id": bench_id, "taskset": TASKSET_VERSION, "split": a.split, "lang": a.lang, "mode": a.mode,
            "model": model, "prompt_lang": a.prompt_lang, "prompt_variant": a.prompt_variant, "sandbox": sb.level,
            "temperature": 0.0 if a.mode != "+roles" else "szerepenként", "seed": 42,
            "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "n_tasks": len(tasks)}
    if a.resume and (out_dir / "meta.json").is_file():  # a resume must continue the SAME measurement
        old = json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))
        diff = [k for k in ("split", "lang", "mode", "model", "prompt_lang", "prompt_variant") if old.get(k) != meta.get(k)]
        if diff:
            print(f"A --resume más beállítással indult, mint az eredeti mérés: {diff}", file=sys.stderr)
            return 2
        meta["started"], meta["resumed"] = old.get("started"), meta["started"]
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    client = llm.OllamaClient()
    try:
        for i, task in enumerate(tasks, 1):
            if task.id in done:
                continue
            for wait_s in (*INFRA_RETRY_S, None):
                row = await bench_task(task, mode=a.mode, llm=client, sandbox=sb, scheduler=scheduler.get_scheduler(),
                                       model=model, prompt_lang=a.prompt_lang, runs_dir=cfg.runs_dir, bench_id=bench_id,
                                       prompt_variant=a.prompt_variant)
                if not is_infra(row):
                    break
                if wait_s is None:
                    print(f"Infrastruktúra-hiba ({row.get('reason_hu')}); a mérés leáll, nem számolom bukásnak. "
                          f"Folytatás: --resume {bench_id}", file=sys.stderr)
                    return 3
                print(f"[{i}/{len(tasks)}] {task.id}: infrastruktúra-hiba, újra {wait_s} s múlva", flush=True)
                await asyncio.sleep(wait_s)
            rows.append(row)
            with results.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            key = METRIC[a.mode]
            print(f"[{i}/{len(tasks)}] {task.id}: {'OK ' if row[key] else 'BUK'} {row['outcome']} "
                  f"{row['wall_ms'] / 1000:.0f} s, rejtett {row['hidden']['passed']}/{row['hidden']['total']}", flush=True)
    finally:
        await client.aclose()
    s = summarize(rows, a.mode)
    (out_dir / "summary.json").write_text(json.dumps({**meta, **s}, ensure_ascii=False, indent=1), encoding="utf-8")
    md = markdown(meta, s, rows)
    (out_dir / "report.md").write_text(md, encoding="utf-8")
    print(md)
    return 0 if s["false_done"] == 0 else 1


def heldout_guard(a: argparse.Namespace, eval_dir: Path | None = None, now: float | None = None) -> str:
    """'' if a heldout run may start: --official, intact frozen manifest, at most one run/week/lang/mode (06/09 §2)."""
    from auri_core import config, taskset

    if not a.official:
        return "A heldout csak hivatalos méréshez futhat: --official (a felhasználó jóváhagyásával, tétlen gépen)."
    if bad := taskset.verify_heldout(a.tasks_dir):
        return "A heldout eltér a befagyasztott manifeszttől:\n  " + "\n  ".join(bad[:10])
    if a.resume:
        return ""
    eval_dir = eval_dir or config.load_config().data_dir / "eval"
    now = time.time() if now is None else now
    for meta in eval_dir.glob("*/meta.json") if eval_dir.is_dir() else ():
        m = json.loads(meta.read_text(encoding="utf-8"))
        started = time.mktime(time.strptime(m.get("started", "1970-01-01T00:00:00"), "%Y-%m-%dT%H:%M:%S"))
        if (m.get("split"), m.get("lang"), m.get("mode")) == ("heldout", a.lang, a.mode) and now - started < 7 * 86400:
            return f"Ezen a héten már volt heldout-mérés ({m.get('bench_id')}); hetente legfeljebb egy (06/09 §2)."
    return ""


def main_bench(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m auri_core bench", description="Mérés az aurikod-hu feladatkészleten (06/09).")
    ap.add_argument("--mode", choices=sorted(MODES), default="model-only")
    ap.add_argument("--split", default="dev", choices=["dev", "heldout", "practice", "regression"])
    ap.add_argument("--lang", default="py", choices=["py", "ts", "js", "sql"])
    ap.add_argument("--model", default=None, help="alap: a config kódoló modellje")
    ap.add_argument("--limit", type=int, default=0, help="csak az első N feladat")
    ap.add_argument("--tasks", default="", help="vesszővel elválasztott feladat-azonosítók")
    ap.add_argument("--prompt-lang", choices=["en", "hu"], default="en", help="belső promptnyelv (NK18 A/B)")
    ap.add_argument("--prompt-variant", default=None, help="promptváltozat A/B-hez, pl. v2 → prompts/code.<nyelv>.v2.txt (alap: v1)")
    ap.add_argument("--resume", default="", help="egy korábbi bench_id folytatása")
    ap.add_argument("--from-bench", default="", help="+cloud: az alapmérés bench_id-ja (dev +repair; a bukott feladatok mennek a felhőbe)")
    ap.add_argument("--suite", choices=["aurikod", "e5", "research"], default="aurikod",
                    help="aurikod: feladatkészlet (alap) · e5: P5 mini-projektek · research: P2 webes kutatás")
    ap.add_argument("--official", action="store_true", help="hivatalos heldout-mérés (jóváhagyással, tétlen gépen)")
    ap.add_argument("--tasks-dir", default=None, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows console (cp1250) vs ✅ ❌ „”
    if a.suite != "aurikod":
        from auri_core.evals import main_suite

        return asyncio.run(main_suite(a))
    if a.split == "heldout" and (err := heldout_guard(a)):
        print(err, file=sys.stderr)
        return 2
    try:
        return asyncio.run(_main_async(a))
    except KeyboardInterrupt:
        print("\nMegszakítva — folytatás: --resume <bench_id>", file=sys.stderr)
        return 130
