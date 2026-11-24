"""auri_core.solve — the P0 thinking cycle for one CodeTask (owner: AI-1).

Spec: 06/05 §2 (the loop), 01/02 (states, stop rules, budgets), 06/06 (errors), 08/04 C3 (reuse).
    RECALL   stored solution for the same task_signature → rerun the tests → green = done, 0 LLM calls
    ACT      model writes the solution file (JSON, schema-checked; tests are frozen, never editable)
    VERIFY   sandbox runs the VISIBLE tests (hidden tests are never read here — bench runs them)
    REPAIR   ≤ N rounds with a short digest; same failure twice → one fresh regeneration, then give up
    STORE    green → VerifiedSnippet (T2) + the fix that worked → ErrorPattern (learnable splits only)
Hard rule: no "pass" without a green RunResult. Every model call runs inside scheduler.lease().
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import secrets
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import (
    ABORTED,
    BUDGETS,
    LEARNABLE_SPLITS,
    REPEAT_ABORT,
    SOLUTION_FILENAME,
    Cancelled,
    CodeMemory,
    CodeTask,
    EndState,
    ErrorFix,
    ErrorPattern,
    Failure,
    LLMClient,
    Outcome,
    OutcomeKind,
    PatternSource,
    Priority,
    PrivacyRejected,
    Provenance,
    RunResult,
    Sandbox,
    Scheduler,
    SnippetEnv,
    SnippetSource,
    SnippetTest,
    SnippetUsage,
    SnippetVerification,
    SolveOptions,
    VerifiedSnippet,
    chat_or_abort,
    tests_hash,
)
from .digest import digest, error_signature, round_signature
from .router import SimpleRouter, load_router

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# 06/05 §7: (max code tokens per generation, repair rounds, wall-clock s) per programming level.
LEVEL_LIMITS: dict[int, tuple[int, int, float]] = {
    0: (200, 2, 3 * 60), 1: (400, 3, 8 * 60), 2: (900, 3, 20 * 60), 3: (900, 3, 60 * 60), 4: (900, 3, 60 * 60),
}
JSON_OVERHEAD_TOKENS = 200  # the JSON wrapper around the file
# JSON-escaped code (\n, \") is longer than plain code. Measured 2026-11-21, gemma4:e2b, py-l1-0001:
# 11 calls, finished replies 221–572 tokens, the 600 cap cut 7 of them → ceiling = 2 × code + overhead.
CODE_TOKEN_FACTOR = 2
# Bumped when the loop's behaviour changes, so bench reports can tell runs apart (part of prompt_ver).
# loop2: garbage replies leave the conversation; "regenerate" starts from a clean context.
LOOP_VERSION = "loop2"
REGEN_TEMPERATURE = 0.7  # 06/05 §6 strategy (1): fresh attempt, higher temperature
LANGUAGE_NAME = {"py": "Python 3.12", "ts": "TypeScript (Node 24, ESM, strict)",
                 "js": "JavaScript (Node 24, ESM)", "sql": "SQLite SQL"}
TEST_FRAMEWORK = {"py": "pytest", "ts": "node:test", "js": "node:test", "sql": "sqlite"}

FILES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["files"],
    "properties": {
        "approach": {"type": "string", "maxLength": 300},
        "files": {
            "type": "array", "minItems": 1, "maxItems": 2,
            "items": {"type": "object", "required": ["path", "content"],
                      "properties": {"path": {"type": "string"}, "content": {"type": "string"}}},
        },
    },
}
_ELIDED = re.compile(r"(#|//)\s*(\.\.\.|rest (of|unchanged)|existing code|unchanged)", re.IGNORECASE)


# ───────────────────────────── helpers ─────────────────────────────


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _b36(n: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while n:
        n, r = divmod(n, 36)
        out = digits[r] + out
    return out or "0"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def task_signature(task: CodeTask) -> str:
    """C3 cache key (08/04 §2): language + normalized signature + normalized description."""
    raw = f"{task.lang}\n{_norm(task.signature)}\n{_norm(task.prompt_hu)}"
    return "tsig:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def load_visible_tests(task: CodeTask) -> dict[str, str]:
    """Only the VISIBLE test file. The hidden one is never opened here (06/09 §8)."""
    if task.root is None:
        raise ValueError(f"{task.id}: no task directory (task.root) — load it with taskset.load()")
    rel = task.files.visible
    return {rel: (Path(task.root) / rel).read_text(encoding="utf-8")}


@dataclass(frozen=True)
class Prompts:
    sections: dict[str, str]
    version: str

    def render(self, name: str, **values: str) -> str:
        text = self.sections[name]
        for k, v in values.items():
            text = text.replace("{{" + k + "}}", v)
        if "{{" in text:
            raise ValueError(f"unfilled placeholder in prompt '{name}'")
        return text


def load_prompts(lang: str = "en", directory: Path = PROMPTS_DIR, *, kind: str = "code",
                 variant: str | None = None) -> Prompts:
    """`<kind>.<lang>[.<variant>].txt`; a variant (e.g. "v2") is only loaded on request, for an A/B run."""
    if variant is not None and not re.fullmatch(r"[a-z0-9]{1,12}", variant):
        raise ValueError(f"invalid prompt variant: {variant!r}")
    fname = f"{kind}.{lang}" + (f".{variant}" if variant else "")
    raw = (directory / f"{fname}.txt").read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    name = None
    for line in raw.splitlines(keepends=True):
        if line.startswith("### "):
            name = line[4:].strip()
            sections[name] = ""
        elif name is not None:
            sections[name] += line
    sections = {k: v.strip("\n") for k, v in sections.items()}
    return Prompts(sections, f"{fname}:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12])


class Journal:
    """JSONL episode log: <runs_dir>/<run_id>/journal.jsonl. Hashes and sizes, never whole prompts."""

    def __init__(self, path: Path | None, listener: Callable[[str, dict[str, Any]], None] | None = None) -> None:
        self.path = path
        self.listener = listener  # ask() turns journal events into its event stream
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: str, **data: Any) -> None:
        if self.listener is not None:
            self.listener(event, data)
        if self.path is None:
            return
        line = json.dumps({"t": _now(), "event": event, **data}, ensure_ascii=False, default=str)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def pick_solution(data: Any, solution_file: str) -> tuple[str | None, list[str]]:
    """Take only the solution file from the model's JSON. Returns (code | None, dropped paths)."""
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        return None, []
    files = [f for f in data["files"] if isinstance(f, dict) and isinstance(f.get("content"), str)]
    dropped: list[str] = []
    keep: list[dict[str, Any]] = []
    for f in files:
        name = str(f.get("path", "")).replace("\\", "/").rsplit("/", 1)[-1]
        if "test" in name.lower() or "conftest" in name.lower():
            dropped.append(name)  # 06/05 §8: the model may not touch tests
        else:
            keep.append({"name": name, "content": f["content"]})
    exact = [f for f in keep if f["name"] == solution_file]
    chosen = exact[0] if exact else (keep[0] if len(keep) == 1 else None)
    if chosen is None or not chosen["content"].strip() or _ELIDED.search(chosen["content"]):
        return None, dropped
    return chosen["content"], dropped


