"""The debate protocol (02/02): proposal → deterministic check FIRST → critique only where the machine
cannot decide → revision → a RULE (not a model) decides. "accept" for code needs a green run."""

from __future__ import annotations

import difflib
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ..contracts import (
    SOLUTION_FILENAME,
    Cancelled,
    CodeTask,
    EndState,
    LLMClient,
    Priority,
    RunResult,
    Sandbox,
    Scheduler,
    tests_hash,
)
from ..digest import digest, error_signature, round_signature
from ..solve import LANGUAGE_NAME, load_visible_tests
from .self_ask import Answerer, answer_subquestions
from .session import BudgetExceeded, RoleCallFailed, RolesConfig, RoleSession
from .turns import (
    Critique,
    Issue,
    LessonCard,
    Proposal,
    Understanding,
    UserQuestion,
    critique,
    lesson,
    propose,
    propose_text,
    revise,
    understand,
)

Verdict = Literal["continue", "accept", "give_up", "ask_help"]
SIMILAR = 0.95  # 02/02 §3: a revision this similar to the previous one, with the same failure, changed nothing


@dataclass
class DebateState:
    kind: Literal["code", "text"]
    mode: str
    round: int = 0
    max_rounds: int = 3
    check_passed: bool | None = None
    blocking: list[Issue] = field(default_factory=list)
    critique_verdict: str | None = None
    budget_exhausted: bool = False
    hashes: list[str] = field(default_factory=list)  # proposal content hashes, oldest first
    signatures: list[str] = field(default_factory=list)  # failure signature of each check
    last_similarity: float = 0.0


def is_oscillating(hashes: list[str]) -> bool:
    """A → B → A: the n-th proposal equals the (n−2)-th (02/02 §3)."""
    return len(hashes) >= 3 and hashes[-1] == hashes[-3] and hashes[-1] != hashes[-2]


def decide(s: DebateState) -> Verdict:
    """02/02 §3, as code. The model never decides that the work is done."""
    if s.check_passed and not s.blocking:
        return "accept"  # reality says it is good
    if s.kind == "text" and s.critique_verdict == "accept" and not s.blocking:
        return "accept"  # nothing to run: an evidence-based critique found no issue
    if s.round >= s.max_rounds:
        return "ask_help" if s.mode == "interactive" else "give_up"
    if s.budget_exhausted:
        return "ask_help"
    if is_oscillating(s.hashes):
        return "give_up"
    same_failure = len(s.signatures) >= 2 and s.signatures[-1] == s.signatures[-2]
    if len(s.hashes) >= 2 and same_failure and (s.hashes[-1] == s.hashes[-2] or s.last_similarity > SIMILAR):
        return "give_up"  # did not change in substance
    return "continue"


@dataclass
class DebateOutcome:
    kind: Literal["code", "text"]
    verdict: Literal["accept", "give_up", "ask_help", "paused"]
    end_state: EndState
    verified: bool  # code: a green run of the (frozen) tests; text: always False (no external check)
    files: dict[str, str] = field(default_factory=dict)
    last_run: RunResult | None = None
    rounds: int = 0
    approach: str = ""
    steps: list[str] = field(default_factory=list)
    understanding: Understanding | None = None
    user_question: UserQuestion | None = None
    critiques: list[Critique] = field(default_factory=list)
    rejected: list[dict[str, str]] = field(default_factory=list)
    reverted_to_green: bool = False
    reason_hu: str | None = None
    sid: str = ""
    prompt_ver: str = ""
    llm_calls: int = 0
    out_tokens: int = 0
    timings: list[dict[str, Any]] = field(default_factory=list)


def _h(text: str | None) -> str:
    return hashlib.sha256((text or "").encode()).hexdigest()[:16]


def _want_kerdezo(cfg: RolesConfig, task_text: str, signature: str) -> bool:
    if cfg.use_kerdezo != "auto":
        return cfg.use_kerdezo == "always"
    # 02/03 §1: skipped interactively when the task is short and well-defined
    return cfg.mode != "interactive" or not signature.strip() or len(task_text) > 600


