"""The role-book session (02/01 §3, 02/04 §0).

One model, ONE byte-stable system prompt (the same T0 role-book that `solve` uses, so the KV cache is
shared), the role is the `<szerep>…</szerep>` tag at the start of each user message, and the
conversation only grows by appending. Every turn: one JSON call inside its own lease, at most one
JSON-fix request, budget counted, timings written to the transcript so the prefix cost can be measured.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from .. import privacy
from ..contracts import ABORTED, Budget, Cancelled, LLMClient, Priority, Role, Scheduler, chat_or_abort
from ..router import SimpleRouter
from ..solve import PROMPTS_DIR, _b36, _parse_json, load_prompts

RoleMode = Literal["interactive", "idle", "night"]  # 02/02 §5: who is waiting decides the budget
Auto = Literal["auto", "always", "never"]

# 02/02 §5 starting budgets (to be tuned from measured transcripts).
MODE_BUDGETS: dict[str, Budget] = {
    "interactive": Budget(llm_calls=6, out_tokens=3000, wall_s=120, repair_rounds=1),
    "idle": Budget(llm_calls=12, out_tokens=8000, wall_s=600, repair_rounds=3),
    "night": Budget(llm_calls=20, out_tokens=16000, wall_s=1800, repair_rounds=3),
}

# 02/01 §5: Gondolkodó 0.4, the others 0.2–0.3 (starting values); Választó samples at 0.7.
DEFAULT_TEMPERATURES: dict[str, float] = {
    Role.KERDEZO: 0.2, Role.TESZTELO: 0.2, Role.GONDOLKODO: 0.4, Role.KRITIKUS: 0.2,
    Role.TANAR: 0.3, Role.KIVONATOLO: 0.2, Role.VALASZTO: 0.7,
}
# num_predict caps: well above the typical output (02/02 §5), because a cut-off JSON is worthless.
DEFAULT_MAX_TOKENS: dict[str, int] = {
    "kerdezo": 400, "tesztelo": 1400, "gondolkodo": 1200, "gondolkodo_text": 600, "kritikus": 600,
    "gondolkodo_revise": 1200, "tesztelo_run": 450, "tanar": 450, "tanar_explain": 700,
    "kivonatolo": 900, "valaszto": 80,
}
GARBAGE = "(unusable reply removed)"


@dataclass(frozen=True)
class RolesConfig:
    """The whole P3 machinery is OFF by default (ai_prompts §3: off unless measurement shows a gain)."""

    enabled: bool = False
    mode: RoleMode = "interactive"
    max_rounds: int | None = None  # None = the mode budget's repair_rounds (interactive: 1, else 3)
    use_kerdezo: Auto = "auto"  # auto: only when the task is ambiguous or long, or not interactive
    use_kritikus: Auto = "auto"  # auto: only when the failure cause is unclear or nothing can be run
    critic_on_green: bool = False  # idle/night: one critique of a green result (weak tests, security)
    prompt_lang: Literal["en", "hu"] = "en"  # NK18: the internal language stays English until measured
    temperatures: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_TEMPERATURES))
    max_tokens: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_MAX_TOKENS))
    seed: int | None = 42
    budget: Budget | None = None  # None = MODE_BUDGETS[mode]

    def effective_budget(self) -> Budget:
        return self.budget or MODE_BUDGETS[self.mode]

    def rounds(self) -> int:
        return self.max_rounds if self.max_rounds is not None else self.effective_budget().repair_rounds


class RoleCallFailed(Exception):
    """A role turn gave no valid JSON even after the one JSON-fix request (02/04 §0)."""


class BudgetExceeded(Exception):
    """The session's budget (calls, output tokens or wall time) is used up."""


# ───────────────────────────── templates ─────────────────────────────

_PH = re.compile(r"\{\{(\w+)\}\}")


def render(template: str, **values: str) -> str:
    """Single-pass fill: a value that itself contains `{{x}}` (user code, Jinja…) is NOT re-expanded."""

    def sub(m: re.Match[str]) -> str:
        if m.group(1) not in values:
            raise KeyError(f"missing prompt value: {m.group(1)}")
        return values[m.group(1)]

    return _PH.sub(sub, template)


def data_block(text: str, tag: str) -> str:
    """Data inside <tag>…</tag> must not be able to close the tag (prompt injection, 09/02)."""
    return re.sub(rf"</\s*{re.escape(tag)}", f"&lt;/{tag}", text or "", flags=re.IGNORECASE)


