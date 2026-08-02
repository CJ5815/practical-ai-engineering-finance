"""Shared test fixtures.

KeywordStubEmbeddingFunction stands in for a real sentence-transformers
model in tests — deterministic, no model download, no network. Same
reasoning as Week 7's injected generate: Callable[[str], str] for LLM
calls, applied to embedding functions (Week 9 §2.2).

conftest.py loads for every test in this repository, not just the [rag]
ones — a student on Week 3 who has only run `pip install -e ".[dev]"`
still needs `pytest` to work for test_returns.py and test_analysis.py.
chromadb is therefore imported defensively: if it's missing, the
chromadb-dependent fixtures below simply aren't defined, rather than
crashing collection for the entire test suite (found live: a plain
`pip install -e ".[dev]"` without `[rag]` broke every test in the repo,
not just the rag-related ones, because this file failed to import at all).
"""

from __future__ import annotations

import pytest

try:
    from chromadb import Documents, EmbeddingFunction, Embeddings
except ImportError:
    EmbeddingFunction = None  # [rag] extra not installed


if EmbeddingFunction is not None:
    from ai_finance_course.vector_store import add_chunks, get_or_create_collection

    _KEYWORDS = ["revenue", "earnings", "rate", "interest"]

    class KeywordStubEmbeddingFunction(EmbeddingFunction):
        """Embeds text as a keyword-presence vector — deterministic, no model needed."""

        def __init__(self) -> None:
            pass

        def __call__(self, input: Documents) -> Embeddings:
            return [[float(keyword in text.lower()) for keyword in _KEYWORDS] for text in input]

        @staticmethod
        def name() -> str:
            return "keyword-stub-embedding-function"

    @pytest.fixture
    def keyword_stub_embedding_function() -> KeywordStubEmbeddingFunction:
        return KeywordStubEmbeddingFunction()

    @pytest.fixture
    def sample_collection(tmp_path, keyword_stub_embedding_function):
        """A small collection pre-populated with an AAPL and a MACRO chunk.

        Depends on tmp_path (built-in) and keyword_stub_embedding_function
        (this file) — fixtures composing other fixtures, not just plain
        helper functions, is what makes this a fixture rather than a
        _sample_collection() helper each test file previously had to define
        (and re-import tmp_path/embedding_function into) on its own.
        """
        collection = get_or_create_collection(tmp_path, "passages", keyword_stub_embedding_function)
        add_chunks(
            collection,
            [
                {"text": "AAPL revenue grew 8% this quarter.", "ticker": "AAPL", "chunk_index": 0},
                {"text": "The Fed raised interest rates.", "ticker": "MACRO", "chunk_index": 0},
            ],
        )
        return collection
