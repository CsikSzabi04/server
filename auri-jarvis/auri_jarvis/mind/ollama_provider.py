"""Ollama chat provider — streaming, tool calls, keep_alive, think (AI-2 / MIND).

Talks to the Ollama REST API (`POST /api/chat`, NDJSON stream) with httpx instead of
the `ollama` client: same wire protocol, one dependency less, and the transport can be
mocked in unit tests. Spec: jarvis_reboot_to_auri.md 3.4 + 5.5.

Errors surface as `LLMError` with a Hungarian `user_message` that is safe to speak or
show on the HUD (never contains secrets).
"""

from __future__ import annotations

import contextlib
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:11434"


class LLMError(RuntimeError):
    """A provider failure with a user-facing Hungarian message."""

    def __init__(self, kind: str, user_message: str, detail: str = "") -> None:
        super().__init__(f"{kind}: {detail or user_message}")
        self.kind = kind  # no_server | no_model | timeout | http | bad_response
        self.user_message = user_message
        self.detail = detail


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMStats:
    model: str = ""
    first_token_ms: int | None = None  # request start → first content/tool-call token
    load_ms: int = 0  # model load (cold start)
    # Ollama counts the WHOLE prompt here, cached prefix included (measured 2026-11-20:
    # 430 tokens both cold and warm). A cache hit shows up in `prompt_ms` instead
    # (gemma2:2b, 430 tokens: 2993 ms cold vs 151 ms warm).
    prompt_tokens: int = 0
    prompt_ms: int = 0
    eval_tokens: int = 0
    eval_ms: int = 0
    total_ms: int = 0  # wall clock of the whole request
    done_reason: str = ""

    @property
    def tok_per_s(self) -> float:
        return self.eval_tokens / (self.eval_ms / 1000) if self.eval_ms > 0 else 0.0


@dataclass
class LLMChunk:
    content: str = ""
    thinking: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    done: bool = False
    stats: LLMStats | None = None  # only on the final chunk


@dataclass(frozen=True)
class ChatOptions:
    """Per-request overrides; None = take the value from the `llm` config section."""

    model: str | None = None
    num_predict: int | None = None
    num_ctx: int | None = None
    temperature: float | None = None
    think: bool | None = None
    keep_alive: int | str | None = None
    format: dict[str, Any] | str | None = None  # Ollama structured output: a JSON schema or "json"


def _ns_to_ms(v: Any) -> int:
    return int(v) // 1_000_000 if isinstance(v, (int, float)) else 0


def _parse_tool_calls(raw: Any) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for tc in raw or []:
        fn = (tc or {}).get("function") or {}
        name = fn.get("name")
        if not isinstance(name, str) or not name:
            continue
        args = fn.get("arguments") or {}
        if isinstance(args, str):  # some templates return a JSON string
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {"_raw": args}
        calls.append(ToolCall(name=name, arguments=args if isinstance(args, dict) else {}))
    return calls


