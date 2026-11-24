"""bench --mode +cloud: what the L4 cloud rescue adds on top of a finished local +repair run (08/03, P6).

    bench --mode +cloud --from-bench <a dev +repair bench_id>

No Ollama is used. Tasks the base run passed are copied as passed; every task it failed gets exactly ONE cloud
attempt (one generation + at most one JSON fix, `solve._cloud_attempt`), checked by the SAME visible tests in the
local sandbox and judged by the hidden tests the cloud never saw. Same honesty rules as bench (06/09): the cloud
answer counts only if the local sandbox says green; a refusal (personal data, secret, quota) is a fail, not a skip.

Guard rails: the heldout split is refused (it is a one-shot measure, not for tuning an escalation); the daily cloud
cap is raised for THIS run only, and only to what the failed tasks can use (2 calls each); the Groq key comes from
the environment / auri-core/.env (AURI_CORE_GROQ_API_KEY) and is never printed or written to a result.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

from auri_core.contracts import EndState, Outcome, Priority, SolveOptions

CALLS_PER_TASK = 2  # l4.MAX_CALLS: one generation + at most one JSON fix


def cloud_extra(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summary extras for +cloud (merged into bench.summarize)."""
    tried = [r for r in rows if r.get("cloud_used")]
    return {
        "local_passed": sum(bool(r.get("local_pass")) for r in rows),
        "cloud_tried": len(tried),
        "cloud_answered": sum(bool(r.get("cloud_answered")) for r in tried),
        "cloud_rescued": sum(bool(r.get("pass_cloud")) for r in tried),
        "cloud_refused": sum(not r.get("cloud_answered") for r in tried),
    }


def cloud_visible(task: Any) -> dict[str, str]:
    """The VISIBLE tests as they may leave the machine: the dev/heldout `AURI-CANARY-<guid>` line is dropped.
    It is a leak marker for OUR store (09 §8.2), not a secret — but the privacy gate rightly reads a guid as a
    high-entropy key and would refuse every request. It is a comment, so the tests themselves do not change.
    The production gate stays strict; only the bench strips the marker."""
    from auri_core.solve import load_visible_tests
    from auri_core.taskset import CANARY_RE

    line = re.compile(r"(?m)^[^\n]*" + CANARY_RE.pattern + r"[^\n]*\n?")
    return {p: line.sub("", t) for p, t in load_visible_tests(task).items()}


def passed_row(base: dict[str, Any], bench_id: str) -> dict[str, Any]:
    """A task the local run already passed: no cloud, same verdict."""
    return {**base, "run_id": bench_id, "mode": "+cloud", "pass_cloud": True, "local_pass": True, "cloud_used": False,
            "cloud_answered": False, "cloud_calls": 0}


async def rescue_row(task: Any, base: dict[str, Any], *, gate: Any, sandbox: Any, runs_dir: Path | None, bench_id: str,
                     prompt_lang: str = "en") -> dict[str, Any]:
    """One cloud attempt for a task the local run failed; the row carries the hidden-test verdict."""
    from auri_core.bench import hidden_tests, result_row
    from auri_core.solve import _cloud_attempt

    stub = Outcome(task_id=task.id, kind="give_up", end_state=EndState.GIVE_UP, files={}, last_run=None,
                   run_id=str(base.get("solve_run_id") or ""), model=str(base.get("model") or ""),
                   reason_hu=base.get("reason_hu"))
    opts = SolveOptions(repair_rounds=0, use_memory=False, learn=False, model=str(base.get("model") or "") or None,
                        temperature=0.0, seed=42, prompt_lang=prompt_lang,  # type: ignore[arg-type]
                        priority=Priority.CHAT)
    # _cloud_attempt swaps in its own llm (CloudLLM), scheduler (NoLane) and store (None): these are placeholders
    kw = {"llm": None, "sandbox": sandbox, "store": None, "scheduler": None, "visible": cloud_visible(task),
          "runs_dir": runs_dir, "router": None, "on_event": None}
    out = await _cloud_attempt(task, stub, gate, opts=opts, kw=kw)
    answered = str(out.model).startswith("cloud:")
    hidden = None
    if answered and out.files:
        hidden = await sandbox.run_tests(out.files, hidden_tests(task), task.lang, task.limits.wall_s,
                                         mem_mb=task.limits.mem_mb)
    row = result_row(task, out, hidden, mode="+cloud", bench_id=bench_id)
    row.update(local_pass=False, cloud_used=True, cloud_answered=answered, cloud_calls=CALLS_PER_TASK if answered else 0)
    if not answered:  # refused / no reply: a fail with the reason, never a green
        row["pass_cloud"] = False
    return row


