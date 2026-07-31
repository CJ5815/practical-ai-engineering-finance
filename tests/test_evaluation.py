"""Tests for evaluation.py.

recall_at_k/precision_at_k/evaluate_retrieval operate on plain dicts, so
these tests need no vector store at all. check_groundedness uses a stub
generate — no real model, no real API key, no network.
"""

from __future__ import annotations

import json

import pytest

from ai_finance_course.evaluation import (
    GroundednessCheck,
    build_groundedness_prompt,
    check_groundedness,
    evaluate_retrieval,
    precision_at_k,
    recall_at_k,
)


def _chunk(text: str) -> dict:
    return {"text": text, "metadata": {}, "distance": 0.0}


def test_recall_at_k_is_one_when_all_relevant_texts_found() -> None:
    retrieved = [_chunk("A"), _chunk("B"), _chunk("C")]

    assert recall_at_k(retrieved, ["A"], k=3) == 1.0


def test_recall_at_k_is_partial_when_some_relevant_texts_missing() -> None:
    retrieved = [_chunk("A"), _chunk("C")]

    assert recall_at_k(retrieved, ["A", "B"], k=2) == 0.5


def test_recall_at_k_only_considers_top_k() -> None:
    retrieved = [_chunk("wrong"), _chunk("A")]

    assert recall_at_k(retrieved, ["A"], k=1) == 0.0


def test_precision_at_k_counts_relevant_fraction_of_returned_results() -> None:
    retrieved = [_chunk("A"), _chunk("wrong")]

    assert precision_at_k(retrieved, ["A"], k=2) == 0.5


def test_precision_at_k_divides_by_actual_results_not_k() -> None:
    """A small corpus returning fewer than k results shouldn't be unfairly penalized."""
    retrieved = [_chunk("A")]

    assert precision_at_k(retrieved, ["A"], k=5) == 1.0


def test_precision_at_k_is_zero_for_empty_results() -> None:
    assert precision_at_k([], ["A"], k=3) == 0.0


def test_evaluate_retrieval_aggregates_across_questions() -> None:
    questions = [
        {"query": "q1", "relevant_texts": ["A"]},
        {"query": "q2", "relevant_texts": ["B"]},
    ]

    def stub_retrieve(query: str) -> list[dict]:
        return [_chunk("A")] if query == "q1" else [_chunk("wrong")]

    result = evaluate_retrieval(questions, stub_retrieve, k=1)

    assert result["mean_recall_at_k"] == 0.5
    assert result["mean_precision_at_k"] == 0.5
    assert result["per_question"][0] == {"query": "q1", "recall": 1.0, "precision": 1.0}
    assert result["per_question"][1] == {"query": "q2", "recall": 0.0, "precision": 0.0}


def test_build_groundedness_prompt_includes_answer_and_evidence() -> None:
    prompt = build_groundedness_prompt("Revenue grew 8%.", ["Apple's revenue grew 8%."])

    assert "Revenue grew 8%." in prompt
    assert "[1] Apple's revenue grew 8%." in prompt
    assert "grounded" in prompt


def test_check_groundedness_returns_validated_result() -> None:
    def stub_generate(prompt: str) -> str:
        return json.dumps({"grounded": True, "reasoning": "The evidence directly states this."})

    result = check_groundedness("Revenue grew 8%.", ["Apple's revenue grew 8%."], stub_generate)

    assert isinstance(result, GroundednessCheck)
    assert result.grounded is True


def test_check_groundedness_detects_unsupported_claims() -> None:
    def stub_generate(prompt: str) -> str:
        return json.dumps({"grounded": False, "reasoning": "The evidence never mentions a forecast."})

    result = check_groundedness("Revenue will grow 20% next year.", ["Revenue grew 8%."], stub_generate)

    assert result.grounded is False


def test_check_groundedness_strips_markdown_fence() -> None:
    def stub_generate(prompt: str) -> str:
        return f"```json\n{json.dumps({'grounded': True, 'reasoning': 'ok'})}\n```"

    result = check_groundedness("answer", ["evidence"], stub_generate)

    assert result.grounded is True


def test_check_groundedness_rejects_invalid_response_shape() -> None:
    """"yes"/"no" strings are NOT a safe invalid case here — pydantic's lax bool
    coercion accepts them (verified directly). Use a value with no bool coercion."""

    def stub_generate(prompt: str) -> str:
        return json.dumps({"grounded": "not-a-bool", "reasoning": "ok"})

    with pytest.raises(ValueError):
        check_groundedness("answer", ["evidence"], stub_generate)
