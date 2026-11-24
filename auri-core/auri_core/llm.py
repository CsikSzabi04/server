"""Ollama client for the Core (owner: AI-3).

Built on the Jarvis provider (`auri_jarvis.mind.ollama_provider`, imported, never modified):
streaming, `format` (JSON / JSON schema), `keep_alive`, cancellation (closing the stream
stops Ollama), per-call statistics and Hungarian error messages (`LLMError.user_message`).

The gate: every call takes a `Lease` from `scheduler.lease()`; without an active lease for
the same model the call raises `LeaseError` before any network I/O.

    async with scheduler.lease(Priority.TASK, cfg.models.code) as lease:
        res = await client.chat(lease, [{"role": "user", "content": "…"}])
        data, res = await client.chat_json(lease, messages, schema={...})
"""

from __future__ import annotations

import contextlib
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx
from auri_jarvis.mind.ollama_provider import ChatOptions, LLMChunk, LLMError, LLMStats, OllamaProvider

from .config import Config, load_config
from .scheduler import Lease

__all__ = ["ChatResult", "ClientStats", "LLMChunk", "LLMError", "LLMStats", "OllamaClient", "parse_json"]


@dataclass
class ChatResult:
    text: str
    stats: LLMStats
    thinking: str = ""


@dataclass
class ClientStats:
    """Running totals for one client (the solve() journal and bench read these)."""

    calls: int = 0
    errors: int = 0
    prompt_tokens: int = 0
    eval_tokens: int = 0
    total_ms: int = 0
    json_ok: int = 0
    json_bad: int = 0
    per_model: dict[str, int] = field(default_factory=dict)

    def add(self, s: LLMStats) -> None:
        self.calls += 1
        self.prompt_tokens += s.prompt_tokens
        self.eval_tokens += s.eval_tokens
        self.total_ms += s.total_ms
        self.per_model[s.model] = self.per_model.get(s.model, 0) + 1


def parse_json(text: str) -> Any | None:
    """Parse a model's JSON answer; tolerates a ```json fence. None if invalid."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        t = t.rsplit("```", 1)[0]
    try:
        return json.loads(t)
    except (json.JSONDecodeError, ValueError):
        return None


class OllamaClient:
    """One per process. `transport` lets tests mock Ollama (httpx.MockTransport)."""

    def __init__(self, cfg: Config | None = None, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.cfg = cfg or load_config()
        self._provider = _CoreProvider(
            {
                "base_url": self.cfg.ollama_url,
                "model": self.cfg.models.code,
                "num_ctx": self.cfg.num_ctx,
                "num_predict_voice": 1024,  # Core default; voice limits are Jarvis's business
                "temperature": 0.2,
                "think": False,
                "keep_alive": self.cfg.keep_alive,
                "request_timeout_s": self.cfg.request_timeout_s,
                "connect_timeout_s": self.cfg.connect_timeout_s,
            },
            transport=transport,
        )
        self._http = httpx.AsyncClient(
            base_url=self.cfg.ollama_url,
            timeout=httpx.Timeout(self.cfg.request_timeout_s, connect=self.cfg.connect_timeout_s),
            transport=transport,
        )
        self.stats = ClientStats()

    # ── chat ─────────────────────────────────────────────────────────────────
    async def chat_stream(
        self,
        lease: Lease,
        messages: list[dict[str, Any]],
        *,
        format: dict[str, Any] | str | None = None,
        num_predict: int | None = None,
        temperature: float | None = None,
        num_ctx: int | None = None,
        keep_alive: int | str | None = None,
        think: bool | None = None,
        options: dict[str, Any] | None = None,
    ) -> AsyncIterator[LLMChunk]:
        """Stream on `lease.model`. Stop early by breaking out / closing the generator:
        the HTTP stream is closed at once, so Ollama stops generating (cancellation)."""
        lease.check()
        opts = CoreChatOptions(
            model=lease.model,
            num_predict=num_predict,
            num_ctx=num_ctx,
            temperature=temperature,
            think=think,
            keep_alive=keep_alive,
            format=format,
            extra=tuple((options or {}).items()),
        )
        try:
            async with contextlib.aclosing(self._provider.chat_stream(messages, None, opts)) as stream:
                async for ch in stream:
                    if ch.done and ch.stats:
                        self.stats.add(ch.stats)
                    yield ch
        except LLMError:
            self.stats.errors += 1
            raise

    async def chat(self, lease: Lease, messages: list[dict[str, Any]], **kw: Any) -> ChatResult:
        text: list[str] = []
        thinking: list[str] = []
        stats = LLMStats(model=lease.model)
        async for ch in self.chat_stream(lease, messages, **kw):
            text.append(ch.content)
            thinking.append(ch.thinking)
            if ch.stats:
                stats = ch.stats
        return ChatResult(text="".join(text), stats=stats, thinking="".join(thinking))

    async def chat_json(
        self, lease: Lease, messages: list[dict[str, Any]], *, schema: dict[str, Any] | None = None, **kw: Any
    ) -> tuple[Any | None, ChatResult]:
        """Structured output: `format=schema` (or "json"). Returns (parsed | None, raw result)."""
        res = await self.chat(lease, messages, format=schema if schema is not None else "json", **kw)
        data = parse_json(res.text)
        if data is None:
            self.stats.json_bad += 1
        else:
            self.stats.json_ok += 1
        return data, res

    # ── embeddings (NK14 g; store search, P1) ───────────────────────────────
    async def embed(self, lease: Lease, texts: list[str], *, keep_alive: int | str = "1m") -> list[list[float]]:
        lease.check()
        t0 = time.perf_counter()
        try:
            r = await self._http.post("/api/embed", json={"model": lease.model, "input": texts, "keep_alive": keep_alive})
            if r.status_code >= 400:
                raise OllamaProvider._http_error(r.status_code, r.text, lease.model)
            data = r.json()
        except httpx.HTTPError as e:
            self.stats.errors += 1
            raise OllamaProvider._map_error(e, lease.model) from e
        self.stats.add(LLMStats(model=lease.model, total_ms=int((time.perf_counter() - t0) * 1000)))
        return [list(map(float, v)) for v in data.get("embeddings", [])]

    # ── housekeeping (no lane needed: no generation) ─────────────────────────
    async def list_models(self) -> list[str]:
        return await self._provider.list_models()

    async def loaded_models(self) -> list[dict[str, Any]]:
        return await self._provider.loaded_models()

    async def unload(self, model: str) -> None:
        await self._provider.unload(model)

    async def aclose(self) -> None:
        await self._provider.aclose()
        await self._http.aclose()


@dataclass(frozen=True)
class CoreChatOptions(ChatOptions):
    """ChatOptions plus raw Ollama `options` keys (e.g. `num_thread`, `seed`)."""

    extra: tuple[tuple[str, Any], ...] = ()


class _CoreProvider(OllamaProvider):
    """The Jarvis provider, subclassed (not modified) to pass extra Ollama options."""

    def _body(self, model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None, o: ChatOptions) -> dict[str, Any]:
        body = super()._body(model, messages, tools, o)
        if isinstance(o, CoreChatOptions) and o.extra:
            body["options"].update(dict(o.extra))
        return body
