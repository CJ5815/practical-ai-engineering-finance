# Project Instructions

## Project purpose

Build an evidence-based investment research system that uses SEC filings
to maintain an investment thesis, financial-driver model, catalyst path,
risk framework, and conviction history.

The first supported company is Apple, ticker AAPL, CIK 0000320193.
The design must support additional companies later.

## Technology

- Python 3.12
- uv or pip for dependency management
- httpx for HTTP requests
- BeautifulSoup or lxml for HTML parsing
- Pydantic for schemas and validation
- DuckDB for local structured storage
- Polars for tabular transformations
- pytest for testing
- Rich or Typer for the command-line interface
- Markdown and JSON for research outputs

Do not build a web application during the first implementation.

## Engineering rules

1. Work in small, testable phases.
2. Explain the intended changes before modifying files.
3. Do not fabricate SEC data, financial values, quotations, or citations.
4. Preserve the exact URL, filing date, accession number, form, section,
   and source text for extracted evidence.
5. Separate:
   - reported facts;
   - analyst assumptions;
   - model-generated inferences.
6. Use deterministic Python for calculations.
7. Use an LLM only for classification, extraction, comparison, synthesis,
   question generation, and red-team analysis.
8. All LLM outputs must conform to Pydantic schemas.
9. The SEC client must use an identifying User-Agent.
10. Use caching and conservative rate limiting.
11. Never overwrite previous thesis versions.
12. Every major module must have tests.
13. Do not add dependencies without explaining why.
14. Do not expose API keys in source code.
15. Update README.md after completing each phase.

## Initial architecture

src/sec_thesis/
    config.py
    cli.py
    sec_client.py
    cik.py
    filings.py
    filing_parser.py
    xbrl.py
    models/
    storage/
    llm/
    analysis/
    reporting/

tests/
data/
    raw/
    processed/
    research/
docs/

## Initial CLI goals

The following commands should eventually work:

    sec-thesis resolve-cik AAPL
    sec-thesis list-filings AAPL --forms 10-K,10-Q,8-K
    sec-thesis fetch-filings AAPL
    sec-thesis extract-sections AAPL
    sec-thesis build-thesis AAPL
    sec-thesis update-thesis AAPL
    sec-thesis show-catalysts AAPL

## Required quality controls

- Unit tests
- Integration tests with mocked SEC responses
- Schema validation
- Logging
- Retry handling
- Source traceability
- Filing-to-filing comparison
- Human approval before changing conviction or issuing a recommendation

## Implementation status

**Phase 1 (Week 18) — done:** `config.py`, `sec_client.py`, `cik.py`,
`filings.py`, `models/filing.py`, `storage/filings_db.py`, `cli.py` with
`resolve-cik`, `list-filings`, and `fetch-filings`. Fully deterministic,
no LLM involved.

**Not yet built:** `filing_parser.py`, `xbrl.py`, `llm/`, `analysis/`,
`reporting/`, and the `extract-sections`, `build-thesis`, `update-thesis`,
`show-catalysts` commands. These are candidates for later phases (Weeks
19+), each following rule 1 — small, testable phases, not one large jump.

This package is intentionally standalone: it does not import from
`ai_finance_course` (the course's teaching package), even though
`ai_finance_course.edgar` already implements similar SEC API patterns
(Week 4/5 of the course). `sec_thesis` is meant to work as a real,
extractable tool, not course scaffolding — so it re-implements what it
needs rather than depending on the course package.
