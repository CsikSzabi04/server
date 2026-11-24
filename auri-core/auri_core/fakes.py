"""auri_core.fakes — test doubles for all three AIs (owner: AI-1). No Ollama, no sandbox, no disk.

FakeLLM checks that every call happens inside the FakeScheduler's active lease, so a test that
uses both proves the "no model call outside the scheduler" rule (01/01 §2).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, replace
from typing import Any

from .contracts import (
    CodeTask,
    Episode,
    ErrorPattern,
    Hit,
    KnowledgeItem,
    LLMReply,
    LLMStats,
    PrivacyRejected,
    Provenance,
    RunResult,
    RuntimeEnv,
    Scope,
    TaskFiles,
    TaskLimits,
    TaskSource,
    TestCase,
    Verification,
    VerifiedSnippet,
    tests_hash,
)


@dataclass(eq=False)
class FakeLease:
    prio: Any
    model: str
    preempt: asyncio.Event = field(default_factory=asyncio.Event)


class FakeScheduler:
    def __init__(self) -> None:
        self.holder: FakeLease | None = None
        self.leases: list[FakeLease] = []
        self.active_user = False
        self.preempt_next = False  # the next lease starts preempted (simulates user activity)

    @asynccontextmanager
    async def lease(self, prio: Any, model: str) -> AsyncIterator[FakeLease]:
        if self.holder is not None:
            raise AssertionError("nested lease: the lane is already held")
        lease = FakeLease(prio, model)
        if self.preempt_next:
            lease.preempt.set()
        self.holder = lease
        self.leases.append(lease)
        try:
            yield lease
        finally:
            self.holder = None

    def user_active(self) -> bool:
        return self.active_user


Reply = str | dict | list | LLMReply | BaseException | Callable[[list[dict[str, Any]]], Any]


class FakeLLM:
    """Scripted replies, in order. An item is raw text, a dict/list (sent as JSON), an LLMReply,
    an exception (raised), or a callable(messages) returning one of those."""

    def __init__(self, replies: list[Reply], *, scheduler: FakeScheduler | None = None) -> None:
        self.replies = list(replies)
        self.scheduler = scheduler
        self.calls: list[dict[str, Any]] = []

    async def chat(self, lease: Any, messages: list[dict[str, Any]], **kw: Any) -> LLMReply:
        if self.scheduler is not None and self.scheduler.holder is not lease:
            raise AssertionError("modellhívás aktív bérlet nélkül")
        self.calls.append({"model": lease.model, "messages": [dict(m) for m in messages], **kw})
        if not self.replies:
            raise AssertionError("FakeLLM: no scripted reply left")
        r: Any = self.replies.pop(0)
        if callable(r) and not isinstance(r, BaseException):
            r = r(messages)
        if isinstance(r, BaseException):
            raise r
        if isinstance(r, LLMReply):
            return r
        text = r if isinstance(r, str) else json.dumps(r)
        prompt_tokens = sum(len(str(m.get("content", ""))) for m in messages) // 4
        out = max(1, len(text) // 4)
        return LLMReply(text, LLMStats(model=lease.model, prompt_tokens=prompt_tokens, eval_tokens=out,
                                       eval_ms=out * 10, total_ms=out * 10 + 5, done_reason="stop"))


@dataclass
class FakeChunk:
    content: str
    done: bool = False
    stats: LLMStats | None = None


class FakeStreamLLM(FakeLLM):
    """FakeLLM + chat_stream (like llm.OllamaClient): the scripted reply comes back word by word.
    `stream_log` records how many chunks the consumer actually pulled (early close = cancellation)."""

    def __init__(self, replies: list[Reply], *, scheduler: FakeScheduler | None = None) -> None:
        super().__init__(replies, scheduler=scheduler)
        self.pulled = 0
        self.closed = False

    async def chat_stream(self, lease: Any, messages: list[dict[str, Any]], **kw: Any) -> AsyncIterator[FakeChunk]:
        reply = await self.chat(lease, messages, **kw)
        words = reply.text.split(" ")
        try:
            for i, w in enumerate(words):
                self.pulled += 1
                yield FakeChunk(w if i == 0 else " " + w)
            yield FakeChunk("", done=True, stats=reply.stats)
        finally:
            self.closed = True


def make_run(
    status: str = "pass",
    *,
    failing: list[tuple[str, str]] | None = None,
    passing: list[str] | None = None,
    stderr: str = "",
    stdout: str = "",
    phase: str = "test",
    blocked_reason: str | None = None,
) -> RunResult:
    """A RunResult for tests. `failing`: (test name, message) pairs."""
    failing = failing or []
    passing = passing or (["test_ok"] if status == "pass" else [])
    tests = [TestCase(n, True) for n in passing] + [TestCase(n, False, m) for n, m in failing]
    return RunResult(
        run_id="fake", status=status, phase=phase, tests=tests,  # type: ignore[arg-type]
        passed=len(passing), failed=len(failing), stdout=stdout, stderr=stderr, duration_ms=7,
        exit_code=0 if status == "pass" else 1, sandbox="S0", env=RuntimeEnv(python="3.12.6"),
        tests_hash="", blocked_reason=blocked_reason,
    )


class FakeSandbox:
    """Returns scripted RunResults (or statuses), or asks `judge(files, tests)`. Sets tests_hash."""

    def __init__(self, script: list[RunResult | str | BaseException] | None = None,
                 judge: Callable[[dict[str, str], dict[str, str]], RunResult | str] | None = None) -> None:
        self.script = list(script or [])
        self.judge = judge
        self.calls: list[dict[str, Any]] = []

    async def run_tests(self, files: dict[str, str], tests: dict[str, str], lang: str, timeout_s: float,
                        *, mem_mb: int | None = None) -> RunResult:
        self.calls.append({"files": dict(files), "tests": dict(tests), "lang": lang})
        r: Any = self.judge(files, tests) if self.judge else self.script.pop(0)
        if isinstance(r, BaseException):
            raise r
        if isinstance(r, str):
            r = make_run(r)
        return replace(r, tests_hash=tests_hash(tests))


class FakeStore:
    """In-memory CodeMemory + a minimal KnowledgeStore. `reject(text)` simulates the privacy gate."""

    def __init__(self, reject: Callable[[str], bool] | None = None) -> None:
        self.reject = reject or (lambda _t: False)
        self.solutions: dict[tuple[str, str], VerifiedSnippet] = {}
        self.uses: list[tuple[str, str, bool]] = []
        self.errors: dict[tuple[str, str], ErrorPattern] = {}
        self.items: dict[str, KnowledgeItem] = {}
        self.episodes: list[Episode] = []

    def _gate(self, *texts: str) -> None:
        if any(self.reject(t) for t in texts):
            raise PrivacyRejected("privacy gate refused the write")

    async def find_solution(self, task_signature: str, lang: str) -> VerifiedSnippet | None:
        return self.solutions.get((task_signature, lang))

    async def save_solution(self, snippet: VerifiedSnippet, *, task_signature: str,
                            prov: list[Provenance]) -> str:
        if not prov:
            raise ValueError("no provenance")
        self._gate(snippet.code, snippet.summary_hu, snippet.title)
        self.solutions[(task_signature, snippet.lang)] = snippet
        return snippet.id

    async def record_use(self, snippet_id: str, task_id: str, ok: bool) -> None:
        self.uses.append((snippet_id, task_id, ok))

    async def find_error(self, signature: str, lang: str) -> ErrorPattern | None:
        return self.errors.get((lang, signature)) or self.errors.get(("any", signature))

    async def save_error(self, pattern: ErrorPattern) -> str:
        self._gate(pattern.example, *(f.text_hu for f in pattern.fixes))
        key = (pattern.lang, pattern.signature)
        old = self.errors.get(key)
        if old is None:
            self.errors[key] = pattern
            return pattern.id
        for fx in pattern.fixes:  # merge counters of fixes with the same text
            same = next((o for o in old.fixes if o.text_hu == fx.text_hu), None)
            if same:
                same.worked += fx.worked
                same.failed += fx.failed
            else:
                old.fixes.append(fx)
        old.trust = max(old.trust, pattern.trust)  # type: ignore[assignment]
        return old.id

    async def search(self, q: str, *, kinds: set[str], scope: Scope, k: int = 8) -> list[Hit]:
        return []

    async def put(self, item: KnowledgeItem, prov: list[Provenance]) -> str:
        self._gate(item.title, item.body)
        self.items[item.id] = item
        return item.id

    async def promote(self, item_id: str, v: Verification) -> None:
        self.items[item_id].status = "verified"

    async def demote(self, item_id: str, reason: str) -> None:
        self.items[item_id].status = "stale"

    async def record_episode(self, ep: Episode) -> None:
        self._gate(ep.goal)
        self.episodes.append(ep)


def make_task(id: str = "py-l1-0001", *, lang: str = "py", split: str = "practice", level: int = 1,
              root: str | None = None) -> CodeTask:
    """A fictional task (no personal data)."""
    test = "tests/test_visible.py" if lang == "py" else "tests/visible.test.ts"
    return CodeTask(
        id=id, level=level, lang=lang, topics=("x.strings",), title_hu="Duplázás",  # type: ignore[arg-type]
        prompt_hu="Írj `double(n)` függvényt, ami a szám kétszeresét adja vissza.",
        signature="def double(n: int) -> int" if lang == "py" else "export function double(n: number): number",
        files=TaskFiles(visible=test, hidden=test.replace("visible", "hidden"), reference="ref/solution.py"),
        source=TaskSource("own", "own"), limits=TaskLimits(), split=split,  # type: ignore[arg-type]
        family="arith", rating=1000, root=root,
    )
