"""Tests for llm_client.py.

Uses httpx.MockTransport (Week 5 §4.3's pattern) to replace the real
Anthropic API with a function this test file controls. No real network
call, no real API key, and — unlike the injected-`generate` stub pattern
used everywhere else in this course — this is the first place the actual
HTTP request/response handling itself gets tested, not just the code that
calls a `generate` function.
"""

from __future__ import annotations

import json

import httpx
import pytest

from ai_finance_course.llm_client import LLMResponseError, call_llm


def test_call_llm_returns_text_from_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": [{"type": "text", "text": "Hello!"}]})

    result = call_llm(
        "Hi", api_key="test-key", model="test-model", transport=httpx.MockTransport(handler)
    )

    assert result == "Hello!"


def test_call_llm_finds_text_block_after_other_block_types() -> None:
    """Some models return a thinking block before the text block — content[0] would be wrong."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "content": [
                    {"type": "thinking", "thinking": "reasoning..."},
                    {"type": "text", "text": "The answer."},
                ]
            },
        )

    result = call_llm(
        "Hi", api_key="test-key", model="test-model", transport=httpx.MockTransport(handler)
    )

    assert result == "The answer."


def test_call_llm_raises_when_no_text_block() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": [{"type": "thinking", "thinking": "..."}]})

    with pytest.raises(LLMResponseError):
        call_llm("Hi", api_key="test-key", model="test-model", transport=httpx.MockTransport(handler))


def test_call_llm_raises_on_http_error_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid api key"}})

    with pytest.raises(httpx.HTTPStatusError):
        call_llm("Hi", api_key="bad-key", model="test-model", transport=httpx.MockTransport(handler))


def test_call_llm_sends_correct_request_shape() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})

    call_llm(
        "What is 2+2?",
        api_key="my-key",
        model="claude-test",
        max_tokens=256,
        transport=httpx.MockTransport(handler),
    )

    assert captured["headers"]["x-api-key"] == "my-key"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert captured["body"]["model"] == "claude-test"
    assert captured["body"]["max_tokens"] == 256
    assert captured["body"]["messages"] == [{"role": "user", "content": "What is 2+2?"}]


def test_call_llm_uses_env_vars_when_not_passed_explicitly(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "env-key")
    monkeypatch.setenv("LLM_MODEL", "env-model")
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})

    call_llm("Hi", transport=httpx.MockTransport(handler))

    assert captured["headers"]["x-api-key"] == "env-key"
    assert captured["body"]["model"] == "env-model"
