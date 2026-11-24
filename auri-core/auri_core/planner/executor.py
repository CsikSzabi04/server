"""The plan executor (07/02): next ready task → injected step runner (produce + verify + repair) →
guards → checkpoint | rollback → bounded re-plan → honest end. One lane, serial.

The runner is a parameter (code tasks will call solve.solve, others ask/chat), so this module imports
neither. Rules kept from the loop: a task is "done" only with a green gating check for EVERY gating
`accept` check (hallucination guard); a task may only write its own files; the final report is built
from the journal, not from a model; `contracts.Cancelled` pauses the run at a task boundary (resumable).
"""

from __future__ import annotations

import json
import secrets
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from ..contracts import Cancelled
from .model import Check, Milestone, Plan, PlanTask, plan_from_dict, plan_to_dict
from .validate import next_ready, validate
from .workspace import Workspace, files_hash

RunState = Literal["done", "failed", "paused", "waiting_user", "cancelled"]
MAX_DIGEST = 600


@dataclass(frozen=True)
class CheckResult:
    kind: str
    target: str = ""
    ok: bool = False
    ms: int = 0
    digest: str | None = None  # failure excerpt — data, not instructions


@dataclass
class StepResult:
    """What a step runner returns for one task (after its own ≤ 3 repair rounds)."""

    ok: bool
    files: dict[str, str] = field(default_factory=dict)  # full contents of the files it wrote
    checks: list[CheckResult] = field(default_factory=list)
    attempts: int = 1
    digest: str | None = None  # the last failure digest
    signature: str | None = None
    needs_user: str | None = None  # ONE question (07/04 §7)
    change_request: str | None = None  # the frozen contract would have to change
    tokens_out: int = 0
    llm_ms: int = 0
    sandbox_ms: int = 0
    infra: bool = False  # sandbox/model failure: re-planning would not help


@dataclass(frozen=True)
class StepContext:
    plan: Plan
    task: PlanTask
    files: dict[str, str]  # what the task may read: its reads + its current writes (edit/repair)
    contract: dict[str, str]  # every finished contract file (always in context, 07/03 §5)
    repo: tuple[str, ...]  # all paths in the workspace (for a repo map)
    last_digest: str | None
    attempt: int
    run_id: str


StepRunner = Callable[[PlanTask, StepContext], Awaitable[StepResult]]
Replanner = Callable[[Plan, PlanTask, StepResult], Awaitable[Plan | None]]
GateRunner = Callable[[Milestone, dict[str, str]], Awaitable[list[CheckResult]]]


@dataclass(frozen=True)
class RunBudget:
    max_wall_s: float = 3600.0  # 07/02 §6: default 60 minutes
    max_task_runs: int = 60


@dataclass
class RunOutcome:
    state: RunState
    plan: Plan
    run_id: str
    done: list[str]
    failed_task: str | None = None
    report_hu: str = ""
    question: str | None = None
    checkpoints: dict[str, str] = field(default_factory=dict)
    replans: int = 0
    tokens_out: int = 0
    wall_ms: int = 0
    files: dict[str, str] = field(default_factory=dict)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class RunJournal:
    """Append-only JSONL (07/02 §7) + an in-memory copy for the report + the on_event hook."""

    def __init__(self, path: Path | None, on_event: Callable[[str, dict[str, Any]], None] | None) -> None:
        self.path = path
        self.on_event = on_event
        self.events: list[dict[str, Any]] = []
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: str, **data: Any) -> None:
        rec = {"t": _now(), "type": event, **data}
        self.events.append(rec)
        if self.on_event is not None:
            self.on_event(event, data)
        if self.path is not None:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def read_journal(run_dir: Path) -> list[dict[str, Any]]:
    p = run_dir / "journal.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def restore(events: list[dict[str, Any]]) -> tuple[Plan, str | None, int]:
    """Replay the journal: latest plan version + finished tasks + last checkpoint + re-plans used."""
    plan_ev = [e for e in events if e["type"] in ("plan.created", "plan.replanned")]
    if not plan_ev:
        raise ValueError("a naplóban nincs terv")
    last = plan_ev[-1]
    plan = plan_from_dict(last["plan"])
    idx = events.index(last)
    done_after = {e["task"] for e in events[idx:] if e["type"] == "task.done"}
    for t in plan.tasks:
        if t.id in done_after:
            t.status = "done"
        elif t.status != "done":
            t.status = "pending"  # running/failed/blocked → ready again
    commits = [e["commit"] for e in events if e["type"] in ("checkpoint", "run.start") and e.get("commit")]
    replans = sum(e["type"] == "plan.replanned" for e in events)
    return plan, (commits[-1] if commits else None), replans


