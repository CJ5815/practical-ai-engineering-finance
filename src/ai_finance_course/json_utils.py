"""Shared helper for parsing JSON out of an LLM's raw text response."""

from __future__ import annotations


def extract_json(text: str) -> str:
    """Strip a ```json fence around the response, if the model added one."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.removeprefix("json").strip()
    return stripped
