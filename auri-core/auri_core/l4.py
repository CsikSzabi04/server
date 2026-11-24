"""L4 = the cloud (08/03), the bridge between the MIND loop and AI-3's `cloud.CloudClient` (owner: AI-1).

When the router answers 4 (L2/L3 failed, or Ollama is down; cloud_mode ≠ off; a live request):
- the cloud is used only with the user's consent for THIS request (`AskRequest.allow_cloud`), or in
  `auto_general` mode for a general chat without context (08/03 §2); guests and background work never;
- without consent the answer offers it (`cloud_offer`), nothing is sent;
- the client refuses personal data / secrets itself (`CloudRefusal.reason`, Hungarian) — shown as is;
- a cloud answer is a hypothesis: code is verified locally in the sandbox, nothing from the cloud is
  learned (08/03 §7: whether the terms allow storing outputs is still open);
- a cloud call never takes the Ollama lane (a voice turn must not wait for Groq).
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from .contracts import AskRequest, LLMReply, LLMStats, Priority, Scope

CLOUD_LABEL = "cloud"  # the model name of the L4 attempt until the client says which provider answered
MAX_CALLS = 2  # one generation + at most one JSON-fix request, like a local attempt (02/04 §0)


@dataclass(frozen=True)
class CloudGate:
    """What the caller may do with the cloud for one request."""

    client: Any  # cloud.CloudClient (AI-3)
    user_id: str | None
    consent: bool  # the user allowed the cloud for this request (or auto_general + general chat)
    live: bool = True  # a live request (VOICE/CHAT); background / long tasks never go to the cloud

    @property
    def configured(self) -> bool:
        return self.client is not None and bool(getattr(self.client, "enabled", False))

    @property
    def usable(self) -> bool:
        return self.configured and self.live and self.consent and self.user_id is not None


def make_gate(client: Any, req: AskRequest, scope: Scope) -> CloudGate | None:
    """None when the cloud is not possible at all for this caller (no client, guest)."""
    if client is None or scope.identity != "user" or not scope.user_id:
        return None
    mode = getattr(getattr(client, "cfg", None), "cloud_mode", "off")
    general = req.mode == "chat" and not any(c.strip() for c in req.context) and req.task is None
    consent = bool(req.allow_cloud) or (mode == "auto_general" and general)
    return CloudGate(client, scope.user_id, consent, live=req.priority >= Priority.CHAT)


class CloudRefused(Exception):
    """The client did not send (off, quota, personal data, secret, …); `user_message` is its reason."""

    def __init__(self, reason: str, kind: str) -> None:
        super().__init__(kind)
        self.user_message = reason
        self.kind = kind


def _is_answer(r: Any) -> bool:
    return getattr(r, "provenance", None) is not None


def canonical_files(text: str) -> str:
    """Ollama enforces the answer schema by grammar (`format`); a cloud model only reads the prompt, and
    gpt-oss-120b regularly answers `{"files": {"solution.py": "<code>"}}` instead of the schema's
    `{"files": [{"path": …, "content": …}]}` — correct code in another shape (measured 2026-11-24, 3 of 8).
    That one alternative shape is rewritten to the schema shape; everything else is returned untouched, so the
    local loop (`pick_solution`) stays strict and the sandbox still decides."""
    from .solve import _parse_json

    data = _parse_json(text)
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, dict) or not files or not all(isinstance(k, str) and isinstance(v, str) for k, v in files.items()):
        return text
    return json.dumps({**data, "files": [{"path": k, "content": v} for k, v in files.items()]}, ensure_ascii=False)


class CloudLLM:
    """The `LLMClient` shape over `CloudClient.chat`, so the P0 loop can run one L4 attempt unchanged.
    The lease is ignored (see NoLane); `format`/`num_predict`/`options` are Ollama-only and dropped."""

    def __init__(self, gate: CloudGate, *, purpose: str, max_calls: int = MAX_CALLS) -> None:
        self.gate, self.purpose, self.max_calls = gate, purpose, max_calls
        self.calls = 0
        self.answer: Any = None  # the last CloudAnswer
        self.refusal: Any = None  # the CloudRefusal, if the client refused

    async def chat(self, lease: Any, messages: list[dict[str, str]], *, format: Any = None, **_: Any) -> LLMReply:
        if self.calls >= self.max_calls:
            raise CloudRefused("egy felhős próbálkozás kérésenként", "cap")
        self.calls += 1
        r = await self.gate.client.chat(messages, purpose=self.purpose, interactive=True, user_id=self.gate.user_id)
        if not _is_answer(r):
            self.refusal = r
            raise CloudRefused(str(getattr(r, "reason", "a felhő nem válaszolt")), str(getattr(r, "kind", "")))
        self.answer = r
        text = canonical_files(r.text) if isinstance(format, dict) and "files" in format.get("properties", {}) else r.text
        return LLMReply(text, LLMStats(model=r.provenance, done_reason="stop"))

    @property
    def provenance(self) -> str | None:
        return getattr(self.answer, "provenance", None)


@dataclass
class _FreeLease:
    prio: Any
    model: str
    preempt: Any = None
    wait_ms: int = 0

    def __post_init__(self) -> None:
        import asyncio

        self.preempt = asyncio.Event()  # never set: nothing local waits for this "lane"


class NoLane:
    """A scheduler stand-in for cloud calls: they do not use (or block) the one Ollama lane."""

    @contextlib.asynccontextmanager
    async def lease(self, prio: Any, model: str) -> AsyncIterator[_FreeLease]:
        yield _FreeLease(prio, model)


def offer_text(why: str = "") -> str:
    tail = f" ({why})" if why else ""
    return ("A felhő (L4) segíthetne, de csak a hozzájárulásoddal megy ki bármi: küldd újra a kérést "
            f"felhő-engedéllyel (allow_cloud). Személyes adatot és titkot akkor sem küldök.{tail}")


def shown_by(provenance: str) -> str:
    """'cloud:groq:openai/gpt-oss-120b' → 'groq · openai/gpt-oss-120b' (08/03 §1: visible)."""
    parts = provenance.split(":", 2)
    return " · ".join(parts[1:]) if len(parts) == 3 else provenance
