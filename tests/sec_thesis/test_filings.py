from pathlib import Path

import httpx

from sec_thesis.config import Settings
from sec_thesis.filings import fetch_filings, list_filings, parse_filings
from sec_thesis.sec_client import SECClient
from sec_thesis.storage.filings_db import FilingsDB

SAMPLE_SUBMISSIONS = {
    "filings": {
        "recent": {
            "form": ["10-K", "4"],
            "filingDate": ["2026-01-02", "2026-01-01"],
            "primaryDocument": ["10k.htm", "form4.xml"],
            "accessionNumber": ["0001140361-26-025622", "0001140361-26-025620"],
        }
    }
}


def _settings(tmp_path) -> Settings:
    return Settings(
        sec_user_agent="Test test@example.com",
        cache_dir=tmp_path / "cache",
        request_delay_seconds=0.0,
    )


def test_parse_filings_builds_correct_url() -> None:
    records = parse_filings("AAPL", "0000320193", SAMPLE_SUBMISSIONS)

    assert len(records) == 2
    assert records[0].form == "10-K"
    assert records[0].source_url == (
        "https://www.sec.gov/Archives/edgar/data/320193/000114036126025622/10k.htm"
    )


def test_list_filings_indexes_and_filters(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE_SUBMISSIONS)

    with SECClient(_settings(tmp_path), transport=httpx.MockTransport(handler)) as client:
        with FilingsDB() as db:
            results = list_filings(client, db, "AAPL", "0000320193", forms=["10-K"])

    assert len(results) == 1
    assert results[0].form == "10-K"


def test_fetch_filings_downloads_and_records_local_path(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "submissions" in str(request.url):
            return httpx.Response(200, json=SAMPLE_SUBMISSIONS)
        return httpx.Response(200, content=b"<html>filing text</html>")

    with SECClient(_settings(tmp_path), transport=httpx.MockTransport(handler)) as client:
        with FilingsDB() as db:
            list_filings(client, db, "AAPL", "0000320193")
            updated = fetch_filings(client, db, "AAPL")

    assert len(updated) == 2
    assert all(record.local_path is not None for record in updated)
    for record in updated:
        assert Path(record.local_path).exists()
