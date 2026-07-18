# Week 18: sec_thesis — Evidence-Based Investment Research (Phase 1)

**Course:** Practical AI Engineering for Finance  
**Audience:** Senior undergraduate students  
**Schedule:** 1 hour per day, 6 days (this week only — an optional, advanced extension)  
**Week Theme:** A standalone CLI tool's foundation — configuration, a caching/rate-limited/retrying SEC client, CIK resolution, a DuckDB filing index, and the first three commands

---

## Week Overview

Week 17 built one skill inside the course's own teaching package. Week 18 starts something different: **`sec_thesis`**, a standalone CLI tool meant to eventually maintain a full evidence-based investment thesis from SEC filings — a financial-driver model, a catalyst path, a risk framework, and a versioned conviction history. The complete project spec (purpose, technology choices, 15 engineering rules, architecture, and CLI goals) lives in [`src/sec_thesis/CLAUDE.md`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/src/sec_thesis/CLAUDE.md) — Claude Code loads it automatically whenever you work inside that directory.

That full spec is large — 7 CLI commands, DuckDB storage, LLM-assisted analysis with human-approval gates, filing-to-filing comparison, conviction versioning. Its own first rule is **"work in small, testable phases."** This week is Phase 1 only: the foundation. Three commands work by the end of Day 6 — `resolve-cik`, `list-filings`, `fetch-filings` — fully deterministic, no LLM involved yet. Phases 2–4 (section extraction with LLM classification, thesis-building with conviction tracking and human approval, catalyst/red-team analysis and reporting) are candidates for future weeks.

