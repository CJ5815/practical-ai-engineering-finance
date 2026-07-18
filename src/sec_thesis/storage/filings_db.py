"""A thin DuckDB wrapper for the filing index.

Storing the filing index in DuckDB (rather than just cached JSON files)
makes it real, queryable structured data from Phase 1 onward — filter by
ticker or form type with SQL instead of re-parsing JSON every time.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from sec_thesis.models.filing import FilingRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS filings (
    ticker VARCHAR,
    cik VARCHAR,
    accession_number VARCHAR PRIMARY KEY,
    form VARCHAR,
    filing_date VARCHAR,
    primary_document VARCHAR,
    source_url VARCHAR,
    local_path VARCHAR
)
"""

_UPSERT = """
INSERT INTO filings
    (ticker, cik, accession_number, form, filing_date, primary_document, source_url, local_path)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (accession_number) DO UPDATE SET
    ticker = EXCLUDED.ticker,
    cik = EXCLUDED.cik,
    form = EXCLUDED.form,
    filing_date = EXCLUDED.filing_date,
    primary_document = EXCLUDED.primary_document,
    source_url = EXCLUDED.source_url,
    local_path = EXCLUDED.local_path
"""


class FilingsDB:
    """A connection to the filings index, backed by a DuckDB file (or :memory:)."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(str(path))
        self._conn.execute(_SCHEMA)

    def __enter__(self) -> FilingsDB:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._conn.close()

    def upsert(self, filing: FilingRecord) -> None:
        """Insert a filing, or update it if its accession number already exists."""
        self._conn.execute(
            _UPSERT,
            [
                filing.ticker,
                filing.cik,
                filing.accession_number,
                filing.form,
                filing.filing_date,
                filing.primary_document,
                filing.source_url,
                filing.local_path,
            ],
        )

    def query_by_ticker(self, ticker: str, forms: list[str] | None = None) -> list[FilingRecord]:
        """Fetch filings for a ticker, optionally filtered by form type."""
        if forms:
            placeholders = ", ".join("?" * len(forms))
            rows = self._conn.execute(
                f"SELECT * FROM filings WHERE ticker = ? AND form IN ({placeholders}) "
                "ORDER BY filing_date DESC",
                [ticker, *forms],
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM filings WHERE ticker = ? ORDER BY filing_date DESC",
                [ticker],
            ).fetchall()

        columns = [
            "ticker",
            "cik",
            "accession_number",
            "form",
            "filing_date",
            "primary_document",
            "source_url",
            "local_path",
        ]
        return [FilingRecord(**dict(zip(columns, row))) for row in rows]
