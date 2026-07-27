"""Splitting documents into overlapping chunks, ready for a vector store."""

from __future__ import annotations


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks of roughly chunk_size characters.

    Args:
        text: The full document text to split.
        chunk_size: Target number of characters per chunk.
        overlap: Number of characters repeated between consecutive chunks,
            so a sentence spanning a chunk boundary isn't lost entirely.

    Returns:
        A list of chunks in order. The final chunk may be shorter than
        chunk_size.

    Raises:
        ValueError: If overlap is greater than or equal to chunk_size —
            chunks would never advance, looping forever.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + chunk_size])
        start += chunk_size - overlap
    return chunks


def chunk_document(
    text: str,
    metadata: dict[str, str],
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[dict]:
    """Split a document into chunks, each carrying a copy of its metadata.

    Args:
        text: The full document text to split.
        metadata: Fields describing the document (e.g. ticker, form,
            filing_date) — copied onto every chunk produced from it.
        chunk_size: Target number of characters per chunk.
        overlap: Number of characters repeated between consecutive chunks.

    Returns:
        One dict per chunk, each with "text" and "chunk_index" added to a
        copy of metadata — ready to hand to a vector store's add() call.
    """
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    return [{**metadata, "text": chunk, "chunk_index": i} for i, chunk in enumerate(chunks)]