**A real architecture decision, worth understanding rather than skimming past:** `sec_thesis` does not import `ai_finance_course.edgar` (Week 4/5's SEC client), even though the two do similar things against the same API. `sec_thesis` is meant to work as a real, extractable tool — not course scaffolding — so it stands on its own, re-implementing what it needs rather than depending on a package literally named after the course.

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Weekly Schedule](#weekly-schedule)
- [Day 1: Project Scaffold and Configuration](#day-1-project-scaffold-and-configuration)
- [Day 2: The SEC Client](#day-2-the-sec-client)
- [Day 3: CIK Resolution and the Filing Index](#day-3-cik-resolution-and-the-filing-index)
- [Day 4: Listing and Fetching Filings](#day-4-listing-and-fetching-filings)
- [Day 5: The CLI](#day-5-the-cli)
- [Day 6: Testing Polish and the Roadmap](#day-6-testing-polish-and-the-roadmap)
- [Week 18 Coding Lab](#week-18-coding-lab)
- [Practice Exercises](#practice-exercises)
- [Common Mistakes](#common-mistakes)
- [Interview Preparation](#interview-preparation)
- [Week 18 Quiz](#week-18-quiz)
- [Week 18 Project Submission Checklist](#week-18-project-submission-checklist)
- [Week 18 Reflection](#week-18-reflection)
- [Key Terms](#key-terms)
- [Week Summary](#week-summary)
- [Suggested Reading](#suggested-reading)
- [Where to Go From Here](#where-to-go-from-here)

---

# Learning Objectives

By the end of Week 18, you should be able to:

- Explain why a project might deliberately avoid reusing an existing internal package.
- Design a `pydantic`-based settings object loaded from environment variables.
- Build an HTTP client with an identifying User-Agent, retry-with-backoff, rate limiting, and disk caching.
- Store and query structured data locally with DuckDB.
- Parse a real API's columnar response shape into individual records.
- Build a multi-command CLI with Typer and format output with Rich.
- Write integration tests against mocked HTTP responses for a new module, following the same pattern used in Week 5.

---

# Weekly Schedule

| Day | Topic | Main Deliverable |
|---|---|---|
| Day 1 | Project scaffold & configuration | `config.py` |
| Day 2 | The SEC client | `sec_client.py` |
| Day 3 | CIK resolution & filing index | `cik.py`, `storage/filings_db.py` |
| Day 4 | Listing & fetching filings | `filings.py` |
| Day 5 | The CLI | `cli.py`, three working commands |
| Day 6 | Testing polish & roadmap | README update, live verification |

Each session follows the same structure as prior weeks: review and setup, new concept, guided practice, testing, and committing the work.

---

# Day 1: Project Scaffold and Configuration

## 1.1 Why a Standalone Package?

`src/sec_thesis/` sits right alongside `src/ai_finance_course/` in this same repository — both are separate top-level Python packages under `src/`, and both install from the same `pyproject.toml` with zero extra configuration (`setuptools`'s default src-layout discovery finds every package under `src/` automatically).

But `sec_thesis` doesn't *import* `ai_finance_course`, even though Week 4/5's `edgar.py`/`EdgarClient` already does CIK resolution and retries against the same SEC API. The reasoning, from `CLAUDE.md`:

- The spec lists the SEC client's requirements (User-Agent, retries, caching, rate limiting) as first-class deliverables of *this* package.
- A tool meant to "support additional companies later" and stand on its own shouldn't depend on a package named after a course.
- The two packages will diverge — `sec_thesis` needs disk caching and DuckDB persistence that `ai_finance_course.edgar` has no reason to grow.

This does mean writing similar retry logic twice. That's a real trade-off, made deliberately rather than by accident.

## 1.2 `config.py`: Settings from the Environment

```python
class Settings(BaseModel):
    sec_user_agent: str
    cache_dir: Path = Path("data/raw")
    duckdb_path: Path = Path("data/processed/sec_thesis.duckdb")
    request_delay_seconds: float = 0.2
    max_retries: int = 3
    backoff_seconds: float = 1.0


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        sec_user_agent=os.environ["SEC_USER_AGENT"],
        cache_dir=Path(os.environ.get("SEC_THESIS_CACHE_DIR", "data/raw")),
        duckdb_path=Path(os.environ.get("SEC_THESIS_DB_PATH", "data/processed/sec_thesis.duckdb")),
    )
```

`sec_user_agent` reuses the same `SEC_USER_AGENT` variable from `.env.example` that Weeks 4/5 already introduced — no new secret to configure. `os.environ["SEC_USER_AGENT"]` (not `.get(...)`) means a missing value fails loudly and immediately, the same reasoning Week 5 §1.2 gave for `ai_finance_course`.

## Day 1 Activity

Read `src/sec_thesis/CLAUDE.md` in full and write two sentences: which of the 15 engineering rules do you think will be hardest to follow once Phase 2 (LLM-assisted analysis) starts, and why?

---

# Day 2: The SEC Client

## 2.1 Identifying User-Agent, Retry, and Rate Limiting

`SECClient._request_with_retries` follows the same retry-decision table Week 5 taught: retry `429`/`5xx` and network-level errors, raise immediately on other `4xx`.

```python
def _rate_limit(self) -> None:
    elapsed = time.monotonic() - self._last_request_at
    remaining = self.settings.request_delay_seconds - elapsed
    if remaining > 0:
        time.sleep(remaining)
```

`_rate_limit` runs before *every* request, not just retries — CLAUDE.md rule 10 asks for "conservative rate limiting," not just backoff after something goes wrong.

## 2.2 Disk-Based Caching

```python
def get_json(self, url: str, *, use_cache: bool = True) -> dict:
    cache_path = self._cache_path(url, ".json")
    if use_cache and cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    data = self._request_with_retries(url).json()
    cache_path.write_text(json.dumps(data), encoding="utf-8")
    return data
```

Each URL hashes to a cache filename under `settings.cache_dir`. This was verified for real, not just in tests: running `list-filings` twice showed a measurable speedup, and — a stronger check — running it a third time with `HTTPS_PROXY`/`HTTP_PROXY` pointed at an unreachable address *still succeeded*, proving the cached path makes zero real network calls.

## Day 2 Activity

Run any `sec-thesis` command twice in a row and time both runs (`time sec-thesis resolve-cik AAPL`). Explain the difference you see.

---

# Day 3: CIK Resolution and the Filing Index

## 3.1 Ticker to CIK

```python
def find_cik(ticker: str, company_tickers: dict) -> str:
    """Pure function — testable with a small hand-built fixture."""
    ticker = ticker.upper()
    for entry in company_tickers.values():
        if entry["ticker"] == ticker:
            return str(entry["cik_str"]).zfill(10)
    raise ValueError(f"Ticker {ticker!r} not found")
```

Same shape as Week 4's `edgar.find_cik` — pure logic separated from the network call (`resolve_cik`, which fetches `company_tickers.json` via `SECClient` and then calls this).

## 3.2 The DuckDB Filing Index

```python
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
INSERT INTO filings (...)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (accession_number) DO UPDATE SET ...
"""
```

`ON CONFLICT ... DO UPDATE` means running `list-filings` again doesn't create duplicates — it updates the existing row for a filing's accession number. `FilingsDB` accepts either a real file path or `:memory:`, so tests never touch disk (`duckdb.connect(":memory:")` is instant and fully isolated).

## Day 3 Activity

Open `data/processed/sec_thesis.duckdb` (once Day 5's CLI exists) with any DuckDB client and run `SELECT form, COUNT(*) FROM filings GROUP BY form`. Compare against what `list-filings` printed.

---

# Day 4: Listing and Fetching Filings

## 4.1 Parsing SEC's Columnar Response

Just like Week 4/5's `edgar.py`, `filings.recent` arrives as parallel lists, not row objects:

```python
def parse_filings(ticker: str, cik: str, submissions: dict) -> list[FilingRecord]:
    recent = submissions["filings"]["recent"]
    records = []
    for form, filing_date, primary_document, accession_number in zip(
        recent["form"], recent["filingDate"], recent["primaryDocument"], recent["accessionNumber"]
    ):
        records.append(FilingRecord(..., source_url=_filing_url(cik, accession_number, primary_document)))
    return records
```

## 4.2 Building the Real Filing URL

```python
def _filing_url(cik: str, accession_number: str, primary_document: str) -> str:
    cik_no_zeros = str(int(cik))
    accession_no_dashes = accession_number.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/{accession_no_dashes}/{primary_document}"
```

This exact format was checked against the real API before being written into the lesson — CIK with leading zeros stripped, the accession number's dashes removed, then the document path.

## 4.3 Fetching and Caching

```python
def fetch_filings(client: SECClient, db: FilingsDB, ticker: str) -> list[FilingRecord]:
    updated = []
    for record in db.query_by_ticker(ticker):
        local_path = client.download(record.source_url)
        record = record.model_copy(update={"local_path": str(local_path)})
        db.upsert(record)
        updated.append(record)
    return updated
```

Note this fetches **every** filing already indexed for the ticker — `list-filings` isn't called with a form filter first, `fetch-filings` downloads the company's entire history. For a company with a decade-plus of filings (Apple has roughly 140), combined with §2.1's rate limiting, this genuinely takes a while — that's the rate limit working as intended, not a bug.

## Day 4 Activity

Run `list-filings AAPL --forms 10-K` (a small subset) before running `fetch-filings`, and explain why doing so doesn't actually limit what `fetch-filings` downloads.

---

# Day 5: The CLI

## 5.1 Wiring Commands with Typer

```python
app = typer.Typer(help="sec_thesis: an evidence-based investment research CLI.")
console = Console()


@app.command("resolve-cik")
def resolve_cik_command(ticker: str) -> None:
    settings = load_settings()
    with SECClient(settings) as client:
        cik = resolve_cik(client, ticker)
    console.print(f"[bold]{ticker.upper()}[/bold] -> CIK {cik}")
```

Each command loads settings, opens a client (and the DuckDB connection, for the two filing commands), does the work, and lets Python's `with` statement guarantee cleanup even if something raises partway through.

## 5.2 Rich Output

```python
table = Table(title=f"{ticker.upper()} filings")
table.add_column("Date")
table.add_column("Form")
table.add_column("Accession Number")
for filing in results:
    table.add_row(filing.filing_date, filing.form, filing.accession_number)
console.print(table)
```

## 5.3 Testing the CLI Itself

```python
from typer.testing import CliRunner

runner = CliRunner()


def test_cli_lists_all_three_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "resolve-cik" in result.output
```

This is a smoke test for wiring, not a re-test of the logic underneath — `sec_client.py`, `cik.py`, and `filings.py` each already have their own `httpx.MockTransport`-based tests (Week 5 §4.3's pattern) that don't need a CLI in front of them to run.

## Day 5 Activity

Run `sec-thesis --help` and confirm all three commands are listed with sensible one-line descriptions.

---

# Day 6: Testing Polish and the Roadmap

## 6.1 Live Verification

Every piece of Phase 1 was checked against the real SEC API, not just mocked tests, including a specific check that caching genuinely eliminates network dependency: running a command a third time with `HTTPS_PROXY` pointed at an unreachable address and confirming it still succeeds.

## 6.2 Updating `README.md`

CLAUDE.md rule 15: update `README.md` after completing each phase. For Phase 1, that means the repository-structure section mentions `src/sec_thesis/` alongside `src/ai_finance_course/`, and the course-length framing reflects the new week.

## Day 6 Activity

Write a short reflection: what did you build, what failed, how did you fix it, and how would you explain the standalone-package decision (§1.1) in an interview?

---

# Week 18 Coding Lab

## sec_thesis Phase 1

Extend [`src/sec_thesis/`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/src/sec_thesis) and its tests:

- confirm `config.py`, `sec_client.py`, `cik.py`, `filings.py`, `models/filing.py`, `storage/filings_db.py`, and `cli.py` all exist and are tested;
- set `SEC_USER_AGENT` in your own `.env` and run all three CLI commands for real;
- confirm re-running a command is faster and confirm caching works even with no network available;
- confirm `pytest` passes, including the `httpx.MockTransport`-based integration tests.

### Required Features

- type hints and a docstring on every function, following Week 2 §3.2's comment rules;
- pure parsing/resolution logic (`find_cik`, `parse_filings`) kept separate from network calls;
- every module has at least one test (CLAUDE.md rule 12);
- no API keys, tokens, or `.env` files committed;
- all work committed and pushed to GitHub.

---

# Practice Exercises

## Exercise 1: A Form Filter for `fetch-filings`

Add a `--forms` option to `fetch-filings`, matching `list-filings`, so a user can fetch just the 10-Ks without downloading the entire history.

## Exercise 2: Cache Expiry

Add an optional `max_age_seconds` to `SECClient` so a cached response older than that is treated as a cache miss. Test it by writing a cache file with a fake old timestamp.

## Exercise 3: A Second Ticker

Run all three commands for a company other than AAPL and confirm the filing index correctly separates the two companies' data.

## Exercise 4: Querying the Index Directly

Write a short script (not a CLI command) that opens `data/processed/sec_thesis.duckdb` directly and prints the five most recent 8-Ks across every indexed company.

## Exercise 5: Git Practice

Make commits for `config.py`/`sec_client.py`, `cik.py`/`storage/`, `filings.py`, and `cli.py` separately.

---

# Common Mistakes

## Assuming caching means no rate limiting is needed

They solve different problems — caching avoids *repeat* requests; rate limiting protects against making *too many new* requests too quickly. `SECClient` does both.

## Forgetting `ON CONFLICT` and getting duplicate rows

Without it, running `list-filings` twice would insert the same filing twice. The upsert (§3.2) makes re-running commands safe.

## Calling `fetch-filings` expecting it to respect an earlier `--forms` filter

It doesn't (§4.3) — `list-filings --forms 10-K` only affects what's *printed*, not what's indexed, so `fetch-filings` still downloads everything indexed for the ticker.

## Testing against the live SEC API

Slow and can trip rate limits. Every module here has `httpx.MockTransport`-based tests for exactly this reason (Week 5 §4.3).

## Depending on `ai_finance_course` "just this once"

The whole point of §1.1's decision was to keep `sec_thesis` standalone — pulling in even one function from `ai_finance_course` undoes that.

---

# Interview Preparation

1. Why does `sec_thesis` avoid depending on `ai_finance_course.edgar`, even though the logic is similar?
2. What's the difference between retrying a request and rate-limiting requests?
3. Why does `FilingsDB` use `ON CONFLICT ... DO UPDATE` instead of a plain `INSERT`?
4. How would you prove, convincingly, that a caching layer actually works?
5. Why is `parse_filings` a pure function, and why does that matter for testing?
6. What would you need to change to support a second company beyond AAPL?
7. Why does the CLI's own test (`test_cli.py`) not re-test the retry logic?
8. What's the difference between a "reported fact" and a "model-generated inference" (CLAUDE.md rule 5), and which does Phase 1 produce?

---

# Week 18 Quiz

## Multiple Choice

1. Why does `sec_thesis` live in its own top-level package instead of inside `ai_finance_course`?

   A. Python doesn't allow two packages in one repo  
   B. It's meant to be a standalone, extractable tool, not course scaffolding  
   C. DuckDB requires its own package  
   D. Typer requires a separate package

2. What does `ON CONFLICT (accession_number) DO UPDATE` prevent?

   A. Missing filings  
   B. Duplicate rows when the same filing is indexed twice  
   C. Network errors  
   D. Rate limiting

3. Why does `_rate_limit` run before every request, not just after a failure?

   A. It's required by CLAUDE.md rule 10's "conservative rate limiting," proactive, not just reactive  
   B. httpx requires it  
   C. It makes requests faster  
   D. DuckDB requires it

4. What proved caching genuinely works, beyond the unit tests?

   A. Reading the code  
   B. Running a command with an unreachable proxy set and confirming it still succeeded  
   C. Checking the file exists  
   D. Asking the LLM

5. Why does `fetch-filings` download a company's entire filing history by default?

   A. It's a bug that will be fixed next week  
   B. It has no form filter — `list-filings --forms` only affects what's printed  
   C. DuckDB requires all rows  
   D. SEC requires bulk downloads

## Short Answer

6. Explain, in your own words, the trade-off in duplicating retry logic instead of reusing `EdgarClient`.

7. Why is `find_cik` pure, and `resolve_cik` isn't?

8. What would break if `SECClient` didn't set a User-Agent header?

9. Why does `FilingsDB` accept `:memory:` as a path, and when is that useful?

10. Name one thing Phase 2 would need to add that Phase 1 deliberately left out.

---

# Week 18 Project Submission Checklist

- [ ] `src/sec_thesis/` has `config.py`, `sec_client.py`, `cik.py`, `filings.py`, `models/filing.py`, `storage/filings_db.py`, `cli.py`.
- [ ] Every function has a docstring and type hints.
- [ ] Every module has at least one test file under `tests/sec_thesis/`.
- [ ] `pytest` passes, including mocked-SEC-response integration tests.
- [ ] All three CLI commands work against the real SEC API.
- [ ] Caching verified to eliminate real network calls on repeat runs.
- [ ] `README.md` updated to reflect Phase 1 (CLAUDE.md rule 15).
- [ ] No API keys or `.env` files committed.
- [ ] All work is committed and pushed to GitHub.

---

# Week 18 Reflection

Write 200–300 words answering:

1. What did you build this week?
2. Why does `sec_thesis` avoid depending on the course's own teaching package?
3. What error did you encounter, and how did you fix it?
4. How did you verify caching actually works, beyond trusting the code?
5. What would you improve, or which Phase 2 command would you build next?

Save as:

```text
week18_reflection.md
```

---

# Key Terms

| Term | Definition |
|---|---|
| Standalone package | A package designed not to depend on other project-specific code |
| Rate limiting | Proactively spacing out requests to avoid overwhelming a server |
| Cache | Stored data reused instead of re-fetching it |
| Upsert | Insert a row, or update it if it already exists |
| CIK | The SEC's unique numeric identifier for a company |
| Accession number | SEC's unique identifier for one specific filing |
| Reported fact | Data taken directly from a source, not inferred or assumed |
| DuckDB | An embedded analytical database, queried with SQL, no server required |

---

# Week Summary

During Week 18, you:

- decided, with reasoning, to keep a new package standalone rather than reusing similar existing code;
- built a `pydantic`-based settings object loaded from the environment;
- built an HTTP client with an identifying User-Agent, retry-with-backoff, rate limiting, and disk caching — and proved the caching works by breaking the network on purpose;
- resolved tickers to CIKs and stored a queryable filing index in DuckDB;
- parsed SEC's columnar filings response and constructed real filing URLs;
- fetched and cached raw filing documents;
- built a three-command CLI with Typer and Rich, tested with both unit tests and a CLI-level smoke test.

---

# Suggested Reading

## Required

- DuckDB documentation, "SQL Introduction" and "Python API"
- Typer documentation, "Tutorial"
- Rich documentation, "Tables"

## Recommended

- SEC EDGAR API documentation (already linked from Week 4)
- `src/sec_thesis/CLAUDE.md` — read it again after finishing this week; it reads differently once you've built against it

---

# Where to Go From Here

Phase 1 is deliberately narrow: three commands, fully deterministic, no LLM. The full `sec_thesis` spec (`CLAUDE.md`) describes four more commands and three more modules:

- **`extract-sections`** (`filing_parser.py`, `xbrl.py`) — parse cached filing HTML/XBRL into structured sections, using BeautifulSoup/lxml (already a dependency, unused until this phase).
- **`build-thesis`** (`llm/`, `analysis/`) — the first LLM-assisted phase: classification, extraction, and synthesis, every output validated against a pydantic schema (rule 8), similar in spirit to Week 17's `evaluate_company`.
- **`update-thesis`** — filing-to-filing comparison and conviction-history versioning (rule 11: never overwrite previous thesis versions), with a human-approval gate before conviction changes.
- **`show-catalysts`** (`reporting/`) — Markdown/JSON research output, echoing Week 17's catalyst timeline in a different system.

Each is its own small, testable phase — not a single large jump.
