import pytest

from ai_finance_course.chunking import chunk_document, chunk_text


def test_chunk_text_splits_into_overlapping_pieces() -> None:
    text = "0123456789" * 3  # 30 characters

    chunks = chunk_text(text, chunk_size=10, overlap=2)

    assert chunks[0] == text[0:10]
    assert chunks[1] == text[8:18]
    assert "".join(chunks) != text  # overlap means chunks aren't a clean partition


def test_chunk_text_covers_the_whole_document() -> None:
    text = "abcdefghij" * 5  # 50 characters

    chunks = chunk_text(text, chunk_size=12, overlap=3)

    assert text[-1] in chunks[-1]
    assert len(chunks) > 1


def test_chunk_text_handles_short_text_as_one_chunk() -> None:
    chunks = chunk_text("short text", chunk_size=500, overlap=50)

    assert chunks == ["short text"]


def test_chunk_text_rejects_overlap_not_smaller_than_chunk_size() -> None:
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=10, overlap=10)


def test_chunk_document_attaches_metadata_and_chunk_index() -> None:
    metadata = {"ticker": "AAPL", "form": "10-K"}

    chunks = chunk_document("word " * 200, metadata, chunk_size=100, overlap=10)

    assert len(chunks) > 1
    assert chunks[0]["ticker"] == "AAPL"
    assert chunks[0]["chunk_index"] == 0
    assert chunks[1]["chunk_index"] == 1
    assert "text" in chunks[0]


def test_chunk_document_does_not_mutate_the_original_metadata() -> None:
    metadata = {"ticker": "AAPL"}

    chunk_document("some document text", metadata, chunk_size=100, overlap=10)

    assert metadata == {"ticker": "AAPL"}


# Verified directly across all four combinations before writing this test
# (Week 13 §2.2): every chunk stays within chunk_size, and the last chunk
# always contains the document's final character, regardless of how
# chunk_size and overlap combine against a length that isn't a clean
# multiple of either.
@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(10, 2), (20, 5), (50, 0), (100, 25)],
)
def test_chunk_text_every_chunk_stays_within_size_limit(chunk_size: int, overlap: int) -> None:
    text = "x" * 237

    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    assert all(len(chunk) <= chunk_size for chunk in chunks)


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(10, 2), (20, 5), (50, 0), (100, 25)],
)
def test_chunk_text_last_chunk_contains_final_character(chunk_size: int, overlap: int) -> None:
    text = "x" * 237

    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    assert text[-1] in chunks[-1]
