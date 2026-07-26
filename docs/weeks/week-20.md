# Week 20: Knowledge Graphs from SEC Filings with Claude

> **Full lesson content:** This page is the day-by-day schedule and checklist. For the complete lesson — concept explanations, guided code walkthroughs, exercises, and the quiz — see [week-20_Practical_AI_Engineering_for_Finance.md](week-20_Practical_AI_Engineering_for_Finance.md).

## Objective

Extend `sec_thesis` (Week 18) with its Phase 2: use Claude to extract
companies, people, and the relationships between them (competitors,
subsidiaries, executives, suppliers) from real SEC filings, and represent
those relationships as a queryable, visualizable knowledge graph with
NetworkX.

The full project spec — architecture, engineering rules, and CLI goals —
lives in `src/sec_thesis/CLAUDE.md`, which already listed `filing_parser.py`
and `llm/` as "not yet built... candidates for later phases."

## Required Output

Two new working `sec-thesis` commands, built on Week 18's cached filings:

```text
sec-thesis extract-relationships AAPL
sec-thesis show-graph AAPL
```

This is an **optional, advanced extension**, following Weeks 17–19.

## Four-Day Schedule

### Day 1 — What a Knowledge Graph Is

- **0–10 minutes:** Review Week 18 and open the repository.
- **10–25 minutes:** Why company relationships (competitors, suppliers, executives) fit a graph better than a flat table.
- **25–50 minutes:** Choosing NetworkX over a graph database server — the same "no unnecessary infra" reasoning that chose DuckDB over Postgres in Week 18.
- **50–60 minutes:** Record notes and commit.

### Day 2 — Extracting Entities and Relationships with Claude

- **0–10 minutes:** Reproduce yesterday's main idea without notes.
- **10–25 minutes:** `filing_parser.py` — turning cached filing HTML into clean prompt text.
- **25–50 minutes:** `llm/extraction.py` — the pydantic schemas, the prompt, and the injected `generate` callable (same testable pattern as Week 17's `value_investor`).
- **50–60 minutes:** Run checks, fix errors, and commit.

### Day 3 — Building and Querying the Graph

- **0–10 minutes:** Define the session's small deliverable.
- **10–25 minutes:** `graph.py` — assembling extraction results into a NetworkX `DiGraph`.
- **25–50 minutes:** Query helpers: `competitors_of`, `most_central_entities`.
- **50–60 minutes:** Document decisions and commit.

### Day 4 — Visualization, Persistence, and the CLI

- **0–10 minutes:** Reproduce yesterday's main idea without notes.
- **10–25 minutes:** Saving/loading the graph as JSON; drawing it with matplotlib.
- **25–50 minutes:** Wiring `extract-relationships` and `show-graph` into the CLI; testing without a real LLM call.
- **50–60 minutes:** Run the full pipeline against a real filing, fix errors, and commit.

## Completion Checklist

- [ ] I can explain why a graph fits this data better than a table.
- [ ] `extract_relationships` is testable with a stub, no API key required.
- [ ] `extract-relationships` and `show-graph` both work against a real cached filing.
- [ ] The saved graph JSON round-trips correctly through `load_graph`.
- [ ] `src/sec_thesis/CLAUDE.md`'s implementation status reflects Phase 2.
- [ ] All work is committed and pushed to GitHub.
