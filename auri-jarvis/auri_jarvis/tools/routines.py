"""Routines (AI-2, spec 5.6 / 5.11): config/routines.yaml + the user's own "Üdv itthon".

A routine expands into steps — `say` (spoken), `tool` (through the registry: allowlist,
tier, validation; `confirm` tools only with `preconfirmed: true` in the YAML), `url` and
`music` (http(s) only, opened in the configured browser). Everything here is logged-in
only; the caller checks the tier first and `run_steps` checks it again.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from ..contracts import Event, UserContext
from ..mind.hu_text import norm
from .registry import ToolContext, ToolRegistry

log = logging.getLogger(__name__)

WELCOME_ID = "udv_itthon"
StepKind = Literal["say", "tool", "url", "music"]


@dataclass(frozen=True)
class Step:
    kind: StepKind
    data: dict[str, Any]


@dataclass
class RoutineBook:
    routines: dict[str, dict[str, Any]] = field(default_factory=dict)
    welcome: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> RoutineBook:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except FileNotFoundError:
            return cls()
        return cls(routines=dict(data.get("routines") or {}), welcome=dict(data.get("welcome") or {}))

    # ── lookup ───────────────────────────────────────────────────────────────
    def phrases(self) -> dict[str, str]:
        """normalised spoken phrase → routine id (for the fast-path)."""
        out: dict[str, str] = {}
        for rid, r in self.routines.items():
            for p in r.get("phrases") or []:
                out[norm(p)] = rid
        for p in self.welcome.get("phrases") or []:
            out[norm(p)] = WELCOME_ID
        return out

    def names(self) -> list[str]:
        return [*self.routines, WELCOME_ID]

    def resolve(self, name: str) -> str | None:
        """Routine id from an id, a display name or a phrase ("munka mód" → munka)."""
        n = norm(name)
        for rid, r in self.routines.items():
            if n in (norm(rid), norm(r.get("name", ""))):
                return rid
        if n in (norm(WELCOME_ID), norm(self.welcome.get("name", "üdv itthon"))):
            return WELCOME_ID
        return self.phrases().get(n)

    def display_name(self, rid: str) -> str:
        if rid == WELCOME_ID:
            return str(self.welcome.get("name") or "Üdv itthon")
        return str(self.routines.get(rid, {}).get("name") or rid)

    def default_welcome(self) -> dict[str, Any]:
        d = self.welcome.get("default") or {}
        return {"music_url": d.get("music_url"), "apps": list(d.get("apps") or []), "urls": list(d.get("urls") or [])}

    # ── expansion ────────────────────────────────────────────────────────────
    def expand(self, rid: str, user: UserContext) -> list[Step] | None:
        """None = no such routine for this user (unknown id, or no welcome routine set)."""
        if rid == WELCOME_ID:
            wr = user.prefs.welcome_routine
            if not wr:
                return None
            addr = (user.prefs.address or "").strip()
            addr = "" if addr.lower() in ("", "you") else f", {addr}"
            steps = [Step("say", {"text": str(self.welcome.get("greeting", "Üdv itthon{address}.")).format(address=addr)})]
            if wr.get("music_url"):
                steps.append(Step("music", {"url": wr["music_url"]}))
            for a in wr.get("apps") or []:
                args = {"name": a.get("app"), "monitor": a.get("monitor"), "fullscreen": bool(a.get("fullscreen"))}
                steps.append(Step("tool", {"name": "open_app", "args": args}))
            for u in wr.get("urls") or []:
                steps.append(Step("url", {"url": u.get("url"), "monitor": u.get("monitor")}))
            return steps
        r = self.routines.get(rid)
        if r is None:
            return None
        steps = []
        for s in r.get("steps") or []:
            if "say" in s:
                steps.append(Step("say", {"text": str(s["say"])}))
            elif "tool" in s and isinstance(s["tool"], dict):
                t = s["tool"]
                steps.append(
                    Step(
                        "tool",
                        {"name": t.get("name"), "args": dict(t.get("args") or {}), "preconfirmed": bool(t.get("preconfirmed"))},
                    )
                )
        return steps


async def run_steps(steps: list[Step], ctx: ToolContext, registry: ToolRegistry) -> AsyncIterator[str]:
    """Execute a routine. Yields what to say (the greeting first, so speech starts while apps
    open), then one sentence about failures, if any."""
    if ctx.user.tier != "user":
        yield "A rutinokhoz be kell jelentkezned."
        return
    failed: list[str] = []
    for step in steps:
        if step.kind == "say":
            yield step.data["text"] + " "
        elif step.kind == "tool":
            res = await registry.call(
                step.data["name"], step.data.get("args"), ctx, confirmed=bool(step.data.get("preconfirmed"))
            )
            if not res.ok:
                failed.append(res.message)
        elif step.kind in ("url", "music"):
            ok = await _open_url(ctx, step)
            if not ok:
                failed.append(f"Nem sikerült megnyitni: {str(step.data.get('url'))[:60]}.")
    if failed:
        yield "Közben gond volt: " + " ".join(failed[:3])


async def _open_url(ctx: ToolContext, step: Step) -> bool:
    s = ctx.services
    url = str(step.data.get("url") or "")
    t0 = time.perf_counter()
    status = "ok"
    try:
        if not url.lower().startswith(("http://", "https://")):
            raise ValueError("only http(s) in routines")  # spotify: needs the desktop app (not installed)
        await asyncio.to_thread(s.platform.open_url, url, browser_path=s.apps.browser_path(), app_window=False)
        mon = step.data.get("monitor")
        browser = s.apps.get(s.apps.browser or "")
        if mon and browser and browser.window_match:
            await asyncio.to_thread(s.platform.place_window, browser.window_match, int(mon), "maximized", wait_s=8.0)
    except Exception as e:
        log.info("routine url step failed: %s", e)
        status = "error"
    ctx.emit(
        Event(
            "tool",
            {
                "name": f"routine.{step.kind}",
                "args": {"url": url[:120]},
                "status": status,
                "ms": int((time.perf_counter() - t0) * 1000),
            },
        )
    )
    return status == "ok"
