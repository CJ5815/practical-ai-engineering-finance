import httpx
import pytest

from sec_thesis.cik import find_cik, resolve_cik
from sec_thesis.config import Settings
from sec_thesis.sec_client import SECClient

SAMPLE_TICKERS = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
}


def test_find_cik() -> None:
    assert find_cik("aapl", SAMPLE_TICKERS) == "0000320193"


def test_find_cik_not_found() -> None:
    with pytest.raises(ValueError, match="not found"):
        find_cik("ZZZZ", SAMPLE_TICKERS)


def test_resolve_cik(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE_TICKERS)

    settings = Settings(
        sec_user_agent="Test test@example.com",
        cache_dir=tmp_path / "cache",
        request_delay_seconds=0.0,
    )
    with SECClient(settings, transport=httpx.MockTransport(handler)) as client:
        cik = resolve_cik(client, "AAPL")

    assert cik == "0000320193"
