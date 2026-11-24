"""auri_core.contracts — the shared language of the three AIs building Auri Core.

Owner: AI-1 (MIND). AI-2 (HANDS) and AI-3 (BODY) only IMPORT from here; nobody keeps a
parallel copy. Change requests: ideas_for_brain/ai_prompts.md §6.3 → AI-1 edits → §6.1 log.

Every type mirrors a schema of the spec in ideas_for_brain/thinking/ (the doc is named in each
docstring). Field names are the snake_case form of the spec's camelCase names. P0 rule: standard
library only (dataclasses); the P1 HTTP layer (AI-3) may wrap these in pydantic models.

Wiring contract (who provides which factory — `python -m auri_core run` relies on these names):
    AI-3  auri_core.llm.OllamaClient()           -> LLMClient
    AI-3  auri_core.scheduler.get_scheduler()    -> Scheduler
    AI-3  auri_core.store.open_store()           -> CodeMemory (+ KnowledgeStore from P1)
    AI-2  auri_core.sandbox.create_sandbox()     -> Sandbox
    AI-2  auri_core.taskset.load(path)           -> CodeTask
    AI-1  auri_core.solve.solve(...)             -> Outcome;   auri_core.solve.main_run(argv) -> int

Run-directory layout (sandbox ⇄ solving loop): the solution file sits at the run-dir root under
SOLUTION_FILENAME[lang]; test files keep their task-relative paths (e.g. "tests/test_visible.py").
This matches the spec examples: `from solution import parse_forint`, `import … from '../solution.ts'`.

Two name clashes in the spec, kept apart here on purpose:
  * "L0–L4" = programming levels (06/01) → TaskLevel; and router levels (08/02) → RouteLevel.
  * "T0–T4" = snippet trust (06/03 §3) → Trust; "T0/T1/T2" = privacy tiers (01/03 §6) → Scope.
"""

from __future__ import annotations

import asyncio
import enum
import hashlib
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

# ───────────────────────────── shared names (thinking.md §9) ─────────────────────────────

Lang = Literal["ts", "js", "py", "sql"]  # languages of a CodeTask (06/08 §1, 06/04 §6)
SnippetLang = Literal["ts", "js", "py", "sql", "css", "html"]  # 06/03 §2
PatternLang = Literal["ts", "js", "py", "sql", "any"]  # 06/06 §7
TaskLevel = Literal[0, 1, 2, 3, 4]  # programming levels L0–L4 (06/01)
RouteLevel = Literal[0, 1, 2, 3, 4]  # router levels: L0 cache … L4 cloud (08/02 §1)
SandboxLevel = Literal["S0", "S0+", "S1", "S2"]  # 06/04 §4
Split = Literal["practice", "dev", "heldout", "regression", "public-sanity"]  # 06/08 §1 + 06/09 §2
Mode = Literal["chat", "code", "research", "study"]  # 01/02 §5
Trust = Literal[0, 1, 2, 3, 4]  # snippet / error-pattern trust T0–T4 (06/03 §3)
KnowledgeStatus = Literal["hypothesis", "verified", "contested", "stale", "refuted", "archived"]  # 01/04 §1
VerificationKind = Literal["tests_passed", "multi_source", "user_confirmed", "curated", "critic_ok"]  # 01/04 §2

# Where the solution file lives inside a run directory (see the module docstring).
SOLUTION_FILENAME: dict[str, str] = {
    "py": "solution.py",
    "ts": "solution.ts",
    "js": "solution.js",
    "sql": "solution.sql",
}

# Splits whose solutions may be learned (06/03 §1: never dev/heldout; 06/09 §2: regression may).
LEARNABLE_SPLITS: frozenset[str] = frozenset({"practice", "regression"})


class Priority(enum.IntEnum):
    """Ollama-lane priority classes (08/02 §4). A higher value wins: VOICE > CHAT > TASK > BACKGROUND."""

    BACKGROUND = 0
    TASK = 1
    CHAT = 2
    VOICE = 3


class State(enum.StrEnum):
    """Working states of the thinking cycle (01/02 §1)."""

    RECALL = "RECALL"
    UNDERSTAND = "UNDERSTAND"
    PLAN = "PLAN"
    ACT = "ACT"
    VERIFY = "VERIFY"
    REPAIR = "REPAIR"
    REFLECT = "REFLECT"
    STORE = "STORE"


