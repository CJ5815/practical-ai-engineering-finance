"""The sec-thesis command-line interface.

Phase 1 wires up the first three commands from CLAUDE.md's CLI goals:
resolve-cik, list-filings, fetch-filings. Later phases add
extract-sections, build-thesis, update-thesis, show-catalysts.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from sec_thesis.cik import resolve_cik
from sec_thesis.config import load_settings
from sec_thesis.filings import fetch_filings, list_filings
from sec_thesis.sec_client import SECClient
from sec_thesis.storage.filings_db import FilingsDB

app = typer.Typer(help="sec_thesis: an evidence-based investment research CLI.")
console = Console()


@app.command("resolve-cik")
def resolve_cik_command(ticker: str) -> None:
    """Resolve a ticker to its SEC CIK."""
    settings = load_settings()
    with SECClient(settings) as client:
        cik = resolve_cik(client, ticker)
    console.print(f"[bold]{ticker.upper()}[/bold] -> CIK {cik}")


@app.command("list-filings")
def list_filings_command(
    ticker: str,
    forms: str = typer.Option(
        None, "--forms", help="Comma-separated form types, e.g. 10-K,10-Q,8-K"
    ),
) -> None:
    """List a company's SEC filings, optionally filtered by form type."""
    settings = load_settings()
    form_list = [f.strip() for f in forms.split(",")] if forms else None

    with SECClient(settings) as client, FilingsDB(settings.duckdb_path) as db:
        cik = resolve_cik(client, ticker)
        results = list_filings(client, db, ticker.upper(), cik, forms=form_list)

    table = Table(title=f"{ticker.upper()} filings")
    table.add_column("Date")
    table.add_column("Form")
    table.add_column("Accession Number")
    for filing in results:
        table.add_row(filing.filing_date, filing.form, filing.accession_number)
    console.print(table)


@app.command("fetch-filings")
def fetch_filings_command(ticker: str) -> None:
    """Download and cache every indexed filing for a company."""
    settings = load_settings()

    with SECClient(settings) as client, FilingsDB(settings.duckdb_path) as db:
        cik = resolve_cik(client, ticker)
        list_filings(client, db, ticker.upper(), cik)
        updated = fetch_filings(client, db, ticker.upper())

    console.print(f"Fetched and cached {len(updated)} filings for {ticker.upper()}.")


if __name__ == "__main__":
    app()
