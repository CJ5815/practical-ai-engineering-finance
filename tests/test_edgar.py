import json

import pytest

from ai_finance_course.edgar import (
    FilingRecord,
    extract_recent_filings,
    find_cik,
    save_filings_json,
)


def test_find_cik() -> None:
    company_tickers = {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
    }

    assert find_cik("aapl", company_tickers) == "0000320193"


def test_find_cik_not_found() -> None:
    company_tickers = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}

    with pytest.raises(ValueError, match="not found"):
        find_cik("ZZZZ", company_tickers)


def test_extract_recent_filings() -> None:
    # "filings.recent" is columnar in the real API: each field is its own
    # parallel list, not a list of row-dicts.
    submissions = {
        "filings": {
            "recent": {
                "form": ["10-K", "4"],
                "filingDate": ["2026-01-02", "2026-01-01"],
                "primaryDocument": ["10k.htm", "form4.xml"],
                "accessionNumber": ["0001-26-000001", "0001-26-000002"],
            }
        }
    }

    filings = extract_recent_filings(submissions, limit=1)

    assert filings == [
        FilingRecord(
            form="10-K",
            filing_date="2026-01-02",
            primary_document="10k.htm",
            accession_number="0001-26-000001",
        )
    ]


def test_save_filings_json(tmp_path) -> None:
    filings = [
        FilingRecord(
            form="10-K",
            filing_date="2026-01-02",
            primary_document="10k.htm",
            accession_number="0001-26-000001",
        )
    ]
    path = tmp_path / "filings.json"

    save_filings_json(filings, str(path))

    saved = json.loads(path.read_text())
    assert saved == [
        {
            "form": "10-K",
            "filing_date": "2026-01-02",
            "primary_document": "10k.htm",
            "accession_number": "0001-26-000001",
        }
    ]