def _parse_json(text: str) -> Any | None:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except (json.JSONDecodeError, ValueError):
        return None


# ───────────────────────────── the loop ─────────────────────────────


@dataclass
class _Ctx:
    task: CodeTask
    opts: SolveOptions
    llm: LLMClient
    sandbox: Sandbox
    store: CodeMemory | None
    scheduler: Scheduler
    journal: Journal
    run_id: str
    model: str
    prompts: Prompts
    solution_file: str
    tests: dict[str, str]
    frozen: str
    t0: float = field(default_factory=time.monotonic)
    llm_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    gen_ms: int = 0
    sandbox_ms: int = 0
    sandbox_runs: int = 0
    messages: list[dict[str, str]] = field(default_factory=list)

    def elapsed(self) -> float:
        return time.monotonic() - self.t0


async def _ask(ctx: _Ctx, user_msg: str, *, num_predict: int, temperature: float) -> str | None:
    """One generation (+ at most one JSON-fix request, 02/04 §0). Appends to the session so the
    KV cache is reused (06/05 §7). Returns the solution code or None."""
    ctx.messages.append({"role": "user", "content": user_msg})
    for attempt in range(2):
        if ctx.llm_calls >= BUDGETS["code"].llm_calls:
            ctx.journal.write("budget", what="llm_calls")
            return None
        options = {"seed": ctx.opts.seed} if ctx.opts.seed is not None else None
        async with ctx.scheduler.lease(ctx.opts.priority, ctx.model) as lease:
            if lease.preempt.is_set():
                raise Cancelled("preempted before the call")
            reply = await chat_or_abort(ctx.llm, lease, ctx.messages, format=FILES_SCHEMA, num_predict=num_predict,
                                       temperature=temperature, options=options)
        s = reply.stats
        ctx.llm_calls += 1
        ctx.tokens_in += s.prompt_tokens
        ctx.tokens_out += s.eval_tokens
        ctx.gen_ms += s.total_ms
        ctx.messages.append({"role": "assistant", "content": reply.text})
        data = _parse_json(reply.text)
        code, dropped = pick_solution(data, ctx.solution_file)
        ctx.journal.write("llm", attempt=attempt, out_tokens=s.eval_tokens, ms=s.total_ms,
                          done_reason=s.done_reason, json_ok=data is not None, code_ok=code is not None,
                          dropped_tests=dropped or None)
        if code is not None:
            return code
        if data is not None:  # valid JSON, unusable content → no point asking for JSON again
            _drop_garbage(ctx)
            return None
        if s.done_reason == REPEAT_ABORT:  # the model looped; Ollama aborted it — a model failure, not infra
            ctx.journal.write("model_error", kind=REPEAT_ABORT)
        if s.done_reason in ABORTED:  # cut off at num_predict: a JSON-fix request would be cut too
            if s.done_reason == "length":
                ctx.journal.write("truncated", num_predict=num_predict)
            _drop_garbage(ctx)
            return None
        if attempt == 0:
            ctx.messages.append({"role": "user", "content": ctx.prompts.render("json_fix")})
    _drop_garbage(ctx)
    return None


