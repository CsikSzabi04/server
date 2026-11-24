"""Privacy gate (owner: AI-3). Spec: thinking/09-biztonsag-es-adatvedelem/01-alapszabalyok.md.

Every knowledge-store write goes through `guard()` (the store calls it; a test checks it):
  * `is_personal(text)` — personal data never enters the shared knowledge (T0).
    Port of `web/src/brain/privacy.ts` (`isPersonal`, own-name matching) plus the Jarvis
    "declared secret" rule (`auri_jarvis.memory.redact.DECLARED_SECRET`).
  * `redact(text)` — secret-looking values (API keys, tokens, card/account numbers, private
    keys) are masked in place before anything is stored, logged or sent out.

Two profiles: `kind="text"` (descriptions, goals, lessons) errs on the side of "personal";
`kind="code"` skips the bare digit-run and date rules (test data such as `1000000` or
`"2024-01-23"` is ordinary code), but keeps e-mail, phone, self-disclosure and own names.
Pure functions, no I/O, never throw on odd input.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Literal

from auri_jarvis.memory.redact import DECLARED_SECRET

from .contracts import PrivacyRejected

Kind = Literal["text", "code"]

# ── personal data (port of web/src/brain/privacy.ts PERSONAL, same order) ─────
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE = re.compile(r"(?:\+\d{1,3}|\b0\d)[\s/-]?(?:\d[\s/-]?){7,}")
_PHONE_US = re.compile(r"\b\d{3}[-.]\d{3}[-.]\d{4}\b")
_DIGITS = re.compile(r"\b\d{6,}\b")
_DATE_YMD = re.compile(
    r"\b(19|20)\d{2}\s*[.\-/]\s*(0?[1-9]|1[0-2]|január|február|március|április|május|június|július|augusztus"
    r"|szeptember|október|november|december)\s*[.\-/]?\s*(0?[1-9]|[12]\d|3[01])\b",
    re.IGNORECASE,
)
_DATE_DMY = re.compile(r"\b(0?[1-9]|[12]\d|3[01])[./](0?[1-9]|1[0-2])[./](19|20)\d{2}\b")
_HU_RECORDS = re.compile(
    r"\b(szület\w*|szülinap\w*|lakcím\w*|lakom|lakunk|lakik|címem|telefonszám\w*|személyi(?!ség)\w*|adóazonosító\w*"
    r"|adószám\w*|taj-?szám\w*|bankkártya\w*|számlaszám\w*|jelszav\w*|jelszó\w*)",
    re.IGNORECASE,
)
_HU_SELF = re.compile(
    r"\b(a nevem|nevem|hívnak engem|éves vagyok|munkahelyem|egyetemre járok|egyetemen tanulok|hallgató vagyok)\b",
    re.IGNORECASE,
)
_HU_CALLED = re.compile(r"\b\S+(nak|nek) hívnak\b", re.IGNORECASE)
_HU_LIVE = re.compile(r"\S{3,}(ban|ben|on|en|ön) (élek|élünk)\b", re.IGNORECASE)
_EN_SELF = re.compile(
    r"\b(my name is|i am called|i was born|born (on|in)|my birthday|i live (in|at)|my address|my phone|phone number"
    r"|my password|password is|social security|credit card|i study at|i work at|years old)\b",
    re.IGNORECASE,
)

_TEXT_RULES: tuple[re.Pattern[str], ...] = (
    _EMAIL, _PHONE, _PHONE_US, _DIGITS, _DATE_YMD, _DATE_DMY, _HU_RECORDS, _HU_SELF, _HU_CALLED, _HU_LIVE, _EN_SELF,
    DECLARED_SECRET,
)
# Code: no bare digit runs, no dates, no "phone"-shaped digit groups (array literals);
# record words ("jelszó", "születési") in code are usually field names, so self-disclosure only.
_CODE_RULES: tuple[re.Pattern[str], ...] = (_EMAIL, _HU_SELF, _HU_CALLED, _HU_LIVE, _EN_SELF, DECLARED_SECRET)

# Fictional data allowed in tests, tasks and fixtures (ai_prompts.md §2 rule 9) is still
# personal-SHAPED and is rejected like real data — that is what the tests assert.

# ── own names (privacy.ts setOwnNames / nameMatchers) ──────────────────────────
_NAME_SUFFIX = r"(?:nak|nek|[a-z]?(?:al|el)|ert|rol|rul|ra|re|ba|be|ban|ben|hoz|hez|tol|tul|nal|nel|ig|kent|bol|bul|ek|e|[aeou]?[tnks])?"
_own_names: list[re.Pattern[str]] = []


def fold(s: str) -> str:
    """lower-case + accents removed: "Máté" and a typed "Mate" match the same way."""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def _name_matchers(names: Iterable[str | None]) -> list[re.Pattern[str]]:
    out: set[str] = set()
    for raw in names:
        n = re.sub(r"\s+", " ", fold(raw or "").strip())
        if len(n) < 3:
            continue
        out.add(n)
        for part in re.split(r"[\s,()/.-]+", n):
            if len(part) >= 3:
                out.add(part)
    return [re.compile(rf"(^|[^\w]){re.escape(n)}{_NAME_SUFFIX}(?!\w)") for n in sorted(out)]


def set_own_names(names: Iterable[str | None]) -> None:
    """Register the signed-in identity's own names (P1; call with [] on logout)."""
    global _own_names
    _own_names = _name_matchers(names)


