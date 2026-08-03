"""A small FastAPI service exposing Week 9's retrieval and Week 10's RAG pipeline.

The collection and the LLM call are both FastAPI dependencies
(`Depends(...)`), not hardcoded inside the route functions — the same
"pass a dependency in, don't hardcode it" reasoning as every injected
`generate: Callable[[str], str]` since Week 7, just expressed through
FastAPI's dependency-injection system instead of a plain function
parameter. Tests override both with `app.dependency_overrides` (Week 14
§2.3) instead of hitting a real vector store or a real LLM.

Week 15 adds three things on top of Week 14: configuration consolidated
into settings.py rather than read ad hoc from os.environ in multiple
places, request logging, and a startup step that indexes the sample
passages if the collection is empty — so `docker build` + `docker run`
alone produces a working, searchable API with no separate indexing
command (Week 15's "fully reproducible local deployment").
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from functools import lru_cache, partial
from pathlib import Path

from chromadb.api.models.Collection import Collection
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from ai_finance_course.chunking import chunk_document
from ai_finance_course.llm_client import call_llm
from ai_finance_course.logging_config import configure_logging
from ai_finance_course.rag import answer_question
from ai_finance_course.settings import Settings, load_settings
from ai_finance_course.vector_store import add_chunks, get_or_create_collection, query_collection

SAMPLE_PASSAGES_PATH = Path("data/sample/passages.json")

logger = logging.getLogger("ai_finance_course.api")


@lru_cache
def get_settings() -> Settings:
    return load_settings()


@lru_cache
def get_collection() -> Collection:
    """The real, persisted Week 9 collection — loaded once per process, not per request.

    Recreating SentenceTransformerEmbeddingFunction on every request would
    reload the embedding model every time; lru_cache means get_or_create_collection
    only runs once. Tests override this entirely via app.dependency_overrides,
    so the cache is never a concern there.
    """
    settings = get_settings()
    return get_or_create_collection(settings.persist_path, settings.collection_name)


def get_generate() -> Callable[[str], str]:
    """The real Anthropic call, bound to settings. Tests override this with a stub."""
    settings = get_settings()
    return partial(call_llm, api_key=settings.llm_api_key, model=settings.llm_model)


def _ensure_sample_index(collection: Collection) -> None:
    """Index the sample passages into `collection` if it's empty.

    Takes the collection as a parameter rather than calling get_collection()
    itself — the same "pass it in, don't reach for it" reasoning as every
    Depends(...) in this file, and it means this function is directly
    testable with a stub collection, no monkeypatching required.
    """
    if collection.count() > 0:
        logger.info("Collection already has %d chunks; skipping startup indexing.", collection.count())
        return

    passages = json.loads(SAMPLE_PASSAGES_PATH.read_text(encoding="utf-8"))
    for passage in passages:
        metadata = {"ticker": passage["ticker"], "doc_type": passage["doc_type"]}
        chunks = chunk_document(passage["text"], metadata, chunk_size=500, overlap=50)
        add_chunks(collection, chunks)
    logger.info("Indexed %d chunks from %d sample passages on startup.", collection.count(), len(passages))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once at process startup (and only when the app is used as a
    context manager — `with TestClient(app) as client:` — not on a plain
    `TestClient(app)`, which is why this course's tests never trigger a
    real embedding-model load; see Week 15 §1.3)."""
    configure_logging(get_settings().log_level)
    _ensure_sample_index(get_collection())
    yield


app = FastAPI(title="Practical AI Engineering for Finance API", lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Logs method, path, status code, and duration for every request.

    Wraps call_next in try/except deliberately — found live, against the
    deployed container, that an unhandled exception (a missing
    LLM_API_KEY) propagates straight through this middleware, so the
    unwrapped version's logging line after call_next never runs. A
    request that crashed is exactly the one you most need logged.
    """
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.monotonic() - start) * 1000
        logger.exception(
            "%s %s -> unhandled exception (%.1fms)", request.method, request.url.path, duration_ms
        )
        raise
    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        "%s %s -> %s (%.1fms)", request.method, request.url.path, response.status_code, duration_ms
    )
    return response


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