GARBAGE = "(unusable reply removed)"


def _drop_garbage(ctx: _Ctx) -> None:
    """A cut-off or invalid reply (often a repetition loop) must not stay in the context: the model
    tends to continue the loop next round (journal run_tove08a9a1: 3 x 1000 tokens, all cut off)."""
    if ctx.messages and ctx.messages[-1]["role"] == "assistant":
        ctx.messages[-1] = {"role": "assistant", "content": GARBAGE}


async def _verify(ctx: _Ctx, code: str) -> RunResult:
    lim = ctx.task.limits
    run = await ctx.sandbox.run_tests({ctx.solution_file: code}, ctx.tests, ctx.task.lang, lim.wall_s,
                                      mem_mb=lim.mem_mb)
    ctx.sandbox_runs += 1
    ctx.sandbox_ms += run.duration_ms
    ctx.journal.write("verify", status=run.status, phase=run.phase, passed=run.passed, failed=run.failed,
                      ms=run.duration_ms, signature=None if run.ok else round_signature(run))
    if run.tests_hash and run.tests_hash != ctx.frozen:
        raise _TestsChanged(run.tests_hash)
    return run


class _TestsChanged(Exception):
    pass


def _outcome(ctx: _Ctx, kind: OutcomeKind, end: EndState, code: str | None, run: RunResult | None,
             **kw: Any) -> Outcome:
    if kind == "pass" and not (run is not None and run.ok):  # hallucination guard (06/09: false "done" = 0)
        ctx.journal.write("false_done_blocked")
        kind, end = "give_up", EndState.GIVE_UP
        kw.setdefault("reason_hu", "nincs zöld tesztfutás, ezért nem mondhatom, hogy kész")
    out = Outcome(task_id=ctx.task.id, kind=kind, end_state=end,
                  files={ctx.solution_file: code} if code is not None else {}, last_run=run, run_id=ctx.run_id,
                  model=ctx.model, prompt_ver=f"{ctx.prompts.version}+{LOOP_VERSION}", llm_calls=ctx.llm_calls,
                  tokens_in=ctx.tokens_in, tokens_out=ctx.tokens_out, wall_ms=int(ctx.elapsed() * 1000),
                  gen_ms=ctx.gen_ms, sandbox_ms=ctx.sandbox_ms, **kw)
    ctx.journal.write("done", kind=out.kind, end_state=str(out.end_state), rounds=out.rounds,
                      from_memory=out.from_memory, no_progress=out.no_progress, llm_calls=out.llm_calls,
                      wall_ms=out.wall_ms, reason=out.reason_hu)
    return out


