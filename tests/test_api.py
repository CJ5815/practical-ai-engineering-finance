"""Tests for api.py.

Uses FastAPI's TestClient plus app.dependency_overrides to replace the
real collection and the real LLM call — no real vector store on disk, no
real API key, no network. The `client` fixture below is a real yield-style
teardown fixture (Week 13 §Exercise 2): it clears dependency_overrides
after every test so one test's override can never leak into the next.
"""

from __future__ import annotations

import json
import logging

import pytest

pytest.importorskip("chromadb", reason="requires the [rag] extra: pip install -e '.[rag]'")
pytest.importorskip("fastapi", reason="requires the [api] extra: pip install -e '.[api]'")

from fastapi.testclient import TestClient

from ai_finance_course.api import _ensure_sample_index, app, get_collection, get_generate
from ai_finance_course.vector_store import add_chunks, get_or_create_collection


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_returns_ok(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_returns_results(client, sample_collection) -> None:
    app.dependency_overrides[get_collection] = lambda: sample_collection

    response = client.post("/search", json={"query": "revenue", "n_results": 2})

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    assert all("text" in r and "distance" in r for r in results)


def test_search_respects_ticker_filter(client, sample_collection) -> None:
    app.dependency_overrides[get_collection] = lambda: sample_collection

    response = client.post("/search", json={"query": "news", "n_results": 5, "ticker": "AAPL"})

    assert response.status_code == 200
    results = response.json()
    assert all(r["ticker"] == "AAPL" for r in results)


def test_search_rejects_empty_query(client, sample_collection) -> None:
    app.dependency_overrides[get_collection] = lambda: sample_collection

    response = client.post("/search", json={"query": ""})

    assert response.status_code == 422


def test_ask_returns_answer_and_sources(client, sample_collection) -> None:
    app.dependency_overrides[get_collection] = lambda: sample_collection

    def stub_generate(prompt: str) -> str:
        return json.dumps({"answer": "Yes, revenue grew.", "citations": [1]})

    app.dependency_overrides[get_generate] = lambda: stub_generate

    response = client.post("/ask", json={"query": "Did revenue grow?", "n_results": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Yes, revenue grew."
    assert body["citations"] == [1]
    assert len(body["sources"]) == 1
    assert "text" in body["sources"][0]


def test_ask_returns_502_on_invalid_llm_response(client, sample_collection) -> None:
    app.dependency_overrides[get_collection] = lambda: sample_collection

    def broken_generate(prompt: str) -> str:
        return "not valid json at all"

    app.dependency_overrides[get_generate] = lambda: broken_generate

    response = client.post("/ask", json={"query": "Did revenue grow?"})

    assert response.status_code == 502


def test_log_requests_middleware_logs_unhandled_exceptions(client, sample_collection, caplog) -> None:
    """Regression test: found live against the deployed container — a
    missing LLM_API_KEY raises KeyError inside call_llm, which the
    original middleware silently let propagate past its own logging
    line. TestClient re-raises server exceptions by default (verified
    directly), so this asserts on the log record, not a response object."""
    app.dependency_overrides[get_collection] = lambda: sample_collection

    def raises_key_error(prompt: str) -> str:
        raise KeyError("LLM_API_KEY")

    app.dependency_overrides[get_generate] = lambda: raises_key_error

    with caplog.at_level(logging.ERROR, logger="ai_finance_course.api"), pytest.raises(KeyError):
        client.post("/ask", json={"query": "Did revenue grow?"})

    assert any("unhandled exception" in record.message for record in caplog.records)


def test_dependency_overrides_do_not_leak_between_tests(client, sample_collection) -> None:
    """Confirms the client fixture's yield-based teardown actually clears overrides —
    if the previous test's override leaked, get_collection would still be lambda: sample_collection
    from a *different* test's tmp_path, and this assertion would still pass by accident
    rather than by design. Checking the override dict itself is the real assertion."""
    assert get_collection not in app.dependency_overrides
    assert get_generate not in app.dependency_overrides


def test_search_uses_upserted_chunks(sample_collection) -> None:
    add_chunks(sample_collection, [{"text": "MSFT cloud revenue grew.", "ticker": "MSFT", "chunk_index": 0}])

    assert sample_collection.count() == 3


def test_log_requests_middleware_logs_request_details(client, caplog) -> None:
    """The middleware fires on every request even without a real embedding
    model or lifespan startup (verified empirically before writing this
    test — TestClient without `with` runs middleware but not lifespan)."""
    with caplog.at_level(logging.INFO, logger="ai_finance_course.api"):
        response = client.get("/health")

    assert response.status_code == 200
    assert any("GET /health -> 200" in record.message for record in caplog.records)


def test_ensure_sample_index_indexes_when_empty(tmp_path, keyword_stub_embedding_function) -> None:
    empty_collection = get_or_create_collection(tmp_path, "empty", keyword_stub_embedding_function)
    assert empty_collection.count() == 0

    _ensure_sample_index(empty_collection)

    assert empty_collection.count() == 8  # data/sample/passages.json has 8 short passages, 1 chunk each


def test_ensure_sample_index_skips_when_already_populated(sample_collection) -> None:
    count_before = sample_collection.count()
    assert count_before > 0

    _ensure_sample_index(sample_collection)

    assert sample_collection.count() == count_before
