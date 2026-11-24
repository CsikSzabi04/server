"""auri_core.roles — P3: the internal dialogue (02-belso-parbeszed), owner: AI-1. OFF by default.

Callers check `RolesConfig.enabled` and skip everything when it is False (the P0/P1 loop stays as is).

Public API
----------
Session (02/01 §3, 02/04 §0)
    RolesConfig(enabled=False, mode="interactive"|"idle"|"night", max_rounds=None, use_kerdezo="auto",
                use_kritikus="auto", critic_on_green=False, prompt_lang="en", temperatures, max_tokens, seed, budget)
    RoleSession(llm, scheduler, *, cfg, model=None, priority=Priority.TASK, transcript_dir=None)
        .call(role, template, schema, *, branch=False, temperature=None, seed=None, **values) -> RoleTurn
        .timings() -> per-turn prompt/first-token/total ms (prefix-switch measurement), .transcript, .exhausted()
Role turns (02/04 T1–T10)
    understand(session, task, knowledge="") -> Understanding                     # KERDEZO
    draft_tests(...) -> TestsDraft · interpret_run(session, raw) -> RunInterpretation   # TESZTELO
    propose(...) / propose_text(...) / revise(session, issue_ids, check) -> Proposal    # GONDOLKODO
    critique(session, check) -> Critique                                         # KRITIKUS
    lesson(session, *, evidence, evidence_text) -> LessonCard | None · explain(...) -> Explanation  # TANAR
    extract_claims(session, *, topic, url, text) -> (list[Claim], dropped)       # KIVONATOLO
    vote(session, question, options, *, k=3) -> Vote                             # VALASZTO
    fogalmazo_context(plan, *, length) -> str                                    # FOGALMAZO (persona session)
Protocol (02/02)
    decide(DebateState) -> "continue"|"accept"|"give_up"|"ask_help"
    debate_code(task, *, llm, sandbox, scheduler, cfg, visible=None, knowledge="", answerers=None, ...) -> DebateOutcome
    debate_text(question, *, llm, scheduler, cfg, knowledge="", check=..., ...) -> DebateOutcome
    teach_from(session, outcome) -> LessonCard | None
Tests before code (02/01, 06/05)
    spec_to_task(session, request, *, lang, interface=None, sandbox=None) -> SpecTask(task, visible, covers, learn=False)
Self-questioning (02/03)
    answer_subquestions(understanding, answerers, *, session=None) · KnowledgeGap · CuriosityQueue · model_unsure
"""

from .debate import DebateOutcome, DebateState, debate_code, debate_text, decide, is_oscillating, teach_from
from .self_ask import CuriosityItem, CuriosityQueue, KnowledgeGap, answer_subquestions, gap_to_curiosity, model_unsure
from .session import (
    MODE_BUDGETS,
    BudgetExceeded,
    RoleCallFailed,
    RolesConfig,
    RoleSession,
    RoleTurn,
    Transcript,
    render,
)
from .spec_tests import SpecTask, SpecTestsRejected, check_tests, interface_name, spec_to_task
from .turns import (
    Claim,
    Critique,
    Explanation,
    Issue,
    LessonCard,
    Proposal,
    RunInterpretation,
    SubQuestion,
    TestsDraft,
    Understanding,
    UserQuestion,
    Vote,
    critique,
    draft_tests,
    explain,
    extract_claims,
    fogalmazo_context,
    interpret_run,
    lesson,
    propose,
    propose_text,
    revise,
    understand,
    vote,
)

__all__ = [
    "MODE_BUDGETS", "BudgetExceeded", "Claim", "Critique", "CuriosityItem", "CuriosityQueue", "DebateOutcome",
    "DebateState", "Explanation", "Issue", "KnowledgeGap", "LessonCard", "Proposal", "RoleCallFailed", "RoleSession",
    "RoleTurn", "RolesConfig", "RunInterpretation", "SpecTask", "SpecTestsRejected", "SubQuestion", "TestsDraft",
    "Transcript", "Understanding", "UserQuestion", "Vote", "answer_subquestions", "check_tests", "critique",
    "debate_code", "debate_text", "decide", "draft_tests", "explain", "extract_claims", "fogalmazo_context",
    "gap_to_curiosity", "interface_name", "interpret_run", "is_oscillating", "lesson", "model_unsure", "propose",
    "propose_text", "render", "revise", "spec_to_task", "teach_from", "understand", "vote",
]
