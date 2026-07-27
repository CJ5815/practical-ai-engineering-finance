"""Week 9: index sample company passages in a real, persistent vector database.

Indexes data/sample/passages.json (the same illustrative Apple/Microsoft/
macro passages from Week 8's cosine-similarity exercise) into a ChromaDB
collection persisted under data/processed/chroma/, using a real
sentence-transformers model to embed them. No API key needed — everything
here runs locally, same as Week 8.

Run this file directly:

    python examples/week-09/build_passage_index.py
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_finance_course.chunking import chunk_document
from ai_finance_course.vector_store import add_chunks, get_or_create_collection, query_collection

PASSAGES_PATH = Path("data/sample/passages.json")
PERSIST_PATH = Path("data/processed/chroma")
COLLECTION_NAME = "sample_passages"


def main() -> None:
    passages = json.loads(PASSAGES_PATH.read_text(encoding="utf-8"))

    collection = get_or_create_collection(PERSIST_PATH, COLLECTION_NAME)

    for passage in passages:
        metadata = {"ticker": passage["ticker"], "doc_type": passage["doc_type"]}
        chunks = chunk_document(passage["text"], metadata, chunk_size=500, overlap=50)
        add_chunks(collection, chunks)

    print(f"Indexed {collection.count()} chunks from {len(passages)} passages.\n")

    query = "did the company beat earnings expectations?"
    print(f"Query: {query!r} (no filter)")
    for result in query_collection(collection, query, n_results=3):
        print(f"  [{result['distance']:.3f}] ({result['metadata']['ticker']}) {result['text']}")

    print(f"\nQuery: {query!r} (filtered to AAPL only)")
    for result in query_collection(collection, query, n_results=3, where={"ticker": "AAPL"}):
        print(f"  [{result['distance']:.3f}] ({result['metadata']['ticker']}) {result['text']}")


if __name__ == "__main__":
    main()