# ───────────────────────────── transcript (02/02 §6) ─────────────────────────────


# Metadata the code itself writes (times, counters, ids, hashes): not checked by the privacy filter —
# an ISO timestamp like 2026-11-21 looks like a birth date to it and would redact every line.
_META_KEYS = frozenset({"sid", "step", "role", "t", "template", "model", "in_tok", "out_tok", "ms_first", "ms_prompt",
                        "ms_load", "ms_total", "attempts", "new_chars", "branch", "ok", "status", "passed", "failed",
                        "cmd", "rounds", "verified", "verdict", "budget_exceeded"})


def _content(data: dict[str, Any]) -> str:
    """The model/user-derived part of a transcript line, the only part the privacy filter must see."""
    rest = {k: v for k, v in data.items() if k not in _META_KEYS}
    out = rest.get("out")
    if isinstance(out, dict) and isinstance(out.get("files"), list):
        rest["out"] = {**out, "files": [f.get("path") for f in out["files"] if isinstance(f, dict)]}
    return json.dumps(rest, ensure_ascii=False, default=str) if rest else ""


class Transcript:
    """JSONL, one line per step. File contents are replaced by sha256; a line whose content the privacy
    filter flags is written as `{"redacted": true}` only (02/02 §6: personal data goes nowhere)."""

    def __init__(self, path: Path | None, sid: str) -> None:
        self.path, self.sid, self.step, self.lines = path, sid, 0, []
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, role: str, **data: Any) -> dict[str, Any]:
        self.step += 1
        line = {"sid": self.sid, "step": self.step, "role": role,
                "t": datetime.now(UTC).isoformat(timespec="seconds"), **data}
        text = json.dumps(line, ensure_ascii=False, default=str)
        if privacy.is_personal(_content(data)):
            line = {"sid": self.sid, "step": self.step, "role": role, "redacted": True}
            text = json.dumps(line)
        self.lines.append(line)
        if self.path is not None:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(text + "\n")
        return line


def hash_files(out: Any) -> Any:
    """Replace file contents with their sha256 (the transcript keeps no code, 02/02 §6)."""
    if not isinstance(out, dict):
        return out
    res = dict(out)
    if isinstance(res.get("files"), list):
        res["files"] = [{"path": f.get("path"), "sha256": hashlib.sha256(str(f.get("content", "")).encode()).hexdigest()[:16]}
                        for f in res["files"] if isinstance(f, dict)]
    return res


# ───────────────────────────── the session ─────────────────────────────


@dataclass
class TurnStats:
    role: str
    template: str
    prompt_tokens: int = 0
    prompt_ms: int = 0
    first_token_ms: int | None = None
    load_ms: int = 0
    out_tokens: int = 0
    total_ms: int = 0
    attempts: int = 1
    new_chars: int = 0  # characters appended for this turn: prompt_ms / new_chars shows the cache reuse


@dataclass
class RoleTurn:
    role: str
    data: dict[str, Any]
    stats: TurnStats


