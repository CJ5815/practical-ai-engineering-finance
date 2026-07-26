"""The sec-thesis command-line interface.

Phase 1 wires up the first three commands from CLAUDE.md's CLI goals:
resolve-cik, list-filings, fetch-filings. Phase 2 (Week 20) adds
extract-relationships and show-graph. Later phases add build-thesis,
update-thesis, show-catalysts.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.table import Table

from sec_thesis.cik import resolve_cik
from sec_thesis.config import load_settings
from sec_thesis.filing_parser import extract_text
from sec_thesis.filings import fetch_filings, list_filings
from sec_thesis.graph import (
    build_graph,
    load_graph,
    most_central_entities,
    save_graph,
    visualize_graph,
)
from sec_thesis.llm.extraction import extract_relationships
from sec_thesis.sec_client import SECClient
from sec_thesis.storage.filings_db import FilingsDB

app = typer.Typer(help="sec_thesis: an evidence-based investment research CLI.")
console = Console()

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"

# A real 10-K's text can run to hundreds of thousands of characters; a
# production system would chunk and retrieve relevant sections (Weeks
# 9-11's RAG techniques). For this course exercise, truncate to a
# manageable prompt size instead.
MAX_FILING_TEXT_CHARS = 15_000


def _call_llm(prompt: str) -> str:
    """Call Anthropic's Messages API directly via httpx (no SDK dependency).

    Same pattern as examples/week-17/evaluate_company.py's _call_llm —
    extract_relationships() itself just takes a generate: Callable[[str], str].
    """
    api_key = os.environ["LLM_API_KEY"]
    model = os.environ["LLM_MODEL"]

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            ANTHROPIC_MESSAGES_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()

        for block in data["content"]:
            if block["type"] == "text":
                return block["text"]
        raise ValueError(f"No text block in response: {data}")


def _graph_path(settings, ticker: str) -> Path:
    return Path(settings.duckdb_path).parent / f"{ticker.upper()}_graph.json"


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


@app.command("extract-relationships")
def extract_relationships_command(ticker: str) -> None:
    """Extract entities/relationships from a company's cached filings and save a graph.

    Requires fetch-filings to have been run first (so cached filing text
    exists), and LLM_API_KEY/LLM_MODEL set in .env.
    """
    settings = load_settings()
    ticker = ticker.upper()

    with FilingsDB(settings.duckdb_path) as db:
        filings = [f for f in db.query_by_ticker(ticker) if f.local_path]

    if not filings:
        console.print(f"No cached filings for {ticker}. Run fetch-filings first.")
        raise typer.Exit(code=1)

    results = []
    for filing in filings:
        html = Path(filing.local_path).read_text(encoding="utf-8", errors="ignore")
        text = extract_text(html)[:MAX_FILING_TEXT_CHARS]
        results.append(extract_relationships(ticker, text, _call_llm))

    graph = build_graph(results)
    save_graph(graph, _graph_path(settings, ticker))

    console.print(
        f"Extracted {graph.number_of_nodes()} entities and {graph.number_of_edges()} "
        f"relationships from {len(filings)} filings for {ticker}."
    )


@app.command("show-graph")
def show_graph_command(ticker: str) -> None:
    """Print a company's extracted relationship graph and save a visualization.

    Requires extract-relationships to have been run first.
    """
    settings = load_settings()
    ticker = ticker.upper()
    graph_path = _graph_path(settings, ticker)

    if not graph_path.exists():
        console.print(f"No saved graph for {ticker}. Run extract-relationships first.")
        raise typer.Exit(code=1)

    graph = load_graph(graph_path)

    table = Table(title=f"{ticker} relationships")
    table.add_column("Source")
    table.add_column("Relation")
    table.add_column("Target")
    for source, target, data in graph.edges(data=True):
        table.add_row(source, data.get("relation_type", ""), target)
    console.print(table)

    console.print("\n[bold]Most central entities:[/bold]")
    for name, score in most_central_entities(graph):
        console.print(f"  {name}: {score:.3f}")

    image_path = graph_path.with_suffix(".png")
    visualize_graph(graph, image_path)
    console.print(f"\nSaved visualization to {image_path}")


if __name__ == "__main__":
    app()
