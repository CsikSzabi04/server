"""Secret filter for the Mind's memory (AI-2, spec 5.8). Modelled on the web app's
`web/src/autolearn/redact.ts` + `web/src/brain/privacy.ts`, but with a different goal:

Jarvis memory is the logged-in user's OWN local store (per user id; a guest stores nothing),
so ordinary personal facts may live there. What never may: passwords, PINs, card / account /
ID numbers, API keys and tokens. `is_secret()` blocks a fact; `mask()` cleans turn text.
"""

from __future__ import annotations

import re

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:jelszav\w*|jelszó\w*|password\w*|passwd|pin ?kód\w*|pinkód\w*|\bpin\b)", re.IGNORECASE),
    re.compile(r"\b(?:bankkártya\w*|kártyaszám\w*|számlaszám\w*|iban|cvc|cvv|credit card)\b", re.IGNORECASE),
    re.compile(r"\b(?:taj-?szám\w*|adóazonosító\w*|adószám\w*|személyi ?(?:igazolvány|szám)\w*|útlevél\w*)", re.IGNORECASE),
    re.compile(r"\b(?:api[ _-]?kulcs\w*|api[ _-]?key|token\w*|secret\w*|titkos kulcs\w*)\b", re.IGNORECASE),
    re.compile(r"(?:\d[ -]?){12,19}"),  # card / account-like digit runs
    re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){3,7}\b"),  # IBAN
    re.compile(r"\b\d{8,}\b"),  # long ids
    re.compile(r"\b(?:sk|pk|rk|ghp|gho|github_pat|xox[bpas]|AIza)[-_][A-Za-z0-9_\-]{12,}"),  # well-known key prefixes
    re.compile(r"\b[A-Za-z0-9+/_\-]{32,}={0,2}\b"),  # long base64/hex blobs
)


# Declarations of one's own secret ("a jelszavam …", "my password is …") — for turn text,
# where merely TALKING about passwords or API keys must stay possible.
DECLARED_SECRET = re.compile(
    r"\b(?:jelszavam|jelszavaim|jelszó(?:m)?\s*(?:az|:|=|is|legyen)|my password|password is|pin ?kódom|pinkódom"
    r"|kártyaszámom|számlaszámom|adóazonosítóm|taj-?számom|személyi(?:m| számom)|api ?kulcsom|tokenem)\b",
    re.IGNORECASE,
)


def is_secret(text: str) -> bool:
    """For FACTS: any mention of a secret kind, or a secret-looking value → don't store."""
    return any(p.search(text) for p in SECRET_PATTERNS)


def mask(text: str) -> str:
    """For TURN text: a declared secret drops the whole sentence (the value is free text
    after it); secret-looking values (digit runs, IBAN, keys) are replaced in place."""
    if not text:
        return text
    if DECLARED_SECRET.search(text):
        return "[kényes adat törölve]"
    out = text
    for p in SECRET_PATTERNS[4:]:
        out = p.sub("[törölve]", out)
    return out
