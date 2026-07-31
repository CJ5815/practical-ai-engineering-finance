"""Formal evaluation: retrieval recall/precision and answer groundedness.

Week 11's hit_rate asked one coarse question: did retrieval find the right
company at all? This module asks two sharper ones: of the evidence that
actually answers the question, how much did retrieval find (recall)? And
of what got cited in the final answer (Week 10's RAGAnswer.citations), is
every claim actually supported by that evidence (groundedness)? Recall and
precision are pure functions, fully deterministic (CLAUDE.md-style rule:
deterministic Python for calculations). Groundedness needs an LLM judge —
injected as `generate`, the same pattern as every other LLM call in this
course — since "does this evidence support this claim" isn't checkable by
string matching.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from pydantic import BaseModel

from ai_finance_course.json_utils import extract_json


def recall_at_k(retrieved: list[dict], relevant_texts: list[str], k: int) -> float:
    """Fraction of the known-relevant texts found among the top-k retrieved chunks.

    Args:
        retrieved: Results from query_collection or retrieve_with_expansion,
            already sorted most-relevant-first.
        relevant_texts: The exact chunk text(s) that actually answer the
            question (see data/sample/eval_questions.json).
        k: How many of the top retrieved results to consider.

    Returns:
        len(relevant found in top-k) / len(relevant_texts). 1.0 means every
        known-relevant chunk was retrieved; 0.0 means none were.
    """
    top_k_texts = {chunk["text"] for chunk in retrieved[:k]}
    found = sum(1 for text in relevant_texts if text in top_k_texts)
    return found / len(relevant_texts)


def precision_at_k(retrieved: list[dict], relevant_texts: list[str], k: int) -> float:
    """Fraction of the top-k retrieved chunks that are actually relevant.

    Args:
        retrieved: Results from query_collection or retrieve_with_expansion.
        relevant_texts: The exact chunk text(s) that actually answer the question.
        k: How many of the top retrieved results to consider.

    Returns:
        len(relevant in top-k) / len(top-k actually returned). Returns 0.0
        if nothing was retrieved. Dividing by what was actually returned
        (not always k) avoids unfairly penalizing a small corpus that has
        fewer than k chunks to return in the first place.
    """
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    relevant_set = set(relevant_texts)
    found = sum(1 for chunk in top_k if chunk["text"] in relevant_set)
    return found / len(top_k)


def evaluate_retrieval(
    questions: list[dict],
    retrieve: Callable[[str], list[dict]],
    k: int = 3,
) -> dict:
    """Compute mean recall@k and precision@k across a labeled question set.

    Args:
        questions: Dicts with "query" and "relevant_texts" (see
            data/sample/eval_questions.json).
        retrieve: A function taking a query string and returning retrieved
            {"text", "metadata", "distance"} dicts — bind a collection and
            n_results with functools.partial before passing it in.
        k: How many retrieved results to evaluate against.

    Returns:
        {"mean_recall_at_k", "mean_precision_at_k", "k", "per_question"} —
        per_question is a list of {"query", "recall", "precision"} dicts,
        useful for spotting exactly which questions are dragging the mean
        down (Week 12's failure-mode analysis).
    """
    per_question = []
    for question in questions:
        retrieved = retrieve(question["query"])
        recall = recall_at_k(retrieved, question["relevant_texts"], k)
        precision = precision_at_k(retrieved, question["relevant_texts"], k)
        per_question.append({"query": question["query"], "recall": recall, "precision": precision})

    return {
        "mean_recall_at_k": sum(r["recall"] for r in per_question) / len(per_question),
        "mean_precision_at_k": sum(r["precision"] for r in per_question) / len(per_question),
        "k": k,
        "per_question": per_question,
    }


class GroundednessCheck(BaseModel):
    """Whether an answer's claims are actually supported by its cited evidence."""

    grounded: bool
    reasoning: str


def build_groundedness_prompt(answer: str, cited_evidence: list[str]) -> str:
    """Build a role/task/evidence/constraints/output-format prompt (Week 6's structure).

    Args:
        answer: The generated answer text to audit (e.g. RAGAnswer.answer).
        cited_evidence: The exact chunk text(s) the answer cited — not the
            model's paraphrase of them, the real retrieved text (Week 10 §4.1).
    """
    evidence_block = "\n".join(f"[{i + 1}] {text}" for i, text in enumerate(cited_evidence))

    return f"""ROLE: You are a fact-checking auditor verifying whether an answer is \
fully supported by its cited evidence.

TASK: Determine whether the ANSWER below is fully supported by the CITED EVIDENCE. \
An answer is grounded only if every claim in it is directly stated or clearly implied \
by the evidence — not just topically related.

ANSWER: {answer}

CITED EVIDENCE:
{evidence_block}

CONSTRAINTS:
- Judge only whether the evidence supports the answer, not whether the answer is well-written.
- If any part of the answer goes beyond what the evidence states, mark it not grounded.

OUTPUT FORMAT: Return ONLY valid JSON, no other text, matching this shape:
{{"grounded": true, "reasoning": "one sentence"}}"""


def check_groundedness(answer: str, cited_evidence: list[str], generate: Callable[[str], str]) -> GroundednessCheck:
    """Ask an LLM judge whether an answer is actually supported by its cited evidence.

    Args:
        answer: The generated answer text.
        cited_evidence: The real retrieved chunk text(s) the answer cited.
        generate: A function that takes a prompt and returns the LLM's raw
            text response. Injected so this function never calls a
            provider's API directly — and so the judge can be a different,
            cheaper model than the one that generated the answer.

    Returns:
        A validated GroundednessCheck.

    Raises:
        pydantic.ValidationError: If the LLM's response doesn't match the
            expected shape (a subclass of ValueError — Week 7 §3.3).
    """
    prompt = build_groundedness_prompt(answer, cited_evidence)
    raw_response = generate(prompt)
    parsed = json.loads(extract_json(raw_response))
    return GroundednessCheck(**parsed)
