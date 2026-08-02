"""Week 20: extract a knowledge graph from real SEC filings using Claude.

Requires LLM_API_KEY and LLM_MODEL in a .env file (see .env.example) —
this script calls a real LLM (Anthropic's Messages API, via a direct
httpx POST, no SDK) to extract entities and relationships. It also
requires SEC_USER_AGENT in .env, and reuses sec_thesis's own SEC client
and filings cache (Week 18) to fetch a real Apple 10-K.

extract_relationships() itself is provider-agnostic; only _call_llm below
is Anthropic-specific — the same pattern as
examples/week-17/evaluate_company.py.

Run this file directly:

    python examples/week-20/build_company_graph.py
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

from sec_thesis.cik import resolve_cik
from sec_thesis.config import load_settings
from sec_thesis.filing_parser import extract_text
from sec_thesis.filings import fetch_filings, list_filings
from sec_thesis.graph import (
    build_graph,
    competitors_of,
    most_central_entities,
    save_graph,
    visualize_graph,
)
from sec_thesis.llm.extraction import extract_relationships
from sec_thesis.sec_client import SECClient
from sec_thesis.storage.filings_db import FilingsDB

TICKER = "AAPL"

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"

# A real 10-K's text can run to hundreds of thousands of characters; a
# production system would chunk and retrieve relevant sections (Weeks
# 9-11's RAG techniques). For this course exercise, truncate to a
# manageable prompt size instead.
MAX_FILING_TEXT_CHARS = 15_000


def _call_llm(prompt: str) -> str:
    """Call Anthropic's Messages API directly via httpx (no SDK dependency).

    This is the one Anthropic-specific piece — extract_relationships()
    itself just takes a generate: Callable[[str], str].
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


def main() -> None:
    load_dotenv()
    settings = load_settings()

    with SECClient(settings) as client, FilingsDB(settings.duckdb_path) as db:
        cik = resolve_cik(client, TICKER)
        list_filings(client, db, TICKER, cik, forms=["10-K"])
        fetch_filings(client, db, TICKER)
        filings = [f for f in db.query_by_ticker(TICKER) if f.local_path]

    most_recent = max(filings, key=lambda f: f.filing_date)
    print(f"Using {TICKER} {most_recent.form} filed {most_recent.filing_date}")

    html = Path(most_recent.local_path).read_text(encoding="utf-8", errors="ignore")
    text = extract_text(html)[:MAX_FILING_TEXT_CHARS]
    print(f"Extracted {len(text)} characters of filing text for the prompt.")

    result = extract_relationships(TICKER, text, generate=_call_llm)
    print(f"\nExtracted {len(result.entities)} entities and {len(result.relationships)} relationships:")
    for rel in result.relationships:
        print(f"  {rel.source} --[{rel.relation_type}]--> {rel.target}")
        print(f"    evidence: {rel.evidence!r}")

    graph = build_graph([result])

    print("\nMost central entities:")
    for name, score in most_central_entities(graph):
        print(f"  {name}: {score:.3f}")

    # The LLM chooses entity names freely (e.g. "Apple Inc." vs "Apple"), so
    # look up the filer's own node by ticker rather than assuming a name.
    filer = next((e for e in result.entities if e.ticker == TICKER), None)
    if filer is not None:
        print(f"\nCompetitors of {filer.name}: {competitors_of(graph, filer.name)}")

    graph_path = Path(settings.duckdb_path).parent / f"{TICKER}_graph.json"
    save_graph(graph, graph_path)
    print(f"\nSaved graph to {graph_path}")

    image_path = graph_path.with_suffix(".png")
    visualize_graph(graph, image_path)
    print(f"Saved visualization to {image_path}")


if __name__ == "__main__":
    main()