class EndState(enum.StrEnum):
    """Final states of the thinking cycle (01/02 §1)."""

    DONE = "DONE"
    ASK_USER = "ASK_USER"
    GIVE_UP = "GIVE_UP"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


class Role(enum.StrEnum):
    """Internal roles of the role-book session + the user-facing writer (02/01, 02/04)."""

    KERDEZO = "KERDEZO"
    TESZTELO = "TESZTELO"
    GONDOLKODO = "GONDOLKODO"
    KRITIKUS = "KRITIKUS"
    TANAR = "TANAR"
    KIVONATOLO = "KIVONATOLO"
    VALASZTO = "VALASZTO"
    FOGALMAZO = "FOGALMAZO"  # runs in the persona session, not in the role-book


# ───────────────────────────── errors shared across modules ─────────────────────────────


class Cancelled(Exception):
    """Work stopped because the lease was preempted (user became active, 08/02 §4)."""


class PrivacyRejected(Exception):
    """Raised by a store when the privacy gate refuses a write (09/01). Never contains the data."""


class InfrastructureError(Exception):
    """The machinery failed (sandbox could not start, Ollama down) — not the code under test (01/02 §2)."""


# ───────────────────────────── CodeTask (06/08 §1) ─────────────────────────────


@dataclass(frozen=True)
class TaskFiles:
    visible: str  # task-relative path, e.g. "tests/visible.test.ts" — the only tests a model may see
    hidden: str  # NEVER read by the solving loop, never shown to a model (06/05 §2, 06/09 §8)
    reference: str  # only for validating the task itself


@dataclass(frozen=True)
class TaskSource:
    kind: Literal["own", "exercism", "generated"]
    license: str  # 'own' or an SPDX id (exercism → 'MIT')


@dataclass(frozen=True)
class TaskLimits:
    wall_s: float = 20.0
    mem_mb: int = 512


@dataclass(frozen=True)
class CodeTask:
    id: str  # "ts-l1-0007"
    level: TaskLevel
    lang: Lang
    topics: tuple[str, ...]
    title_hu: str
    prompt_hu: str
    signature: str  # "export function slugifyHu(s: string): string"
    files: TaskFiles
    source: TaskSource
    limits: TaskLimits
    split: Split
    family: str
    rating: int
    root: str | None = None  # runtime only: the task directory, set by taskset.load(); not in task.yaml


# ───────────────────────────── RunResult (06/04 §7) ─────────────────────────────

RunStatus = Literal["pass", "fail", "error", "timeout", "oom", "blocked"]
RunPhase = Literal["static", "typecheck", "test"]


@dataclass
class TestCase:
    __test__ = False  # not a pytest test class

    name: str
    ok: bool
    message: str | None = None
    expected: str | None = None
    actual: str | None = None


@dataclass
class RuntimeEnv:
    node: str | None = None
    python: str | None = None
    typescript: str | None = None


@dataclass
class RunResult:
    __test__ = False

    run_id: str
    status: RunStatus
    phase: RunPhase  # where it stopped
    tests: list[TestCase]
    passed: int
    failed: int
    stdout: str  # ANSI stripped, run path → '<RUN>', ≤ 8 KB
    stderr: str
    duration_ms: int
    exit_code: int | None
    sandbox: SandboxLevel
    env: RuntimeEnv
    tests_hash: str  # tests_hash() of the frozen tests (06/05 §8)
    blocked_reason: str | None = None  # static filter / audit hook / permission
    peak_mem_mb: float | None = None

    @property
    def ok(self) -> bool:
        return self.status == "pass"


TestReport = RunResult  # 01/01 §4 calls the Verifier's result TestReport; it is the same object


def tests_hash(tests: dict[str, str]) -> str:
    """Hash of a frozen test set (06/05 §8). Order-independent; sandbox and loop must both use this."""
    h = hashlib.sha256()
    for path in sorted(tests):
        h.update(path.replace("\\", "/").encode("utf-8"))
        h.update(b"\x00")
        h.update(tests[path].replace("\r\n", "\n").encode("utf-8"))
        h.update(b"\x00")
    return "sha256:" + h.hexdigest()


# ───────────────────────────── VerifiedSnippet (06/03 §2) ─────────────────────────────


@dataclass
class SnippetTest:
    framework: Literal["node:test", "pytest", "sqlite", "static"]
    code: str


