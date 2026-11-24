"""OllamaProvider against a mocked Ollama (httpx.MockTransport) — no real server needed."""

from __future__ import annotations

import json

import httpx
import pytest

from auri_jarvis.mind.ollama_provider import ChatOptions, LLMError, OllamaProvider


def ndjson(*objs: dict) -> bytes:
    return ("\n".join(json.dumps(o) for o in objs) + "\n").encode()


DONE = {
    "done": True,
    "done_reason": "stop",
    "model": "m",
    "load_duration": 5_000_000,
    "prompt_eval_count": 42,
    "prompt_eval_duration": 300_000_000,
    "eval_count": 10,
    "eval_duration": 1_000_000_000,
}


def make(handler) -> OllamaProvider:
    return OllamaProvider({"model": "m", "num_predict_voice": 160}, transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_stream_yields_deltas_and_stats():
    seen: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen.update(json.loads(req.content))
        return httpx.Response(
            200,
            content=ndjson(
                {"message": {"role": "assistant", "content": "Szia"}, "done": False},
                {"message": {"role": "assistant", "content": "!"}, "done": False},
                {**DONE, "message": {"role": "assistant", "content": ""}},
            ),
        )

    p = make(handler)
    chunks = [c async for c in p.chat_stream([{"role": "user", "content": "hi"}])]
    await p.aclose()

    assert "".join(c.content for c in chunks) == "Szia!"
    final = chunks[-1]
    assert final.done and final.stats is not None
    assert final.stats.prompt_tokens == 42 and final.stats.prompt_ms == 300
    assert final.stats.tok_per_s == pytest.approx(10.0)
    assert final.stats.first_token_ms is not None
    # Voice defaults from config reach the request.
    assert seen["keep_alive"] == -1 and seen["think"] is False and seen["stream"] is True
    assert seen["options"]["num_predict"] == 160 and seen["options"]["num_ctx"] == 8192


@pytest.mark.asyncio
async def test_tool_calls_parsed_including_string_arguments():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=ndjson(
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "set_volume",
                                    "arguments": {"level": 30},
                                }
                            },
                            {
                                "function": {
                                    "name": "open_app",
                                    "arguments": '{"name": "vscode", "monitor": 2}',
                                }
                            },
                        ],
                    },
                    "done": False,
                },
                {**DONE, "message": {"role": "assistant", "content": ""}},
            ),
        )

    p = make(handler)
    text, calls, stats = await p.chat([{"role": "user", "content": "x"}], tools=[{"type": "function"}])
    await p.aclose()
    assert text == ""
    assert [(c.name, c.arguments) for c in calls] == [
        ("set_volume", {"level": 30}),
        ("open_app", {"name": "vscode", "monitor": 2}),
    ]
    assert stats.first_token_ms is not None  # a tool call counts as the first token


@pytest.mark.asyncio
async def test_missing_model_maps_to_hungarian_no_model_error():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": 'model "qwen3.5:4b" not found, try pulling it first'})

    p = make(handler)
    with pytest.raises(LLMError) as ei:
        await p.chat([{"role": "user", "content": "x"}], opts=ChatOptions(model="qwen3.5:4b"))
    await p.aclose()
    assert ei.value.kind == "no_model"
    assert "ollama pull qwen3.5:4b" in ei.value.user_message


@pytest.mark.asyncio
async def test_no_server_maps_to_no_server_error():
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=req)

    p = make(handler)
    with pytest.raises(LLMError) as ei:
        await p.chat([{"role": "user", "content": "x"}])
    await p.aclose()
    assert ei.value.kind == "no_server"
    assert "Ollamát" in ei.value.user_message


@pytest.mark.asyncio
async def test_think_unsupported_is_retried_without_think_once():
    bodies: list[dict] = []

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        bodies.append(body)
        if "think" in body:
            return httpx.Response(400, json={"error": '"m" does not support thinking'})
        return httpx.Response(
            200,
            content=ndjson({**DONE, "message": {"role": "assistant", "content": "ok"}}),
        )

    p = make(handler)
    text, _, _ = await p.chat([{"role": "user", "content": "x"}])
    text2, _, _ = await p.chat([{"role": "user", "content": "y"}])
    await p.aclose()
    assert text == "ok" and text2 == "ok"
    assert len(bodies) == 3  # first call retried once; the second call omits `think` up front
    assert "think" not in bodies[2]


@pytest.mark.asyncio
async def test_error_line_inside_stream_raises():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=ndjson({"error": "out of memory"}))

    p = make(handler)
    with pytest.raises(LLMError) as ei:
        await p.chat([{"role": "user", "content": "x"}])
    await p.aclose()
    assert ei.value.kind == "http"


@pytest.mark.asyncio
async def test_stream_without_done_is_an_error():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=ndjson({"message": {"content": "fél"}, "done": False}))

    p = make(handler)
    with pytest.raises(LLMError) as ei:
        await p.chat([{"role": "user", "content": "x"}])
    await p.aclose()
    assert ei.value.kind == "bad_response"


@pytest.mark.asyncio
async def test_warmup_uses_one_token():
    seen: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen.update(json.loads(req.content))
        return httpx.Response(200, content=ndjson({**DONE, "message": {"content": "."}}))

    p = make(handler)
    stats = await p.warmup([{"role": "system", "content": "prefix"}])
    await p.aclose()
    assert seen["options"]["num_predict"] == 1
    assert stats.prompt_tokens == 42
