"""Listing and fetching a company's SEC filings."""

from __future__ import annotations

from sec_thesis.models.filing import FilingRecord
from sec_thesis.sec_client import SECClient
from sec_thesis.storage.filings_db import FilingsDB

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"


def _filing_url(cik: str, accession_number: str, primary_document: str) -> str:
    """Build a filing document's real URL from its accession number.

    Verified against the live API: CIK with leading zeros stripped, the
    accession number's dashes removed, then the primary document path.
    """
    cik_no_zeros = str(int(cik))
    accession_no_dashes = accession_number.replace("-", "")
    return f"{ARCHIVES_BASE}/{cik_no_zeros}/{accession_no_dashes}/{primary_document}"


def parse_filings(ticker: str, cik: str, submissions: dict) -> list[FilingRecord]:
    """Turn a submissions payload's columnar "filings.recent" into records.

    Pure function — no network — so it's testable with a small hand-built
    fixture, the same shape ai_finance_course.edgar used in Week 4.
    """
    recent = submissions["filings"]["recent"]
    records = []
    for form, filing_date, primary_document, accession_number in zip(
        recent["form"], recent["filingDate"], recent["primaryDocument"], recent["accessionNumber"]
    ):
        records.append(
            FilingRecord(
                ticker=ticker,
                cik=cik,
                accession_number=accession_number,
                form=form,
                filing_date=filing_date,
                primary_document=primary_document,
                source_url=_filing_url(cik, accession_number, primary_document),
            )
        )
    return records


def list_filings(
    client: SECClient,
    db: FilingsDB,
    ticker: str,
    cik: str,
    forms: list[str] | None = None,
) -> list[FilingRecord]:
    """Fetch a company's recent filings, index them in DuckDB, and return them.

    Args:
        client: A configured SECClient.
        db: The filings index to record results in.
        ticker: The company's ticker.
        cik: The company's zero-padded 10-digit CIK.
        forms: If given, only return filings of these form types
            (e.g. ["10-K", "10-Q", "8-K"]) — filtered after indexing, so
            the full filing history is still cached in DuckDB either way.

    Returns:
        The matching filings, most recent first.
    """
    submissions = client.get_json(SUBMISSIONS_URL.format(cik=cik))
    records = parse_filings(ticker, cik, submissions)
    for record in records:
        db.upsert(record)
    return db.query_by_ticker(ticker, forms=forms)


def fetch_filings(client: SECClient, db: FilingsDB, ticker: str) -> list[FilingRecord]:
    """Download and cache every indexed filing for a ticker, recording local paths.

    Requires list_filings to have been run first (or run now) so the
    filing index for this ticker already exists.

    Args:
        client: A configured SECClient.
        db: The filings index.
        ticker: The company's ticker.

    Returns:
        The filings, with local_path now set for each.
    """
    updated = []
    for record in db.query_by_ticker(ticker):
        local_path = client.download(record.source_url)
        record = record.model_copy(update={"local_path": str(local_path)})
        db.upsert(record)
        updated.append(record)
    return updated
