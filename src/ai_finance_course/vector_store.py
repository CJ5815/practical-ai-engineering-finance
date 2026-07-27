"""A thin wrapper around ChromaDB, embedding with sentence-transformers.

The embedding function is injectable — the same "pass a function in, don't
hardcode a dependency" pattern used for LLM calls (Week 7's `generate:
Callable[[str], str]`). Tests pass a small deterministic stub instead of
loading a real model, so they run fast with no network call or model
download. Real callers get the real SentenceTransformerEmbeddingFunction
by default (see examples/week-09/build_passage_index.py).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from chromadb.api.models.Collection import Collection


class SentenceTransformerEmbeddingFunction(EmbeddingFunction):
    """Wraps a sentence-transformers model as a ChromaDB embedding function.

    The model loads once, in __init__ (Week 8 §2.3's "load once, reuse many
    times") — ChromaDB then calls this object automatically on every
    add()/query() call.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def __call__(self, input: Documents) -> Embeddings:
        return self.model.encode(list(input)).tolist()

    @staticmethod
    def name() -> str:
        return "sentence-transformer-embedding-function"


def get_or_create_collection(
    persist_path: str | Path,
    collection_name: str,
    embedding_function: EmbeddingFunction | None = None,
) -> Collection:
    """Open (or create) a persistent ChromaDB collection.

    Args:
        persist_path: Directory where the collection's data is stored on disk.
        collection_name: Name of the collection within that directory.
        embedding_function: Defaults to a real sentence-transformers model
            (all-MiniLM-L6-v2). Pass a stub in tests to avoid downloading
            model weights or running real inference.

    Returns:
        A ChromaDB Collection ready for add_chunks()/query_collection() calls.
    """
    if embedding_function is None:
        embedding_function = SentenceTransformerEmbeddingFunction()

    client = chromadb.PersistentClient(path=str(persist_path))
    return client.get_or_create_collection(name=collection_name, embedding_function=embedding_function)


def _chunk_id(chunk: dict) -> str:
    """A stable id derived from the chunk's own text, not just its metadata.

    Hashing the text — rather than relying on ticker/doc_type/chunk_index
    alone — matters because two different source documents commonly share
    the same ticker and doc_type (e.g. two different filings' "risk"
    sections). Without the text hash, both would resolve to the same id and
    silently overwrite each other via upsert instead of both being stored.
    Re-adding the exact same chunk still produces the exact same id, so
    re-running indexing stays idempotent rather than creating duplicates.
    """
    text_hash = hashlib.sha256(chunk["text"].encode("utf-8")).hexdigest()[:12]
    ticker = chunk.get("ticker", "doc")
    doc_type = chunk.get("doc_type", "na")
    chunk_index = chunk.get("chunk_index", 0)
    return f"{ticker}-{doc_type}-{chunk_index}-{text_hash}"


def add_chunks(collection: Collection, chunks: list[dict]) -> None:
    """Add pre-chunked documents (from chunking.chunk_document) to a collection.

    Args:
        collection: A collection from get_or_create_collection.
        chunks: Dicts with a "text" key (the chunk's content) — every other
            key is stored as metadata (e.g. ticker, doc_type, chunk_index).

    Adding the exact same chunk again overwrites it rather than duplicating
    it (§_chunk_id); a chunk with different text is always stored separately,
    even if it shares the same ticker and doc_type as another chunk.
    """
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [{key: value for key, value in chunk.items() if key != "text"} for chunk in chunks]
    ids = [_chunk_id(chunk) for chunk in chunks]
    collection.upsert(documents=documents, metadatas=metadatas, ids=ids)


def query_collection(
    collection: Collection,
    query: str,
    n_results: int = 3,
    where: dict | None = None,
) -> list[dict]:
    """Query a collection and return results as plain dicts, most relevant first.

    Args:
        collection: A collection from get_or_create_collection.
        query: The natural-language question or search text.
        n_results: Maximum number of results to return.
        where: Optional metadata filter, e.g. {"ticker": "AAPL"}.

    Returns:
        A list of {"text", "metadata", "distance"} dicts, in the order
        ChromaDB returns them (most relevant first). Lower distance means
        more relevant — the same "closer is more similar" idea Week 8's
        cosine similarity taught by hand, now computed by the vector store.
    """
    results = collection.query(query_texts=[query], n_results=n_results, where=where)
    return [
        {"text": doc, "metadata": metadata, "distance": distance}
        for doc, metadata, distance in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        )
    ]
