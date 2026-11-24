"""Making and re-making plans (07/01 §7, 07/02 §5).

make_plan: recipe first (0 model calls) → else one schema-constrained JSON call (+1 JSON fix) →
validate → if invalid, ONE re-plan with the validation errors → still invalid: an honest failure.
replan_subtree: only the failed task + its descendants are replaced; finished ancestors stay.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any

from ..contracts import LLMClient, Priority, Scheduler
from ..router import SimpleRouter
from .llm_call import EventSink, LLMSession, load_prompts
from .model import PLAN_SCHEMA, REPLAN_SCHEMA, Plan, PlanError, PlanTask, plan_from_dict, task_from_dict
from .recipes import RecipeBook
from .validate import descendants, is_test_path, validate

# 07/02 §6 said ≤ 1000, but measured (2026-11-24, gemma4:e2b, E5-01): a 9-step plan is ~1500–1650 tokens
# of pretty-printed JSON, so 1000 cut EVERY plan (e5: 0/5, all "no valid JSON").
PLAN_NUM_PREDICT = 2000
REPLAN_NUM_PREDICT = 1500
MAX_ERRORS_SHOWN = 12


@dataclass
class PlanResult:
    plan: Plan | None
    ok: bool
    errors: list[str] = field(default_factory=list)
    created_by: str = "model"
    llm_calls: int = 0
    tokens_out: int = 0
    prompt_ver: str = ""
    reason_hu: str | None = None


def _bullets(items: list[str] | tuple[str, ...]) -> str:
    return "\n".join(f"- {x}" for x in items) if items else "(none)"


def _session(llm: LLMClient, scheduler: Scheduler, router: SimpleRouter | None, prompt_lang: str,
             priority: Priority, on_event: EventSink | None) -> LLMSession:
    model, _why = (router or SimpleRouter()).chat_model()
    prompts = load_prompts(prompt_lang)
    s = LLMSession(llm, scheduler, model, prompts, priority=priority, on_event=on_event)
    s.messages = [{"role": "system", "content": prompts.render("system")}]
    return s


def normalize_plan_dict(data: Any) -> Any:
    """Deterministic fixes of the small model's typical slips, BEFORE validation (nothing is invented):
    - a task id in `reads` → that task's files; a file name in `depends_on` → its writer's id;
    - a file written again by a descendant of its first writer (not a contract) → the later task is an `edit`."""
    tasks = data.get("tasks") if isinstance(data, dict) else None
    if not isinstance(tasks, list) or not all(isinstance(t, dict) for t in tasks):
        return data
    ids = {str(t.get("id")) for t in tasks}
    writes = {str(t.get("id")): [str(f) for f in t.get("writes") or []] for t in tasks}
    writer: dict[str, str] = {}
    for t in tasks:
        for f in writes[str(t.get("id"))]:
            writer.setdefault(f, str(t.get("id")))
    for t in tasks:
        tid = str(t.get("id"))
        reads: list[str] = []
        for r in t.get("reads") or []:
            for x in (writes[str(r)] if str(r) in ids and str(r) != tid else [str(r)]):
                if x not in reads:
                    reads.append(x)
        t["reads"] = reads
        deps: list[str] = []
        for d in t.get("depends_on") or []:
            d = writer.get(str(d), str(d)) if str(d) not in ids else str(d)
            if d != tid and d not in deps:
                deps.append(d)
        t["depends_on"] = deps
    by_id = {str(t.get("id")): t for t in tasks}

    def ancestors(tid: str, seen: set[str] | None = None) -> set[str]:
        seen = set() if seen is None else seen
        for d in by_id.get(tid, {}).get("depends_on") or []:
            if d not in seen:
                seen.add(d)
                ancestors(d, seen)
        return seen

    for t in tasks:
        tid = str(t.get("id"))
        firsts = {writer[f] for f in writes[tid] if writer.get(f) not in (None, tid)}
        if (firsts and t.get("kind") == "code" and all(w in ancestors(tid) for w in firsts)
                and all(by_id[w].get("kind") != "contract" for w in firsts)):
            t["kind"] = "edit"
    return data


_MODULE = re.compile(r"(?<![\w/.-])([A-Za-z_][\w-]*\.(?:py|ts|js))(?!\w)(?!\.\w)")
MAX_MODULES = 6


def module_plan_dict(goal: str) -> dict[str, Any] | None:
    """Fallback when the model's own plan stays invalid (e5, gemma4:e2b: contract + code writing the same
    file, tests after code). The modules named in the goal, in order; per module a test task (red-test)
    and then a code task (green test + guard); a later module may use the earlier ones. Built by code →
    always a valid DAG; the model still writes every file, the checks still decide."""
    files: list[str] = []
    for m in _MODULE.finditer(goal):
        if not is_test_path(m.group(1)) and m.group(1) not in files:
            files.append(m.group(1))
    if not files or len(files) > MAX_MODULES:
        return None
    tests = [f"test_{f[:-3]}.py" if f.endswith(".py") else f"{f.rsplit('.', 1)[0]}.test.{f.rsplit('.', 1)[1]}"
             for f in files]
    tasks: list[dict[str, Any]] = []
    for i, (f, tf) in enumerate(zip(files, tests, strict=True), 1):
        tasks.append({"id": f"T{i}", "milestone": "M1", "kind": "test", "writes": [tf], "reads": [], "depends_on": [],
                      "title": f"Tests for {f}, exactly as the goal describes it (behaviour and errors).",
                      "accept": [{"kind": "red-test", "target": tf}]})
    for i, (f, tf) in enumerate(zip(files, tests, strict=True), 1):
        tasks.append({"id": f"C{i}", "milestone": "M2", "kind": "code", "writes": [f], "reads": [tf, *files[:i - 1]],
                      "depends_on": [f"T{i}", *(f"C{j}" for j in range(1, i))],
                      "title": f"Implement {f} as the goal describes it, so that {tf} passes.",
                      "accept": [{"kind": "test", "target": tf}, {"kind": "guard", "target": f}]})
    return {"acceptance": [f"{tf} zöld" for tf in tests],
            "milestones": [{"id": "M1", "title": "Tesztek"}, {"id": "M2", "title": "Kód"}], "tasks": tasks}


def _to_plan(data: Any, goal: str, scaffold: tuple[str, ...]) -> tuple[Plan | None, list[str]]:
    if data is None:
        return None, ["a modell nem adott érvényes JSON-t"]
    data = normalize_plan_dict(data)
    try:
        plan = plan_from_dict(data, goal=goal)
    except PlanError as e:
        return None, e.errors
    plan = replace(plan, scaffold=scaffold or plan.scaffold, created_by="model", version=1)
    for t in plan.tasks:
        t.status, t.attempts = "pending", 0
    return plan, validate(plan)


async def make_plan(
    goal: str,
    *,
    llm: LLMClient,
    scheduler: Scheduler,
    router: SimpleRouter | None = None,
    recipes: RecipeBook | None = None,
    acceptance: tuple[str, ...] = (),
    scaffold: tuple[str, ...] = (),
    context: str = "",
    prompt_lang: str = "en",
    priority: Priority = Priority.TASK,
    on_event: EventSink | None = None,
) -> PlanResult:
    """Raises contracts.Cancelled when the lease is preempted (the caller pauses)."""
    goal = goal.strip()
    if not goal:
        return PlanResult(None, False, ["üres cél"], reason_hu="üres cél")
    if recipes is not None and (plan := await recipes.lookup(goal)) is not None:
        plan = replace(plan, scaffold=scaffold or plan.scaffold,
                       acceptance=tuple(acceptance) or plan.acceptance)
        if not validate(plan):
            return PlanResult(plan, True, created_by="recipe")
    s = _session(llm, scheduler, router, prompt_lang, priority, on_event)
    msg = s.prompts.render("plan", goal=goal, acceptance=_bullets(acceptance), context=context.strip() or "(none)",
                           scaffold=", ".join(scaffold) or "(none)")
    plan, errs = _to_plan(await s.json_call(msg, PLAN_SCHEMA, num_predict=PLAN_NUM_PREDICT), goal, scaffold)
    if plan is None or errs:
        if on_event:
            on_event("plan.invalid", {"errors": errs[:MAX_ERRORS_SHOWN], "attempt": 1})
        fix = s.prompts.render("fix_plan", errors=_bullets(errs[:MAX_ERRORS_SHOWN]))
        plan, errs = _to_plan(await s.json_call(fix, PLAN_SCHEMA, num_predict=PLAN_NUM_PREDICT), goal, scaffold)
    if plan is None or errs:
        if on_event:
            on_event("plan.invalid", {"errors": errs[:MAX_ERRORS_SHOWN], "attempt": 2})
        fallback, ferrs = _to_plan(module_plan_dict(goal), goal, scaffold)
        if fallback is not None and not ferrs:
            if on_event:
                on_event("plan.fallback", {"tasks": len(fallback.tasks)})
            plan = replace(fallback, created_by="modules",
                           acceptance=tuple(acceptance) or fallback.acceptance)
            return PlanResult(plan, True, created_by="modules", llm_calls=s.calls, tokens_out=s.tokens_out,
                              prompt_ver=s.prompts.version)
        return PlanResult(None, False, errs, llm_calls=s.calls, tokens_out=s.tokens_out,
                          prompt_ver=s.prompts.version,
                          reason_hu="nem sikerült érvényes tervet készíteni: " + "; ".join(errs[:3]))
    if acceptance:
        plan = replace(plan, acceptance=tuple(acceptance))
    return PlanResult(plan, True, created_by="model", llm_calls=s.calls, tokens_out=s.tokens_out,
                      prompt_ver=s.prompts.version)


def subtree(plan: Plan, task_id: str) -> set[str]:
    return {task_id} | descendants(plan, task_id)


def merge_subtree(plan: Plan, removed: set[str], new_tasks: list[PlanTask]) -> Plan:
    """Keep every task outside `removed` (with its status); append the new tasks as pending."""
    kept = [t for t in plan.tasks if t.id not in removed]
    fresh = [replace(t, status="pending", attempts=0) for t in new_tasks]
    known_ms = {m.id for m in plan.milestones}
    fresh = [replace(t, milestone=t.milestone if t.milestone in known_ms else plan.milestones[-1].id)
             for t in fresh]
    return replace(plan, tasks=kept + fresh, version=plan.version + 1)


async def replan_subtree(
    plan: Plan,
    failed: PlanTask,
    *,
    digest: str | None,
    llm: LLMClient,
    scheduler: Scheduler,
    router: SimpleRouter | None = None,
    prompt_lang: str = "en",
    priority: Priority = Priority.TASK,
    on_event: EventSink | None = None,
) -> Plan | None:
    """A new plan version, or None if the model's replacement is unusable/invalid."""
    removed = subtree(plan, failed.id)
    done_files = sorted({f for t in plan.tasks if t.status == "done" for f in t.writes})
    s = _session(llm, scheduler, router, prompt_lang, priority, on_event)
    msg = s.prompts.render(
        "replan", task_id=failed.id, task_title=failed.title, attempts=str(max(1, failed.attempts)),
        digest=(digest or "(no details)")[:1500], done_files=", ".join(done_files) or "(none)",
        subtree=", ".join(sorted(removed)))
    data = await s.json_call(msg, REPLAN_SCHEMA, num_predict=REPLAN_NUM_PREDICT)
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        return None
    errs: list[str] = []
    new_tasks = [t for i, x in enumerate(data["tasks"]) if (t := task_from_dict(x, f"tasks[{i}]", errs))]
    if errs or not new_tasks:
        return None
    new = merge_subtree(plan, removed, new_tasks)
    if on_event:
        on_event("plan.replan_reason", {"reason": str(data.get("reason") or "")[:300]})
    problems = validate(new)
    if problems:
        if on_event:
            on_event("plan.invalid", {"errors": problems[:MAX_ERRORS_SHOWN], "attempt": "replan"})
        return None
    return new


def make_replanner(*, llm: LLMClient, scheduler: Scheduler, router: SimpleRouter | None = None,
                   prompt_lang: str = "en", priority: Priority = Priority.TASK,
                   on_event: EventSink | None = None) -> Any:
    """A `Replanner` for executor.execute bound to one model client."""

    async def replanner(plan: Plan, failed: PlanTask, result: Any) -> Plan | None:
        return await replan_subtree(plan, failed, digest=getattr(result, "digest", None), llm=llm,
                                    scheduler=scheduler, router=router, prompt_lang=prompt_lang,
                                    priority=priority, on_event=on_event)

    return replanner