def _load_base(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]] | str:
    meta_p, res_p = path / "meta.json", path / "results.jsonl"
    if not meta_p.is_file() or not res_p.is_file():
        return f"Nincs ilyen alapmérés: {path}"
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    if meta.get("mode") != "+repair":
        return f"Az alapmérés módja {meta.get('mode')!r}, de +repair kell (a felhő a helyi javítás után jön)."
    if meta.get("split") == "heldout":
        return "A heldout nem használható a felhős eszkaláció mérésére (egyszeri mérés, nem hangolásra való). Dev kell."
    rows = [json.loads(line) for line in res_p.read_text(encoding="utf-8").splitlines() if line.strip()]
    return meta, rows


async def main_cloud(a: argparse.Namespace) -> int:
    from auri_core import config, sandbox, taskset
    from auri_core.bench import TASKSET_VERSION, load_resumable, markdown, summarize
    from auri_core.cloud.client import CloudClient
    from auri_core.l4 import CloudGate
    from auri_core.store import SqliteCodeMemory

    if not a.from_bench:
        print("A +cloud módhoz kell az alapmérés: --from-bench <bench_id> (egy dev +repair mérés).", file=sys.stderr)
        return 2
    cfg = config.load_config()
    eval_dir = cfg.data_dir / "eval"
    base = _load_base(eval_dir / a.from_bench)
    if isinstance(base, str):
        print(base, file=sys.stderr)
        return 2
    base_meta, base_rows = base
    if not cfg.groq_api_key:
        print("Nincs Groq-kulcs (AURI_CORE_GROQ_API_KEY az auri-core/.env-ben vagy a környezetben); nem küldök semmit.",
              file=sys.stderr)
        return 2
    by_id = {t.id: t for t in taskset.iter_tasks(base_meta["split"], base_meta["lang"], a.tasks_dir)}
    if a.tasks:
        wanted = set(a.tasks.split(","))
        base_rows = [r for r in base_rows if r["task_id"] in wanted]
    if a.limit:
        base_rows = base_rows[: a.limit]
    failed = [r for r in base_rows if not r.get("pass_repair3") and r["task_id"] in by_id]
    bench_id = a.resume or f"bench_{time.strftime('%Y%m%dT%H%M%S')}_{base_meta['lang']}_cloud"
    out_dir = eval_dir / bench_id
    out_dir.mkdir(parents=True, exist_ok=True)
    results = out_dir / "results.jsonl"
    rows = load_resumable(results)
    done = {r["task_id"] for r in rows}
    sb = sandbox.create_sandbox()
    meta = {"bench_id": bench_id, "taskset": TASKSET_VERSION, "split": base_meta["split"], "lang": base_meta["lang"],
            "mode": "+cloud", "model": base_meta["model"], "prompt_lang": base_meta.get("prompt_lang"),
            "prompt_variant": base_meta.get("prompt_variant"), "sandbox": sb.level, "base": a.from_bench,
            "cloud_model": cfg.cloud_model or "gpt-oss-120b (Groq)", "cloud_temperature": 0.2,
            "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "n_tasks": len(base_rows)}
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    run_cfg = dataclasses.replace(cfg, cloud_mode="ask", cloud_daily_cap=CALLS_PER_TASK * len(failed) + 2)
    store = SqliteCodeMemory(out_dir / "cloud.db")  # own quota/audit tables: a measurement does not touch core.db
    client = CloudClient(run_cfg, store)
    gate = CloudGate(client, user_id="bench", consent=True, live=True)
    try:
        for i, base_row in enumerate(base_rows, 1):
            tid = base_row["task_id"]
            if tid in done or tid not in by_id:
                continue
            if base_row.get("pass_repair3"):
                row = passed_row(base_row, bench_id)
            else:
                row = await rescue_row(by_id[tid], base_row, gate=gate, sandbox=sb, runs_dir=cfg.runs_dir,
                                       bench_id=bench_id, prompt_lang=str(base_meta.get("prompt_lang") or "en"))
            rows.append(row)
            with results.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            tag = "helyi OK" if row["local_pass"] else ("MENTVE" if row["pass_cloud"] else "BUK")
            print(f"[{i}/{len(base_rows)}] {tid}: {tag}"
                  + ("" if row["local_pass"] else f" · {row['outcome']} · rejtett {row['hidden']['passed']}/{row['hidden']['total']}"
                     + ("" if row["cloud_answered"] else f" · felhő nem válaszolt: {row.get('reason_hu')}")),
                  flush=True)
    finally:
        await client.aclose()
        store.close()
    s = summarize(rows, "+cloud")
    (out_dir / "summary.json").write_text(json.dumps({**meta, **s}, ensure_ascii=False, indent=1), encoding="utf-8")
    md = markdown(meta, s, rows)
    (out_dir / "report.md").write_text(md, encoding="utf-8")
    print(md)
    return 0 if s["false_done"] == 0 else 1