class OllamaProvider:
    """`chat_stream(messages, tools, opts)` per spec 5.5; one instance per daemon."""

    def __init__(
        self,
        llm_cfg: dict[str, Any] | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        cfg = llm_cfg or {}
        self.base_url = str(cfg.get("base_url") or DEFAULT_BASE_URL).rstrip("/")
        self.model = str(cfg.get("model") or "qwen3.5:4b")
        self.num_ctx = int(cfg.get("num_ctx") or 8192)
        self.num_predict = int(cfg.get("num_predict_voice") or 160)
        self.temperature = float(cfg.get("temperature") if cfg.get("temperature") is not None else 0.6)
        self.think = bool(cfg.get("think", False))
        self.keep_alive: int | str = cfg.get("keep_alive", -1)
        timeout = httpx.Timeout(
            float(cfg.get("request_timeout_s") or 120),
            connect=float(cfg.get("connect_timeout_s") or 3),
        )
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout, transport=transport)
        # Models that rejected the `think` field (older/non-thinking templates) → omit it.
        self._no_think: set[str] = set()

    # ── public API ───────────────────────────────────────────────────────────
    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        opts: ChatOptions | None = None,
    ) -> AsyncIterator[LLMChunk]:
        """Stream a chat completion. Yields content/thinking/tool-call chunks, then a
        final chunk with `done=True` and `stats`. Raises `LLMError`."""
        o = opts or ChatOptions()
        model = o.model or self.model
        body = self._body(model, messages, tools, o)
        # aclosing: if the consumer stops early (barge-in), the HTTP stream is closed NOW,
        # which makes Ollama stop generating — not whenever the GC finalises the generator.
        try:
            async with contextlib.aclosing(self._stream(model, body)) as stream:
                async for chunk in stream:
                    yield chunk
        except LLMError as e:
            # Retry once without `think` if the model's template doesn't support it.
            if "think" in body and "think" in e.detail.lower() and model not in self._no_think:
                self._no_think.add(model)
                body.pop("think", None)
                async with contextlib.aclosing(self._stream(model, body)) as stream:
                    async for chunk in stream:
                        yield chunk
            else:
                raise

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        opts: ChatOptions | None = None,
    ) -> tuple[str, list[ToolCall], LLMStats]:
        """Non-streaming convenience: collect the whole answer."""
        text: list[str] = []
        calls: list[ToolCall] = []
        stats = LLMStats()
        async for ch in self.chat_stream(messages, tools, opts):
            text.append(ch.content)
            calls.extend(ch.tool_calls)
            if ch.stats:
                stats = ch.stats
        return "".join(text), calls, stats

    async def warmup(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
    ) -> LLMStats:
        """Load the model and prefill the static prefix so the KV cache is hot."""
        _, _, stats = await self.chat(messages, tools, ChatOptions(model=model, num_predict=1, temperature=0.0))
        return stats

    async def list_models(self) -> list[str]:
        data = await self._get_json("/api/tags")
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]

    async def loaded_models(self) -> list[dict[str, Any]]:
        """`/api/ps`: currently loaded models with `size` / `size_vram` (bytes)."""
        data = await self._get_json("/api/ps")
        return list(data.get("models", []))

    async def has_model(self, name: str) -> bool:
        names = await self.list_models()
        base = name if ":" in name else f"{name}:latest"
        return name in names or base in names

    async def unload(self, model: str | None = None) -> None:
        """Free the model's RAM now (keep_alive 0) — e.g. before loading the smart model."""
        try:
            r = await self._client.post("/api/generate", json={"model": model or self.model, "keep_alive": 0})
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise self._map_error(e, model or self.model) from e

    async def aclose(self) -> None:
        await self._client.aclose()

    # ── internals ────────────────────────────────────────────────────────────
    def _body(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        o: ChatOptions,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "keep_alive": o.keep_alive if o.keep_alive is not None else self.keep_alive,
            "options": {
                "num_ctx": o.num_ctx or self.num_ctx,
                "num_predict": o.num_predict or self.num_predict,
                "temperature": o.temperature if o.temperature is not None else self.temperature,
            },
        }
        if tools:
            body["tools"] = tools
        if o.format is not None:
            body["format"] = o.format
        if model not in self._no_think:
            body["think"] = o.think if o.think is not None else self.think
        return body

    async def _stream(self, model: str, body: dict[str, Any]) -> AsyncIterator[LLMChunk]:
        t0 = time.perf_counter()
        first_ms: int | None = None
        try:
            async with self._client.stream("POST", "/api/chat", json=body) as r:
                if r.status_code >= 400:
                    detail = (await r.aread()).decode("utf-8", "replace")
                    raise self._http_error(r.status_code, detail, model)
                async for line in r.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        j = json.loads(line)
                    except json.JSONDecodeError as e:
                        raise LLMError(
                            "bad_response",
                            "Érthetetlen választ kaptam a modelltől.",
                            line[:200],
                        ) from e
                    if "error" in j:
                        raise self._http_error(500, str(j["error"]), model)
                    msg = j.get("message") or {}
                    content = msg.get("content") or ""
                    thinking = msg.get("thinking") or ""
                    calls = _parse_tool_calls(msg.get("tool_calls"))
                    if first_ms is None and (content or calls):
                        first_ms = int((time.perf_counter() - t0) * 1000)
                    if j.get("done"):
                        stats = LLMStats(
                            model=str(j.get("model") or model),
                            first_token_ms=first_ms,
                            load_ms=_ns_to_ms(j.get("load_duration")),
                            prompt_tokens=int(j.get("prompt_eval_count") or 0),
                            prompt_ms=_ns_to_ms(j.get("prompt_eval_duration")),
                            eval_tokens=int(j.get("eval_count") or 0),
                            eval_ms=_ns_to_ms(j.get("eval_duration")),
                            total_ms=int((time.perf_counter() - t0) * 1000),
                            done_reason=str(j.get("done_reason") or ""),
                        )
                        yield LLMChunk(
                            content=content,
                            thinking=thinking,
                            tool_calls=calls,
                            done=True,
                            stats=stats,
                        )
                        return
                    if content or thinking or calls:
                        yield LLMChunk(content=content, thinking=thinking, tool_calls=calls)
        except httpx.HTTPError as e:
            raise self._map_error(e, model) from e
        raise LLMError(
            "bad_response",
            "A modell válasza félbeszakadt.",
            "stream ended without done",
        )

    async def _get_json(self, path: str) -> dict[str, Any]:
        try:
            r = await self._client.get(path)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            raise self._map_error(e, self.model) from e

    @staticmethod
    def _http_error(status: int, detail: str, model: str) -> LLMError:
        try:
            detail = str(json.loads(detail).get("error", detail))
        except (json.JSONDecodeError, AttributeError):
            pass
        low = detail.lower()
        if status == 404 or ("not found" in low and "model" in low):
            return LLMError(
                "no_model",
                f"A(z) {model} modell nincs letöltve. Futtasd ezt: ollama pull {model}",
                detail[:300],
            )
        return LLMError("http", "Hiba történt a nyelvi modellnél.", f"HTTP {status}: {detail[:300]}")

    @staticmethod
    def _map_error(e: httpx.HTTPError, model: str) -> LLMError:
        if isinstance(e, LLMError):  # pragma: no cover — defensive
            return e
        if isinstance(e, httpx.ConnectError):
            return LLMError("no_server", "Nem érem el az Ollamát. Fut a háttérben?", str(e))
        if isinstance(e, httpx.TimeoutException):
            return LLMError("timeout", "A nyelvi modell nem válaszolt időben.", type(e).__name__)
        if isinstance(e, httpx.HTTPStatusError):
            return OllamaProvider._http_error(e.response.status_code, e.response.text, model)
        return LLMError("http", "Hiba történt a nyelvi modellnél.", f"{type(e).__name__}: {e}")