async def _learn(ctx: _Ctx, code: str, run: RunResult, fixed_error: str | None) -> str | None:
    """STORE (01/02 §2): green solution → T2 snippet; the error it fixed → ErrorPattern."""
    if ctx.store is None:
        return None
    task, now = ctx.task, _now()
    snip_id = f"snip_{task.lang}_{re.sub(r'[^a-z0-9]+', '_', task.id.lower())}_{secrets.token_hex(3)}"
    snippet = VerifiedSnippet(
        id=snip_id, lang=task.lang, title=task.title_hu, summary_hu=task.prompt_hu.strip().split("\n")[0][:300],
        code=code, tests=[SnippetTest(TEST_FRAMEWORK[task.lang], c) for c in ctx.tests.values()],  # type: ignore[arg-type]
        env=SnippetEnv(node=run.env.node, python=run.env.python, typescript=run.env.typescript),
        topics=list(task.topics), symbols=[], source=SnippetSource("own-loop", "own"), trust=2,
        verification=SnippetVerification("pass", run.run_id, now, run.sandbox if run.sandbox in ("S0", "S1") else None),  # type: ignore[arg-type]
        usage=SnippetUsage(), created_at=now, updated_at=now,
    )
    prov = [Provenance("verified_by", "episode", ctx.run_id), Provenance("generated_by", "model", ctx.model)]
    try:
        saved = await ctx.store.save_solution(snippet, task_signature=task_signature(task), prov=prov)
        ctx.journal.write("store", snippet=saved)
        if fixed_error:
            await ctx.store.save_error(ErrorPattern(
                id=f"err_{hashlib.sha256(fixed_error.encode()).hexdigest()[:12]}", lang=task.lang,
                signature=fixed_error, example=fixed_error, causes=[],
                fixes=[ErrorFix(f"Bevált javítás ({task.id}), ld. a kódrészletet.", snippet_id=saved, worked=1)],
                source=PatternSource("own-loop", "own"), trust=2))
            ctx.journal.write("store", error_pattern=fixed_error)
        return saved
    except PrivacyRejected:
        ctx.journal.write("store_rejected", reason="privacy gate")
        return None


