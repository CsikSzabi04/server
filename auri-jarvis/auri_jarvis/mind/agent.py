"""Agent loop (AI-2, spec 5.5): LLM + tools, at most `max_rounds` tool rounds.

- Text is released sentence by sentence (the Mouth synthesises per sentence anyway, so
  this costs no latency) and every sentence passes the HALLUCINATION GUARD: a sentence that
  claims an action ("megnyitottam", "beállítottam", …) while no tool succeeded in this turn
  is never spoken; the turn ends with an honest sentence instead. Tool results are the truth.
- A `confirm` tool never runs here: the registry returns needs_confirm, the question is
  spoken, and the Mind keeps it as a pending action for the next turn ("igen" → run).
- Every message of the turn (assistant tool calls, tool results, final answer) is recorded
  verbatim in `turn_messages`, so the session history can be replayed byte-for-byte and the
  next request resumes the KV cache (see prompts.SEED_REQUEST).
"""

from __future__ import annotations

import contextlib
import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from ..tools.registry import ToolContext, ToolRegistry, ToolResult
from .ollama_provider import ChatOptions, LLMStats, OllamaProvider

log = logging.getLogger(__name__)

# Past-tense, first-person action CLAIMS (HU + EN), matched per sentence. Present tense
# ("megnyitom" = I'll open it) is an intention that small models say alongside the tool
# call, so it is allowed; only "I did it" without a successful tool is blocked.
CLAIM = re.compile(
    r"\b(?:megnyitottam|elindítottam|beállítottam|átállítottam|bezártam|zároltam|lezártam|"
    r"elmentettem|feljegyeztem|megjegyeztem|áttettem|áthelyeztem|lenémítottam|némítottam|"
    r"kikapcsoltam|bekapcsoltam|töröltem|létrehoztam|elküldtem|megcsináltam|elintéztem|"
    r"lejátszottam|elindult|megnyílt|i(?:'ve| have) (?:opened|set|closed|started)|opened|launched)\b",
    re.IGNORECASE,
)
NO_ACTION = "Ezt nem tudtam megcsinálni, mert nem volt hozzá sikeres műveletem."
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+|\n+")
MAX_SENTENCE = 220


@dataclass
class AgentResult:
    text: str = ""  # what was spoken / shown
    turn_messages: list[dict[str, Any]] = field(default_factory=list)  # verbatim, for the session
    ok_tools: list[str] = field(default_factory=list)
    pending: ToolResult | None = None  # needs_confirm result, if the turn ended in a question
    stats: LLMStats | None = None
    first_ms: int | None = None
    guarded: bool = False  # the hallucination guard replaced the rest of the answer


def _split_ready(buf: str) -> tuple[list[str], str]:
    """Complete sentences out of the buffer; the unfinished tail stays."""
    parts = SENTENCE_END.split(buf)
    if len(parts) == 1:
        if len(buf) > MAX_SENTENCE and " " in buf[:MAX_SENTENCE]:
            cut = buf.rfind(" ", 0, MAX_SENTENCE)
            return [buf[:cut]], buf[cut + 1 :]
        return [], buf
    return [p for p in parts[:-1] if p.strip()], parts[-1]


async def run_agent(
    *,
    provider: OllamaProvider,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    registry: ToolRegistry,
    ctx: ToolContext,
    opts: ChatOptions,
    max_rounds: int,
    result: AgentResult,
) -> AsyncIterator[str]:
    """Yields speakable text chunks (whole sentences). `messages` = the full prompt (it is
    extended in place with this turn's tool round trips); `result` collects the outcome."""
    spoken: list[str] = []

    def guard(sentence: str) -> bool:
        if not result.ok_tools and CLAIM.search(sentence):
            log.info("agent: hallucination guard blocked an action claim")
            result.guarded = True
            return False
        return True

    def _say(s: str) -> None:
        # Update before yielding: on barge-in the generator is closed AT the yield, and the
        # Mind must still know what was actually said.
        spoken.append(s)
        result.text = " ".join(spoken)

    for rnd in range(max_rounds + 1):
        use_tools = tools if (tools and rnd < max_rounds) else None
        buf = ""
        round_text: list[str] = []
        calls: list[Any] = []
        blocked = False
        # aclosing: on barge-in the HTTP stream closes immediately (Ollama stops generating).
        async with contextlib.aclosing(provider.chat_stream(messages, use_tools, opts)) as stream:
            async for ch in stream:
                if ch.tool_calls:
                    calls.extend(ch.tool_calls)
                if ch.done and ch.stats:
                    result.stats = ch.stats
                    if result.first_ms is None:
                        result.first_ms = ch.stats.first_token_ms
                if not ch.content or blocked:
                    continue
                round_text.append(ch.content)
                buf += ch.content
                ready, buf = _split_ready(buf)
                for s in ready:
                    if not guard(s):
                        blocked = True
                        break
                    _say(s.strip())
                    yield s.strip() + " "
        if not blocked and buf.strip() and not calls:
            if guard(buf):
                _say(buf.strip())
                yield buf.strip()
            else:
                blocked = True
        if blocked:
            _say(NO_ACTION)
            yield NO_ACTION
            result.text = " ".join(spoken)
            result.turn_messages.append({"role": "assistant", "content": result.text})
            return

        if not calls:
            text = "".join(round_text)
            result.turn_messages.append({"role": "assistant", "content": text})
            result.text = " ".join(spoken)
            return

        # ── tool round ────────────────────────────────────────────────────────
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": "".join(round_text),
            "tool_calls": [{"function": {"name": c.name, "arguments": c.arguments}} for c in calls],
        }
        messages.append(assistant_msg)
        result.turn_messages.append(assistant_msg)
        for c in calls:
            res = await registry.call(c.name, c.arguments, ctx)
            if res.status == "needs_confirm":
                result.pending = res
                _say(res.message)
                yield res.message
                result.text = " ".join(spoken)
                # Record a plain answer so the session stays a valid chat transcript.
                tool_msg = {"role": "tool", "content": res.for_llm(), "tool_name": c.name}
                result.turn_messages.append(tool_msg)
                result.turn_messages.append({"role": "assistant", "content": res.message})
                return
            if res.ok:
                result.ok_tools.append(c.name)
            tool_msg = {"role": "tool", "content": res.for_llm(), "tool_name": c.name}
            messages.append(tool_msg)
            result.turn_messages.append(tool_msg)
        # Some small models stop after the tool call; the next round lets them speak.
    result.text = " ".join(spoken)
