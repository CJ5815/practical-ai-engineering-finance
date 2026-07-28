"""Tests for retrieval_eval.py.

Uses conftest.py's keyword_stub_embedding_function — no real model needed.
"""

from __future__ import annotations

import json
from functools import partial

from ai_finance_course.query_expansion import retrieve_with_expansion
from ai_finance_course.retrieval_eval import hit_rate
from ai_finance_course.vector_store import add_chunks, get_or_create_collection, query_collection


def test_hit_rate_is_one_when_every_question_finds_its_ticker(tmp_path, keyword_stub_embedding_function) -> None:
    collection = get_or_create_collection(tmp_path, "passages", keyword_stub_embedding_function)
    add_chunks(
        collection,
        [
            {"text": "revenue grew this quarter", "ticker": "AAPL", "chunk_index": 0},
            {"text": "interest rates rose", "ticker": "MACRO", "chunk_index": 0},
        ],
    )
    questions = [
        {"query": "did revenue grow?", "expected_ticker": "AAPL"},
        {"query": "what happened to interest rates?", "expected_ticker": "MACRO"},
    ]

    assert hit_rate(collection, questions, query_collection, n_results=1) == 1.0


def test_hit_rate_is_partial_when_some_questions_miss(tmp_path, keyword_stub_embedding_function) -> None:
    collection = get_or_create_collection(tmp_path, "passages", keyword_stub_embedding_function)
    add_chunks(
        collection,
        [
            {"text": "revenue grew this quarter", "ticker": "AAPL", "chunk_index": 0},
            {"text": "interest rates rose", "ticker": "MACRO", "chunk_index": 0},
        ],
    )
    questions = [
        {"query": "did revenue grow?", "expected_ticker": "AAPL"},
        # Expects MACRO, but this query shares no keywords with the MACRO chunk.
        {"query": "unrelated phrasing with nothing in common", "expected_ticker": "MACRO"},
    ]

    assert hit_rate(collection, questions, query_collection, n_results=1) == 0.5


def test_hit_rate_accepts_retrieve_with_expansion_via_partial(tmp_path, keyword_stub_embedding_function) -> None:
    """Confirms retrieve_with_expansion's (collection, query, n_results) signature
    matches query_collection's closely enough that hit_rate can call either one."""
    collection = get_or_create_collection(tmp_path, "passages", keyword_stub_embedding_function)
    add_chunks(collection, [{"text": "revenue grew this quarter", "ticker": "AAPL", "chunk_index": 0}])
    questions = [{"query": "did revenue grow?", "expected_ticker": "AAPL"}]

    def stub_generate(prompt: str) -> str:
        return json.dumps({"rephrasings": ["did sales increase?"]})

    improved_retrieve = partial(retrieve_with_expansion, generate=stub_generate)

    assert hit_rate(collection, questions, improved_retrieve, n_results=1) == 1.0
