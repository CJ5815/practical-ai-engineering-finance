# Week 18: sec_thesis — Evidence-Based Investment Research (Phase 1)

> **Full lesson content:** This page is the day-by-day schedule and checklist. For the complete lesson — concept explanations, guided code walkthroughs, exercises, and the quiz — see [week-18_Practical_AI_Engineering_for_Finance.md](week-18_Practical_AI_Engineering_for_Finance.md).

## Objective

Build the foundation of `sec_thesis`, a standalone CLI tool that will
eventually maintain a full evidence-based investment thesis from SEC
filings. Phase 1 (this week): a caching, rate-limited, retrying SEC
client; CIK resolution; a DuckDB-backed filing index; and the first three
CLI commands.

The full project spec — architecture, engineering rules, and CLI goals —
lives in `src/sec_thesis/CLAUDE.md`.

## Required Output

A tested `sec-thesis` CLI with three working commands:

```text
sec-thesis resolve-cik AAPL
sec-thesis list-filings AAPL --forms 10-K,10-Q,8-K
sec-thesis fetch-filings AAPL
```

This is an **optional, advanced extension**, following Week 17. Phases 2–4
of `sec_thesis` (section extraction, LLM-assisted thesis building,
conviction tracking, catalyst/red-team analysis) are candidates for future
weeks, not part of this week's deliverable.

## Six-Day Schedule

### Day 1 — Project Scaffold and Configuration

- **0–10 minutes:** Review Week 17 and open the repository.
- **10–25 minutes:** Why `sec_thesis` is a standalone package, not built on `ai_finance_course`.
- **25–50 minutes:** `config.py` — settings loaded from `.env`.
- **50–60 minutes:** Record notes and commit the work.

### Day 2 — The SEC Client

- **0–10 minutes:** Reproduce yesterday's main idea without notes.
- **10–25 minutes:** Identifying User-Agent, retry-with-backoff, rate limiting.
- **25–50 minutes:** Disk-based response caching.
- **50–60 minutes:** Run checks, fix errors, and commit.

### Day 3 — CIK Resolution and the Filing Index

- **0–10 minutes:** Define the session's small deliverable.
- **10–25 minutes:** Ticker-to-CIK resolution.
- **25–50 minutes:** The DuckDB filing index (`storage/filings_db.py`).
- **50–60 minutes:** Document decisions and commit.

### Day 4 — Listing and Fetching Filings

- **0–10 minutes:** Reproduce yesterday's main idea without notes.
- **10–25 minutes:** Parsing SEC's columnar filings response into records.
- **25–50 minutes:** Fetching and caching raw filing documents.
- **50–60 minutes:** Run checks, fix errors, and commit.

### Day 5 — The CLI

- **0–10 minutes:** Define the session's small deliverable.
- **10–25 minutes:** Wiring `resolve-cik`, `list-filings`, `fetch-filings` with Typer and Rich.
- **25–50 minutes:** Integration tests with mocked SEC responses.
- **50–60 minutes:** Document decisions and commit.

### Day 6 — Testing Polish and the Roadmap

- **0–10 minutes:** Review unfinished work.
- **10–25 minutes:** Run the full CLI live against the real SEC API; confirm caching works.
- **25–45 minutes:** Update `README.md` (per `CLAUDE.md` rule 15); test and improve the deliverable.
- **45–55 minutes:** Write a short reflection:
    - What did I build?
    - What failed?
    - How did I fix it?
    - How would I explain it in an interview?
- **55–60 minutes:** Push the final commit.

## Completion Checklist

- [ ] I can explain the week's main concept in plain English.
- [ ] My code runs from a clean environment.
- [ ] I did not commit API keys or private data.
- [ ] Tests pass, including the mocked-SEC-response integration tests.
- [ ] `README.md` reflects Phase 1 (rule 15).
- [ ] All work is committed and pushed to GitHub.
