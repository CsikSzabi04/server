"""Recipes (07/01 §7, 07/05 §9): a plan that ran to green is stored as reusable knowledge and found
again by a normalized goal signature → the next plan needs 0 model calls.

Stored as a `KnowledgeItem(kind="howto", topic="recipe")` through the store API (privacy gate inside
the store; a refusal never breaks the run). Status `verified` with `tests_passed`: the evidence is the
run's green checks (provenance: verified_by episode <run_id>), never the model's opinion.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any

from ..contracts import GUEST, KnowledgeItem, PrivacyRejected, Provenance, Scope
from .model import Plan, PlanError, plan_from_dict, plan_to_dict
from .validate import validate

RECIPE_VERSION = 1
# filler words that do not change what is being built (hu + en; compared after accent stripping)
_STOP = frozenset({
    "a", "az", "egy", "es", "meg", "is", "hogy", "kell", "kerlek", "legyen", "nekem", "szamomra", "irj",
    "csinalj", "keszits", "the", "an", "and", "please", "me", "for", "make", "write", "create", "build",
    "some", "with",
})


def normalize_goal(goal: str) -> str:
    t = unicodedata.normalize("NFKD", goal.lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    words = [w for w in re.findall(r"[a-z0-9]+", t) if w not in _STOP]
    return " ".join(words)


def goal_signature(goal: str) -> str:
    """One alphanumeric token (survives the store's FTS tokenizer as a single term)."""
    return "rcp" + hashlib.sha256(normalize_goal(goal).encode("utf-8")).hexdigest()[:24]


def _field(h: Any, name: str) -> Any:
    v = getattr(h, name, None)
    if v is None:
        v = (getattr(h, "data", None) or {}).get(name)
    return v


class RecipeBook:
    """Recipes over any store with `search` + `put` (contracts.KnowledgeStore / store.SqliteCodeMemory)."""

    def __init__(self, store: Any, *, scope: Scope = GUEST, on_event: Any = None) -> None:
        self.store = store
        self.scope = scope
        self.on_event = on_event

    def _emit(self, event: str, **data: Any) -> None:
        if self.on_event is not None:
            self.on_event(event, data)

    async def lookup(self, goal: str) -> Plan | None:
        """A verified recipe for this goal → a fresh plan (version 1, created_by 'recipe'), else None."""
        if self.store is None or not normalize_goal(goal):
            return None
        sig = goal_signature(goal)
        try:
            hits = await self.store.search(sig, kinds={"knowledge"}, scope=self.scope, k=5)
        except Exception as e:  # a broken store must not stop planning
            self._emit("recipe.error", kind=type(e).__name__)
            return None
        for h in hits or []:
            if _field(h, "status") != "verified":
                continue
            body = _field(h, "body")
            try:
                data = json.loads(body) if isinstance(body, str) else None
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(data, dict) or data.get("goal_signature") != sig:
                continue
            try:
                plan = plan_from_dict(data.get("plan"), goal=goal)
            except PlanError:
                continue
            plan = plan.fresh(version=1, created_by="recipe")
            for t in plan.tasks:
                t.recipe = sig
            if validate(plan):
                continue
            item_id = _field(h, "item_id") or _field(h, "id")
            self._emit("recipe.hit", recipe=sig, item=item_id)
            return plan
        return None

    async def save(self, goal: str, plan: Plan, *, run_id: str, model: str | None = None,
                   lang: str = "hu") -> str | None:
        """Store a plan that ran to green. Returns the item id, or None if refused (privacy gate)."""
        if self.store is None:
            return None
        sig = goal_signature(goal)
        item_id = f"recipe_{sig}"
        has = getattr(self.store, "has_item", None)
        if callable(has) and has(item_id):  # reused again successfully → a little more trust
            adjust = getattr(self.store, "adjust_trust", None)
            if callable(adjust):
                await adjust(item_id, 0.05, ref_id=run_id)
            self._emit("recipe.reused", recipe=sig)
            return item_id
        stored = plan.fresh(version=1)
        body = json.dumps({"recipe_version": RECIPE_VERSION, "goal_signature": sig,
                           "goal_normalized": normalize_goal(goal), "plan": plan_to_dict(stored)},
                          ensure_ascii=False, sort_keys=True)
        item = KnowledgeItem(id=item_id, kind="howto", lang=lang, title=f"recept {sig}: {goal.strip()[:120]}",
                             body=body, status="verified", verification="tests_passed", trust=0.6,
                             topic="recipe", tags=["recipe", sig])
        prov = [Provenance("verified_by", "episode", run_id)]
        if model:
            prov.append(Provenance("generated_by", "model", model))
        try:
            saved = await self.store.put(item, prov)
        except PrivacyRejected:
            self._emit("recipe.rejected", reason="privacy gate")
            return None
        except Exception as e:  # e.g. a duplicate id in a store without has_item — never fatal
            self._emit("recipe.error", kind=type(e).__name__)
            return None
        self._emit("recipe.saved", recipe=sig, item=saved)
        return saved
