"""A small FastAPI service exposing Week 9's retrieval and Week 10's RAG pipeline.

The collection and the LLM call are both FastAPI dependencies
(`Depends(...)`), not hardcoded inside the route functions — the same
"pass a dependency in, don't hardcode it" reasoning as every injected
`generate: Callable[[str], str]` since Week 7, just expressed through
FastAPI's dependency-injection system instead of a plain function
parameter. Tests override both with `app.dependency_overrides` (Week 14
§2.3) instead of hitting a real vector store or a real LLM.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

from chromadb.api.models.Collection import Collection
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from ai_finance_course.llm_client import call_llm
from ai_finance_course.rag import answer_question
from ai_finance_course.vector_store import get_or_create_collection, query_collection

PERSIST_PATH = Path("data/processed/chroma")
COLLECTION_NAME = "sample_passages"

app = FastAPI(title="Practical AI Engineering for Finance — Week 14 API")


@lru_cache
def get_collection() -> Collection:
    """The real, persisted Week 9 collection — loaded once per process, not per request.

    Recreating SentenceTransformerEmbeddingFunction on every request would
    reload the embedding model every time; lru_cache means get_or_create_collection
    only runs once. Tests override this entirely via app.dependency_overrides,
    so the cache is never a concern there.
    """
    return get_or_create_collection(PERSIST_PATH, COLLECTION_NAME)


def get_generate() -> Callable[[str], str]:
    """The real Anthropic call. Tests override this with a stub."""
    return call_llm


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    n_results: int = Field(default=3, ge=1, le=20)
    ticker: str | None = None


class SearchResult(BaseModel):
    text: str
    ticker: str | None
    doc_type: str | None
    distance: float


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    n_results: int = Field(default=3, ge=1, le=20)


class AskResponse(BaseModel):
    answer: str
    citations: list[int]
    sources: list[SearchResult]


@app.get("/health")
def health() -> dict[str, str]:
    """A minimal liveness check — no dependencies, no external calls."""
    return {"status": "ok"}


@app.post("/search", response_model=list[SearchResult])
def search(request: SearchRequest, collection: Collection = Depends(get_collection)) -> list[SearchResult]:
    """Retrieve relevant passages for a query — no LLM call, retrieval only."""
    where = {"ticker": request.ticker} if request.ticker else None
    results = query_collection(collection, request.query, n_results=request.n_results, where=where)
    return [
        SearchResult(
            text=result["text"],
            ticker=result["metadata"].get("ticker"),
            doc_type=result["metadata"].get("doc_type"),
            distance=result["distance"],
        )
        for result in results
    ]


@app.post("/ask", response_model=AskResponse)
def ask(
    request: AskRequest,
    collection: Collection = Depends(get_collection),
    generate: Callable[[str], str] = Depends(get_generate),
) -> AskResponse:
    """Retrieve evidence and generate a grounded, cited answer (Week 10's answer_question)."""
    try:
        result, evidence = answer_question(request.query, collection, generate, n_results=request.n_results)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"LLM response was invalid: {exc}") from exc

    sources = [
        SearchResult(
            text=evidence[citation - 1]["text"],
            ticker=evidence[citation - 1]["metadata"].get("ticker"),
            doc_type=evidence[citation - 1]["metadata"].get("doc_type"),
            distance=evidence[citation - 1]["distance"],
        )
        for citation in result.citations
    ]
    return AskResponse(answer=result.answer, citations=result.citations, sources=sources)
