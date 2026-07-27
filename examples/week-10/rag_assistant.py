"""Week 10: a command-line RAG assistant over the Week 9 sample passage index.

Requires LLM_API_KEY and LLM_MODEL in a .env file (see .env.example) — this
calls a real LLM (Anthropic's Messages API, via a direct httpx POST, no
SDK) to generate the grounded answer. Retrieval itself needs no API key,
same as Week 9 — reuses the persistent collection built by
examples/week-09/build_passage_index.py (run that first if
data/processed/chroma doesn't exist yet).

answer_question() itself is provider-agnostic; only _call_llm below is
Anthropic-specific.

Run this file directly, with your question as the argument:

    python examples/week-10/rag_assistant.py "did the company beat earnings expectations?"
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

from ai_finance_course.rag import answer_question
from ai_finance_course.vector_store import get_or_create_collection

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

    if len(sys.argv) < 2:
        print('Usage: python examples/week-10/rag_assistant.py "your question"')
        raise SystemExit(1)
    question = sys.argv[1]

    if not PERSIST_PATH.exists():
        print(f"No index found at {PERSIST_PATH}. Run examples/week-09/build_passage_index.py first.")
        raise SystemExit(1)

    collection = get_or_create_collection(PERSIST_PATH, COLLECTION_NAME)
    result, evidence = answer_question(question, collection, _call_llm, n_results=3)

    print(f"Q: {question}")
    print(f"A: {result.answer}\n")

    if result.citations:
        print("Sources:")
        for citation in result.citations:
            chunk = evidence[citation - 1]
            print(f"  [{citation}] ({chunk['metadata']['ticker']}, {chunk['metadata']['doc_type']}) {chunk['text']}")
    else:
        print("No sources cited.")


if __name__ == "__main__":
    main()
