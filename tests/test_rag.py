"""Tests for rag.py.

Uses conftest.py's sample_collection fixture (Week 13 §2's fixture-
composing-fixtures example) and a stub generate — same reasoning as
Week 7's injected generate: Callable[[str], str] for LLM calls. No real
model, no real API key, no network.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("chromadb", reason="requires the [rag] extra: pip install -e '.[rag]'")

from ai_finance_course.rag import RAGAnswer, answer_question, build_grounded_prompt


def test_build_grounded_prompt_numbers_evidence_and_includes_metadata() -> None:
    evidence = [
        {"text": "AAPL revenue grew 8%.", "metadata": {"ticker": "AAPL", "doc_type": "earnings"}, "distance": 0.1}
    ]

    prompt = build_grounded_prompt("Did revenue grow?", evidence)

    assert "[1] (AAPL, earnings): AAPL revenue grew 8%." in prompt
    assert "Did revenue grow?" in prompt
    assert "citations" in prompt


def test_answer_question_returns_validated_answer_and_evidence(sample_collection) -> None:
    def stub_generate(prompt: str) -> str:
        assert "revenue" in prompt.lower()
        return json.dumps({"answer": "Yes, revenue grew 8%.", "citations": [1]})

    result, evidence = answer_question("Did revenue grow?", sample_collection, stub_generate, n_results=2)

    assert isinstance(result, RAGAnswer)
    assert result.citations == [1]
    assert len(evidence) == 2


def test_answer_question_strips_markdown_fence(sample_collection) -> None:
    def stub_generate(prompt: str) -> str:
        return f"```json\n{json.dumps({'answer': 'Yes.', 'citations': [1]})}\n```"

    result, _ = answer_question("Did revenue grow?", sample_collection, stub_generate, n_results=1)

    assert result.answer == "Yes."


def test_answer_question_respects_metadata_filter(sample_collection) -> None:
    def stub_generate(prompt: str) -> str:
        assert "MACRO" not in prompt
        return json.dumps({"answer": "Yes.", "citations": [1]})

    _, evidence = answer_question(
        "Did revenue grow?", sample_collection, stub_generate, n_results=5, where={"ticker": "AAPL"}
    )

    assert all(chunk["metadata"]["ticker"] == "AAPL" for chunk in evidence)


def test_answer_question_rejects_invalid_response_shape(sample_collection) -> None:
    def stub_generate(prompt: str) -> str:
        return json.dumps({"answer": "Yes.", "citations": "not-a-list"})

    with pytest.raises(ValueError):
        answer_question("Did revenue grow?", sample_collection, stub_generate, n_results=1)


def test_answer_question_rejects_out_of_range_citation(sample_collection) -> None:
    """Regression test: found live when a stub cited [99] with only 1 chunk retrieved,
    which previously would have crashed with an unhandled IndexError downstream."""

    def stub_generate(prompt: str) -> str:
        return json.dumps({"answer": "Yes.", "citations": [99]})

    with pytest.raises(ValueError, match="99"):
        answer_question("Did revenue grow?", sample_collection, stub_generate, n_results=1)
