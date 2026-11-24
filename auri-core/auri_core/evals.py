"""Real-model evaluations beyond E2 (owner: AI-2): P3 roles, P5 projects, P2 research.

    bench --mode +roles   --split dev --lang py      P3: the debate protocol (roles ON) on the dev set
    bench --suite e5                                   P5: tasks/e5 multi-file mini-projects (plan → steps → accept)
    bench --suite research                             P2: web research on fixed, stable facts (no store, no learning)

Same honesty rules as bench (06/09): the verdict comes from checks the system under test never saw (hidden tests,
hidden acceptance tests, expected keywords); no memory, no learning, BACKGROUND priority; every result row is
appended at once (data/eval/<id>/results.jsonl) so a long run can --resume.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path
from typing import Any

from auri_core.contracts import CodeTask, Priority

E5_ACCEPT = "auri_accept/test_e5_accept.py"  # its own folder: never collides with the plan's tests/

# P2: stable public facts; the answer counts as correct if it contains ANY of the keywords (case/space-insensitive).
RESEARCH_QS: list[tuple[str, str, tuple[str, ...]]] = [
    ("r01", "Melyik évben jelent meg a Python 3.0?", ("2008",)),
    ("r02", "Ki alkotta meg a Python programozási nyelvet?", ("rossum",)),
    ("r03", "Mi Magyarország legmagasabb pontja?", ("kékes",)),
    ("r04", "Hány Celsius-fokon forr a víz tengerszinten?", ("100",)),
    ("r05", "Melyik évben jelent meg a Linux kernel első verziója?", ("1991",)),
    ("r06", "Melyik HTTP-állapotkód jelenti azt, hogy a kért erőforrás nem található?", ("404",)),
    ("r07", "Melyik Python-verzióban jelent meg a str.removeprefix metódus?", ("3.9",)),
    ("r08", "Hány bájt egy kibibájt (KiB)?", ("1024",)),
]


# ── P3: bench --mode +roles ───────────────────────────────────────────────────

async def bench_roles_task(task: CodeTask, *, llm: Any, sandbox: Any, scheduler: Any, model: str | None,
                           prompt_lang: str = "en", runs_dir: Path | None = None, bench_id: str = "") -> dict[str, Any]:
    """debate_code (roles ON, ≤ 3 rounds, BACKGROUND) → the hidden tests decide. Critic accuracy from its last verdict."""
    from auri_core.bench import TASKSET_VERSION, hidden_tests
    from auri_core.roles import RolesConfig, debate_code

    cfg = RolesConfig(enabled=True, mode="idle", max_rounds=3, prompt_lang=prompt_lang)  # type: ignore[arg-type]
    t0 = time.monotonic()
    out = await debate_code(task, llm=llm, sandbox=sandbox, scheduler=scheduler, cfg=cfg, model=model,
                            priority=Priority.BACKGROUND,
                            transcript_dir=runs_dir / f"roles_{bench_id}" if runs_dir else None)
    wall = int((time.monotonic() - t0) * 1000)
    hidden = None
    if out.files:
        hidden = await sandbox.run_tests(out.files, hidden_tests(task), task.lang, task.limits.wall_s, mem_mb=task.limits.mem_mb)
    ok = hidden is not None and hidden.status == "pass"
    claimed = out.verdict == "accept"
    last = out.critiques[-1] if out.critiques else None
    return {
        "run_id": bench_id, "task_id": task.id, "split": task.split, "lang": task.lang, "level": task.level,
        "mode": "+roles", "model": model, "prompt_ver": out.prompt_ver, "taskset": TASKSET_VERSION, "pass_roles3": ok,
        "outcome": "pass" if claimed else out.verdict, "end_state": str(out.end_state), "rounds": out.rounds,
        "no_progress": False, "wall_ms": wall, "tokens_out": out.out_tokens, "llm_calls": out.llm_calls,
        "visible": out.last_run.status if out.last_run else None,
        "hidden": {"status": hidden.status if hidden else None, "passed": hidden.passed if hidden else 0,
                   "total": len(hidden.tests) if hidden else 0},
        "false_done": claimed and (out.last_run is None or out.last_run.status != "pass"),
        "visible_pass_hidden_fail": claimed and not ok, "reverted_to_green": out.reverted_to_green,
        "kerdezo": out.understanding is not None, "critiques": len(out.critiques),
        "critic_last": last.verdict if last else None,
        "critic_false_accept": bool(last and last.verdict == "accept" and not ok),
        "critic_false_alarm": bool(last and last.verdict == "revise" and ok),
        "sid": out.sid, "reason_hu": out.reason_hu,
    }


def roles_extra(rows: list[dict[str, Any]]) -> dict[str, Any]:
    judged = [r for r in rows if r.get("critic_last")]
    wrong = sum(r["critic_false_accept"] + r["critic_false_alarm"] for r in judged)
    return {"critic_judged": len(judged), "critic_accuracy": round(1 - wrong / len(judged), 3) if judged else None,
            "critic_false_accept": sum(r["critic_false_accept"] for r in judged),
            "critic_false_alarm": sum(r["critic_false_alarm"] for r in judged),
            "kerdezo_used": sum(bool(r.get("kerdezo")) for r in rows),
            "reverted_to_green": sum(bool(r.get("reverted_to_green")) for r in rows)}


# ── P5: --suite e5 ────────────────────────────────────────────────────────────

def load_e5(root: Path) -> list[dict[str, Any]]:
    out = []
    for d in sorted(p for p in (root / "e5").iterdir() if (p / "meta.json").is_file()):
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        out.append({**meta, "goal": (d / "goal_hu.md").read_text(encoding="utf-8"),
                    "accept": {E5_ACCEPT: (d / "accept" / "test_e5_accept.py").read_text(encoding="utf-8")},
                    "ref": {p.name: p.read_text(encoding="utf-8") for p in sorted((d / "ref").glob("*.py"))}})
    return out


async def run_project(p: dict[str, Any], *, llm: Any, sandbox: Any, scheduler: Any, model: str,
                      runs_dir: Path | None, bench_id: str) -> dict[str, Any]:
    """make_plan (no recipes) → execute with the real step runner → the hidden acceptance test on the final files."""
    from auri_core.planner import RecipeBook, execute, make_plan, make_replanner
    from auri_core.project import make_step_runner
    from auri_core.router import SimpleRouter

    rt = SimpleRouter(model)
    prio = Priority.BACKGROUND
    t0 = time.monotonic()
    row: dict[str, Any] = {"run_id": bench_id, "project": p["id"], "model": model, "state": "no_plan", "tasks": 0,
                           "done_steps": 0, "replans": 0, "plan_calls": 0, "tokens_out": 0, "files": [],
                           "accept": {"status": None, "passed": 0, "total": 0}, "project_pass": False, "reason": None}
    planned = await make_plan(p["goal"], llm=llm, scheduler=scheduler, router=rt, recipes=RecipeBook(None),
                              acceptance=tuple(p["acceptance"]), priority=prio)
    row.update(plan_calls=planned.llm_calls, tokens_out=planned.tokens_out, prompt_ver=planned.prompt_ver)
    if planned.ok and planned.plan is not None:
        runner = make_step_runner(llm=llm, scheduler=scheduler, sandbox=sandbox, model=model, priority=prio)
        replanner = make_replanner(llm=llm, scheduler=scheduler, router=rt, priority=prio)
        run_id = f"e5_{bench_id}_{p['id']}"
        out = await execute(planned.plan, runner=runner, replanner=replanner, run_id=run_id,
                            run_dir=runs_dir / run_id if runs_dir else None)
        row.update(state=out.state, tasks=len(out.plan.tasks), done_steps=len(out.done), replans=out.replans,
                   tokens_out=row["tokens_out"] + out.tokens_out, files=sorted(out.files), reason=out.failed_task)
        impl = {k: v for k, v in out.files.items() if not Path(k).name.startswith("test")}  # the plan's own tests stay out
        if impl:
            acc = await sandbox.run_tests(impl, p["accept"], "py", float(p["limits"]["wall_s"]), mem_mb=512)
            row["accept"] = {"status": acc.status, "passed": acc.passed, "total": len(acc.tests)}
            row["project_pass"] = acc.status == "pass"
    else:
        row["reason"] = planned.reason_hu or "; ".join(planned.errors[:3])
    row["wall_ms"] = int((time.monotonic() - t0) * 1000)
    row["false_done"] = row["state"] == "done" and not row["project_pass"]  # "done" claimed, acceptance red
    return row


# ── P2: --suite research ──────────────────────────────────────────────────────

def keyword_hit(answer: str, keywords: tuple[str, ...]) -> bool:
    a = "".join(answer.lower().split())
    return any("".join(k.lower().split()) in a for k in keywords)


async def run_research(q: tuple[str, str, tuple[str, ...]], *, llm: Any, scheduler: Any, model: str,
                       bench_id: str) -> dict[str, Any]:
    from auri_core.research import DuckDuckGoHtml, ResilientSearch, SafeFetcher, Searxng, research
    from auri_core.router import SimpleRouter

    qid, question, keywords = q
    t0 = time.monotonic()
    r = await research(question, llm=llm, scheduler=scheduler, store=None,
                       search=ResilientSearch([DuckDuckGoHtml(), Searxng()]), fetcher=SafeFetcher(), lang="hu",
                       priority=Priority.BACKGROUND, use_memory=False, learn=False, router=SimpleRouter(model))
    from auri_core.lang import detect_lang

    verified = [c for c in r.claims if c.status == "verified"]
    return {"run_id": bench_id, "q": qid, "question": question, "model": model, "kind": r.kind,
            "correct": keyword_hit(r.answer, keywords), "web_checked": r.web_checked, "claims": len(r.claims),
            "verified": len(verified), "corroborated": sum(c.independent >= 2 for c in verified),
            "probable": sum(c.status == "probable" for c in r.claims), "hypothesis": sum(c.status == "hypothesis" for c in r.claims),
            # a Hungarian question must get Hungarian claims (a Turkish page leaked through in the first run)
            "wrong_lang": sum(detect_lang(c.text) not in ("hu", "unknown") for c in r.claims),
            "rejected_quotes": r.rejected_claims, "sources": len(r.sources), "searches": r.searches, "pages": r.pages,
            "llm_calls": r.llm_calls, "tokens_out": r.tokens_out, "wall_ms": int((time.monotonic() - t0) * 1000),
            "answer": r.answer[:600], "reason_hu": r.reason_hu}


# ── suite runner + summaries ──────────────────────────────────────────────────

def summarize_suite(suite: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    from auri_core.bench import _p90, wilson

    n = len(rows)
    key = "project_pass" if suite == "e5" else "correct"
    k = sum(bool(r[key]) for r in rows)
    lo, hi = wilson(k, n)
    wall = [r["wall_ms"] / 1000 for r in rows]
    s: dict[str, Any] = {"suite": suite, "metric": key, "n": n, "passed": k, "rate": round(k / n, 3) if n else 0.0,
                         "ci95": [round(lo, 3), round(hi, 3)],
                         "wall_s_median": round(statistics.median(wall), 1) if wall else 0.0, "wall_s_p90": round(_p90(wall), 1)}
    if suite == "e5":
        s.update(done=sum(r["state"] == "done" for r in rows), no_plan=sum(r["state"] == "no_plan" for r in rows),
                 false_done=sum(r["false_done"] for r in rows), replans=sum(r["replans"] for r in rows),
                 steps_done=f"{sum(r['done_steps'] for r in rows)}/{sum(r['tasks'] for r in rows)}")
    else:
        s.update(answered=sum(r["kind"] == "answered" for r in rows), give_up=sum(r["kind"] == "give_up" for r in rows),
                 web_checked=sum(r["web_checked"] for r in rows), verified_claims=sum(r["verified"] for r in rows),
                 corroborated=sum(r["corroborated"] for r in rows), rejected_quotes=sum(r["rejected_quotes"] for r in rows),
                 probable_claims=sum(r.get("probable", 0) for r in rows), hypothesis_claims=sum(r.get("hypothesis", 0) for r in rows),
                 # answered with no verified claim behind it: OK only if the answer labels it (e.g. "egy forrás szerint")
                 no_verified_answers=sum(r["kind"] == "answered" and r["verified"] == 0 for r in rows),
                 wrong_lang_answers=sum(r.get("wrong_lang", 0) > 0 for r in rows))
    return s


def suite_markdown(meta: dict[str, Any], s: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    head = [f"## Mérés: {s['suite']} · {meta['model']}", "",
            f"- **{s['metric']}: {s['passed']}/{s['n']} = {s['rate']:.1%}** (95% Wilson: {s['ci95'][0]:.1%}–{s['ci95'][1]:.1%})",
            f"- falióra: medián {s['wall_s_median']} s, p90 {s['wall_s_p90']} s · bench_id: `{meta['bench_id']}`"]
    if s["suite"] == "e5":
        head += [f"- terv kész → végig: {s['done']}/{s['n']} · terv nélkül: {s['no_plan']} · lépések: {s['steps_done']}"
                 f" · újratervezés: {s['replans']} · **hamis „kész”: {s['false_done']}**", "",
                 "| projekt | állapot | lépések | elfogadás | idő (s) |", "|---|---|---|---|---|"]
        head += [f"| {r['project']} | {'✅' if r['project_pass'] else '❌'} {r['state']} | {r['done_steps']}/{r['tasks']} "
                 f"| {r['accept']['passed']}/{r['accept']['total']} | {r['wall_ms'] / 1000:.0f} |" for r in rows]
    else:
        head += [f"- válaszolt: {s['answered']} · feladta: {s['give_up']} · neten ellenőrizve: {s['web_checked']}"
                 f" · igazolt állítás: {s['verified_claims']} (≥ 2 forrás: {s['corroborated']}) · eldobott idézet: "
                 f"{s['rejected_quotes']} · valószínű: {s['probable_claims']} · hipotézis: {s['hypothesis_claims']}"
                 f" · igazolt állítás nélküli válasz: {s['no_verified_answers']} · **más nyelvű válasz: {s['wrong_lang_answers']}**", "",
                 "| kérdés | helyes | fajta | igazolt | források | idő (s) |", "|---|---|---|---|---|---|"]
        head += [f"| {r['q']} | {'✅' if r['correct'] else '❌'} | {r['kind']} | {r['verified']} | {r['sources']} "
                 f"| {r['wall_ms'] / 1000:.0f} |" for r in rows]
    return "\n".join(head) + "\n"


async def main_suite(a: argparse.Namespace) -> int:
    from auri_core import config, llm, sandbox, scheduler
    from auri_core.bench import INFRA_PREFIX, INFRA_RETRY_S, is_infra, load_resumable

    cfg = config.load_config()
    model = a.model or cfg.models.code
    bench_id = a.resume or f"bench_{time.strftime('%Y%m%dT%H%M%S')}_{a.suite}"
    out_dir = cfg.data_dir / "eval" / bench_id
    out_dir.mkdir(parents=True, exist_ok=True)
    results = out_dir / "results.jsonl"
    rows = load_resumable(results)
    key = "project" if a.suite == "e5" else "q"
    done = {r[key] for r in rows}
    items: list[Any] = load_e5(Path(a.tasks_dir) if a.tasks_dir else cfg.tasks_dir) if a.suite == "e5" else RESEARCH_QS
    if a.limit:
        items = items[: a.limit]
    sb = sandbox.create_sandbox() if a.suite == "e5" else None
    meta = {"bench_id": bench_id, "suite": a.suite, "model": model, "sandbox": sb.level if sb else None,
            "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "n_items": len(items)}
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    client = llm.OllamaClient()
    try:
        for i, it in enumerate(items, 1):
            iid = it["id"] if a.suite == "e5" else it[0]
            if iid in done:
                continue
            for wait_s in (*INFRA_RETRY_S, None):
                try:
                    if a.suite == "e5":
                        row = await run_project(it, llm=client, sandbox=sb, scheduler=scheduler.get_scheduler(), model=model,
                                                runs_dir=cfg.runs_dir, bench_id=bench_id)
                    else:
                        row = await run_research(it, llm=client, scheduler=scheduler.get_scheduler(), model=model,
                                                 bench_id=bench_id)
                except Exception as e:  # an unreachable model in the planner raises: infrastructure, not a fail
                    row = {"reason": f"{INFRA_PREFIX}: {type(e).__name__}"}
                if not is_infra(row):
                    break
                if wait_s is None:
                    print(f"Infrastruktúra-hiba ({row.get('reason_hu') or row.get('reason')}); leállok. "
                          f"Folytatás: --resume {bench_id}", flush=True)
                    return 3
                print(f"[{i}/{len(items)}] {iid}: infrastruktúra-hiba, újra {wait_s} s múlva", flush=True)
                await asyncio.sleep(wait_s)
            ok = row["project_pass"] if a.suite == "e5" else row["correct"]
            rows.append(row)
            with results.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"[{i}/{len(items)}] {iid}: {'OK ' if ok else 'BUK'} {row['wall_ms'] / 1000:.0f} s", flush=True)
    finally:
        await client.aclose()
    s = summarize_suite(a.suite, rows)
    (out_dir / "summary.json").write_text(json.dumps({**meta, **s}, ensure_ascii=False, indent=1), encoding="utf-8")
    md = suite_markdown(meta, s, rows)
    (out_dir / "report.md").write_text(md, encoding="utf-8")
    print(md)
    return 0 if s.get("false_done", 0) == 0 else 1
