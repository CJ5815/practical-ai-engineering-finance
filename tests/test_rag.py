"""Tests for rag.py.

Uses the same stub embedding function as test_vector_store.py and a stub
generate — same reasoning as Week 7's injected generate: Callable[[str],
str] for LLM calls. No real model, no real API key, no network.
"""

from __future__ import annotations

import json

import pytest
from chromadb import Documents, EmbeddingFunction, Embeddings

from ai_finance_course.rag import RAGAnswer, answer_question, build_grounded_prompt
from ai_finance_course.vector_store import add_chunks, get_or_create_collection

_KEYWORDS = ["revenue", "earnings", "rate", "interest"]


class KeywordStubEmbeddingFunction(EmbeddingFunction):
    def __init__(self) -> None:
        pass

    def __call__(self, input: Documents) -> Embeddings:
        return [[float(keyword in text.lower()) for keyword in _KEYWORDS] for text in input]

    @staticmethod
    def name() -> str:
        return "keyword-stub-embedding-function"


def _sample_collection(tmp_path):
    collection = get_or_create_collection(tmp_path, "passages", KeywordStubEmbeddingFunction())
    add_chunks(
        collection,
        [
            {"text": "AAPL revenue grew 8% this quarter.", "ticker": "AAPL", "chunk_index": 0},
            {"text": "The Fed raised interest rates.", "ticker": "MACRO", "chunk_index": 0},
        ],
    )
    return collection


def test_build_grounded_prompt_numbers_evidence_and_includes_metadata() -> None:
    evidence = [
        {"text": "AAPL revenue grew 8%.", "metadata": {"ticker": "AAPL", "doc_type": "earnings"}, "distance": 0.1}
    ]

    prompt = build_grounded_prompt("Did revenue grow?", evidence)

    assert "[1] (AAPL, earnings): AAPL revenue grew 8%." in prompt
    assert "Did revenue grow?" in prompt
    assert "citations" in prompt


def test_answer_question_returns_validated_answer_and_evidence(tmp_path) -> None:
    collection = _sample_collection(tmp_path)

    def stub_generate(prompt: str) -> str:
        assert "revenue" in prompt.lower()
        return json.dumps({"answer": "Yes, revenue grew 8%.", "citations": [1]})

    result, evidence = answer_question("Did revenue grow?", collection, stub_generate, n_results=2)

    assert isinstance(result, RAGAnswer)
    assert result.citations == [1]
    assert len(evidence) == 2


def test_answer_question_strips_markdown_fence(tmp_path) -> None:
    collection = _sample_collection(tmp_path)

    def stub_generate(prompt: str) -> str:
        return f"```json\n{json.dumps({'answer': 'Yes.', 'citations': [1]})}\n```"

    result, _ = answer_question("Did revenue grow?", collection, stub_generate, n_results=1)

    assert result.answer == "Yes."


def test_answer_question_respects_metadata_filter(tmp_path) -> None:
    collection = _sample_collection(tmp_path)

    def stub_generate(prompt: str) -> str:
        assert "MACRO" not in prompt
        return json.dumps({"answer": "Yes.", "citations": [1]})

    _, evidence = answer_question(
        "Did revenue grow?", collection, stub_generate, n_results=5, where={"ticker": "AAPL"}
    )

    assert all(chunk["metadata"]["ticker"] == "AAPL" for chunk in evidence)


def test_answer_question_rejects_invalid_response_shape(tmp_path) -> None:
    collection = _sample_collection(tmp_path)

    def stub_generate(prompt: str) -> str:
        return json.dumps({"answer": "Yes.", "citations": "not-a-list"})

    with pytest.raises(ValueError):
        answer_question("Did revenue grow?", collection, stub_generate, n_results=1)


def test_answer_question_rejects_out_of_range_citation(tmp_path) -> None:
    """Regression test: found live when a stub cited [99] with only 1 chunk retrieved,
    which previously would have crashed with an unhandled IndexError downstream."""
    collection = _sample_collection(tmp_path)

    def stub_generate(prompt: str) -> str:
        return json.dumps({"answer": "Yes.", "citations": [99]})

    with pytest.raises(ValueError, match="99"):
        answer_question("Did revenue grow?", collection, stub_generate, n_results=1)
