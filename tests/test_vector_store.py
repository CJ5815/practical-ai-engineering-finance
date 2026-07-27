"""Tests for vector_store.py.

Uses a small deterministic stub embedding function instead of a real
sentence-transformers model — same reasoning as Week 7's injected
generate: Callable[[str], str] for LLM calls. This keeps tests fast and
network-free; examples/week-09/build_passage_index.py uses the real
SentenceTransformerEmbeddingFunction.
"""

from __future__ import annotations

from chromadb import Documents, EmbeddingFunction, Embeddings

from ai_finance_course.vector_store import add_chunks, get_or_create_collection, query_collection

_KEYWORDS = ["revenue", "earnings", "rate", "interest"]


class KeywordStubEmbeddingFunction(EmbeddingFunction):
    """Embeds text as a keyword-presence vector — deterministic, no model needed.

    Texts sharing more of _KEYWORDS end up closer together, which is enough
    to test add/query/filter behavior without a real embedding model.
    """

    def __init__(self) -> None:
        pass

    def __call__(self, input: Documents) -> Embeddings:
        return [[float(keyword in text.lower()) for keyword in _KEYWORDS] for text in input]

    @staticmethod
    def name() -> str:
        return "keyword-stub-embedding-function"


def test_get_or_create_collection_persists_across_calls(tmp_path) -> None:
    collection = get_or_create_collection(tmp_path, "passages", KeywordStubEmbeddingFunction())
    add_chunks(collection, [{"text": "revenue grew", "ticker": "AAPL", "chunk_index": 0}])

    reopened = get_or_create_collection(tmp_path, "passages", KeywordStubEmbeddingFunction())

    assert reopened.count() == 1


def test_add_chunks_upserts_instead_of_duplicating(tmp_path) -> None:
    collection = get_or_create_collection(tmp_path, "passages", KeywordStubEmbeddingFunction())
    chunk = {"text": "revenue grew 8%", "ticker": "AAPL", "chunk_index": 0}

    add_chunks(collection, [chunk])
    add_chunks(collection, [chunk])

    assert collection.count() == 1


def test_add_chunks_does_not_collide_when_metadata_matches_but_text_differs(tmp_path) -> None:
    """Regression test: two different documents sharing ticker/doc_type/chunk_index
    must not silently overwrite each other (found during Week 9's live verification)."""
    collection = get_or_create_collection(tmp_path, "passages", KeywordStubEmbeddingFunction())

    add_chunks(
        collection,
        [
            {"text": "Apple's revenue grew 8% year over year.", "ticker": "AAPL", "chunk_index": 0},
            {"text": "Quarterly earnings exceeded expectations.", "ticker": "AAPL", "chunk_index": 0},
        ],
    )

    assert collection.count() == 2


def test_query_collection_ranks_by_keyword_similarity(tmp_path) -> None:
    collection = get_or_create_collection(tmp_path, "passages", KeywordStubEmbeddingFunction())
    add_chunks(
        collection,
        [
            {"text": "Revenue and earnings both grew this quarter.", "ticker": "AAPL", "chunk_index": 0},
            {"text": "The interest rate was raised again.", "ticker": "MACRO", "chunk_index": 0},
        ],
    )

    results = query_collection(collection, "How did earnings and revenue look?", n_results=2)

    assert results[0]["text"].startswith("Revenue and earnings")


def test_query_collection_respects_metadata_filter(tmp_path) -> None:
    collection = get_or_create_collection(tmp_path, "passages", KeywordStubEmbeddingFunction())
    add_chunks(
        collection,
        [
            {"text": "AAPL revenue grew.", "ticker": "AAPL", "chunk_index": 0},
            {"text": "MSFT revenue grew.", "ticker": "MSFT", "chunk_index": 0},
        ],
    )

    results = query_collection(collection, "revenue growth", n_results=5, where={"ticker": "AAPL"})

    assert len(results) == 1
    assert results[0]["metadata"]["ticker"] == "AAPL"


def test_query_collection_returns_distance_and_metadata(tmp_path) -> None:
    collection = get_or_create_collection(tmp_path, "passages", KeywordStubEmbeddingFunction())
    add_chunks(collection, [{"text": "revenue grew", "ticker": "AAPL", "chunk_index": 0}])

    results = query_collection(collection, "revenue", n_results=1)

    assert "distance" in results[0]
    assert results[0]["metadata"]["ticker"] == "AAPL"