def _matches(c: Check, r: CheckResult) -> bool:
    return r.kind == c.kind and (not c.target or not r.target or r.target == c.target)


def _missing_green(task: PlanTask, checks: list[CheckResult]) -> list[str]:
    return [f"{c.kind}:{c.target}" if c.target else c.kind for c in task.accept
            if c.gating and not any(r.ok and _matches(c, r) for r in checks)]


def _first_line(s: str | None) -> str:
    return (s or "").strip().splitlines()[0][:200] if (s or "").strip() else ""


def report_from_journal(events: list[dict[str, Any]], goal: str, state: RunState) -> str:
    """Hungarian report; every "kész" claim points to green check events of that task."""
    plans = [e for e in events if e["type"] in ("plan.created", "plan.replanned")]
    titles = {t["id"]: t["title"] for t in plans[-1]["plan"]["tasks"]} if plans else {}
    total = len(titles)
    green: dict[str, list[str]] = {}
    for e in events:
        if e["type"] == "check" and e.get("ok") and e.get("task") in titles:
            label = f"{e['check']}:{e['target']}" if e.get("target") else e["check"]
            green.setdefault(e["task"], []).append(label)
    done = [e["task"] for e in events if e["type"] == "task.done" and e["task"] in titles]
    done = list(dict.fromkeys(done))
    n_green = sum(len(green.get(t, [])) for t in done)
    lines: list[str] = []
    if state == "done":
        lines.append(f"Kész: {goal} — {len(done)}/{total} feladat kész, {n_green} zöld ellenőrzés.")
    elif state == "failed":
        lines.append(f"Nem sikerült teljesen: {goal} — {len(done)}/{total} feladat kész.")
        fails = [e for e in events if e["type"] == "task.failed"]
        if fails:
            f = fails[-1]
            lines.append(f"Elakadt: {f['task']} ({titles.get(f['task'], '')}) — {_first_line(f.get('digest'))}")
        gate = [e for e in events if e["type"] == "gate.failed"]
        if gate:
            lines.append(f"A(z) {gate[-1]['milestone']} mérföldkő kapuja piros.")
    elif state == "paused":
        reason = next((e.get("reason") for e in reversed(events) if e["type"] == "run.paused"), "")
        lines.append(f"Szünetel: {goal} — {len(done)}/{total} feladat kész ({reason}).")
    elif state == "waiting_user":
        q = next((e.get("question") for e in reversed(events) if e["type"] == "ask_user"), "")
        lines.append(f"Kérdésem van: {q}")
    else:
        lines.append(f"Megszakítva: {goal} — {len(done)}/{total} feladat kész.")
    for t in done:
        lines.append(f"- {t} ({titles[t]}): " + ", ".join(dict.fromkeys(green.get(t, []))))
    replans = sum(e["type"] == "plan.replanned" for e in events)
    if replans:
        lines.append(f"Újratervezés: {replans}×.")
    return "\n".join(lines)