@dataclass
class SnippetEnv:
    node: str | None = None
    python: str | None = None
    typescript: str | None = None
    deps: dict[str, str] = field(default_factory=dict)


@dataclass
class SnippetSource:
    kind: Literal["own-loop", "curated", "doc", "web", "own-repo"]
    license: str  # SPDX id, 'own' or 'unknown'
    url: str | None = None
    repo_path: str | None = None
    commit: str | None = None
    attribution: str | None = None


@dataclass
class SnippetVerification:
    status: Literal["pass", "fail", "never"]
    run_id: str | None = None
    at: str | None = None  # ISO-8601
    sandbox: Literal["S0", "S1"] | None = None


@dataclass
class SnippetUsage:
    retrieved: int = 0
    used_in_solution: int = 0
    solution_passed: int = 0
    last_used_at: str | None = None


@dataclass
class VerifiedSnippet:
    """A stored, tested piece of code. The 01/04 `code_snippets` row additionally carries a
    KnowledgeStatus: verification.status == 'pass' and trust ≥ 2 ⇒ 'verified', else 'hypothesis'."""

    id: str  # 'snip_ts_slugify_hu_01'
    lang: SnippetLang
    title: str
    summary_hu: str  # what it does, when to use it (1–2 sentences)
    code: str  # verbatim, ≤ 80 lines (06/03 §1)
    tests: list[SnippetTest]
    env: SnippetEnv
    topics: list[str]
    symbols: list[str]  # used APIs: 'Array.prototype.map', 'pathlib.Path'
    source: SnippetSource
    trust: Trust
    verification: SnippetVerification
    usage: SnippetUsage
    created_at: str
    updated_at: str
    superseded_by: str | None = None


# ───────────────────────────── ErrorPattern (06/06 §7) ─────────────────────────────


@dataclass
class ErrorCause:
    text_hu: str
    freq: int = 1


@dataclass
class ErrorFix:
    text_hu: str
    snippet_id: str | None = None
    worked: int = 0
    failed: int = 0


@dataclass
class PatternSource:
    kind: Literal["own-loop", "doc", "web"]
    license: str
    url: str | None = None


@dataclass
class ErrorPattern:
    id: str
    lang: PatternLang
    signature: str  # normalized form — the key (digest.normalize_error)
    example: str  # one real, normalized example
    causes: list[ErrorCause]
    fixes: list[ErrorFix]
    source: PatternSource
    trust: Trust  # only a fix that turned a test green in the sandbox raises it to T2+


@dataclass(frozen=True)
class NormalizedError:
    signature: str
    slots: tuple[str, ...]


# ───────────────────────────── knowledge store (01/04) ─────────────────────────────


@dataclass(frozen=True)
class Scope:
    """Who is asking (01/03 §6): guest reads T0 only; user reads T0 + own T1; system writes T0 only."""

    identity: Literal["guest", "user", "system"]
    user_id: str | None = None  # only for identity == "user"


GUEST = Scope("guest")
SYSTEM = Scope("system")


@dataclass(frozen=True)
class Provenance:
    """One `provenance` row (01/04 §2). No knowledge without at least one."""

    relation: Literal["derived_from", "verified_by", "contradicted_by", "generated_by"]
    ref_type: Literal["source", "episode", "model", "feedback", "seed", "cloud"]
    ref_id: str


@dataclass(frozen=True)
class Verification:
    """Why an item may become 'verified' (01/04 §4)."""

    kind: VerificationKind
    evidence: Provenance


@dataclass
class KnowledgeItem:
    """One `knowledge_items` row (01/04 §2)."""

    id: str
    kind: Literal["fact", "concept", "howto", "qa", "summary"]
    lang: str
    title: str
    body: str
    status: KnowledgeStatus = "hypothesis"
    verification: VerificationKind | None = None
    trust: float = 0.3  # 0..1
    topic: str | None = None
    tags: list[str] = field(default_factory=list)
    version_tag: str | None = None
    ttl_days: int | None = None


@dataclass
class Hit:
    item_type: Literal["knowledge", "snippet", "lesson", "error_pattern"]
    item_id: str
    title: str
    body: str
    status: KnowledgeStatus
    trust: float
    score: float


@dataclass
class EpisodeStep:
    """One `episode_steps` row (01/04 §2)."""

    seq: int
    state: str  # State or EndState value
    model: str | None = None
    prompt_hash: str | None = None
    out_tokens: int | None = None
    ms: int | None = None
    verdict: str | None = None
    signature: str | None = None


