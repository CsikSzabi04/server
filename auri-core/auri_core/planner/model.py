"""Plan data model (07/01 §3): goal → milestones → tasks (the planning atom) → steps (executor-made).

Types live here, not in contracts.py. JSON keys are snake_case; camelCase from a model is accepted.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Any

TASK_KINDS = ("scaffold", "contract", "test", "code", "config", "doc", "research", "integrate", "edit")
CHECK_KINDS = ("parse", "typecheck", "lint", "test", "red-test", "schema", "smoke", "guard", "critic")
TASK_STATUSES = ("pending", "ready", "running", "verifying", "done", "failed", "blocked")
CREATED_BY = ("recipe", "recipe+model", "model", "modules")


class PlanError(ValueError):
    """The model's JSON is not a plan at all (wrong shape). `errors` are Hungarian."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass(frozen=True)
class Check:
    """A machine "done when" (07/01 §3). `critic` is advice only, never a gate (07/04 §5)."""

    kind: str
    target: str = ""
    expect: str | None = None

    @property
    def gating(self) -> bool:
        return self.kind != "critic"


@dataclass(frozen=True)
class TaskBudget:
    max_attempts: int = 4  # 1 + 3 repair rounds (07/02 §6)
    max_tokens_out: int = 2000  # num_predict ceiling of one call (e5 2026-11-24: a test file cut off at 1000)
    max_wall_s: int = 1200  # 20 minutes per task


@dataclass
class PlanTask:
    id: str
    milestone: str
    title: str  # one Hungarian sentence
    kind: str
    writes: tuple[str, ...] = ()  # files ONLY this task writes (ownership)
    reads: tuple[str, ...] = ()  # contract, dependency signatures, tests
    depends_on: tuple[str, ...] = ()
    accept: tuple[Check, ...] = ()
    budget: TaskBudget = field(default_factory=TaskBudget)
    status: str = "pending"
    attempts: int = 0
    recipe: str | None = None


@dataclass(frozen=True)
class Milestone:
    id: str
    title: str
    gate: tuple[Check, ...] = ()


@dataclass
class Plan:
    goal: str
    acceptance: tuple[str, ...]
    milestones: tuple[Milestone, ...]
    tasks: list[PlanTask]
    version: int = 1  # +1 on every re-plan
    created_by: str = "model"
    scaffold: tuple[str, ...] = ()  # files the template provides before any task
    contracts_hash: str | None = None

    def by_id(self) -> dict[str, PlanTask]:
        return {t.id: t for t in self.tasks}

    def task(self, task_id: str) -> PlanTask:
        return self.by_id()[task_id]

    def done_ids(self) -> set[str]:
        return {t.id for t in self.tasks if t.status == "done"}

    def fresh(self, **kw: Any) -> Plan:
        """A copy with every task pending again (recipe instantiation)."""
        tasks = [replace(t, status="pending", attempts=0) for t in self.tasks]
        return replace(self, tasks=tasks, **kw)


# ───────────────────────────── JSON ↔ Plan ─────────────────────────────


def _check_to_dict(c: Check) -> dict[str, Any]:
    d: dict[str, Any] = {"kind": c.kind, "target": c.target}
    if c.expect is not None:
        d["expect"] = c.expect
    return d


def task_to_dict(t: PlanTask) -> dict[str, Any]:
    return {
        "id": t.id, "milestone": t.milestone, "title": t.title, "kind": t.kind, "writes": list(t.writes),
        "reads": list(t.reads), "depends_on": list(t.depends_on), "accept": [_check_to_dict(c) for c in t.accept],
        "budget": {"max_attempts": t.budget.max_attempts, "max_tokens_out": t.budget.max_tokens_out,
                   "max_wall_s": t.budget.max_wall_s},
        "status": t.status, "attempts": t.attempts, **({"recipe": t.recipe} if t.recipe else {}),
    }


def plan_to_dict(p: Plan) -> dict[str, Any]:
    return {
        "goal": p.goal, "version": p.version, "created_by": p.created_by, "acceptance": list(p.acceptance),
        "scaffold": list(p.scaffold), "contracts_hash": p.contracts_hash,
        "milestones": [{"id": m.id, "title": m.title, "gate": [_check_to_dict(c) for c in m.gate]}
                       for m in p.milestones],
        "tasks": [task_to_dict(t) for t in p.tasks],
    }


