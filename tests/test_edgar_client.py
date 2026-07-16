import httpx
import pytest

from ai_finance_course.edgar import EdgarAPIError, EdgarClient

SAMPLE_SUBMISSIONS = {
    "filings": {
        "recent": {
            "form": ["10-K", "4"],
            "filingDate": ["2026-01-02", "2026-01-01"],
            "primaryDocument": ["10k.htm", "form4.xml"],
            "accessionNumber": ["0001-26-000001", "0001-26-000002"],
        },
        "files": [
            {"name": "CIK0000320193-submissions-001.json", "filingFrom": "1994-01-26"},
        ],
    }
}

SAMPLE_OLDER_PAGE = {
    "form": ["8-K"],
    "filingDate": ["2015-05-13"],
    "primaryDocument": ["8k.htm"],
    "accessionNumber": ["0001-15-000001"],
}

SAMPLE_TICKERS = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}


def _client(handler, **overrides) -> EdgarClient:
    kwargs = {"user_agent": "Test test@example.com", "backoff_seconds": 0.01, "max_retries": 2}
    kwargs.update(overrides)
    return EdgarClient(transport=httpx.MockTransport(handler), **kwargs)


def test_get_recent_filings_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE_SUBMISSIONS)

    with _client(handler) as client:
        filings = client.get_recent_filings("0000320193", limit=1)

    assert filings[0].form == "10-K"


def test_retries_on_429_then_succeeds() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, json={"error": "slow down"})
        return httpx.Response(200, json=SAMPLE_SUBMISSIONS)

    with _client(handler) as client:
        filings = client.get_recent_filings("0000320193", limit=1)

    assert calls["count"] == 2
    assert filings[0].form == "10-K"


def test_404_raises_without_retry() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(404, json={"error": "not found"})

    with _client(handler) as client:
        with pytest.raises(EdgarAPIError, match="404"):
            client.get_recent_filings("0000000000")

    assert calls["count"] == 1


def test_retries_exhausted_raises() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(500, json={"error": "server error"})

    with _client(handler, max_retries=2) as client:
        with pytest.raises(EdgarAPIError, match="failed after 3 attempts"):
            client.get_recent_filings("0000320193")

    assert calls["count"] == 3


def test_find_cik_via_client() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE_TICKERS)

    with _client(handler) as client:
        assert client.find_cik("aapl") == "0000320193"


def test_get_older_filings() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "submissions-001" in str(request.url):
            return httpx.Response(200, json=SAMPLE_OLDER_PAGE)
        return httpx.Response(200, json=SAMPLE_SUBMISSIONS)

    with _client(handler) as client:
        filings = client.get_older_filings("0000320193", page=0)

    assert filings[0].form == "8-K"


def test_get_older_filings_out_of_range() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE_SUBMISSIONS)

    with _client(handler) as client:
        filings = client.get_older_filings("0000320193", page=5)

    assert filings == []