# Reserved documentation addresses (RFC 2606 / 6761 domains, RFC 5737 / 3849 IPs) belong to no one,
# so `ann@example.com` or `user@192.0.2.10` in a code sample is not personal data.
_RESERVED_ADDR = re.compile(
    r"\b[\w.+-]+@(?:(?:[\w-]+\.)*(?:example\.(?:com|org|net)|[\w-]+\.(?:example|test|invalid|localhost))"
    r"|192\.0\.2\.\d{1,3}|198\.51\.100\.\d{1,3}|203\.0\.113\.\d{1,3})\b",
    re.IGNORECASE,
)


def is_personal(text: str, names: Iterable[str] = (), *, kind: Kind = "text") -> bool:
    """Does this text contain personal data that must never enter the shared knowledge?"""
    if not text:
        return False
    text = _RESERVED_ADDR.sub(" ", text)
    rules = _CODE_RULES if kind == "code" else _TEXT_RULES
    if any(r.search(text) for r in rules):
        return True
    extra = list(names)
    if not _own_names and not extra:
        return False
    t = fold(text)
    if any(r.search(t) for r in _own_names):
        return True
    return bool(extra) and any(r.search(t) for r in _name_matchers(extra))


# ── secrets (masked in place) ──────────────────────────────────────────────────
MASK = "[törölve]"
_SECRET_VALUES: tuple[re.Pattern[str], ...] = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)"),
    re.compile(r"\b(?:sk|pk|rk|ghp|gho|ghs|github_pat|xox[bpas]|glpat|hf)[-_][A-Za-z0-9_\-]{12,}"),  # well-known prefixes
    re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}"),  # Google API key
    re.compile(r"\bgsk_[A-Za-z0-9]{20,}"),  # Groq
    re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"),  # JWT (Supabase keys)
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key id
    # high-entropy blob: ≥ 32 chars with a digit, an upper- and a lower-case letter
    # (long snake_case identifiers have no upper case + digit mix, so code survives)
    re.compile(r"\b(?=[A-Za-z0-9+/_\-]*\d)(?=[A-Za-z0-9+/_\-]*[A-Z])(?=[A-Za-z0-9+/_\-]*[a-z])[A-Za-z0-9+/_\-]{32,}={0,2}"),
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),  # card / account-like digit runs
    re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){3,7}\b"),  # IBAN
)
# `API_KEY = "…"`, `password: …`, `SUPABASE_SERVICE_ROLE_KEY=…` → keep the name, mask the value.
# Only a quoted literal or a whole `.env`-style line counts — `token = get_token()` is code.
_SECRET_NAME = r"[A-Z0-9_]*(?:api[_-]?key|secret|token|passw(?:or)?d|pwd|supabase_[a-z_]*key|access[_-]?key)[A-Z0-9_]*"
_SECRET_ASSIGN = re.compile(rf"(?i)\b({_SECRET_NAME})(\s*[:=]\s*)([\"'])([^\"'\s]{{6,}})\3")
_SECRET_ENV_LINE = re.compile(rf"(?im)^(\s*(?:export\s+)?{_SECRET_NAME})(\s*=\s*)()([^\s\"'#()\[\]{{}}]{{6,}})\s*$")


def redact(text: str, *, kind: Kind = "text") -> str:
    """Mask secret-looking values; the rest of the text stays (code stays runnable shape).
    `kind="text"` also drops a sentence that declares one's own secret (Jarvis rule)."""
    if not text:
        return text
    if kind == "text" and DECLARED_SECRET.search(text):
        return "[kényes adat törölve]"
    out = text
    for assign in (_SECRET_ASSIGN, _SECRET_ENV_LINE):
        out = assign.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{MASK}{m.group(3)}", out)
    for p in _SECRET_VALUES:
        out = p.sub(MASK, out)
    return out


def has_secret(text: str) -> bool:
    return bool(text) and redact(text, kind="code") != text


class PrivacyError(PrivacyRejected, ValueError):
    """A write was refused by the privacy gate (personal data, or a secret inside code)."""

    def __init__(self, field: str, reason: Literal["personal", "secret"] = "personal") -> None:
        what = "személyes adat" if reason == "personal" else "titoknak látszó érték a kódban"
        super().__init__(f"{what} a(z) „{field}” mezőben — nem tárolható a közös tudásban")
        self.field = field
        self.reason = reason


def guard(fields: dict[str, str | None], *, code_fields: Iterable[str] = (), names: Iterable[str] = ()) -> dict[str, str | None]:
    """The gate for one write: raise PrivacyError if any field is personal; text fields come
    back with secrets redacted. A code field with a secret is refused, not altered: the
    stored code must be exactly the code that passed its tests."""
    code = set(code_fields)
    names = list(names)
    out: dict[str, str | None] = {}
    for key, value in fields.items():
        if value is None:
            out[key] = None
            continue
        kind: Kind = "code" if key in code else "text"
        if is_personal(value, names, kind=kind):
            raise PrivacyError(key)
        cleaned = redact(value, kind=kind)
        if kind == "code" and cleaned != value:
            raise PrivacyError(key, "secret")
        out[key] = cleaned
    return out
