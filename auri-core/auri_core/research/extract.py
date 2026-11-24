"""KIVONATOLÓ (T9, 02/04) — one batched JSON call over all pages, then CODE checks every quote.

The model sees each page as `<web_adat forras="S1" …>…</web_adat>` (data, not instructions). A claim
survives only with ≥ 1 support whose quote, after whitespace/quote-mark normalisation, occurs
VERBATIM in that source's text (03/04 §3: dropped, never "fixed"). Code must occur verbatim too.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .text import extract_keywords, keyword_overlap, norm_quote
from .types import PageDoc, Section

MAX_CLAIMS = 6
MIN_QUOTE = 12
MAX_QUOTE = 300
PAGE_CHARS = 1800  # per page in the prompt: the most relevant sections only (CPU prefill is time)
KINDS = ("fact", "api", "snippet", "fix", "concept")

EXTRACT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["claims"],
    "properties": {
        "claims": {
            "type": "array",
            "maxItems": MAX_CLAIMS,
            "items": {
                "type": "object",
                "required": ["kind", "key", "claim", "support"],
                "properties": {
                    "kind": {"type": "string", "enum": list(KINDS)},
                    "key": {"type": "string", "maxLength": 80},
                    "claim": {"type": "string", "maxLength": 300},
                    "support": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 4,
                        "items": {
                            "type": "object",
                            "required": ["source", "quote"],
                            "properties": {"source": {"type": "string"}, "quote": {"type": "string", "maxLength": 220}},
                        },
                    },
                    "code": {"type": "string", "maxLength": 800},
                    "applies_to": {"type": "string", "maxLength": 60},
                },
            },
        }
    },
}

_TAG_ESCAPE = re.compile(r"<\s*(/?)\s*(web_adat|szerep|system|tudas|ellenorzes)", re.IGNORECASE)


@dataclass
class RawSupport:
    source: str  # "S1"
    quote: str


@dataclass
class RawClaim:
    kind: str
    key: str
    claim: str
    support: list[RawSupport]
    code: str | None = None
    applies_to: str | None = None


def relevant_text(page: PageDoc, question: str, limit: int = PAGE_CHARS) -> str:
    """The page's sections most relevant to the question, in page order, within `limit` chars."""
    scored: list[tuple[int, int, Section]] = []
    for i, s in enumerate(page.sections):
        body = s.text + " " + " ".join(c for _l, c in s.code) + " " + " ".join(s.path)
        scored.append((keyword_overlap(question, body), i, s))
    picked: list[tuple[int, str]] = []
    used = 0
    for score, i, s in sorted(scored, key=lambda x: (-x[0], x[1])):
        if score == 0 and picked:
            break
        parts = [s.text] + [f"```{lang}\n{code}\n```" for lang, code in s.code]
        chunk = "\n".join(p for p in parts if p)
        room = limit - used
        if room <= 80:
            break
        chunk = chunk[:room]
        picked.append((i, chunk))
        used += len(chunk) + 1
    return "\n".join(c for _, c in sorted(picked))


def web_block(source_id: str, page: PageDoc, text: str) -> str:
    """Untrusted page text, framed as data; our own tags inside it are defused."""
    safe = _TAG_ESCAPE.sub(lambda m: f"&lt;{m.group(1)}{m.group(2)}", text)
    title = _TAG_ESCAPE.sub("", page.title.replace('"', "'"))[:120]
    return f'<web_adat forras="{source_id}" cim="{title}">\n{safe}\n</web_adat>'


def parse_claims(data: Any) -> list[RawClaim]:
    """Shape-check the model's JSON (it may ignore the schema); unknown parts are dropped."""
    if not isinstance(data, dict) or not isinstance(data.get("claims"), list):
        return []
    out: list[RawClaim] = []
    for c in data["claims"][:MAX_CLAIMS]:
        if not isinstance(c, dict):
            continue
        claim = " ".join(str(c.get("claim") or "").split())[:300]
        sup = []
        for s in c.get("support") or []:
            if isinstance(s, dict) and isinstance(s.get("quote"), str) and isinstance(s.get("source"), str):
                sup.append(RawSupport(s["source"].strip().upper(), s["quote"]))
        if not claim or not sup:
            continue
        kind = str(c.get("kind") or "fact").lower()
        code = c.get("code") if isinstance(c.get("code"), str) and c.get("code").strip() else None
        applies = c.get("applies_to") if isinstance(c.get("applies_to"), str) and c.get("applies_to").strip() else None
        key = " ".join(str(c.get("key") or "").lower().split())[:80] or " ".join(extract_keywords(claim, 4))
        out.append(RawClaim(kind if kind in KINDS else "fact", key, claim, sup, code, applies))
    return out


def quote_ok(quote: str, page_text_norm: str) -> bool:
    """Verbatim check (03/04 §3). An elided quote ("…", "...") is not verbatim."""
    q = norm_quote(quote).strip(" \"'")
    if not (MIN_QUOTE <= len(q) <= MAX_QUOTE):
        return False
    if "..." in q or "…" in q:
        return False
    return q in page_text_norm


def code_ok(code: str, page: PageDoc) -> bool:
    c = norm_quote(code)
    if len(c) < 3:
        return False
    return any(c in norm_quote(block) for s in page.sections for _l, block in s.code) or c in norm_quote(page.text)
