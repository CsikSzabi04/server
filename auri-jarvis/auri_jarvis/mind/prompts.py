"""Prompt assembly for the Mind (AI-2) — the byte-stable static prefix (spec 3.4 / 5.5).

Order is sacred:
  [system]  persona → profile (logged-in only) → skill index      ← identical bytes per user
  [history] rolling last N turns (plain request/answer text, no context blocks)
  [user]    <kontextus>…volatile data…</kontextus><kérés>…</kérés>  ← always at the END

Tool JSON schemas go in Ollama's `tools` field (fixed list), so they are part of the
cached prefix too. Nothing time-dependent may ever reach `build_system_prompt`.

Pure functions only (no I/O except `load_persona` / `load_me_md`), so the stability
guarantee is unit-testable without Ollama.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
PERSONA_PATH = CONFIG_DIR / "persona.md"
ME_MD_PATH = CONFIG_DIR / "me.md"

GUEST_ADDRESS_VALUES = {"", "you"}
PROFILE_CHAR_BUDGET = 1600  # ≈ 400 tokens (spec 5.8: me.md ≤ 400 tokens)

TIER_NOTE_GUEST = (
    "Vendéggel beszélsz: személyes adatokat (emlékek, emlékeztetők, projektek) nem adsz ki, "
    "és nem is kérdezel ilyet. Ezt csak akkor említed, ha ilyesmit kér: ehhez be kell "
    "jelentkeznie."
)
TIER_NOTE_USER = "A gép bejelentkezett tulajdonosával beszélsz."


def load_persona(path: Path = PERSONA_PATH) -> str:
    return path.read_text(encoding="utf-8")


def load_me_md(path: Path = ME_MD_PATH) -> str | None:
    """Optional, user-owned profile supplement (gitignored). Logged-in tier only."""
    try:
        txt = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return txt or None


def address_rule(address: str | None) -> str:
    """Resolve the address deterministically (small models handle conditionals badly)."""
    a = (address or "").strip()
    if a.lower() in GUEST_ADDRESS_VALUES:
        return "Tegezed a felhasználót (te, neked), név és titulus nélkül; soha nem magázod."
    return f"Így szólítod: „{a}”. Tegezed, nem magázod; a megszólítást természetesen használd, ne minden mondatban."


def tier_note(tier: str) -> str:
    return TIER_NOTE_USER if tier == "user" else TIER_NOTE_GUEST


def render_persona(template: str, *, tier: str, address: str | None) -> str:
    return template.replace("{address_rule}", address_rule(address)).replace("{tier_note}", tier_note(tier)).strip()


def _clean(v: Any) -> str:
    return " ".join(str(v).split()) if v is not None else ""


def render_profile(profile: Mapping[str, Any] | None, me_md: str | None = None) -> str:
    """The "You" layer: Supabase `profiles` row (+ optional me.md), deterministic text.

    Only the stable, human-written fields are used (no `prefs`, no timestamps), in a fixed
    order, so the same profile always renders to the same bytes.
    """
    p = profile or {}
    lines: list[str] = []
    name, nick = _clean(p.get("name")), _clean(p.get("nickname"))
    if name:
        lines.append(f"Név: {name}" + (f" (becenév: {nick})" if nick else ""))
    elif nick:
        lines.append(f"Becenév: {nick}")
    for key, label in (("about", "Róla"), ("tone", "Válaszstílus, amit szeret")):
        val = _clean(p.get(key))
        if val:
            lines.append(f"{label}: {val}")
    interests = [i for i in (_clean(x) for x in (p.get("interests") or [])) if i]
    if interests:
        lines.append("Érdeklődés: " + "; ".join(interests))
    text = "\n".join(lines)
    if me_md:
        text = (text + "\n" if text else "") + me_md.strip()
    if len(text) > PROFILE_CHAR_BUDGET:
        text = text[:PROFILE_CHAR_BUDGET].rsplit(" ", 1)[0] + " …"
    return text


def render_skill_index(skills: Iterable[tuple[str, str]]) -> str:
    """Skill NAMES + one-line descriptions only (bodies load on demand, spec 5.6)."""
    rows = sorted((n.strip(), _clean(d)) for n, d in skills if n and n.strip())
    return "\n".join(f"- {n}: {d}" for n, d in rows)


def build_system_prompt(
    persona_template: str,
    *,
    tier: str,
    address: str | None,
    profile: Mapping[str, Any] | None = None,
    me_md: str | None = None,
    skills: Iterable[tuple[str, str]] = (),
    profile_facts: Sequence[str] = (),
) -> str:
    """The static prefix. Byte-identical for the same (tier, address, profile, me.md, skills,
    profile_facts). `profile_facts` = dream proposals the user ACCEPTED on the HUD (in a
    stable order — the store returns them by id); never shown to a guest."""
    parts = [render_persona(persona_template, tier=tier, address=address)]
    if tier == "user":
        prof = render_profile(profile, me_md)
        facts = [_clean(f) for f in profile_facts if _clean(f)]
        if facts:
            prof = (prof + "\n" if prof else "") + "Amit jóváhagyott magáról:\n" + "\n".join(f"- {f}" for f in facts)
        if prof:
            parts.append("## Akivel beszélsz\n" + prof)
    idx = render_skill_index(skills)
    if idx:
        parts.append("## Elérhető skillek (a use_skill eszközzel töltheted be)\n" + idx)
    return "\n\n".join(parts) + "\n"


def _neutralize(s: str) -> str:
    """Context values are data: they must not be able to close/open our tags."""
    return s.replace("<", "‹").replace(">", "›")


def build_user_message(text: str, context: Mapping[str, Any] | Sequence[tuple[str, Any]] = ()) -> str:
    """Dynamic tail: `<kontextus>` (volatile data) + `<kérés>` (the transcript)."""
    items = list(context.items()) if isinstance(context, Mapping) else list(context)
    lines = [f"{_neutralize(_clean(k))}: {_neutralize(str(v).strip())}" for k, v in items if v not in (None, "", [])]
    req = _neutralize(text.strip())
    if not lines:
        return f"<kérés>{req}</kérés>"
    return "<kontextus>\n" + "\n".join(lines) + "\n</kontextus>\n<kérés>" + req + "</kérés>"


# Fixed seed exchange right after the system prompt. MEASURED (2026-11-20, Ollama 0.40,
# qwen3.5:4b and gemma2:2b): these models can't truncate their KV cache at an arbitrary
# divergence point (hybrid/recurrent and sliding-window attention) — Ollama only resumes
# from the end of an earlier *prompt*. So warming just [system] does NOT help the next
# turn (qwen3.5: 4.9 s prefill), while warming [system, seed request] makes every later
# [system, seed, seed reply, …, new request] resume there (qwen3.5: ~1.4 s, gemma2: ~0.55 s),
# for independent questions and for growing sessions alike.
#
# The seed is also a tiny IN-CONTEXT DEMO. MEASURED (2026-11-21, eval_tools): with the voice
# persona, gemma4:e2b answered "Nyisom meg a VS Code-ot…" in text for 4/4 action commands
# instead of calling open_app (with a minimal system prompt it called it correctly). One
# action → tool call → short confirmation, and one question → plain answer, teach the small
# model the pattern. Static → part of the cached prefix, so it costs no per-turn time.
SEED: tuple[dict[str, Any], ...] = (
    {"role": "user", "content": "<kérés>Nyisd meg a jegyzettömböt a bal monitoron.</kérés>"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "open_app", "arguments": {"name": "notepad", "monitor": 1}}}],
    },
    {
        "role": "tool",
        "content": '{"status": "ok", "message": "Megnyitottam: Jegyzettömb, a bal monitoron."}',
        "tool_name": "open_app",
    },
    {"role": "assistant", "content": "Megnyitottam a jegyzettömböt a bal monitoron."},
    {"role": "user", "content": "<kérés>Mi Franciaország fővárosa?</kérés>"},
    {"role": "assistant", "content": "Párizs."},
)
SEED_REQUEST = SEED[-2]["content"]  # the last seed request (warm point)
SEED_REPLY = SEED[-1]["content"]

WARM_PROBE = "<kérés>Próba.</kérés>"


def warm_sequence(system: str) -> list[list[dict[str, Any]]]:
    """Requests `warmup` prefills, in order (1 token each).

    MEASURED (gemma4:e2b, 1369-token prefix): after only the seed warmup the FIRST real
    question still prefilled 2.6 s (later ones 0.4 s); one throwaway probe turn after the
    seed moves that cost into startup → first real question 0.58 s, then ~0.34 s.
    """
    return [seed_messages(system), build_messages(system, [], WARM_PROBE)]


def seed_messages(system: str) -> list[dict[str, Any]]:
    """What `warmup` prefills first: the static prefix up to the last seed request."""
    return [{"role": "system", "content": system}, *(dict(m) for m in SEED[:-1])]


def build_messages(
    system: str,
    history: Sequence[Mapping[str, Any] | tuple[str, str]],
    user_message: str,
) -> list[dict[str, Any]]:
    """system → seed exchange → session turns (verbatim) → current user message.

    `history` items are either message dicts (kept as-is, e.g. an assistant tool call and
    its tool result) or (request, answer) pairs. It must be append-only within a session and
    passed back byte-for-byte as it was sent (user content incl. its <kontextus>, the model's
    exact reply): any rewrite of an earlier turn breaks the cache resume point. The Mind
    decides when a session resets (idle gap, budget, identity change) instead of rolling a
    window every turn.
    """
    msgs: list[dict[str, Any]] = [*seed_messages(system), {"role": "assistant", "content": SEED_REPLY}]
    for item in history:
        if isinstance(item, tuple):
            msgs.append({"role": "user", "content": item[0]})
            msgs.append({"role": "assistant", "content": item[1]})
        else:
            msgs.append(dict(item))
    msgs.append({"role": "user", "content": user_message})
    return msgs
