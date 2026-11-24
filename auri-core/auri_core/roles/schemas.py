"""JSON schemas of the role turns (02/04 T1–T10). They go into Ollama's `format` field; the code
re-validates every reply anyway (small models break schemas). Every list and string is bounded:
on a CPU, short output IS speed."""

from __future__ import annotations

from typing import Any

SOURCES = ("store", "sandbox", "web", "model", "user")  # cheapest first (02/03 §1)
SEVERITIES = ("blocking", "major", "minor")


def _str(max_len: int) -> dict[str, Any]:
    return {"type": "string", "maxLength": max_len}


def _arr(items: dict[str, Any], max_items: int) -> dict[str, Any]:
    return {"type": "array", "maxItems": max_items, "items": items}


def _obj(required: list[str], **props: Any) -> dict[str, Any]:
    return {"type": "object", "required": required, "properties": props}


_FILE = _obj(["path", "content"], path=_str(120), content={"type": "string"})

# T1 — KERDEZO
KERDEZO = _obj(
    ["goal", "subquestions", "unknowns", "ask_user"],
    goal=_str(300),
    subquestions=_arr(_obj(["q", "why", "source"], q=_str(200), why=_str(160), source={"enum": list(SOURCES)}), 5),
    unknowns=_arr(_str(160), 5),
    ask_user={"anyOf": [{"type": "null"}, _obj(["question", "options", "default"], question=_str(200),
                                                  options=_arr(_str(80), 3), default=_str(80))]},
)

# T2 — TESZTELO (tests before code). `interface` is filled only when the caller did not give one.
TESZTELO = _obj(
    ["framework", "files", "covers"],
    framework={"enum": ["unittest", "pytest", "node:test", "vitest"]},
    interface=_str(200),
    files={**_arr(_FILE, 2), "minItems": 1},
    covers=_arr(_str(120), 10),
)

# T3 — GONDOLKODO (proposal, code)
GONDOLKODO = _obj(
    ["approach", "files"],
    approach=_str(300),
    steps=_arr(_str(160), 6),
    files={**_arr(_FILE, 2), "minItems": 1},
    assumptions=_arr(_str(160), 5),
    confidence={"enum": ["low", "mid", "high"]},
)

# T3' — GONDOLKODO (proposal, text: nothing to run)
GONDOLKODO_TEXT = _obj(
    ["approach", "steps"],
    approach=_str(600),
    steps=_arr(_str(200), 6),
    assumptions=_arr(_str(160), 5),
    confidence={"enum": ["low", "mid", "high"]},
)

# T4 — KRITIKUS (verbatim from 02/04)
KRITIKUS = _obj(
    ["issues", "verdict"],
    issues=_arr(_obj(["id", "severity", "where", "problem", "evidence"], id=_str(20),
                     severity={"enum": list(SEVERITIES)}, where=_str(120), problem=_str(240),
                     evidence=_str(300), fix_hint=_str(200)), 6),
    verdict={"enum": ["accept", "revise"]},
)

# T5 — GONDOLKODO (revision)
GONDOLKODO_REVISE = _obj(
    ["addresses", "rejected", "files"],
    addresses=_arr(_str(20), 6),
    rejected=_arr(_obj(["id", "reason"], id=_str(20), reason=_str(200)), 6),
    files=_arr(_FILE, 2),
)

# T6 — TESZTELO (interpreting a run)
TESZTELO_RUN = _obj(
    ["failing", "next_action"],
    failing=_arr(_obj(["test", "cause", "location"], test=_str(120), cause=_str(200), location=_str(120)), 6),
    next_action={"enum": ["fix_code", "fix_test", "need_info", "give_up"]},
)

# T7 — TANAR (lesson card; `evidence` is overwritten by the code)
TANAR = _obj(
    ["title", "lesson_en", "lesson_hu", "when_applies", "tags", "evidence"],
    title=_str(80), lesson_en=_str(300), lesson_hu=_str(300), when_applies=_str(200),
    snippet={"anyOf": [{"type": "null"}, _str(800)]},
    tags=_arr(_str(40), 6),
    evidence={"enum": ["tests_passed", "sources_agree", "unverified"]},
)

# T7' — TANAR (explanation for the user)
TANAR_EXPLAIN = _obj(
    ["explanation_hu", "key_points", "hypotheses"],
    explanation_hu=_str(900),
    key_points=_arr(_str(200), 5),
    hypotheses=_arr(_str(200), 5),
)

# T9 — KIVONATOLO
KIVONATOLO = _obj(
    ["claims"],
    claims=_arr(_obj(["kind", "claim", "quote"], kind={"enum": ["fact", "api", "snippet", "fix", "concept"]},
                     claim=_str(300), quote=_str(200), code=_str(800), applies_to=_str(120)), 6),
)


# T10 — VALASZTO
def valaszto(n_options: int) -> dict[str, Any]:
    letters = [chr(ord("A") + i) for i in range(n_options)]
    return _obj(["choice", "reason"], choice={"enum": letters}, reason=_str(120))
