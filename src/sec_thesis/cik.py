"""Ticker to CIK resolution."""

from __future__ import annotations

from sec_thesis.sec_client import SECClient

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


def find_cik(ticker: str, company_tickers: dict) -> str:
    """Find a company's zero-padded 10-digit CIK from its ticker.

    Pure function — no network — so it's testable with a small hand-built
    fixture (tests/sec_thesis/test_cik.py).

    Args:
        ticker: A stock ticker, such as "AAPL". Case-insensitive.
        company_tickers: The mapping returned by SEC's company_tickers.json.

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


def resolve_cik(client: SECClient, ticker: str) -> str:
    """Fetch the ticker-to-CIK mapping and resolve one ticker.

    Args:
        client: A configured SECClient.
        ticker: A stock ticker, such as "AAPL".

    Returns:
        The CIK as a 10-digit, zero-padded string.
    """
    company_tickers = client.get_json(TICKERS_URL)
    return find_cik(ticker, company_tickers)
