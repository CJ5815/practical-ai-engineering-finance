"""Week 5: fetch a company's filings through the reusable EdgarClient.

Compare this to Week 4's examples/week-04/fetch_company_filings.py — same
task, but the client now owns configuration, timeouts, and retries, instead
of every call site managing its own httpx.Client.

Requires SEC_USER_AGENT to be set in a .env file (see .env.example).

Run this file directly:

    python examples/week-05/reliable_fetch.py
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from ai_finance_course.edgar import EdgarAPIError, EdgarClient, save_filings_json

TICKER = "AAPL"
OUTPUT_PATH = "aapl_recent_filings.json"


def main() -> None:
    load_dotenv()
    user_agent = os.environ["SEC_USER_AGENT"]

    try:
        with EdgarClient(user_agent=user_agent) as client:
            filings = client.get_filings_for_ticker(TICKER, limit=5)
    except EdgarAPIError as exc:
        # A clear, specific error instead of a raw httpx traceback.
        print(f"Could not fetch filings for {TICKER}: {exc}")
        return

    print(f"Most recent filings for {TICKER}:")
    for filing in filings:
        print(f"  {filing.filing_date}  {filing.form:<6}  {filing.primary_document}")

    save_filings_json(filings, OUTPUT_PATH)
    print(f"\nSaved {len(filings)} filings to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
