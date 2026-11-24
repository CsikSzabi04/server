"""M5 (AI-2): "okos mód" and "screen_look" — two explicit, slower paths (spec 5.5 / 12.3).

- Smart mode: "gondold át alaposan …" / "okos mód: …" → the bigger `smart_model`
  (qwen3.5:9b) with thinking on and a longer answer budget. The main model is unloaded first
  (RAM, spec 3.6) and re-warmed afterwards. A bare "okos mód" arms it for the next question.
- Screen look: "mit látsz a képernyőn?" / "nézd meg a képernyőt, …" → a screenshot (in
  memory only, never stored) goes to the main vision-capable model. Logged-in users only:
  the screen may show anything personal.
"""

from __future__ import annotations

import re

SMART_RX = re.compile(
    r"^(?:(?:hey\s+)?(?:auri|jarvis)[,!\s]+)?(?:okos ?mód(?:ban)?|gondold (?:át|végig) alaposan|gondolkodj alaposan"
    r"|alaposan gondold (?:át|végig)|think (?:carefully|hard))\b[\s,:;.!-]*(?P<q>.*)$",
    re.IGNORECASE,
)
SCREEN_RX = re.compile(
    r"^(?:(?:hey\s+)?(?:auri|jarvis)[,!\s]+)?(?:mit látsz a (?:képernyőn|monitoron)|nézd meg a (?:képernyőt|monitort)"
    r"|mi (?:ez|van) a képernyőn|mi ez a hiba a képernyőn|look at (?:my|the) screen)\b[\s,:;.?!-]*(?P<q>.*)$",
    re.IGNORECASE,
)
SMART_NOTE = "Ezt alaposan átgondolom, ez eltart egy darabig."
SMART_ARMED = "Rendben, a következő kérdésedet alaposan átgondolom. Mondd!"
SMART_STYLE = "okos mód: alaposan átgondolt, de legfeljebb 5 mondatos, beszélt válasz"
SCREEN_NOTE = "Megnézem, ez eltarthat pár másodpercig."
SCREEN_GUEST = "A képernyőt csak bejelentkezve nézem meg."
SCREEN_DEFAULT_Q = "Mit látsz a képernyőn? Foglald össze röviden, a legfontosabbal kezdve."


def match_smart(text: str) -> str | None:
    """None = not a smart-mode request; "" = armed for the next question; else the question."""
    m = SMART_RX.match(text.strip())
    return None if m is None else m.group("q").strip()


def match_screen(text: str) -> str | None:
    m = SCREEN_RX.match(text.strip())
    return None if m is None else (m.group("q").strip() or SCREEN_DEFAULT_Q)
