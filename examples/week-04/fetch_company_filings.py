"""Week 4: fetch a company's recent SEC filings and save a clean subset.

Requires SEC_USER_AGENT to be set in a .env file (see .env.example) —
SEC asks every automated caller to identify itself with a real contact.

Run this file directly:

    python examples/week-04/fetch_company_filings.py
"""

from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

from ai_finance_course.edgar import (
    extract_recent_filings,
    fetch_company_tickers,
    fetch_submissions,
    find_cik,
    save_filings_json,
)

TICKER = "AAPL"
OUTPUT_PATH = "aapl_recent_filings.json"


def main() -> None:
    load_dotenv()
    user_agent = os.environ["SEC_USER_AGENT"]

    # SEC's own policy: identify every caller with a real name/contact,
    # not a generic library default.
    with httpx.Client(headers={"User-Agent": user_agent}, timeout=10.0) as client:
        company_tickers = fetch_company_tickers(client)
        cik = find_cik(TICKER, company_tickers)
        submissions = fetch_submissions(client, cik)

    filings = extract_recent_filings(submissions, limit=5)

    print(f"Most recent filings for {TICKER} (CIK {cik}):")
    for filing in filings:
        print(f"  {filing.filing_date}  {filing.form:<6}  {filing.primary_document}")

    save_filings_json(filings, OUTPUT_PATH)
    print(f"\nSaved {len(filings)} filings to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