async def execute(
    plan: Plan | None,
    *,
    runner: StepRunner,
    workspace: Workspace | None = None,
    run_dir: Path | None = None,
    run_id: str | None = None,
    on_event: Callable[[str, dict[str, Any]], None] | None = None,
    replanner: Replanner | None = None,
    gate_runner: GateRunner | None = None,
    max_replans: int = 2,
    budget: RunBudget | None = None,
    resume: bool = False,
    clock: Callable[[], float] = time.monotonic,
) -> RunOutcome:
    """Run a plan to the end. With `resume=True`, `run_dir`'s journal gives the plan and the state."""
    budget = budget or RunBudget()
    t0 = clock()
    journal = RunJournal(run_dir / "journal.jsonl" if run_dir else None, on_event)
    ckpt_dir = run_dir / "checkpoints" if run_dir else None
    replans = 0
    if resume:
        if run_dir is None:
            raise ValueError("resume needs run_dir")
        old = read_journal(run_dir)
        plan, last_commit, replans = restore(old)
        journal.events = old  # the report covers the whole run
        run_id = run_id or next((e.get("run_id") for e in old if e["type"] == "run.start"), None)
        ws = workspace or Workspace(checkpoint_dir=ckpt_dir)
        ws.checkpoint_dir = ws.checkpoint_dir or ckpt_dir
        if last_commit:
            ws.reset(last_commit)
        journal.log("run.resumed", version=plan.version, done=sorted(plan.done_ids()))
    else:
        if plan is None:
            raise ValueError("plan is required unless resume=True")
        ws = workspace or Workspace(checkpoint_dir=ckpt_dir)
        ws.checkpoint_dir = ws.checkpoint_dir or ckpt_dir
    run_id = run_id or f"plan_{secrets.token_hex(4)}"
    assert plan is not None
    outcome = RunOutcome("failed", plan, run_id, [])

    def finish(state: RunState, *, failed: str | None = None, question: str | None = None) -> RunOutcome:
        journal.log("run.end", state=state, done=sorted(plan.done_ids()), version=plan.version)
        outcome.state, outcome.plan, outcome.failed_task, outcome.question = state, plan, failed, question
        outcome.done = [t.id for t in plan.tasks if t.status == "done"]
        outcome.replans = replans
        outcome.wall_ms = int((clock() - t0) * 1000)
        outcome.files = ws.view()
        outcome.report_hu = report_from_journal(journal.events, plan.goal, state)
        return outcome

    if not resume:
        errs = validate(plan)
        if errs:
            journal.log("plan.rejected", errors=errs)
            outcome.report_hu = "Érvénytelen terv: " + "; ".join(errs[:5])
            outcome.state = "failed"
            return outcome
        base = ws.commit()
        journal.log("run.start", run_id=run_id, commit=base, goal_chars=len(plan.goal))
        journal.log("plan.created", version=plan.version, created_by=plan.created_by, plan=plan_to_dict(plan))
    last_digest: dict[str, str | None] = {}
    runs = 0
    while (task := next_ready(plan)) is not None:
        if clock() - t0 > budget.max_wall_s or runs >= budget.max_task_runs:
            minutes = int((clock() - t0) // 60)
            q = (f"{minutes} perc ment el, {len(plan.done_ids())}/{len(plan.tasks)} feladat kész. "
                 "Folytassam?")
            journal.log("run.paused", reason="elfogyott a keret", task=task.id)
            return finish("paused", question=q)
        runs += 1
        base = ws.commit()
        task.status = "running"
        journal.log("task.start", task=task.id, attempt=task.attempts + 1, kind=task.kind, title=task.title)
        contract_files = {f: c for t in plan.tasks if t.kind == "contract" and t.status == "done"
                          for f in t.writes if (c := ws.read(f)) is not None}
        ctx = StepContext(plan, task, ws.view(list(task.reads) + list(task.writes)), contract_files,
                          tuple(sorted(ws.files)), last_digest.get(task.id), task.attempts + 1, run_id)
        try:
            res = await runner(task, ctx)
        except Cancelled:
            task.status = "pending"
            journal.log("run.paused", reason="megszakítva: magasabb prioritású kérés", task=task.id)
            return finish("paused")
        except Exception as e:  # runner bug / infrastructure — never the plan's fault
            res = StepResult(ok=False, digest=f"infrastruktúra: {type(e).__name__}", infra=True)
        task.attempts += max(1, res.attempts)
        outcome.tokens_out += res.tokens_out
        for c in res.checks:
            journal.log("check", task=task.id, check=c.kind, target=c.target, ok=c.ok, ms=c.ms,
                        digest=(c.digest or "")[:MAX_DIGEST] or None)
        problem: str | None = None
        foreign = sorted(set(res.files) - set(task.writes))
        if foreign:
            problem = f"idegen fájlt írt: {', '.join(foreign)}"
        elif res.ok:
            missing_out = [f for f in task.writes if f not in res.files and ws.read(f) is None]
            missing = _missing_green(task, res.checks)
            if missing_out:
                problem = f"hiányzó kimenet: {', '.join(missing_out)}"
            elif missing:
                problem = f"nincs zöld gépi ellenőrzés ehhez: {', '.join(missing)} — nem mondhatom késznek"
        if res.ok and problem is None:
            for path, content in res.files.items():
                ws.write(path, content)
            sha = ws.commit()
            task.status = "done"
            outcome.checkpoints[task.id] = sha
            if task.kind == "contract":
                plan.contracts_hash = "sha256:" + files_hash({f: ws.read(f) or "" for f in task.writes})
            journal.log("checkpoint", task=task.id, commit=sha)
            journal.log("task.done", task=task.id, attempt=task.attempts)
            ms = next(m for m in plan.milestones if m.id == task.milestone)
            if all(t.status == "done" for t in plan.tasks if t.milestone == ms.id):
                gate_checks = await gate_runner(ms, ws.view()) if gate_runner else []
                for c in gate_checks:
                    journal.log("check", task=ms.id, check=c.kind, target=c.target, ok=c.ok, ms=c.ms,
                                digest=(c.digest or "")[:MAX_DIGEST] or None)
                gate_red = any(c.gating and not any(r.ok and _matches(c, r) for r in gate_checks) for c in ms.gate)
                if gate_red or any(not r.ok and r.kind != "critic" for r in gate_checks):
                    journal.log("gate.failed", milestone=ms.id)
                    return finish("failed", failed=task.id)
                journal.log("milestone.done", milestone=ms.id)
            continue

        # ── failure: rollback, then ask / re-plan / give up ──
        digest = problem or res.digest or "ismeretlen hiba"
        previous, last_digest[task.id] = last_digest.get(task.id), digest
        ws.reset(base)
        journal.log("rollback", to=base, task=task.id, reason=_first_line(digest))
        if res.needs_user and not problem:
            task.status = "pending"
            journal.log("ask_user", task=task.id, question=res.needs_user)
            return finish("waiting_user", question=res.needs_user)
        # repair round (07/02 §6: 1 + 3): the same task again with the failure digest (ctx.last_digest) before any
        # re-plan. e5 2026-11-24: without it a step got one try, then the 2B model's re-plan was invalid → 0/5.
        # The exact same digest twice in a row (e.g. a cut-off reply) = no progress → stop repairing.
        stuck = task.attempts > 1 and previous == digest
        if not (res.infra or res.change_request or stuck) and task.attempts < task.budget.max_attempts:
            task.status = "pending"
            journal.log("task.retry", task=task.id, attempt=task.attempts, digest=digest[:MAX_DIGEST],
                        signature=res.signature)
            continue
        task.status = "blocked" if res.change_request else "failed"
        if res.change_request:
            journal.log("contract.change_request", task=task.id, request=res.change_request[:MAX_DIGEST])
        journal.log("task.failed", task=task.id, attempt=task.attempts, digest=digest[:MAX_DIGEST],
                    signature=res.signature)
        if replanner is None or res.infra or replans >= max_replans:
            return finish("failed", failed=task.id)
        try:
            new = await replanner(plan, task, res)
        except Cancelled:
            task.status = "pending"
            journal.log("run.paused", reason="megszakítva újratervezés közben", task=task.id)
            return finish("paused")
        if new is None or validate(new):
            journal.log("replan.failed", task=task.id)
            return finish("failed", failed=task.id)
        new.version = max(new.version, plan.version + 1)
        for t in new.tasks:  # finished work stays finished
            old = next((o for o in plan.tasks if o.id == t.id and o.status == "done" and o.writes == t.writes), None)
            t.status = "done" if old is not None else "pending"  # only work that really finished
        plan = new
        replans += 1
        journal.log("plan.replanned", version=plan.version, reason=_first_line(digest), plan=plan_to_dict(plan))
    if all(t.status == "done" for t in plan.tasks):
        return finish("done")
    return finish("failed", failed=next((t.id for t in plan.tasks if t.status != "done"), None))