async def _solve_once(
    task: CodeTask,
    *,
    llm: LLMClient,
    sandbox: Sandbox,
    store: CodeMemory | None,
    scheduler: Scheduler,
    opts: SolveOptions | None = None,
    visible: dict[str, str] | None = None,
    runs_dir: Path | None = None,
    router: SimpleRouter | None = None,
    on_event: Callable[[str, dict[str, Any]], None] | None = None,
) -> Outcome:
    """Solve one CodeTask (06/05 §2). Never raises for model/sandbox failures: returns an Outcome."""
    opts = opts or SolveOptions()
    # No date-like digit runs: the privacy gate (rightly) treats "20261121" as a possible birth date.
    run_id = f"run_{_b36(int(time.time()))}{secrets.token_hex(2)}_{task.id}"
    journal = Journal(runs_dir / run_id / "journal.jsonl" if runs_dir else None, on_event)
    model, why = (opts.model, "SolveOptions.model") if opts.model else (router or load_router()).code_model(task)
    tests = visible if visible is not None else load_visible_tests(task)
    ctx = _Ctx(task, opts, llm, sandbox, store, scheduler, journal, run_id, model,
               load_prompts(opts.prompt_lang, variant=opts.prompt_variant),
               SOLUTION_FILENAME[task.lang], tests, tests_hash(tests))
    code_tokens, level_rounds, wall_s = LEVEL_LIMITS.get(task.level, LEVEL_LIMITS[2])
    max_rounds = max(0, min(opts.repair_rounds, level_rounds))
    learn = opts.learn if opts.learn is not None else task.split in LEARNABLE_SPLITS
    journal.write("start", task=task.id, level=task.level, lang=task.lang, split=task.split, model=model,
                  route=why, prompt_ver=f"{ctx.prompts.version}+{LOOP_VERSION}", max_rounds=max_rounds, learn=learn,
                  tests_hash=ctx.frozen)
    code: str | None = None
    run: RunResult | None = None
    rounds = 0
    try:
        # 1. RECALL — C3: same task signature → rerun its tests, no model call (08/04 §2).
        if opts.use_memory and store is not None:
            snip = await store.find_solution(task_signature(task), task.lang)
            if snip is not None:
                run = await _verify(ctx, snip.code)
                await store.record_use(snip.id, task.id, run.ok)
                journal.write("recall", snippet=snip.id, ok=run.ok)
                if run.ok:
                    return _outcome(ctx, "pass", EndState.DONE, snip.code, run, from_memory=True, snippet_id=snip.id)
                run = None

        # 2. ACT
        p = ctx.prompts
        tests_txt = "\n\n".join(f"# {path}\n{body}" for path, body in tests.items())
        first = p.render("generate", language=LANGUAGE_NAME[task.lang], solution_file=ctx.solution_file,
                         title=task.title_hu, prompt=task.prompt_hu.strip(), signature=task.signature,
                         knowledge="(none)", tests=tests_txt)
        system = {"role": "system", "content": p.render("system")}
        ctx.messages = [system]
        num_predict = code_tokens * CODE_TOKEN_FACTOR + JSON_OVERHEAD_TOKENS
        code = await _ask(ctx, first, num_predict=num_predict, temperature=opts.temperature)

        seen: list[str] = []
        regenerated = False
        no_progress = False
        while True:
            # 3. VERIFY
            if code is not None:
                run = await _verify(ctx, code)
                if run.ok:
                    break
                sig = round_signature(run)
            else:
                sig = "INVALID_OUTPUT"
            stuck = bool(seen) and seen[-1] == sig
            seen.append(sig)
            over = ctx.elapsed() > wall_s or ctx.sandbox_runs >= BUDGETS["code"].sandbox_runs + 1
            if rounds >= max_rounds or over or (stuck and regenerated):
                no_progress = no_progress or stuck
                why_hu = ("nincs előrelépés: ugyanaz a hiba ismétlődik" if stuck else
                          "elfogyott a keret" if over and rounds < max_rounds else
                          f"{rounds} javítási kör után sem zöld")
                return _outcome(ctx, "give_up", EndState.GIVE_UP, code, run, rounds=rounds,
                                no_progress=no_progress, reason_hu=f"{why_hu} ({sig[:160]})")
            # 4. REPAIR
            hint = None
            if run is not None and opts.use_memory and store is not None and (es := error_signature(run)):
                pat = await store.find_error(es.signature, task.lang)
                if pat and pat.fixes:
                    best = max(pat.fixes, key=lambda f: f.worked - f.failed)
                    hint = best.text_hu
            feedback = (digest(run, files={ctx.solution_file: code} if code else None,
                               previous_signature=seen[-2] if len(seen) > 1 else None, hint=hint,
                               lang=opts.prompt_lang)
                        if run is not None and code is not None else "The previous reply had no usable solution file.")
            rounds += 1
            if stuck:  # 06/05 §6 strategy (1): one fresh attempt with a higher temperature
                regenerated = no_progress = True
                ctx.messages = ctx.messages[:1]  # clean context: the task again + what failed (same prefix → KV cache)
                msg = first + "\n\n" + p.render("regenerate", solution_file=ctx.solution_file, feedback=feedback)
                temp = REGEN_TEMPERATURE
            else:
                msg = p.render("repair", solution_file=ctx.solution_file, feedback=feedback)
                temp = opts.temperature
            journal.write("repair", round=rounds, strategy="regenerate" if stuck else "repair", hint=bool(hint))
            code, run = await _ask(ctx, msg, num_predict=num_predict, temperature=temp), None

        # 5. STORE (only green, only learnable splits)
        fixed = None
        if len(seen) > 0 and seen[-1] != "INVALID_OUTPUT":
            fixed = seen[-1].split(" :: ", 1)[-1]
        snippet_id = await _learn(ctx, code, run, fixed) if learn else None  # type: ignore[arg-type]
        return _outcome(ctx, "pass", EndState.DONE, code, run, rounds=rounds, no_progress=no_progress,
                        snippet_id=snippet_id)
    except Cancelled:
        return _outcome(ctx, "give_up", EndState.PAUSED, code, run, rounds=rounds,
                        reason_hu="megszakítva: a felhasználó aktív lett")
    except _TestsChanged:
        return _outcome(ctx, "give_up", EndState.GIVE_UP, code, None, rounds=rounds,
                        reason_hu="infrastruktúra: a tesztek lenyomata eltér, nem futtatom")
    except Exception as e:  # sandbox / Ollama / store failure — not the code's fault (01/02 §2)
        msg = getattr(e, "user_message", None) or type(e).__name__
        journal.write("infra_error", kind=type(e).__name__)
        return _outcome(ctx, "give_up", EndState.GIVE_UP, code, run, rounds=rounds,
                        reason_hu=f"infrastruktúra: {msg}")


