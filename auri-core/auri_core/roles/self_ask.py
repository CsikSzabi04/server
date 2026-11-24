"""Self-questioning (02/03): answer sub-questions from the cheapest source, notice gaps from external
signals, keep curiosity questions for later (P4) — never with personal data, never duplicated."""

from __future__ import annotations

import difflib
import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from .. import privacy
from .schemas import SOURCES
from .session import RoleSession
from .turns import SubQuestion, Understanding, understand

Answerer = Callable[[str], Awaitable[str | None]]
AUTO_SOURCES = tuple(s for s in SOURCES if s != "user")  # the user is never asked automatically


async def answer_subquestions(u: Understanding, answerers: dict[str, Answerer], *,
                             session: RoleSession | None = None, depth: int = 0, max_depth: int = 1) -> Understanding:
    """02/03 §1 selfAsk: try the declared source, then the next more expensive ones (never `user`).
    An unanswered sub-question may be split once more (max depth 2 in total) if a session is given."""
    for s in u.subquestions:
        start = AUTO_SOURCES.index(s.source) if s.source in AUTO_SOURCES else len(AUTO_SOURCES)
        for src in AUTO_SOURCES[start:]:
            fn = answerers.get(src)
            if fn is None:
                continue
            ans = await fn(s.q)
            if ans:
                s.answer, s.answered_by = ans, src
                break
        if s.answer is None and session is not None and depth < max_depth and s.source != "user":
            sub = await answer_subquestions(await understand(session, s.q), answerers, session=None,
                                            depth=depth + 1, max_depth=max_depth)
            got = [f"{x.q} → {x.answer}" for x in sub.subquestions if x.answer]
            if got:
                s.answer, s.answered_by = "; ".join(got)[:600], "self_ask"
    return u


# ───────────────────────────── gaps (02/03 §3) ─────────────────────────────

GapSignal = Literal["no_card", "unknown_api", "version_mismatch", "unknown_error", "sources_disagree",
                    "self_inconsistent", "model_unsure"]


@dataclass(frozen=True)
class KnowledgeGap:
    topic: str
    signal: GapSignal
    severity: Literal[1, 2, 3]  # 3 = the task cannot be solved without it → fill now or ask_help
    seen_in: str  # session id, never the user's text


_UNSURE = re.compile(r"\b(i don'?t know|not sure|unsure|nem tudom|nem vagyok biztos|bizonytalan)\b", re.I)


def model_unsure(text: str) -> bool:
    """The weakest gap signal (02/03 §3): the model itself says it does not know."""
    return bool(_UNSURE.search(text or ""))


# ───────────────────────────── curiosity queue (02/03 §5) ─────────────────────────────

Origin = Literal["gap", "failed_task", "disputed", "teach_back"]
_PATHISH = re.compile(r"[A-Za-z]:[\\/]|(?:^|\s)/(?:home|users|Users)/|\\\\")


@dataclass
class CuriosityItem:
    question: str
    topic: str
    origin: Origin
    priority: float
    created_at: str
    seen: int = 1
    usefulness: float = 0.5  # programming usefulness 0..1
    severity: int = 1
    attempts: int = 0
    status: Literal["open", "studied", "dropped"] = "open"


def topic_key(text: str) -> str:
    t = privacy.fold(text) if hasattr(privacy, "fold") else text.lower()
    words = re.findall(r"[a-z0-9_.+#-]{3,}", t)
    return " ".join(sorted(set(words))[:8])


@dataclass
class CuriosityQueue:
    """Bounded (200 open items, 02/03 §5), dedup by topic key + similarity ≥ 0.82, privacy-filtered.
    priority = seen × usefulness × severity. Optional JSON persistence (`path`)."""

    path: Path | None = None
    limit: int = 200
    similar: float = 0.82
    items: list[CuriosityItem] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path, **kw: object) -> CuriosityQueue:
        q = cls(path=path, **kw)  # type: ignore[arg-type]
        if path.exists():
            q.items = [CuriosityItem(**d) for d in json.loads(path.read_text(encoding="utf-8"))]
        return q

    def save(self) -> None:
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps([asdict(i) for i in self.items], ensure_ascii=False, indent=1),
                                 encoding="utf-8")

    def _find(self, question: str, topic: str) -> CuriosityItem | None:
        for it in self.items:
            if it.status != "dropped" and (it.topic == topic or difflib.SequenceMatcher(
                    None, it.question.casefold(), question.casefold()).ratio() >= self.similar):
                return it
        return None

    def add(self, question: str, *, origin: Origin = "gap", usefulness: float = 0.5, severity: int = 1,
            topic: str | None = None) -> CuriosityItem | None:
        """Returns the (new or bumped) item, or None if refused (personal data, path, empty)."""
        q = " ".join((question or "").split())[:300]
        if not q or privacy.is_personal(q) or _PATHISH.search(q):
            return None  # must be general and impersonal: no names, no paths (02/03 §5 rule 1)
        key = topic or topic_key(q)
        old = self._find(q, key)
        if old is not None:
            old.seen += 1
            old.severity = max(old.severity, severity)
            old.usefulness = max(old.usefulness, usefulness)
            old.priority = old.seen * old.usefulness * old.severity
            return old
        it = CuriosityItem(q, key, origin, usefulness * max(1, severity),
                           datetime.now(UTC).isoformat(timespec="seconds"), usefulness=usefulness,
                           severity=max(1, min(3, severity)))
        self.items.append(it)
        open_items = [i for i in self.items if i.status == "open"]
        if len(open_items) > self.limit:  # the lowest priority falls out
            self.items.remove(min(open_items, key=lambda i: (i.priority, i.created_at)))
        return it if it in self.items else None

    def attempt(self, item: CuriosityItem, *, success: bool) -> None:
        item.attempts += 1
        if success:
            item.status = "studied"
        elif item.attempts >= 3:
            item.status = "dropped"

    def next(self, n: int = 5) -> list[CuriosityItem]:
        return sorted((i for i in self.items if i.status == "open"), key=lambda i: -i.priority)[:n]


def gap_to_curiosity(queue: CuriosityQueue, gap: KnowledgeGap, question: str, usefulness: float = 0.5) -> None:
    if gap.severity < 3:  # severity 3 is filled now (or ends in ask_help), not queued
        queue.add(question, origin="gap", usefulness=usefulness, severity=gap.severity, topic=None)


__all__ = ["AUTO_SOURCES", "CuriosityItem", "CuriosityQueue", "KnowledgeGap", "SubQuestion", "answer_subquestions",
           "gap_to_curiosity", "model_unsure", "topic_key"]
