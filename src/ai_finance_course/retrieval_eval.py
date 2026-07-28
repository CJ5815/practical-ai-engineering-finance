"""Measuring whether retrieval actually finds the right evidence.

A small, deliberately simple metric: for each labeled question, does any
retrieved chunk's ticker match the expected one? This is coarser than
Week 12's full evaluation (which checks groundedness and specific claims,
not just "right company") — good enough to compare basic retrieval against
an improved retrieval strategy on the same question set, which is this
week's whole point.
"""

from __future__ import annotations

from collections.abc import Callable

from chromadb.api.models.Collection import Collection


def hit_rate(
    collection: Collection,
    questions: list[dict],
    retrieve: Callable[[Collection, str, int], list[dict]],
    n_results: int = 3,
) -> float:
    """Fraction of questions whose expected ticker appears among the retrieved results.

    Args:
        collection: A ChromaDB collection from vector_store.get_or_create_collection.
        questions: Dicts with "query" and "expected_ticker" (see
            data/sample/eval_questions.json for the format).
        retrieve: A function taking (collection, query, n_results) and
            returning a list of {"text", "metadata", "distance"} dicts —
            vector_store.query_collection works directly; pass
            query_expansion.retrieve_with_expansion via functools.partial
            with generate already bound (it's keyword-only for exactly
            this reason).
        n_results: How many results each retrieval call should return.

    Returns:
        The fraction (0.0-1.0) of questions where at least one retrieved
        chunk's metadata ticker matches expected_ticker. This does NOT
        confirm the retrieved chunk is the single best one available —
        only that retrieval found the right company's evidence at all.
    """
    hits = 0
    for question in questions:
        results = retrieve(collection, question["query"], n_results)
        if any(result["metadata"].get("ticker") == question["expected_ticker"] for result in results):
            hits += 1
    return hits / len(questions)