def plan_hash(p: Plan) -> str:
    """Hash of the plan's structure (statuses excluded) — for the journal and recipes."""
    d = plan_to_dict(p)
    for t in d["tasks"]:
        t.pop("status", None)
        t.pop("attempts", None)
    raw = json.dumps(d, sort_keys=True, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _strs(v: Any, where: str, errs: list[str]) -> tuple[str, ...]:
    if v is None:
        return ()
    if isinstance(v, str):
        return (v,)
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        errs.append(f"{where}: szöveglista kell")
        return ()
    return tuple(x.strip() for x in v if x.strip())


def _checks(v: Any, where: str, errs: list[str]) -> tuple[Check, ...]:
    if v is None:
        return ()
    if not isinstance(v, list):
        errs.append(f"{where}: ellenőrzés-lista kell")
        return ()
    out = []
    for i, c in enumerate(v):
        if isinstance(c, str):  # "test:tests/x.py" shorthand
            kind, _, target = c.partition(":")
            out.append(Check(kind.strip(), target.strip()))
        elif isinstance(c, dict) and isinstance(c.get("kind"), str):
            exp = c.get("expect")
            out.append(Check(c["kind"].strip(), str(c.get("target") or "").strip(),
                             None if exp is None else str(exp)))
        else:
            errs.append(f"{where}[{i}]: hibás ellenőrzés")
    return tuple(out)


def _budget(v: Any) -> TaskBudget:
    if not isinstance(v, dict):
        return TaskBudget()

    def num(*keys: str, default: int) -> int:
        for k in keys:
            if isinstance(v.get(k), int | float) and not isinstance(v.get(k), bool):
                return int(v[k])
        return default

    d = TaskBudget()
    return TaskBudget(num("max_attempts", "maxAttempts", default=d.max_attempts),
                      num("max_tokens_out", "maxTokensOut", default=d.max_tokens_out),
                      num("max_wall_s", "maxWallS", default=d.max_wall_s))


def task_from_dict(d: Any, where: str, errs: list[str]) -> PlanTask | None:
    if not isinstance(d, dict):
        errs.append(f"{where}: objektum kell")
        return None
    tid = d.get("id")
    if not isinstance(tid, str) or not tid.strip():
        errs.append(f"{where}: hiányzó azonosító")
        return None
    tid = tid.strip()
    status = d.get("status") if d.get("status") in TASK_STATUSES else "pending"
    return PlanTask(
        id=tid, milestone=str(d.get("milestone") or "").strip(), title=str(d.get("title") or "").strip(),
        kind=str(d.get("kind") or "").strip(), writes=_strs(d.get("writes"), f"{tid}.writes", errs),
        reads=_strs(d.get("reads"), f"{tid}.reads", errs),
        depends_on=_strs(d.get("depends_on", d.get("dependsOn")), f"{tid}.depends_on", errs),
        accept=_checks(d.get("accept"), f"{tid}.accept", errs), budget=_budget(d.get("budget")),
        status=str(status), attempts=int(d.get("attempts") or 0) if isinstance(d.get("attempts"), int) else 0,
        recipe=d.get("recipe") if isinstance(d.get("recipe"), str) else None,
    )


def plan_from_dict(d: Any, *, goal: str | None = None) -> Plan:
    """Model/recipe JSON → Plan. Raises PlanError for a wrong shape; rules are checked by validate()."""
    errs: list[str] = []
    if not isinstance(d, dict):
        raise PlanError(["a terv nem JSON-objektum"])
    ms_raw = d.get("milestones")
    tasks_raw = d.get("tasks")
    if not isinstance(tasks_raw, list) or not tasks_raw:
        errs.append("nincs egyetlen feladat sem (tasks)")
        tasks_raw = []
    milestones: list[Milestone] = []
    if isinstance(ms_raw, list):
        for i, m in enumerate(ms_raw):
            if isinstance(m, dict) and isinstance(m.get("id"), str) and m["id"].strip():
                milestones.append(Milestone(m["id"].strip(), str(m.get("title") or "").strip(),
                                            _checks(m.get("gate"), f"{m['id']}.gate", errs)))
            else:
                errs.append(f"milestones[{i}]: hiányzó azonosító")
    elif ms_raw is not None:
        errs.append("milestones: lista kell")
    tasks = [t for i, x in enumerate(tasks_raw) if (t := task_from_dict(x, f"tasks[{i}]", errs)) is not None]
    if not milestones and tasks:  # tolerate a flat plan: one implicit milestone
        milestones = [Milestone("M1", "Egyetlen mérföldkő")]
        tasks = [replace(t, milestone=t.milestone or "M1") for t in tasks]
    acceptance = _strs(d.get("acceptance"), "acceptance", errs)
    scaffold = _strs(d.get("scaffold"), "scaffold", errs)
    if errs:
        raise PlanError(errs)
    version = d.get("version") if isinstance(d.get("version"), int) else 1
    created = d.get("created_by") if d.get("created_by") in CREATED_BY else "model"
    return Plan(
        goal=goal if goal is not None else str(d.get("goal") or ""),
        acceptance=acceptance, milestones=tuple(milestones), tasks=tasks,
        version=version, created_by=str(created), scaffold=scaffold,
        contracts_hash=d.get("contracts_hash") if isinstance(d.get("contracts_hash"), str) else None,
    )


# JSON schema for the model's plan (Ollama `format`). Budgets/statuses are ours, not the model's.
_CHECK_SCHEMA = {
    "type": "object",
    "properties": {"kind": {"type": "string", "enum": list(CHECK_KINDS)}, "target": {"type": "string"},
                   "expect": {"type": "string"}},
    "required": ["kind", "target"],
}
TASK_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"}, "milestone": {"type": "string"}, "title": {"type": "string", "maxLength": 200},
        "kind": {"type": "string", "enum": list(TASK_KINDS)},
        "writes": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        "reads": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        "depends_on": {"type": "array", "items": {"type": "string"}},
        "accept": {"type": "array", "items": _CHECK_SCHEMA, "minItems": 1, "maxItems": 4},
    },
    "required": ["id", "milestone", "title", "kind", "writes", "reads", "depends_on", "accept"],
}
PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "acceptance": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        "milestones": {"type": "array", "minItems": 1, "maxItems": 6, "items": {
            "type": "object",
            "properties": {"id": {"type": "string"}, "title": {"type": "string"},
                           "gate": {"type": "array", "items": _CHECK_SCHEMA}},
            "required": ["id", "title"]}},
        "tasks": {"type": "array", "minItems": 1, "maxItems": 30, "items": TASK_SCHEMA},
    },
    "required": ["acceptance", "milestones", "tasks"],
}
REPLAN_SCHEMA = {
    "type": "object",
    "properties": {"reason": {"type": "string", "maxLength": 300},
                   "tasks": {"type": "array", "minItems": 1, "maxItems": 12, "items": TASK_SCHEMA}},
    "required": ["tasks"],
}
