"""Week 16: the capstone, integrating Weeks 4/5, 9, 10, and 12 into one run.

Nothing in this script is new library code — every function it calls
already exists and is already tested (EdgarClient from Weeks 4-5,
chunk_document/get_or_create_collection/add_chunks/query_collection from
Week 9, answer_question from Week 10, evaluate_retrieval/check_groundedness
from Week 12). This week's actual work is integration: wiring already-built,
already-tested pieces into the shape docs/projects/capstone.md describes,
against a small set of real public companies.

Three real steps, each doing what it says:

1. Real document discovery — EdgarClient.get_filings_for_ticker makes a
   real HTTPS call to SEC EDGAR for three real companies (AAPL, MSFT,
   GOOGL), the same live-verified module Weeks 4-5 already built and
   tested. This satisfies capstone.md's "load at least three public
   company documents" at the discovery layer.

2. Indexing a small capstone dataset — data/sample/capstone_passages.json
   holds short earnings/risk passages for those same three companies.
   This is a DELIBERATELY SEPARATE file and a DELIBERATELY SEPARATE
   ChromaDB collection ("capstone_passages") from Week 9-15's
   "sample_passages" — reusing passages.json directly would have changed
   its row count and silently broken Week 15's
   test_ensure_sample_index_indexes_when_empty, which hardcodes
   count() == 8. Two collections can coexist in the same persist_path
   without conflict; ChromaDB namespaces by collection name, not by
   directory alone.

3. The full evaluation report — recall/precision (deterministic, no API
   key needed) plus generation and groundedness (needs LLM_API_KEY,
   skipped with a clear message if it's not set, rather than crashing
   partway through — capstone.md's rubric explicitly grades "reliable
   ... error handling").

Requires LLM_API_KEY, LLM_MODEL, and SEC_USER_AGENT in a .env file (see
.env.example). SEC_USER_AGENT is required by SEC EDGAR's terms of service
even for the metadata-only calls in step 1; step 2 and the retrieval half
of step 3 work with no API key at all.

Run this file directly:

    python examples/week-16/build_capstone.py
"""

from __future__ import annotations

import json
import os
from functools import partial
from pathlib import Path

import httpx
from dotenv import load_dotenv

from ai_finance_course.chunking import chunk_document
from ai_finance_course.edgar import EdgarClient
from ai_finance_course.evaluation import check_groundedness, evaluate_retrieval
from ai_finance_course.rag import answer_question
from ai_finance_course.vector_store import add_chunks, get_or_create_collection, query_collection

PASSAGES_PATH = Path("data/sample/capstone_passages.json")
QUESTIONS_PATH = Path("data/sample/capstone_eval_questions.json")
PERSIST_PATH = Path("data/processed/chroma")
COLLECTION_NAME = "capstone_passages"
TICKERS = ["AAPL", "MSFT", "GOOGL"]

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


def discover_filings() -> None:
    """Step 1: real document discovery against SEC EDGAR for three real companies."""
    print(f"=== Discovering recent filings for {', '.join(TICKERS)} ===\n")
    with EdgarClient(user_agent=os.environ["SEC_USER_AGENT"]) as client:
        for ticker in TICKERS:
            filings = client.get_filings_for_ticker(ticker, limit=3)
            print(f"{ticker}:")
            for filing in filings:
                print(f"  {filing.form:8s} {filing.filing_date}  {filing.primary_document}")
    print()


def build_index():
    """Step 2: chunk and index the capstone passage set into its own collection."""
    collection = get_or_create_collection(PERSIST_PATH, COLLECTION_NAME)
    passages = json.loads(PASSAGES_PATH.read_text(encoding="utf-8"))
    for passage in passages:
        metadata = {"ticker": passage["ticker"], "doc_type": passage["doc_type"]}
        chunks = chunk_document(passage["text"], metadata, chunk_size=500, overlap=50)
        add_chunks(collection, chunks)
    print(f"=== Indexed {collection.count()} chunks from {len(passages)} passages across {len(TICKERS)} companies ===\n")
    return collection


def run_evaluation(collection) -> None:
    """Step 3: the full evaluation report, retrieval metrics plus generation/groundedness."""
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))

    print(f"=== Retrieval metrics across {len(questions)} questions ===\n")
    retrieval_result = evaluate_retrieval(questions, partial(query_collection, collection, n_results=3), k=3)
    print(f"Mean recall@3:    {retrieval_result['mean_recall_at_k']:.1%}")
    print(f"Mean precision@3: {retrieval_result['mean_precision_at_k']:.1%}\n")

    retrieval_failures = [r for r in retrieval_result["per_question"] if r["recall"] < 1.0]
    print(f"Retrieval failures ({len(retrieval_failures)}):")
    for failure in retrieval_failures:
        print(f"  recall={failure['recall']:.2f} precision={failure['precision']:.2f}  {failure['query']!r}")

    if not os.environ.get("LLM_API_KEY"):
        print("\nLLM_API_KEY not set — skipping generation and groundedness (set it in .env to run this part).")
        return

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


def main() -> None:
    load_dotenv()
    discover_filings()
    collection = build_index()
    run_evaluation(collection)


if __name__ == "__main__":
    main()
