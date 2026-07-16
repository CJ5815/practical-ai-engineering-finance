"""Small helpers for calling the SEC EDGAR API, used during the API weeks."""

from __future__ import annotations

import json
import time

import httpx
from pydantic import BaseModel

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_BASE = "https://data.sec.gov/submissions/"
SUBMISSIONS_URL = SUBMISSIONS_BASE + "CIK{cik}.json"


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


def _extract_filings(columnar: dict, limit: int) -> list[FilingRecord]:
    """Zip a columnar filings dict into a list of validated FilingRecords.

    Both "filings.recent" and each paginated older-filings file (§3.3)
    use this same columnar shape: each field is its own parallel list,
    and row i across every list describes one filing.
    """
    rows = zip(
        columnar["form"],
        columnar["filingDate"],
        columnar["primaryDocument"],
        columnar["accessionNumber"],
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


def extract_recent_filings(submissions: dict, limit: int = 5) -> list[FilingRecord]:
    """Extract the most recent filings as validated records.

    Args:
        submissions: The payload returned by fetch_submissions.
        limit: Maximum number of recent filings to return.

    Returns:
        Up to `limit` FilingRecord objects, most recent first.
    """
    return _extract_filings(submissions["filings"]["recent"], limit=limit)


def save_filings_json(filings: list[FilingRecord], path: str) -> None:
    """Save filings as a clean JSON array.

    Args:
        filings: Validated filing records, such as from extract_recent_filings.
        path: Where to write the JSON file.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump([filing.model_dump() for filing in filings], f, indent=2)


class EdgarAPIError(Exception):
    """Raised when SEC EDGAR returns an error response, or retries are exhausted."""


class EdgarClient:
    """A configured, reusable client for the SEC EDGAR API.

    Owns its own httpx.Client (User-Agent, timeout) and retries transient
    failures (429, 5xx, timeouts) with backoff, so callers don't have to
    re-implement that logic for every request.
    """

    def __init__(
        self,
        user_agent: str,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """Configure the client.

        Args:
            user_agent: A descriptive User-Agent, e.g. "Name email@example.com".
            timeout: Seconds to wait for a response before raising.
            max_retries: Retry attempts for transient failures, beyond the first try.
            backoff_seconds: Base delay between retries; doubles each attempt
                (ignored when the server sends a Retry-After header).
            transport: Optional httpx transport override, for testing with
                httpx.MockTransport instead of the real network.
        """
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> EdgarClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._client.close()

    def _request_with_retries(self, url: str) -> httpx.Response:
        """GET a URL, retrying transient failures with backoff.

        Retries on 429, 5xx, and network-level errors (timeouts,
        connection failures). Does not retry other 4xx responses, such
        as 404 — retrying a request that will never succeed just wastes time.

        Raises:
            EdgarAPIError: For a non-retryable error response, or once
                retries are exhausted.
        """
        last_error = ""
        response: httpx.Response | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.get(url)
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                response = None
            else:
                if response.status_code < 400:
                    return response
                if response.status_code != 429 and response.status_code < 500:
                    raise EdgarAPIError(
                        f"GET {url} failed with {response.status_code}: {response.text[:200]}"
                    )
                last_error = f"HTTP {response.status_code}"

            if attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After") if response is not None else None
                wait_seconds = (
                    float(retry_after) if retry_after else self.backoff_seconds * (2**attempt)
                )
                time.sleep(wait_seconds)

        raise EdgarAPIError(f"GET {url} failed after {self.max_retries + 1} attempts: {last_error}")

    def find_cik(self, ticker: str) -> str:
        """Look up a company's zero-padded CIK from its ticker."""
        response = self._request_with_retries(TICKERS_URL)
        return find_cik(ticker, response.json())

    def get_recent_filings(self, cik: str, limit: int = 5) -> list[FilingRecord]:
        """Fetch a company's most recent filings (up to SEC's ~1000-row cap)."""
        response = self._request_with_retries(SUBMISSIONS_URL.format(cik=cik))
        return extract_recent_filings(response.json(), limit=limit)

    def get_older_filings(self, cik: str, page: int = 0, limit: int = 5) -> list[FilingRecord]:
        """Fetch a page of older filings, beyond what get_recent_filings includes.

        SEC paginates filing history older than the "recent" cutoff into
        separate files, listed under submissions["filings"]["files"].

        Args:
            cik: A zero-padded 10-digit CIK.
            page: Which page of filings["files"] to fetch (0 is the oldest cutoff).
            limit: Maximum number of filings to return from that page.

        Returns:
            Up to `limit` FilingRecord objects from that page, or an empty
            list if the company has no page at that index.
        """
        submissions = self._request_with_retries(SUBMISSIONS_URL.format(cik=cik)).json()
        files = submissions["filings"]["files"]
        if page >= len(files):
            return []
        page_response = self._request_with_retries(SUBMISSIONS_BASE + files[page]["name"])
        return _extract_filings(page_response.json(), limit=limit)

    def get_filings_for_ticker(self, ticker: str, limit: int = 5) -> list[FilingRecord]:
        """Convenience: look up a ticker's CIK, then fetch its recent filings."""
        cik = self.find_cik(ticker)
        return self.get_recent_filings(cik, limit=limit)