class RoleSession:
    """One thinking session: fixed model, fixed system prompt, append-only messages, shared budget."""

    def __init__(
        self,
        llm: LLMClient,
        scheduler: Scheduler,
        *,
        cfg: RolesConfig | None = None,
        model: str | None = None,
        priority: Priority = Priority.TASK,
        transcript_dir: Path | None = None,
        prompts_dir: Path = PROMPTS_DIR,
    ) -> None:
        self.cfg = cfg or RolesConfig()
        self.llm, self.scheduler, self.priority = llm, scheduler, priority
        self.model = model or SimpleRouter().chat_model()[0]  # code_model == chat_model in P1 (one model)
        self.budget = self.cfg.effective_budget()
        code = load_prompts(self.cfg.prompt_lang, prompts_dir, kind="code")
        self.templates = load_prompts(self.cfg.prompt_lang, prompts_dir, kind="roles")
        self.system = code.sections["system"]  # the T0 role-book, byte-identical to solve's session
        self.prompt_ver = f"{code.version}+{self.templates.version}"
        self.sid = f"th_{_b36(int(time.time()))}{secrets.token_hex(2)}"
        self.messages: list[dict[str, str]] = [{"role": "system", "content": self.system}]
        self.transcript = Transcript(transcript_dir / self.sid / "transcript.jsonl" if transcript_dir else None,
                                     self.sid)
        self.turns: list[TurnStats] = []
        self.llm_calls = 0
        self.out_tokens = 0
        self.t0 = time.monotonic()

    # ── budget ──
    def elapsed_s(self) -> float:
        return time.monotonic() - self.t0

    def budget_left(self) -> dict[str, float]:
        b = self.budget
        return {"llm_calls": b.llm_calls - self.llm_calls, "out_tokens": b.out_tokens - self.out_tokens,
                "wall_s": b.wall_s - self.elapsed_s()}

    def exhausted(self) -> bool:
        return any(v <= 0 for v in self.budget_left().values())

    # ── one role turn ──
    def message(self, template: str, **values: str) -> str:
        return render(self.templates.sections[template], **values)

    async def call(
        self,
        role: Role | str,
        template: str,
        schema: dict[str, Any],
        *,
        branch: bool = False,
        temperature: float | None = None,
        seed: int | None = None,
        **values: str,
    ) -> RoleTurn:
        """Render `template`, append it, ask the model for JSON. `branch=True` (voting): the turn is not
        kept in the conversation, so k samples see the same prefix. Raises RoleCallFailed,
        BudgetExceeded, Cancelled."""
        role = str(role)
        user = self.message(template, **values)
        if not user.lstrip().startswith(f"<szerep>{role}</szerep>"):
            raise ValueError(f"template {template!r} is not tagged for role {role}")
        msgs = list(self.messages) if branch else self.messages
        msgs.append({"role": "user", "content": user})
        st = TurnStats(role, template, new_chars=len(user))
        temp = self.cfg.temperatures.get(role, 0.2) if temperature is None else temperature
        num_predict = self.cfg.max_tokens.get(template, 600)
        seed = self.cfg.seed if seed is None else seed
        data: Any = None
        for attempt in range(2):
            if self.exhausted():
                self.transcript.write(role, template=template, budget_exceeded=self.budget_left())
                raise BudgetExceeded(template)
            async with self.scheduler.lease(self.priority, self.model) as lease:
                if lease.preempt.is_set():
                    raise Cancelled(f"preempted before {role}")
                reply = await chat_or_abort(self.llm, lease, msgs, format=schema, num_predict=num_predict,
                                            temperature=temp,
                                            options={"seed": seed} if seed is not None else None)
            s = reply.stats
            self.llm_calls += 1
            self.out_tokens += int(getattr(s, "eval_tokens", 0) or 0)
            st.attempts = attempt + 1
            st.prompt_tokens += int(getattr(s, "prompt_tokens", 0) or 0)
            st.prompt_ms += int(getattr(s, "prompt_ms", 0) or 0)
            st.load_ms += int(getattr(s, "load_ms", 0) or 0)
            st.out_tokens += int(getattr(s, "eval_tokens", 0) or 0)
            st.total_ms += int(getattr(s, "total_ms", 0) or 0)
            if st.first_token_ms is None:
                st.first_token_ms = getattr(s, "first_token_ms", None)
            msgs.append({"role": "assistant", "content": reply.text})
            data = _parse_json(reply.text)
            if isinstance(data, dict):
                break
            data = None
            if getattr(s, "done_reason", "") in ABORTED or attempt == 1:
                break  # a cut-off reply would be cut again; the second failure ends the turn
            msgs.append({"role": "user", "content": self.templates.sections["json_fix"]})
        self.turns.append(st)
        self.transcript.write(role, template=template, model=self.model, in_tok=st.prompt_tokens,
                              out_tok=st.out_tokens, ms_first=st.first_token_ms, ms_prompt=st.prompt_ms,
                              ms_load=st.load_ms, ms_total=st.total_ms, attempts=st.attempts,
                              new_chars=st.new_chars, branch=branch, ok=data is not None,
                              out=hash_files(data) if data is not None else None)
        if data is None:
            if not branch and msgs[-1]["role"] == "assistant":
                msgs[-1] = {"role": "assistant", "content": GARBAGE}  # loop2 lesson: garbage leaves the context
            raise RoleCallFailed(f"{role}/{template}: no valid JSON")
        return RoleTurn(role, data, st)

    def timings(self) -> list[dict[str, Any]]:
        """Per-turn costs for the prefix-switch measurement (02/01 §6.1)."""
        return [{"role": t.role, "template": t.template, "prompt_tokens": t.prompt_tokens, "prompt_ms": t.prompt_ms,
                 "first_token_ms": t.first_token_ms, "load_ms": t.load_ms, "out_tokens": t.out_tokens,
                 "total_ms": t.total_ms, "new_chars": t.new_chars, "attempts": t.attempts} for t in self.turns]
