"""Small JSON-call helper for the planner: lease → preempt check → schema-constrained chat → parse,
with at most one JSON-fix request (02/04 §0). Also the prompt-template loader (`### section` format).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..contracts import ABORTED, Cancelled, LLMClient, Priority, Scheduler, chat_or_abort

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
EventSink = Callable[[str, dict[str, Any]], None]


@dataclass(frozen=True)
class Prompts:
    sections: dict[str, str]
    version: str

    def render(self, name: str, **values: str) -> str:
        """Fill the template's own placeholders; a value (user text) may itself contain braces."""
        text = self.sections[name]
        missing = set(_PLACEHOLDER.findall(text)) - set(values)
        if missing:
            raise ValueError(f"unfilled placeholder(s) in prompt '{name}': {sorted(missing)}")
        return _PLACEHOLDER.sub(lambda m: values[m.group(1)], text)


def load_prompts(lang: str = "en", *, kind: str = "planner", directory: Path = PROMPTS_DIR) -> Prompts:
    raw = (directory / f"{kind}.{lang}.txt").read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    name = None
    for line in raw.splitlines(keepends=True):
        if line.startswith("### "):
            name = line[4:].strip()
            sections[name] = ""
        elif name is not None:
            sections[name] += line
    sections = {k: v.strip("\n") for k, v in sections.items()}
    return Prompts(sections, f"{kind}.{lang}:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12])


def parse_json(text: str) -> Any | None:
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except (json.JSONDecodeError, ValueError):
        return None


@dataclass
class LLMSession:
    """One planning conversation on one model; counts calls and tokens."""

    llm: LLMClient
    scheduler: Scheduler
    model: str
    prompts: Prompts
    priority: Priority = Priority.TASK
    on_event: EventSink | None = None
    seed: int = 42
    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    ms: int = 0
    messages: list[dict[str, str]] = field(default_factory=list)

    def _emit(self, event: str, **data: Any) -> None:
        if self.on_event is not None:
            self.on_event(event, data)

    async def _chat(self, schema: dict[str, Any], num_predict: int, temperature: float) -> tuple[str, str | None]:
        async with self.scheduler.lease(self.priority, self.model) as lease:
            if lease.preempt.is_set():
                raise Cancelled("preempted before the call")
            reply = await chat_or_abort(self.llm, lease, self.messages, format=schema, num_predict=num_predict,
                                        temperature=temperature, options={"seed": self.seed})
        s = reply.stats
        self.calls += 1
        self.tokens_in += s.prompt_tokens
        self.tokens_out += s.eval_tokens
        self.ms += s.total_ms
        self.messages.append({"role": "assistant", "content": reply.text})
        self._emit("llm", model=self.model, tokens_in=s.prompt_tokens, tokens_out=s.eval_tokens, ms=s.total_ms,
                   done_reason=s.done_reason)
        return reply.text, s.done_reason

    async def json_call(self, user_msg: str, schema: dict[str, Any], *, num_predict: int,
                        temperature: float = 0.0) -> Any | None:
        """Append `user_msg`, ask for JSON; one JSON-fix request on invalid (not cut-off) output."""
        self.messages.append({"role": "user", "content": user_msg})
        for attempt in range(2):
            text, done_reason = await self._chat(schema, num_predict, temperature)
            data = parse_json(text)
            if isinstance(data, dict):
                return data
            if done_reason in ABORTED:  # cut off / repetition abort: a fix request would end the same way
                self._emit("truncated", num_predict=num_predict)
                break
            if attempt == 0:
                self.messages.append({"role": "user", "content": self.prompts.render("json_fix")})
        if self.messages and self.messages[-1]["role"] == "assistant":
            self.messages[-1] = {"role": "assistant", "content": "(unusable reply removed)"}
        return None