def _failure_is_clear(run: RunResult | None) -> bool:
    """A clear failure (an assertion with expected/got, a located error) needs no model critique."""
    if run is None or run.ok:
        return False
    bad = [t for t in run.tests if not t.ok]
    if run.status == "fail" and bad and all((t.message or t.expected is not None) for t in bad):
        return True
    sig = error_signature(run)
    return bool(sig and sig.signature and not sig.signature.startswith(("exit code", "sandbox")))


def _want_kritikus(cfg: RolesConfig, run: RunResult | None) -> bool:
    if cfg.use_kritikus != "auto":
        return cfg.use_kritikus == "always" and run is not None
    if run is None:
        return False  # no usable file: there is nothing to criticise, just ask again
    return cfg.mode != "interactive" or not _failure_is_clear(run)


def _issue_lines(issues: list[Issue]) -> str:
    return "\n".join(f"{i.id} [{i.severity}] {i.where}: {i.problem} — evidence: {i.evidence}"
                     + (f" — hint: {i.fix_hint}" if i.fix_hint else "") for i in issues)


def _pick(files: dict[str, str], sol: str) -> str | None:
    if sol in files:
        return files[sol]
    return next(iter(files.values())) if len(files) == 1 else None


async def debate_code(
    task: CodeTask,
    *,
    llm: LLMClient,
    sandbox: Sandbox,
    scheduler: Scheduler,
    cfg: RolesConfig | None = None,
    visible: dict[str, str] | None = None,
    knowledge: str = "",
    answerers: dict[str, Answerer] | None = None,
    model: str | None = None,
    priority: Priority = Priority.TASK,
    transcript_dir: Path | None = None,
    session: RoleSession | None = None,
) -> DebateOutcome:
    """The full P3 protocol for a CodeTask. Never raises for model/sandbox failures."""
    cfg = cfg or RolesConfig(enabled=True)
    s = session or RoleSession(llm, scheduler, cfg=cfg, model=model, priority=priority, transcript_dir=transcript_dir)
    sol = SOLUTION_FILENAME[task.lang]
    tests = visible if visible is not None else load_visible_tests(task)
    frozen = tests_hash(tests)
    state = DebateState("code", cfg.mode, max_rounds=cfg.rounds())
    out = DebateOutcome("code", "give_up", EndState.GIVE_UP, False, sid=s.sid, prompt_ver=s.prompt_ver)
    last_green: tuple[str, RunResult] | None = None
    files: dict[str, str] = {}
    run: RunResult | None = None

    def finish(verdict: str, end: EndState, reason: str | None = None) -> DebateOutcome:
        nonlocal files, run
        if verdict != "accept" and last_green is not None:  # 02/02 §8: back to the last green version
            files, run = {sol: last_green[0]}, last_green[1]
            verdict, end, out.reverted_to_green = "accept", EndState.DONE, True
            reason = (reason or "") + " — visszaállítva az utolsó zöld változatra"
        verified = run is not None and run.ok and verdict == "accept"
        if verdict == "accept" and not verified:  # hallucination guard
            verdict, end, reason = "give_up", EndState.GIVE_UP, "nincs zöld tesztfutás, ezért nem mondhatom, hogy kész"
        out.verdict, out.end_state, out.verified = verdict, end, verified  # type: ignore[assignment]
        out.files, out.last_run, out.rounds, out.reason_hu = files, run, state.round, reason
        out.llm_calls, out.out_tokens, out.timings = s.llm_calls, s.out_tokens, s.timings()
        s.transcript.write("DONTES", verdict=out.verdict, reason=reason, rounds=state.round, verified=verified)
        return out

    try:
        # 1. MEGÉRTÉS (Kérdező) — optional
        if _want_kerdezo(cfg, task.prompt_hu, task.signature):
            try:
                u = await understand(s, task.prompt_hu, knowledge)
                if answerers:
                    u = await answer_subquestions(u, answerers)
                out.understanding = u
                if u.ask_user is not None and cfg.mode == "interactive":
                    out.user_question = u.ask_user
                    return finish("ask_help", EndState.ASK_USER, "pontosító kérdés a felhasználónak")
                extra = [f"goal: {u.goal}"] + [f"{q.q} → {q.answer}" for q in u.subquestions if q.answer]
                knowledge = "\n".join(x for x in [knowledge, *extra] if x)
            except RoleCallFailed:
                pass
        # 3. JAVASLAT (Gondolkodó) — the tests come from the task (or from spec_tests.spec_to_task)
        try:
            prop: Proposal | None = await propose(s, task.prompt_hu, language=LANGUAGE_NAME[task.lang],
                                                  solution_file=sol, tests=tests, knowledge=knowledge)
        except RoleCallFailed:
            prop = None
        out.approach = prop.approach if prop else ""
        files = dict(prop.files) if prop else {}
        critic_on_green_done = False
        prev_code: str | None = None
        while True:
            # 4. ELLENŐRZÉS — always first
            code = _pick(files, sol)
            if code is not None:
                run = await sandbox.run_tests({sol: code}, tests, task.lang, task.limits.wall_s,
                                              mem_mb=task.limits.mem_mb)
                if run.tests_hash and run.tests_hash != frozen:
                    return finish("give_up", EndState.GIVE_UP, "infrastruktúra: a tesztek lenyomata eltér")
                sig = "pass" if run.ok else round_signature(run)
                s.transcript.write("SANDBOX", status=run.status, passed=run.passed, failed=run.failed,
                                   summary=sig[:200], ms_total=run.duration_ms)
            else:
                run, sig = None, "INVALID_OUTPUT"
            state.hashes.append(_h(code))
            state.signatures.append(sig)
            state.last_similarity = (difflib.SequenceMatcher(None, prev_code, code).ratio()
                                     if prev_code is not None and code is not None else 0.0)
            prev_code = code if code is not None else prev_code
            state.check_passed = bool(run and run.ok)
            state.blocking = []
            if run is not None and run.ok:
                last_green = (code, run)  # type: ignore[assignment]
            check_txt = (digest(run, files={sol: code} if code else None, lang=cfg.prompt_lang) or
                         f"{run.passed} tests passed") if run is not None else \
                "The previous reply had no usable solution file."
            # 5. KRITIKA — only where the machine cannot decide (or one look at a green result, idle/night)
            crit: Critique | None = None
            green_review = (run is not None and run.ok and cfg.critic_on_green and cfg.mode != "interactive"
                            and not critic_on_green_done and cfg.use_kritikus != "never")
            if green_review or (run is not None and not run.ok and _want_kritikus(cfg, run)):
                critic_on_green_done = critic_on_green_done or green_review
                try:
                    crit = await critique(s, check_txt)
                    out.critiques.append(crit)
                    state.blocking, state.critique_verdict = crit.blocking, crit.verdict
                except RoleCallFailed:
                    crit = None
            # 7. DÖNTÉS
            state.budget_exhausted = s.exhausted()
            v = decide(state)
            if v == "accept":
                return finish("accept", EndState.DONE)
            if v != "continue":
                why = {"give_up": "nincs előrelépés vagy elfogytak a körök", "ask_help": "elfogyott a keret / a kör"}[v]
                return finish(v, EndState.GIVE_UP if v == "give_up" else EndState.ASK_USER, f"{why} ({sig[:160]})")
            # 6. JAVÍTÁS
            state.round += 1
            ids = [i.id for i in state.blocking] or [f"T:{t.name}" for t in (run.tests if run else []) if not t.ok][:6]
            fb = check_txt + ("\n" + _issue_lines(state.blocking) if state.blocking else "")
            try:
                rev = await revise(s, ids, fb)
                out.rejected.extend(rev.rejected)
                if rev.files:
                    files = {**files, **rev.files}
                elif run is not None and run.ok:
                    return finish("accept", EndState.DONE, "a Gondolkodó indokkal elutasította a kritikát")
            except RoleCallFailed:
                files = {}
    except Cancelled:
        return finish("paused", EndState.PAUSED, "megszakítva: a felhasználó aktív lett (folytatható)")
    except BudgetExceeded:
        return finish("ask_help", EndState.ASK_USER, "elfogyott a keret")
    except Exception as e:  # sandbox / Ollama failure — not the code's fault
        return finish("give_up", EndState.GIVE_UP, f"infrastruktúra: {getattr(e, 'user_message', None) or type(e).__name__}")