async def solve(
    task: CodeTask,
    *,
    llm: LLMClient,
    sandbox: Sandbox,
    store: CodeMemory | None,
    scheduler: Scheduler,
    opts: SolveOptions | None = None,
    visible: dict[str, str] | None = None,
    runs_dir: Path | None = None,
    router: Any = None,
    on_event: Callable[[str, dict[str, Any]], None] | None = None,
    cloud: Any = None,
) -> Outcome:
    """Solve one CodeTask (06/05 §2) + at most one escalation to a stronger measured model (08/02 §3),
    or, when the router says L4 and `cloud` (an `l4.CloudGate`) allows it, one cloud attempt verified in
    the local sandbox (08/03). No escalation when the caller fixed the model (bench) or the run was paused."""
    opts = opts or SolveOptions()
    router = router if router is not None else (None if opts.model else load_router())
    kw = {"llm": llm, "sandbox": sandbox, "store": store, "scheduler": scheduler, "visible": visible,
          "runs_dir": runs_dir, "router": router, "on_event": on_event}
    out = await _solve_once(task, opts=opts, **kw)
    if (out.kind == "pass" or opts.model or out.end_state != EndState.GIVE_UP or BUDGETS["code"].escalations < 1
            or (out.reason_hu or "").startswith("infrastruktúra") or not hasattr(router, "pick")):
        return out
    failure = Failure("no_progress" if out.no_progress else
                      "budget" if "keret" in (out.reason_hu or "") else "tests_failed",
                      round_signature(out.last_run) if out.last_run is not None else None)
    nxt = router.escalate(2, failure, interactive=opts.priority >= Priority.CHAT, kind="code", lang=task.lang,
                          task_level=task.level)
    why = getattr(router, "last_reason", "")
    if on_event is not None:
        on_event("escalate", {"to": nxt, "reason": why})
    if nxt == 4:
        return await _cloud_attempt(task, out, cloud, opts=opts, kw=kw)
    if nxt != 3:
        return out
    model3 = router.pick("code", task.lang, task.level, tier=3)[0]
    if not model3 or model3 == out.model:
        return out
    second = await _solve_once(task, opts=replace(opts, model=model3), **kw)
    if second.kind != "pass" and second.reason_hu:
        second.reason_hu = f"{second.reason_hu} (L3-on is: {model3})"
    return second