@dataclass
class Episode:
    """One `episodes` row + its steps (01/04 §2). Append-only."""

    id: str
    mode: Mode
    origin: Literal["user", "selfstudy", "system"]
    goal: str  # passes the privacy gate before it is written
    started_at: str
    outcome: EndState | None = None
    level_start: int | None = None
    level_end: int | None = None
    llm_calls: int = 0
    out_tokens: int = 0
    wall_ms: int = 0
    repair_rounds: int = 0
    predicted_success: float | None = None
    ended_at: str | None = None
    steps: list[EpisodeStep] = field(default_factory=list)


@dataclass
class Lesson:
    """One `lessons` row (01/04 §2): ≤ 3 sentences from an episode."""

    id: str
    episode_id: str | None
    text: str
    success: bool
    tags: list[str] = field(default_factory=list)


class KnowledgeStore(Protocol):
    """The general store (01/01 §4). Implemented by AI-3 from P1; every write passes the privacy gate."""

    async def search(self, q: str, *, kinds: set[str], scope: Scope, k: int = 8) -> list[Hit]: ...
    async def put(self, item: KnowledgeItem, prov: list[Provenance]) -> str: ...  # status 'hypothesis'
    async def promote(self, item_id: str, v: Verification) -> None: ...  # → 'verified'
    async def demote(self, item_id: str, reason: str) -> None: ...  # → 'stale' / 'refuted'
    async def record_episode(self, ep: Episode) -> None: ...


class CodeMemory(Protocol):
    """The P0 part of the store: solutions (C3 cache, 08/04 §2) and the error knowledge base (06/06 §7).

    Implemented by AI-3 (`store.open_store()`). Every write runs the privacy gate and raises
    PrivacyRejected when refused. `task_signature` is computed by the solving loop."""

    async def find_solution(self, task_signature: str, lang: str) -> VerifiedSnippet | None: ...
    async def save_solution(
        self, snippet: VerifiedSnippet, *, task_signature: str, prov: list[Provenance]
    ) -> str: ...
    async def record_use(self, snippet_id: str, task_id: str, ok: bool) -> None: ...  # snippet_use row
    async def find_error(self, signature: str, lang: str) -> ErrorPattern | None: ...
    async def save_error(self, pattern: ErrorPattern) -> str: ...  # upsert by (lang, signature)


# ───────────────────────────── model calls + the lane (08/02 §4) ─────────────────────────────


@dataclass
class LLMStats:
    """Same fields as auri_jarvis.mind.ollama_provider.LLMStats, so AI-3 can copy them 1:1."""

    model: str = ""
    first_token_ms: int | None = None
    load_ms: int = 0
    prompt_tokens: int = 0
    prompt_ms: int = 0
    eval_tokens: int = 0
    eval_ms: int = 0
    total_ms: int = 0
    done_reason: str = ""  # "length" = cut off at num_predict


@dataclass
class LLMReply:
    text: str
    stats: LLMStats


REPEAT_ABORT = "repeat_limit"  # LLMStats.done_reason of a reply Ollama aborted as a repetition loop
ABORTED = ("length", REPEAT_ABORT)  # cut off / aborted: a JSON-fix request would end the same way


async def chat_or_abort(llm: Any, lease: Any, messages: list[dict[str, Any]], **kw: Any) -> LLMReply:
    """`llm.chat`, except that Ollama's 'token repeat limit reached' abort (HTTP 500; heldout
    py-l1-h-0021, 2026-11-22) becomes an EMPTY reply with done_reason=REPEAT_ABORT: the model looped,
    which is the model's failure (garbage output), not infrastructure. Everything else is re-raised."""
    try:
        return await llm.chat(lease, messages, **kw)
    except Exception as e:
        if "repeat limit" not in f"{getattr(e, 'detail', '')} {e}".lower():
            raise
        return LLMReply("", LLMStats(model=str(getattr(lease, "model", "")), done_reason=REPEAT_ABORT))


class Lease(Protocol):
    """A grant of the one Ollama lane (AI-3: scheduler.Lease). The model is fixed by the lease."""

    prio: Any
    model: str
    preempt: asyncio.Event  # set → a higher priority wants the lane; stop at the next step


