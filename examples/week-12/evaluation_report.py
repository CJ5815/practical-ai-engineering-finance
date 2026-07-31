"""Week 12: a full evaluation report — recall/precision, groundedness, failure modes.

Requires LLM_API_KEY and LLM_MODEL in a .env file (see .env.example) — used
for both generating each answer (Week 10's answer_question) and for the
groundedness judge (a second, independent call). Retrieval metrics
(recall@k, precision@k) need no API key at all — they're fully
deterministic. Reuses the persistent collection Week 9 built
(data/processed/chroma) — run examples/week-09/build_passage_index.py
first if you haven't already.

Run this file directly:

    python examples/week-12/evaluation_report.py
"""

from __future__ import annotations

import json
import os
from functools import partial
from pathlib import Path

import httpx
from dotenv import load_dotenv

from ai_finance_course.evaluation import check_groundedness, evaluate_retrieval
from ai_finance_course.rag import answer_question
from ai_finance_course.vector_store import get_or_create_collection, query_collection

QUESTIONS_PATH = Path("data/sample/eval_questions.json")
PERSIST_PATH = Path("data/processed/chroma")
COLLECTION_NAME = "sample_passages"

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


def _call_llm(prompt: str) -> str:
    """Call Anthropic's Messages API directly via httpx (no SDK dependency)."""
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            ANTHROPIC_MESSAGES_URL,
            headers={
                "x-api-key": os.environ["LLM_API_KEY"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": os.environ["LLM_MODEL"],
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()
        for block in data["content"]:
            if block["type"] == "text":
                return block["text"]
        raise ValueError(f"No text block in response: {data}")


def main() -> None:
    load_dotenv()

    if not PERSIST_PATH.exists():
        print(f"No index found at {PERSIST_PATH}. Run examples/week-09/build_passage_index.py first.")
        raise SystemExit(1)

    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    collection = get_or_create_collection(PERSIST_PATH, COLLECTION_NAME)

    print(f"=== Retrieval metrics across {len(questions)} questions ===\n")
    retrieval_result = evaluate_retrieval(
        questions, partial(query_collection, collection, n_results=3), k=3
    )
    print(f"Mean recall@3:    {retrieval_result['mean_recall_at_k']:.1%}")
    print(f"Mean precision@3: {retrieval_result['mean_precision_at_k']:.1%}\n")

    retrieval_failures = [r for r in retrieval_result["per_question"] if r["recall"] < 1.0]
    print(f"Retrieval failures ({len(retrieval_failures)}):")
    for failure in retrieval_failures:
        print(f"  recall={failure['recall']:.2f} precision={failure['precision']:.2f}  {failure['query']!r}")

    print(f"\n=== Generation and groundedness across {len(questions)} questions ===\n")
    groundedness_failures = []
    for question in questions:
        result, evidence = answer_question(question["query"], collection, _call_llm, n_results=3)
        cited_texts = [evidence[c - 1]["text"] for c in result.citations]
        check = check_groundedness(result.answer, cited_texts, _call_llm)
        status = "OK  " if check.grounded else "FAIL"
        print(f"{status} {question['query']!r}")
        print(f"      answer: {result.answer}")
        print(f"      grounded: {check.grounded} — {check.reasoning}")
        if not check.grounded:
            groundedness_failures.append({"query": question["query"], "reasoning": check.reasoning})

    print("\n=== Summary ===")
    print(f"Retrieval failures: {len(retrieval_failures)}/{len(questions)}")
    print(f"Groundedness failures: {len(groundedness_failures)}/{len(questions)}")


if __name__ == "__main__":
    main()
