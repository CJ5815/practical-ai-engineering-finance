"""Tests for query_expansion.py.

Uses conftest.py's keyword_stub_embedding_function and a stub generate —
no real model, no real API key, no network.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("chromadb", reason="requires the [rag] extra: pip install -e '.[rag]'")

from ai_finance_course.query_expansion import (
    QueryExpansion,
    build_expansion_prompt,
    expand_query,
    retrieve_with_expansion,
)
from ai_finance_course.vector_store import (
    add_chunks,
    get_or_create_collection,
    query_collection,
)


def test_build_expansion_prompt_includes_query() -> None:
    prompt = build_expansion_prompt("did revenue grow?")

    assert "did revenue grow?" in prompt
    assert "rephrasings" in prompt


def test_expand_query_returns_original_plus_rephrasings() -> None:
    def stub_generate(prompt: str) -> str:
        return json.dumps({"rephrasings": ["did sales increase?", "was there revenue growth?"]})

    variants = expand_query("did revenue grow?", stub_generate)

    assert variants == ["did revenue grow?", "did sales increase?", "was there revenue growth?"]


def test_expand_query_strips_markdown_fence() -> None:
    def stub_generate(prompt: str) -> str:
        return f"```json\n{json.dumps({'rephrasings': ['variant']})}\n```"

    variants = expand_query("original", stub_generate)

    assert variants == ["original", "variant"]


def test_expand_query_rejects_invalid_response_shape() -> None:
    def stub_generate(prompt: str) -> str:
        return json.dumps({"rephrasings": "not-a-list"})

    with pytest.raises(ValueError):
        expand_query("original", stub_generate)


def test_query_expansion_model_requires_rephrasings_field() -> None:
    with pytest.raises(ValueError):
        QueryExpansion()


def test_retrieve_with_expansion_finds_a_variant_the_original_misses(
    tmp_path, keyword_stub_embedding_function
) -> None:
    """A stripped-down version of a real failure (Week 11 §Day 3): the original
    query alone ranks an unrelated chunk first; a rephrasing that shares the
    target chunk's own wording ranks the right one first instead."""
    collection = get_or_create_collection(tmp_path, "passages", keyword_stub_embedding_function)
    add_chunks(
        collection,
        [
            {"text": "The Fed raised interest rates sharply.", "ticker": "MACRO", "chunk_index": 0},
            {"text": "Revenue growth this quarter.", "ticker": "OTHER", "chunk_index": 0},
        ],
    )

    def stub_generate(prompt: str) -> str:
        return json.dumps({"rephrasings": ["what happened with the interest rate?"]})

    # Verified directly: "borrowing costs" alone ranks OTHER (distance 1.0)
    # above MACRO (distance 2.0) — a genuine miss, not a tie.
    original_only = query_collection(collection, "borrowing costs", n_results=1)
    assert original_only[0]["metadata"]["ticker"] == "OTHER"

    results = retrieve_with_expansion(
        collection, "borrowing costs", n_results=1, generate=stub_generate
    )

    assert results[0]["metadata"]["ticker"] == "MACRO"


def test_retrieve_with_expansion_deduplicates_by_text(tmp_path, keyword_stub_embedding_function) -> None:
    collection = get_or_create_collection(tmp_path, "passages", keyword_stub_embedding_function)
    add_chunks(collection, [{"text": "revenue grew this quarter", "ticker": "AAPL", "chunk_index": 0}])

    def stub_generate(prompt: str) -> str:
        return json.dumps({"rephrasings": ["did revenue increase?", "was there revenue growth?"]})

    results = retrieve_with_expansion(collection, "revenue growth", n_results=5, generate=stub_generate)

    # Three query variants all retrieve the same single chunk; it must appear once.
    assert len(results) == 1


def test_retrieve_with_expansion_respects_where_filter(tmp_path, keyword_stub_embedding_function) -> None:
    collection = get_or_create_collection(tmp_path, "passages", keyword_stub_embedding_function)
    add_chunks(
        collection,
        [
            {"text": "AAPL revenue grew.", "ticker": "AAPL", "chunk_index": 0},
            {"text": "MSFT revenue grew.", "ticker": "MSFT", "chunk_index": 0},
        ],
    )

    def stub_generate(prompt: str) -> str:
        return json.dumps({"rephrasings": ["did sales increase?"]})

    results = retrieve_with_expansion(
        collection, "revenue growth", n_results=5, generate=stub_generate, where={"ticker": "AAPL"}
    )

    assert all(r["metadata"]["ticker"] == "AAPL" for r in results)