class LLMClient(Protocol):
    """Ollama client (AI-3, `llm.OllamaClient()`). Usable ONLY with an active lease (else LeaseError).

    `messages` are Ollama chat messages ({"role": "system"|"user"|"assistant", "content": str}).
    `format` is a JSON schema (or "json"); `options` carries extra Ollama options, e.g. {"seed": 42}.
    The reply has `.text` and `.stats` (LLMReply shape; AI-3 returns llm.ChatResult)."""

    async def chat(
        self,
        lease: Lease,
        messages: list[dict[str, Any]],
        *,
        format: dict[str, Any] | str | None = None,
        num_predict: int | None = None,
        temperature: float | None = None,
        num_ctx: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> LLMReply: ...


class Scheduler(Protocol):
    """The one Ollama lane (AI-3, `scheduler.get_scheduler()`); 08/02 §4."""

    def lease(self, prio: Priority, model: str) -> AbstractAsyncContextManager[Lease]: ...
    def user_active(self) -> bool: ...


# ───────────────────────────── sandbox (06/04) ─────────────────────────────


class Sandbox(Protocol):
    """Runs code in isolation (AI-2, `sandbox.create_sandbox()`); the `Verifier.run_tests` of 01/01 §4.

    `files` / `tests`: run-dir-relative path → content (layout: module docstring). The sandbox
    refuses to run when the tests do not match `tests_hash(tests)` (status 'blocked').
    Raises InfrastructureError only when the sandbox itself fails; failing code is a RunResult."""

    async def run_tests(
        self,
        files: dict[str, str],
        tests: dict[str, str],
        lang: str,
        timeout_s: float,
        *,
        mem_mb: int | None = None,
    ) -> RunResult: ...


# ───────────────────────────── routing + budgets (01/02 §5, 08/02) ─────────────────────────────


@dataclass(frozen=True)
class Budget:
    """Per-task budget; all roles' calls count together (01/02 §5)."""

    llm_calls: int
    out_tokens: int
    wall_s: float
    repair_rounds: int = 3
    sandbox_runs: int = 4
    web_searches: int = 0
    web_pages: int = 0
    escalations: int = 1


# 01/02 §5 table (estimates, to be calibrated from P0 episodes).
BUDGETS: dict[str, Budget] = {
    "chat": Budget(llm_calls=2, out_tokens=400, wall_s=90, repair_rounds=0, escalations=0),
    "code": Budget(llm_calls=8, out_tokens=5000, wall_s=15 * 60, repair_rounds=3, escalations=1),
    "research": Budget(
        llm_calls=6, out_tokens=2500, wall_s=10 * 60, repair_rounds=0, web_searches=3, web_pages=6
    ),
    "study": Budget(
        llm_calls=10, out_tokens=8000, wall_s=30 * 60, repair_rounds=3, web_searches=3, web_pages=6,
        escalations=0,
    ),
}


@dataclass(frozen=True)
class Goal:
    text: str
    mode: Mode
    interactive: bool = False
    lang: Literal["hu", "en"] | None = None
    freshness_risk: float = 0.0  # 0..1 (08/02 §2)


@dataclass
class Recall:
    """What RECALL found (01/02 §2)."""

    hits: list[Hit] = field(default_factory=list)
    known_ratio: float = 0.0  # 0..1: verified coverage of the key concepts

    def verified_fresh(self) -> Hit | None:
        return next((h for h in self.hits if h.status == "verified"), None)


@dataclass(frozen=True)
class Assessment:
    """Router decision (08/02 §2). `reason` is always logged."""

    kind: str
    level: RouteLevel
    model: str
    difficulty: float
    predicted_success: float
    budget: Budget
    reason: str


@dataclass(frozen=True)
class Failure:
    """Why a level failed (08/02 §3)."""

    kind: Literal["verify", "no_progress", "missing_knowledge", "timeout", "llm_unavailable"]
    signature: str | None = None


class Stats(Protocol):
    def success_rate(self, kind: str, *, like: Goal, default: float = 0.5) -> float: ...


class Router(Protocol):
    def assess(self, goal: Goal, recall: Recall, history: Stats | None = None) -> Assessment: ...
    # None = nothing stronger. Optional kw (P6 StatsRouter): interactive, kind, lang, task_level; reason in last_reason.
    def escalate(self, level: int, failure: Failure, **kw: Any) -> int | None: ...


# ───────────────────────────── solving a CodeTask (06/05 §2) ─────────────────────────────


@dataclass(frozen=True)
class SolveOptions:
    """Knobs of `solve()`; `bench` sets them per mode (06/09 §6)."""

    repair_rounds: int = 3  # 0 = model-only (pass@1); 3 = +repair (javítással@3)
    use_memory: bool = True  # reuse a stored solution / error hints (the `+kb` ablation)
    learn: bool | None = None  # store results; None = only for LEARNABLE_SPLITS
    model: str | None = None  # None = the router's choice
    temperature: float = 0.0
    seed: int | None = 42
    prompt_lang: Literal["en", "hu"] = "en"  # NK18 A/B; English until measured
    prompt_variant: str | None = None  # e.g. "v2" → prompts/code.<lang>.v2.txt (A/B only; None = v1)
    priority: Priority = Priority.TASK


OutcomeKind = Literal["pass", "partial", "give_up"]  # 06/05 §9


@dataclass
class Outcome:
    """Result of solve(). `kind == 'pass'` ⇒ `last_run.status == 'pass'` — always (hallucination guard).

    `files` are the final solution files; bench runs the hidden tests on them (06/09 §3)."""

    task_id: str
    kind: OutcomeKind
    end_state: EndState
    files: dict[str, str]
    last_run: RunResult | None
    run_id: str  # journal: <runs dir>/<run_id>/journal.jsonl
    model: str = ""
    prompt_ver: str = ""  # hash of the prompt templates used (06/09 §5)
    from_memory: bool = False  # solved from the store, without a model call
    snippet_id: str | None = None  # the reused snippet, or the one stored after success
    rounds: int = 0  # repair rounds used
    no_progress: bool = False  # the same failure signature twice in a row (06/05 §6)
    llm_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    wall_ms: int = 0
    gen_ms: int = 0
    sandbox_ms: int = 0
    reason_hu: str | None = None  # honest reason when not passing (Hungarian, no secrets)


# ───────────────────────────── ask(): the event stream behind POST /ask (01/03 §4) ─────────────────────────────

HumanLang = Literal["hu", "en", "de", "unknown"]  # NK11; not `Lang` (that one is a programming language)
AskEventType = Literal["route", "step", "delta", "verify", "done", "error"]


@dataclass(frozen=True)
class AskRequest:
    """Mirror of the server's pydantic AskRequest (AI-3 converts). `task` set → the P0 loop with tests."""

    text: str
    mode: Mode = "chat"
    lang: Literal["hu", "en"] | None = None  # None = detect_lang(text)
    context: tuple[str, ...] = ()  # caller-filtered context (e.g. from T1); untrusted data, not instructions
    allow_web: bool = False
    allow_cloud: bool = False
    task: CodeTask | None = None
    plan: bool = False  # mode=code: a multi-step goal → planner (P5)
    priority: Priority = Priority.CHAT


@dataclass(frozen=True)
class AskEvent:
    """One SSE event. data per type:
    route {level, model, mode, lang} · step {state, ms} · delta {text} · verify {ok, tests, signature?}
    · done {outcome, episode_id, sources[], verified, reason?} · error {kind, message} (Hungarian, no secrets)."""

    type: AskEventType
    data: dict[str, Any]


# ───────────────────────────── recall(): POST /recall (01/03 §4) ─────────────────────────────


@dataclass(frozen=True)
class RecallRequest:
    """Top-k VERIFIED knowledge with provenance, for the caller's own prompt (Jarvis, AuriGPT).
    Hypotheses are never returned (only counted). Scope (guest/user) comes from the server's auth."""

    query: str
    kinds: tuple[str, ...] = ("knowledge", "snippet")
    k: int = 5  # clamped to 1..20
    max_chars: int = 2000  # budget of the whole prompt_block
    lang: Literal["hu", "en"] | None = None  # labels of prompt_block; None = detect_lang(query)


@dataclass(frozen=True)
class RecallItem:
    item_type: str  # knowledge | snippet
    item_id: str
    title: str
    text: str  # body / code, cut to a few hundred characters
    trust: float
    score: float
    sources: tuple[Provenance, ...] = ()


@dataclass(frozen=True)
class RecallResult:
    items: tuple[RecallItem, ...]
    prompt_block: str  # "" if nothing verified; numbered [1]..[n], marked as data (not instructions)
    withheld: int = 0  # matching hypotheses / contested items that were NOT returned
