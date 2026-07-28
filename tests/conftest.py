"""Shared test fixtures for ai_finance_course tests requiring the [rag] extra.

KeywordStubEmbeddingFunction stands in for a real sentence-transformers
model in tests — deterministic, no model download, no network. Same
reasoning as Week 7's injected generate: Callable[[str], str] for LLM
calls, applied to embedding functions (Week 9 §2.2).
"""

from __future__ import annotations

import pytest
from chromadb import Documents, EmbeddingFunction, Embeddings

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