async def _cloud_attempt(task: CodeTask, out: Outcome, gate: Any, *, opts: SolveOptions,
                         kw: dict[str, Any]) -> Outcome:
    """L4 (08/03): one cloud generation (+ JSON fix), verified by the same visible tests in the sandbox.
    Never learned, never from memory; refusal or no consent → the local outcome with the reason."""
    from .l4 import CLOUD_LABEL, CloudLLM, NoLane, shown_by

    on_event = kw.get("on_event")
    if gate is None or not gate.configured:
        return out
    if not gate.usable:
        if on_event is not None:
            on_event("cloud_offer", {"live": gate.live})
        return out
    llm = CloudLLM(gate, purpose="code")
    second = await _solve_once(task, opts=replace(opts, model=CLOUD_LABEL, repair_rounds=0, learn=False,
                                                  use_memory=False),
                               **{**kw, "llm": llm, "scheduler": NoLane(), "store": None})
    if llm.answer is None:  # refused (personal data, secret, quota, …) or no reply at all
        reason = getattr(llm.refusal, "reason", None) or second.reason_hu or "a felhő nem válaszolt"
        if on_event is not None:
            on_event("cloud", {"ok": False, "reason": reason})
        out.reason_hu = " · ".join(x for x in (out.reason_hu, f"felhő (L4): {reason}") if x)
        return out
    second.model = llm.provenance or CLOUD_LABEL
    if on_event is not None:
        on_event("cloud", {"ok": second.kind == "pass", "provenance": second.model})
    if second.kind != "pass" and second.reason_hu:
        second.reason_hu = f"{second.reason_hu} (a felhőben is: {shown_by(second.model)})"
    return second


# ───────────────────────────── CLI: python -m auri_core run <task dir> ─────────────────────────────


def _summary(o: Outcome) -> str:
    if o.kind == "pass":
        src = "a tárból, 0 LLM-hívással" if o.from_memory else f"{o.rounds} javítási kör, {o.llm_calls} LLM-hívás"
        return f"ZÖLD: {o.task_id} ({src}, {o.wall_ms / 1000:.1f} s)."
    return f"NEM SIKERÜLT: {o.task_id} — {o.reason_hu} ({o.llm_calls} LLM-hívás, {o.wall_ms / 1000:.1f} s)."


async def _main_async(a: argparse.Namespace) -> int:
    from . import config, llm, sandbox, scheduler, store, taskset  # AI-2 / AI-3 modules

    task = taskset.load(a.task)
    client = llm.OllamaClient()
    try:
        out = await solve(
            task, llm=client, sandbox=sandbox.create_sandbox(), store=None if a.no_memory else store.open_store(),
            scheduler=scheduler.get_scheduler(), runs_dir=config.load_config().runs_dir,
            opts=SolveOptions(repair_rounds=a.rounds, use_memory=not a.no_memory,
                              learn=False if a.no_learn else None, model=a.model, prompt_lang=a.prompt_lang),
        )
    finally:
        await client.aclose()
    if a.json:
        print(json.dumps({k: v for k, v in out.__dict__.items() if k not in ("last_run", "files")},
                         ensure_ascii=False, default=str))
    else:
        print(_summary(out))
        if out.kind != "pass" and out.last_run is not None:
            print(digest(out.last_run, files=out.files or None, lang="hu"))
        print(f"Napló: {out.run_id}")
    return 0 if out.kind == "pass" else 1


def main_run(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m auri_core run", description="Egy feladat megoldása (P0 ciklus).")
    ap.add_argument("task", help="a feladat mappája, pl. tasks/py-l1-0001")
    ap.add_argument("--model", default=None, help="modell (alap: a config szerinti kódoló modell)")
    ap.add_argument("--rounds", type=int, default=3, help="javítási körök (0 = csak a modell)")
    ap.add_argument("--no-memory", action="store_true", help="tár nélkül (nincs emlékezés, nincs tanulás)")
    ap.add_argument("--no-learn", action="store_true", help="ne tárolja az eredményt")
    ap.add_argument("--prompt-lang", choices=["en", "hu"], default="en", help="belső promptnyelv (NK18)")
    ap.add_argument("--json", action="store_true", help="gépi kimenet")
    a = ap.parse_args(argv)
    try:
        return asyncio.run(_main_async(a))
    except ImportError as e:
        print(f"Még hiányzik egy modul a futtatáshoz: {e.name or e}", file=sys.stderr)
        return 3
