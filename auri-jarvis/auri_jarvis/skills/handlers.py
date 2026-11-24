"""Data gatherers for the built-in skills (AI-2): real data → <kontextus> lines, so the
LLM only phrases it (never invents it). Logged-in users only (the Mind checks the tier)."""

from __future__ import annotations

import asyncio
from datetime import datetime

from ..mind.hu_text import say_when
from ..tools.projects import list_repos, repo_status
from ..tools.registry import ToolContext
from ..tools.timers import owner_key

MAX_REPOS = 8


async def gather(name: str, ctx: ToolContext) -> list[tuple[str, str]]:
    s = ctx.services
    uid = str(ctx.user.user_id or "")
    lines: list[tuple[str, str]] = []
    if name == "napi-briefing":
        now = s.clock()
        if s.timers is not None:
            for it in s.timers.list(owner_key(ctx.user)):
                when = datetime.fromtimestamp(it.due)
                if when.date() == now.date():
                    lines.append(("briefing ma", f"{say_when(when, now)} {it.text or 'időzítő'}"))
        if s.memory is not None and uid:
            for f in s.memory.facts(uid, kind="summary", limit=1):
                lines.append(("briefing legutóbb", f.text))
        statuses = await asyncio.to_thread(lambda: [repo_status(p) for p in list_repos(s.projects_root)[:MAX_REPOS]])
        for st in statuses:
            if st.changed:
                lines.append(("briefing projekt", f"{st.name}: {st.changed} nem commitolt fájl"))
        if not lines:
            lines.append(("briefing", "nincs mai emlékeztető, nincs nem commitolt munka"))
    elif name == "projekt-statusz":
        statuses = await asyncio.to_thread(lambda: [repo_status(p) for p in list_repos(s.projects_root)[:MAX_REPOS]])
        lines = [("projekt", st.sentence()) for st in statuses] or [("projekt", "nincs git-projekt a projektmappában")]
    return lines