async def debate_text(
    question: str,
    *,
    llm: LLMClient,
    scheduler: Scheduler,
    cfg: RolesConfig | None = None,
    knowledge: str = "",
    check: str = "Nothing can be run. Review the draft against the task and the knowledge only.",
    model: str | None = None,
    priority: Priority = Priority.TASK,
    transcript_dir: Path | None = None,
    session: RoleSession | None = None,
) -> DebateOutcome:
    """Text (nothing to run): draft → evidence-based critique → redraft. Accepted only on a critique
    without actionable issues; never `verified` (a source match is research's job, 03/03)."""
    cfg = cfg or RolesConfig(enabled=True)
    s = session or RoleSession(llm, scheduler, cfg=cfg, model=model, priority=priority, transcript_dir=transcript_dir)
    state = DebateState("text", cfg.mode, max_rounds=cfg.rounds())
    out = DebateOutcome("text", "give_up", EndState.GIVE_UP, False, sid=s.sid, prompt_ver=s.prompt_ver)

    def finish(verdict: str, end: EndState, reason: str | None = None) -> DebateOutcome:
        out.verdict, out.end_state, out.rounds, out.reason_hu = verdict, end, state.round, reason  # type: ignore[assignment]
        out.llm_calls, out.out_tokens, out.timings = s.llm_calls, s.out_tokens, s.timings()
        s.transcript.write("DONTES", verdict=verdict, reason=reason, rounds=state.round, verified=False)
        return out

    try:
        notes = knowledge
        while True:
            try:
                p = await propose_text(s, question, notes)
            except RoleCallFailed:
                return finish("give_up", EndState.GIVE_UP, "a Gondolkodó nem adott érvényes vázlatot")
            out.approach, out.steps = p.approach, p.steps
            state.hashes.append(_h(p.approach + "\n".join(p.steps)))
            try:
                crit = await critique(s, check)
                out.critiques.append(crit)
                state.blocking, state.critique_verdict = crit.blocking, crit.verdict
            except RoleCallFailed:
                state.blocking, state.critique_verdict = [], None
            state.signatures.append(",".join(sorted(i.id for i in state.blocking)))
            state.budget_exhausted = s.exhausted()
            v = decide(state)
            if v == "accept":
                return finish("accept", EndState.DONE)
            if v != "continue":
                return finish(v, EndState.GIVE_UP if v == "give_up" else EndState.ASK_USER, "nincs elfogadható vázlat")
            state.round += 1
            notes = "\n".join(x for x in [knowledge, "Issues to address:", _issue_lines(state.blocking)] if x)
    except Cancelled:
        return finish("paused", EndState.PAUSED, "megszakítva: a felhasználó aktív lett (folytatható)")
    except BudgetExceeded:
        return finish("ask_help", EndState.ASK_USER, "elfogyott a keret")
    except Exception as e:
        return finish("give_up", EndState.GIVE_UP, f"infrastruktúra: {getattr(e, 'user_message', None) or type(e).__name__}")


async def teach_from(session: RoleSession, outcome: DebateOutcome) -> LessonCard | None:
    """8. TANULSÁG (deferred, idle time): the evidence label comes from the outcome, not the model."""
    if outcome.kind == "code" and outcome.verified and outcome.last_run is not None:
        ev, txt = "tests_passed", f"{outcome.last_run.passed} tests passed after {outcome.rounds} revision(s)"
    else:
        ev, txt = "unverified", outcome.reason_hu or "no green check"
    try:
        return await lesson(session, evidence=ev, evidence_text=txt)  # type: ignore[arg-type]
    except (RoleCallFailed, BudgetExceeded):
        return None
