"""Tool registry (AI-2): decorator → compact JSON schema, pydantic validation, risk and
tier gates, and one `tool` event per call (spec 5.6, 5.11, 8.5).

    reg = ToolRegistry()

    @reg.tool(risk="confirm", min_tier="user", confirm="Biztosan bezárjam: {name}?")
    def close_app(ctx: ToolContext, name: Annotated[str, Field(description="...")]) -> ToolResult:
        "Egy alkalmazás bezárása."

Gates, in this order: unknown tool → error · tier (guest calling a `user` tool) → denied ·
argument validation → error · `confirm` risk without explicit confirmation →
needs_confirm (the tool does NOT run) · run (exceptions → error, detail only in the log).
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal, get_type_hints

from pydantic import BaseModel, ConfigDict, ValidationError, create_model

from ..contracts import Emit, Event, UserContext

log = logging.getLogger(__name__)

Risk = Literal["safe", "confirm"]
MinTier = Literal["guest", "user"]
Status = Literal["ok", "error", "denied", "needs_confirm"]

DENIED_GUEST = "Ehhez be kell jelentkezned."


@dataclass(frozen=True)
class ToolResult:
    status: Status
    message: str  # Hungarian, safe to speak; what the LLM / the user gets
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def for_llm(self) -> str:
        """Tool-message content. Data from outside (clipboard, files…) stays marked as data."""
        payload: dict[str, Any] = {"status": self.status, "message": self.message}
        if self.data:
            payload["data"] = self.data
        return json.dumps(payload, ensure_ascii=False)


def ok(message: str, **data: Any) -> ToolResult:
    return ToolResult("ok", message, data)


def fail(message: str, **data: Any) -> ToolResult:
    return ToolResult("error", message, data)


def denied(message: str = DENIED_GUEST) -> ToolResult:
    return ToolResult("denied", message)


@dataclass
class ToolContext:
    user: UserContext
    emit: Emit
    services: Any = None  # tools.builtin.ToolServices (platform, apps, timers, clock…)


ToolFn = Callable[..., ToolResult | Awaitable[ToolResult]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    fn: ToolFn
    model: type[BaseModel]
    risk: Risk
    min_tier: MinTier
    confirm: str | Callable[[dict[str, Any]], str] | None  # question: template or fn(args)

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": _compact(self.model)},
        }


def _strip_titles(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _strip_titles(v) for k, v in node.items() if k != "title"}
    if isinstance(node, list):
        return [_strip_titles(v) for v in node]
    return node


def _compact(model: type[BaseModel]) -> dict[str, Any]:
    """Small-model friendly JSON schema: no titles, Optional[X] → X (not required)."""
    s = _strip_titles(model.model_json_schema())
    props: dict[str, Any] = s.get("properties", {})
    for name, p in list(props.items()):
        if "anyOf" in p:
            branches = [b for b in p["anyOf"] if b.get("type") != "null"]
            if len(branches) == 1:
                merged = {**branches[0], **{k: v for k, v in p.items() if k not in ("anyOf", "default")}}
                props[name] = merged
        props[name].pop("default", None)
    out: dict[str, Any] = {"type": "object", "properties": props}
    if s.get("required"):
        out["required"] = s["required"]
    return out


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def tool(
        self,
        *,
        risk: Risk = "safe",
        min_tier: MinTier = "guest",
        confirm: str | Callable[[dict[str, Any]], str] | None = None,
        name: str | None = None,
    ) -> Callable[[ToolFn], ToolFn]:
        def deco(fn: ToolFn) -> ToolFn:
            tname = name or fn.__name__
            if tname in self._tools:
                raise ValueError(f"duplicate tool {tname}")
            hints = get_type_hints(fn, include_extras=True)
            params = list(inspect.signature(fn).parameters.values())[1:]  # skip ctx
            fields: dict[str, Any] = {}
            for p in params:
                default = ... if p.default is inspect.Parameter.empty else p.default
                fields[p.name] = (hints.get(p.name, str), default)
            model = create_model(f"{tname}_args", __config__=ConfigDict(extra="forbid"), **fields)
            doc = inspect.getdoc(fn) or tname
            desc = " ".join(doc.split("\n\n", 1)[0].split())
            self._tools[tname] = ToolSpec(tname, desc, fn, model, risk, min_tier, confirm)
            return fn

        return deco

    # ── introspection ─────────────────────────────────────────────────────────
    def names(self) -> list[str]:
        return sorted(self._tools)

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def schemas(self) -> list[dict[str, Any]]:
        """Fixed order (by name) → byte-stable part of the cached prompt prefix."""
        return [self._tools[n].schema() for n in self.names()]

    # ── execution ─────────────────────────────────────────────────────────────
    async def call(self, name: str, args: dict[str, Any] | None, ctx: ToolContext, *, confirmed: bool = False) -> ToolResult:
        t0 = time.perf_counter()
        spec = self._tools.get(name)
        clean: dict[str, Any] = dict(args or {})
        if spec is None:
            res = fail("Ilyen eszközöm nincs.")
        elif spec.min_tier == "user" and ctx.user.tier != "user":
            res = denied()
        else:
            try:
                validated = spec.model.model_validate(clean)
            except ValidationError as e:
                fields = ", ".join(sorted({str(err["loc"][0]) for err in e.errors() if err.get("loc")}))
                res = fail(f"Hibás paraméter: {fields or 'ismeretlen'}.")
            else:
                clean = validated.model_dump()
                if spec.risk == "confirm" and not confirmed:
                    if callable(spec.confirm):
                        question = spec.confirm(clean)
                    else:
                        question = (spec.confirm or "Biztos? Mondd, hogy igen.").format(**clean)
                    res = ToolResult("needs_confirm", question, {"tool": name, "args": clean})
                else:
                    res = await self._run(spec, ctx, clean)
        ms = int((time.perf_counter() - t0) * 1000)
        ctx.emit(
            Event(
                "tool",
                {"name": name, "args": clean, "status": res.status, "ms": ms, "message": res.message},
            )
        )
        if res.status == "denied":
            log.info("tool %s denied for tier %s", name, ctx.user.tier)
        return res

    @staticmethod
    async def _run(spec: ToolSpec, ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
        # Sync tools may block (window waits, git, COM) → worker thread, never on the loop
        # (JARVIS_BUILD 2.2). Async tools (timers) run on the loop.
        try:
            if inspect.iscoroutinefunction(spec.fn):
                out = await spec.fn(ctx, **args)
            else:
                out = await asyncio.to_thread(spec.fn, ctx, **args)
        except Exception:
            log.exception("tool %s failed", spec.name)
            return fail("Ez most nem sikerült.")
        if not isinstance(out, ToolResult):
            log.error("tool %s returned %r", spec.name, type(out))
            return fail("Ez most nem sikerült.")
        return out
