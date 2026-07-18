"""The FilingRecord schema: a reported fact, not an assumption or inference.

CLAUDE.md rule 4: preserve the exact URL, filing date, accession number,
form, and section for extracted evidence. This schema is that record for
a filing's metadata; the extracted text/section itself arrives in a later
phase (filing_parser.py).
"""

from __future__ import annotations

from pydantic import BaseModel


class FilingRecord(BaseModel):
    """One filing in a company's SEC submission history."""

    ticker: str
    cik: str
    accession_number: str
    form: str
    filing_date: str
    primary_document: str
    source_url: str
    local_path: str | None = None
    """Set once fetch-filings has downloaded and cached the document."""
