"""A reusable, testable Claude API client.

Every example script since Week 6 has copy-pasted the same ~20 lines: a
direct httpx POST to Anthropic's Messages API, no SDK. This module
extracts that pattern once, and — unlike the copy-pasted versions — is
actually testable, using the same transport-injection technique Week 5
used for EdgarClient (httpx.MockTransport replaces the real network with
a function you control, so tests never need a real API key).
"""

from __future__ import annotations

import os

import httpx

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


class LLMResponseError(Exception):
    """Raised when Anthropic's response has no text content block."""


def call_llm(
    prompt: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
    transport: httpx.BaseTransport | None = None,
) -> str:
    """Call Anthropic's Messages API directly via httpx (no SDK dependency).

    Args:
        prompt: The user message to send.
        api_key: Defaults to the LLM_API_KEY environment variable.
        model: Defaults to the LLM_MODEL environment variable.
        max_tokens: Passed through to the Messages API.
        transport: Only set in tests — httpx.MockTransport replaces the
            real network with a function you control (Week 5 §4.3).

    Returns:
        The text of the first text content block in the response. Some
        models return other block types (e.g. thinking) before the text
        block, so this searches by type rather than assuming content[0].

    Raises:
        httpx.HTTPStatusError: If the API returns a non-2xx response.
        LLMResponseError: If the response has no text content block.
    """
    api_key = api_key or os.environ["LLM_API_KEY"]
    model = model or os.environ["LLM_MODEL"]

    with httpx.Client(timeout=60.0, transport=transport) as client:
        response = client.post(
            ANTHROPIC_MESSAGES_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()

        for block in data["content"]:
            if block["type"] == "text":
                return block["text"]
        raise LLMResponseError(f"No text block in response: {data}")
