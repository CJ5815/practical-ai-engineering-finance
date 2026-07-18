from sec_thesis.models.filing import FilingRecord
from sec_thesis.storage.filings_db import FilingsDB

FILING_10K = FilingRecord(
    ticker="AAPL",
    cik="0000320193",
    accession_number="0001-26-000001",
    form="10-K",
    filing_date="2026-01-02",
    primary_document="10k.htm",
    source_url="https://www.sec.gov/Archives/edgar/data/320193/10k.htm",
)

FILING_10Q = FilingRecord(
    ticker="AAPL",
    cik="0000320193",
    accession_number="0001-26-000002",
    form="10-Q",
    filing_date="2026-02-01",
    primary_document="10q.htm",
    source_url="https://www.sec.gov/Archives/edgar/data/320193/10q.htm",
)


def test_upsert_and_query_by_ticker() -> None:
    with FilingsDB() as db:
        db.upsert(FILING_10K)
        db.upsert(FILING_10Q)

        results = db.query_by_ticker("AAPL")

    assert len(results) == 2
    assert results[0].accession_number == "0001-26-000002"  # most recent first


def test_query_by_ticker_filtered_by_form() -> None:
    with FilingsDB() as db:
        db.upsert(FILING_10K)
        db.upsert(FILING_10Q)

        results = db.query_by_ticker("AAPL", forms=["10-K"])

    assert len(results) == 1
    assert results[0].form == "10-K"


def test_upsert_updates_existing_record() -> None:
    with FilingsDB() as db:
        db.upsert(FILING_10K)

        updated = FILING_10K.model_copy(update={"local_path": "data/raw/abc123.html"})
        db.upsert(updated)

        results = db.query_by_ticker("AAPL")

    assert len(results) == 1
    assert results[0].local_path == "data/raw/abc123.html"


def test_persists_to_file(tmp_path) -> None:
    db_path = tmp_path / "sec_thesis.duckdb"

    with FilingsDB(db_path) as db:
        db.upsert(FILING_10K)

    with FilingsDB(db_path) as db:
        results = db.query_by_ticker("AAPL")

    assert len(results) == 1
