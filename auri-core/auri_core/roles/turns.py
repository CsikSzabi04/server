"""One function per role turn (02/04 T1–T10): render → call → re-validate → typed result.

The code never trusts the model's self-assessment: issues without evidence do not count, quotes are
looked up in the page, the lesson's `evidence` is overwritten with the real check result."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Literal

from .. import privacy
from ..contracts import Role
from ..solve import _ELIDED
from . import schemas
from .session import RoleCallFailed, RoleSession, data_block

# ───────────────────────────── T1 KERDEZO ─────────────────────────────


@dataclass
class SubQuestion:
    q: str
    why: str
    source: str  # store | sandbox | web | model | user
    answer: str | None = None
    answered_by: str | None = None


@dataclass(frozen=True)
class UserQuestion:
    question: str
    options: tuple[str, ...]
    default: str


@dataclass
class Understanding:
    goal: str
    subquestions: list[SubQuestion]
    unknowns: list[str]
    ask_user: UserQuestion | None


def _s(v: Any, n: int) -> str:
    return str(v or "").strip()[:n]


async def understand(session: RoleSession, task: str, knowledge: str = "") -> Understanding:
    turn = await session.call(Role.KERDEZO, "kerdezo", schemas.KERDEZO, task=data_block(task, "feladat"),
                              knowledge=data_block(knowledge or "(none)", "tudas"))
    d = turn.data
    subs = []
    for s in (d.get("subquestions") or [])[:5]:
        if isinstance(s, dict) and _s(s.get("q"), 200):
            src = s.get("source") if s.get("source") in schemas.SOURCES else "model"
            subs.append(SubQuestion(_s(s.get("q"), 200), _s(s.get("why"), 160), src))
    ask = d.get("ask_user")
    user_q = None
    if isinstance(ask, dict) and _s(ask.get("question"), 200):
        opts = tuple(_s(o, 80) for o in (ask.get("options") or [])[:3] if _s(o, 80))
        default = _s(ask.get("default"), 80) or (opts[0] if opts else "")
        question = _s(ask.get("question"), 200)
        if not privacy.is_personal(question):  # 02/03 §4: never ask for personal data
            user_q = UserQuestion(question, opts, default)
    unknowns = [_s(u, 160) for u in (d.get("unknowns") or [])[:5] if _s(u, 160)]
    return Understanding(_s(d.get("goal"), 300), subs, unknowns, user_q)


# ───────────────────────────── T2 / T6 TESZTELO ─────────────────────────────


@dataclass
class TestsDraft:
    __test__ = False  # not a pytest class
    framework: str
    files: dict[str, str]
    covers: list[str]
    interface: str | None = None


async def draft_tests(session: RoleSession, spec: str, *, framework: str, framework_rules: str,
                      interface: str) -> TestsDraft:
    turn = await session.call(Role.TESZTELO, "tesztelo", schemas.TESZTELO, framework=framework,
                              framework_rules=framework_rules, interface=interface, task=data_block(spec, "feladat"))
    d = turn.data
    files = {str(f.get("path", "")): f["content"] for f in (d.get("files") or [])[:2]
             if isinstance(f, dict) and isinstance(f.get("content"), str) and f["content"].strip()}
    covers = [_s(c, 120) for c in (d.get("covers") or [])[:10] if _s(c, 120)]
    return TestsDraft(str(d.get("framework") or framework), files, covers, _s(d.get("interface"), 200) or None)


@dataclass
class RunInterpretation:
    failing: list[dict[str, str]]
    next_action: Literal["fix_code", "fix_test", "need_info", "give_up"]


async def interpret_run(session: RoleSession, raw_output: str) -> RunInterpretation:
    tail = "\n".join((raw_output or "").splitlines()[-80:])  # 02/04 T6: the last 80 lines
    turn = await session.call(Role.TESZTELO, "tesztelo_run", schemas.TESZTELO_RUN,
                              output=data_block(tail, "ellenorzes"))
    d = turn.data
    failing = [{"test": _s(f.get("test"), 120), "cause": _s(f.get("cause"), 200), "location": _s(f.get("location"), 120)}
               for f in (d.get("failing") or [])[:6] if isinstance(f, dict)]
    act = d.get("next_action")
    return RunInterpretation(failing, act if act in ("fix_code", "fix_test", "need_info", "give_up") else "need_info")


# ───────────────────────────── T3 / T5 GONDOLKODO ─────────────────────────────


@dataclass
class Proposal:
    approach: str
    files: dict[str, str]
    steps: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    confidence: str = "low"
    addresses: list[str] = field(default_factory=list)
    rejected: list[dict[str, str]] = field(default_factory=list)


def _files(d: dict[str, Any]) -> dict[str, str]:
    """Complete files only (no `# rest unchanged`), never a test file (06/05 §8)."""
    out: dict[str, str] = {}
    for f in (d.get("files") or [])[:2]:
        if not (isinstance(f, dict) and isinstance(f.get("content"), str)):
            continue
        name = str(f.get("path", "")).replace("\\", "/").rsplit("/", 1)[-1]
        if not name or "test" in name.lower() or "conftest" in name.lower():
            continue
        if f["content"].strip() and not _ELIDED.search(f["content"]):
            out[name] = f["content"]
    return out


async def propose(session: RoleSession, task: str, *, language: str, solution_file: str, tests: dict[str, str],
                  knowledge: str = "", deps: str = "standard library only") -> Proposal:
    tests_txt = "\n\n".join(f"# {p}\n{b}" for p, b in tests.items()) or "(none)"
    turn = await session.call(Role.GONDOLKODO, "gondolkodo", schemas.GONDOLKODO, language=language, deps=deps,
                              solution_file=solution_file, task=data_block(task, "feladat"),
                              knowledge=data_block(knowledge or "(none)", "tudas"), tests=data_block(tests_txt, "tesztek"))
    d = turn.data
    return Proposal(_s(d.get("approach"), 300), _files(d), [_s(x, 160) for x in (d.get("steps") or [])[:6]],
                    [_s(x, 160) for x in (d.get("assumptions") or [])[:5]], str(d.get("confidence") or "low"))


async def propose_text(session: RoleSession, task: str, knowledge: str = "") -> Proposal:
    turn = await session.call(Role.GONDOLKODO, "gondolkodo_text", schemas.GONDOLKODO_TEXT,
                              task=data_block(task, "feladat"), knowledge=data_block(knowledge or "(none)", "tudas"))
    d = turn.data
    return Proposal(_s(d.get("approach"), 600), {}, [_s(x, 200) for x in (d.get("steps") or [])[:6]],
                    [_s(x, 160) for x in (d.get("assumptions") or [])[:5]], str(d.get("confidence") or "low"))


async def revise(session: RoleSession, issue_ids: list[str], check: str) -> Proposal:
    turn = await session.call(Role.GONDOLKODO, "gondolkodo_revise", schemas.GONDOLKODO_REVISE,
                              issue_ids=", ".join(issue_ids) or "(the failing check)",
                              check=data_block(check, "ellenorzes"))
    d = turn.data
    rejected = [{"id": _s(r.get("id"), 20), "reason": _s(r.get("reason"), 200)}
                for r in (d.get("rejected") or [])[:6] if isinstance(r, dict) and _s(r.get("reason"), 200)]
    return Proposal("", _files(d), addresses=[_s(a, 20) for a in (d.get("addresses") or [])[:6]], rejected=rejected)


# ───────────────────────────── T4 KRITIKUS ─────────────────────────────


@dataclass(frozen=True)
class Issue:
    id: str
    severity: Literal["blocking", "major", "minor"]
    where: str
    problem: str
    evidence: str
    fix_hint: str = ""

    @property
    def actionable(self) -> bool:
        """Starts a new round: blocking/major AND with evidence (02/02 §8: minor never does)."""
        return self.severity in ("blocking", "major") and bool(self.evidence.strip())


@dataclass
class Critique:
    issues: list[Issue]
    verdict: Literal["accept", "revise"]
    ignored: int = 0  # issues dropped for missing evidence / location

    @property
    def blocking(self) -> list[Issue]:
        return [i for i in self.issues if i.actionable]


async def critique(session: RoleSession, check: str) -> Critique:
    turn = await session.call(Role.KRITIKUS, "kritikus", schemas.KRITIKUS, check=data_block(check, "ellenorzes"))
    d = turn.data
    issues, ignored, seen = [], 0, set()
    for n, i in enumerate((d.get("issues") or [])[:6], 1):
        if not isinstance(i, dict):
            ignored += 1
            continue
        sev = i.get("severity") if i.get("severity") in schemas.SEVERITIES else "minor"
        iid = _s(i.get("id"), 20) or f"K{n}"
        if iid in seen:
            iid = f"{iid}-{n}"
        seen.add(iid)
        issue = Issue(iid, sev, _s(i.get("where"), 120), _s(i.get("problem"), 240), _s(i.get("evidence"), 300),
                      _s(i.get("fix_hint"), 200))
        if not issue.where or not issue.evidence:  # 02/02 §8: no evidence / no location → does not count
            ignored += 1
            continue
        issues.append(issue)
    # the verdict follows the evidence, not the model's word
    verdict: Literal["accept", "revise"] = "revise" if any(i.actionable for i in issues) else "accept"
    return Critique(issues, verdict, ignored)


# ───────────────────────────── T7 TANAR ─────────────────────────────

Evidence = Literal["tests_passed", "sources_agree", "unverified"]


@dataclass
class LessonCard:
    title: str
    lesson_en: str
    lesson_hu: str
    when_applies: str
    snippet: str | None
    tags: list[str]
    evidence: Evidence


async def lesson(session: RoleSession, *, evidence: Evidence, evidence_text: str) -> LessonCard | None:
    """A reusable lesson. `evidence` is what the CHECK proved — the model's own label is overwritten.
    Returns None if the card would contain personal data (it must never enter the shared T0)."""
    turn = await session.call(Role.TANAR, "tanar", schemas.TANAR, evidence=f"{evidence}: {evidence_text}"[:400])
    d = turn.data
    card = LessonCard(_s(d.get("title"), 80), _s(d.get("lesson_en"), 300), _s(d.get("lesson_hu"), 300),
                      _s(d.get("when_applies"), 200), (_s(d.get("snippet"), 800) or None),
                      [_s(t, 40) for t in (d.get("tags") or [])[:6] if _s(t, 40)], evidence)
    text = " ".join([card.title, card.lesson_en, card.lesson_hu, card.when_applies, *card.tags])
    if privacy.is_personal(text) or (card.snippet and privacy.is_personal(card.snippet, kind="code")):
        session.transcript.write("TANAR", dropped="personal data in lesson card")
        return None
    return card


@dataclass
class Explanation:
    explanation_hu: str
    key_points: list[str]
    hypotheses: list[str]


async def explain(session: RoleSession, topic: str, verified_facts: list[str]) -> Explanation:
    facts = "\n".join(f"- {f}" for f in verified_facts[:12]) or "(no verified facts)"
    turn = await session.call(Role.TANAR, "tanar_explain", schemas.TANAR_EXPLAIN, topic=data_block(topic, "feladat"),
                              facts=data_block(facts, "tudas"))
    d = turn.data
    return Explanation(_s(d.get("explanation_hu"), 900), [_s(p, 200) for p in (d.get("key_points") or [])[:5]],
                       [_s(h, 200) for h in (d.get("hypotheses") or [])[:5]])


# ───────────────────────────── T9 KIVONATOLO ─────────────────────────────


@dataclass(frozen=True)
class Claim:
    kind: str
    claim: str
    quote: str
    code: str | None = None
    applies_to: str | None = None


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


async def extract_claims(session: RoleSession, *, topic: str, url: str, text: str) -> tuple[list[Claim], int]:
    """Claims whose VERBATIM quote is really in the page (04-tanulas-a-webbol). Returns (claims, dropped)."""
    turn = await session.call(Role.KIVONATOLO, "kivonatolo", schemas.KIVONATOLO, topic=data_block(topic, "web_adat"),
                              url=url.replace('"', "%22"), text=data_block(text, "web_adat"))
    page = _norm_ws(text)
    claims, dropped = [], 0
    for c in (turn.data.get("claims") or [])[:6]:
        if not isinstance(c, dict):
            dropped += 1
            continue
        quote = _s(c.get("quote"), 200)
        if not quote or _norm_ws(quote) not in page:
            dropped += 1  # an invented quote = an invented claim
            continue
        kind = c.get("kind") if c.get("kind") in ("fact", "api", "snippet", "fix", "concept") else "fact"
        claims.append(Claim(kind, _s(c.get("claim"), 300), quote, _s(c.get("code"), 800) or None,
                            _s(c.get("applies_to"), 120) or None))
    return claims, dropped


# ───────────────────────────── T10 VALASZTO ─────────────────────────────


@dataclass
class Vote:
    choice: str | None  # None = "bizonytalan" (tie or no valid sample)
    counts: dict[str, int]
    reasons: list[str]


async def vote(session: RoleSession, question: str, options: list[str], *, k: int = 3) -> Vote:
    """k samples at temperature 0.7 on a branch (each sees the same prefix, different seed), majority."""
    if not 2 <= len(options) <= 3:
        raise ValueError("2–3 options")
    letters = [chr(ord("A") + i) for i in range(len(options))]
    opts = " ".join(f"{letter}) {o}" for letter, o in zip(letters, options, strict=True))
    schema = schemas.valaszto(len(options))
    picks, reasons = [], []
    base = session.cfg.seed or 0
    for i in range(k):
        try:
            turn = await session.call(Role.VALASZTO, "valaszto", schema, branch=True, seed=base + i,
                                      question=data_block(question, "feladat"), options=opts)
        except RoleCallFailed:
            continue
        if turn.data.get("choice") in letters:
            picks.append(turn.data["choice"])
            reasons.append(_s(turn.data.get("reason"), 120))
    counts = dict(Counter(picks))
    top = Counter(picks).most_common(2)
    if not top or (len(top) == 2 and top[0][1] == top[1][1]):
        return Vote(None, counts, reasons)
    return Vote(top[0][0], counts, reasons)


# ───────────────────────────── T8 FOGALMAZO (persona session, no model call here) ─────────────────────────────


def fogalmazo_context(plan: dict[str, Any], *, length: str = "rövid, 2–4 mondat") -> str:
    """The <kontextus> block for the persona session (02/04 T8): the writer works from the plan only."""
    import json

    return ("<kontextus>\n<terv>" + data_block(json.dumps(plan, ensure_ascii=False), "terv") + "</terv>\n"
            "Szabályok: csak a terv pontjaiból dolgozz; minden állítás után a forrás azonosítója: [k12].\n"
            'A "bizonytalan" pontot így mondd: "nem biztos, de …". Szakszó angolul, backtickben,\n'
            f"kötőjeles toldalékkal (`commit`-ot). Hossz: {length}.\n</kontextus>")
