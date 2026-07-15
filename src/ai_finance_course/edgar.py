"""Small helpers for calling the SEC EDGAR API, used during the API weeks."""

from __future__ import annotations

import json

import httpx
from pydantic import BaseModel

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"


class FilingRecord(BaseModel):
    """One filing from a company's SEC submission history."""

    form: str
    filing_date: str
    primary_document: str
    accession_number: str


def fetch_company_tickers(client: httpx.Client) -> dict:
    """Fetch the SEC's full ticker-to-CIK mapping.

    Args:
        client: An httpx.Client configured with a descriptive User-Agent header.

    Returns:
        A dict keyed by arbitrary index, each value a dict with
        "cik_str", "ticker", and "title".
    """
    response = client.get(TICKERS_URL)
    response.raise_for_status()
    return response.json()


def find_cik(ticker: str, company_tickers: dict) -> str:
    """Find a company's zero-padded 10-digit CIK from its ticker.

    Args:
        ticker: A stock ticker, such as "AAPL". Case-insensitive.
        company_tickers: The mapping returned by fetch_company_tickers.

    Returns:
        The CIK as a 10-digit, zero-padded string, e.g. "0000320193".

    Raises:
        ValueError: If the ticker isn't found in company_tickers.
    """
    ticker = ticker.upper()
    for entry in company_tickers.values():
        if entry["ticker"] == ticker:
            return str(entry["cik_str"]).zfill(10)
    raise ValueError(f"Ticker {ticker!r} not found")


def fetch_submissions(client: httpx.Client, cik: str) -> dict:
    """Fetch a company's filing history from SEC EDGAR.

    Args:
        client: An httpx.Client configured with a descriptive User-Agent header.
        cik: A zero-padded 10-digit CIK, as returned by find_cik.

    Returns:
        The full submissions JSON payload, including company info and filings.
    """
    response = client.get(SUBMISSIONS_URL.format(cik=cik))
    response.raise_for_status()
    return response.json()


def extract_recent_filings(submissions: dict, limit: int = 5) -> list[FilingRecord]:
    """Extract the most recent filings as validated records.

    The SEC returns "filings.recent" in columnar form: each field is a
    separate list, and row i across every list describes one filing.
    This zips those parallel lists back into one record per filing.

    Args:
        submissions: The payload returned by fetch_submissions.
        limit: Maximum number of recent filings to return.

    Returns:
        Up to `limit` FilingRecord objects, most recent first.
    """
    recent = submissions["filings"]["recent"]
    rows = zip(
        recent["form"],
        recent["filingDate"],
        recent["primaryDocument"],
        recent["accessionNumber"],
    )
    return [
        FilingRecord(
            form=form,
            filing_date=filing_date,
            primary_document=primary_document,
            accession_number=accession_number,
        )
        for form, filing_date, primary_document, accession_number in list(rows)[:limit]
    ]


def save_filings_json(filings: list[FilingRecord], path: str) -> None:
    """Save filings as a clean JSON array.

    Args:
        filings: Validated filing records, such as from extract_recent_filings.
        path: Where to write the JSON file.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump([filing.model_dump() for filing in filings], f, indent=2)
