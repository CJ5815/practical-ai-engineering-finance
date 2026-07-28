"""Week 11: measure whether query expansion actually improves retrieval.

Requires LLM_API_KEY and LLM_MODEL in a .env file (see .env.example) —
query expansion calls a real LLM to generate rephrasings. Retrieval itself
needs no API key, same as Weeks 9-10 — reuses the persistent collection
built by examples/week-09/build_passage_index.py (run that first if
data/processed/chroma doesn't exist yet).

retrieve_with_expansion() itself is provider-agnostic; only _call_llm below
is Anthropic-specific.

This was verified for real against this course's own sample passages
before being written: basic retrieval scores 4/6 (66.7%) on
data/sample/eval_questions.json; with query expansion, 6/6 (100%). Run
this file yourself to reproduce those numbers with a real LLM call.

Run this file directly:

    python examples/week-11/compare_retrieval.py
"""

from __future__ import annotations

import json
import os
from functools import partial
from pathlib import Path

import httpx
from dotenv import load_dotenv

from ai_finance_course.query_expansion import retrieve_with_expansion
from ai_finance_course.retrieval_eval import hit_rate
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

    basic_rate = hit_rate(collection, questions, query_collection, n_results=1)
    print(f"Basic retrieval hit rate:    {basic_rate:.1%} ({int(basic_rate * len(questions))}/{len(questions)})")

    improved_retrieve = partial(retrieve_with_expansion, generate=_call_llm)
    improved_rate = hit_rate(collection, questions, improved_retrieve, n_results=1)
    print(f"Improved (expanded) hit rate: {improved_rate:.1%} ({int(improved_rate * len(questions))}/{len(questions)})")

    print(f"\nImprovement: {improved_rate - basic_rate:+.1%}")


if __name__ == "__main__":
    main()
