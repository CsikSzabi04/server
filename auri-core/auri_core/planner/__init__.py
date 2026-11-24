"""auri_core.planner — complex tasks (P5, owner: AI-1). Spec: thinking/07-komplex-feladatok/01–05.

make_plan (recipe → model JSON → validate → one fix) · validate (DAG rules) · execute (step runner
injected; checkpoints, rollback, bounded re-plan, honest report from the journal) · RecipeBook ·
ProjectManifest + repo_map. Nothing here calls Ollama outside `scheduler.lease()`.
"""

from .executor import (
    CheckResult,
    RunBudget,
    RunOutcome,
    StepContext,
    StepResult,
    execute,
    read_journal,
    report_from_journal,
    restore,
)
from .manifest import (
    Dependency,
    ProjectFile,
    ProjectManifest,
    manifest_from_plan,
    repo_map,
    validate_manifest,
)
from .model import PLAN_SCHEMA, Check, Milestone, Plan, PlanError, PlanTask, TaskBudget, plan_from_dict, plan_to_dict
from .planning import PlanResult, make_plan, make_replanner, merge_subtree, replan_subtree, subtree
from .recipes import RecipeBook, goal_signature, normalize_goal
from .validate import ancestors, next_ready, toposort, validate
from .workspace import Workspace

__all__ = [
    "PLAN_SCHEMA", "Check", "CheckResult", "Dependency", "Milestone", "Plan", "PlanError", "PlanResult",
    "PlanTask", "ProjectFile", "ProjectManifest", "RecipeBook", "RunBudget", "RunOutcome", "StepContext",
    "StepResult", "TaskBudget", "Workspace", "ancestors", "execute", "goal_signature", "make_plan",
    "make_replanner", "manifest_from_plan", "merge_subtree", "next_ready", "normalize_goal", "plan_from_dict",
    "plan_to_dict", "read_journal", "replan_subtree", "repo_map", "report_from_journal", "restore", "subtree",
    "toposort", "validate", "validate_manifest",
]
