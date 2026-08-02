# Week 13: Testing

**Course:** Practical AI Engineering for Finance  
**Audience:** Senior undergraduate students  
**Schedule:** 1 hour per day, 4 days per week  
**Week Theme:** Fixtures, mocking, and continuous integration — taught around a real incident in this course's own repository, not a hypothetical one

---

## Week Overview

This week's CI section almost didn't need an invented example. While preparing this lesson, `gh run list` showed the repository's own "Python tests" workflow had been failing since Week 10 — three commits, three red runs, unnoticed. Chasing it down turned into three bugs, each hidden behind the last: pre-existing `ruff` lint errors that had been correctly identified in earlier weeks as "not introduced by this change" and deferred; a missing `[rag]` extra in the CI install step, invisible because the ruff failure meant `pytest` never even ran; and — the most severe of the three, found only by fixing the first two — `tests/conftest.py` importing `chromadb` unconditionally, which broke `pytest` entirely for *any* student who hadn't yet installed `[rag]`, not just the CI workflow. All three are fixed as of this week, and Day 4 walks through how each was found and why each stayed invisible until the one before it was gone.

Everything else this week builds real, tested code: a `call_llm` function extracted from six weeks of copy-pasted example scripts, finally testable with `httpx.MockTransport`; a pytest fixture that composes another fixture; and parametrized tests verified across real parameter combinations before being written down.

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Weekly Schedule](#weekly-schedule)
- [Day 1: Unit Tests](#day-1-unit-tests)
- [Day 2: Fixtures and Parameterization](#day-2-fixtures-and-parameterization)
- [Day 3: Mocking External APIs](#day-3-mocking-external-apis)
- [Day 4: Continuous Integration](#day-4-continuous-integration)
- [Week 13 Coding Lab](#week-13-coding-lab)
- [Practice Exercises](#practice-exercises)
- [Common Mistakes](#common-mistakes)
- [Interview Preparation](#interview-preparation)
- [Week 13 Quiz](#week-13-quiz)
- [Week 13 Project Submission Checklist](#week-13-project-submission-checklist)
- [Week 13 Reflection](#week-13-reflection)
- [Key Terms](#key-terms)
- [Week Summary](#week-summary)
- [Suggested Reading](#suggested-reading)
- [Next Week](#next-week)

---

# Learning Objectives

By the end of Week 13, you should be able to:

- Explain what makes a good unit test, using this project's own test suite as reference.
- Write a pytest fixture, including one that composes another fixture, rather than a plain helper function.
- Write parametrized tests that verify one property across many real inputs, not one input restated many times.
- Mock an external HTTP API with `httpx.MockTransport`, extending Week 5's pattern to the LLM-calling code for the first time.
- Read a CI failure log and distinguish "this step failed" from "this step never ran because an earlier step failed."
- Explain why a passing test suite locally doesn't guarantee a passing CI run, and vice versa.

---

# Weekly Schedule

| Day | Topic | Main Deliverable |
|---|---|---|
| Day 1 | Unit tests | Reading this project's own test suite critically |
| Day 2 | Fixtures and parameterization | A fixture composing a fixture; parametrized chunking tests |
| Day 3 | Mock external APIs | A tested, extracted `call_llm` using `httpx.MockTransport` |
| Day 4 | Continuous integration | The real CI incident, found, diagnosed, and fixed |

Each class follows the same session structure as Weeks 1–12: review and setup, new concept, guided practice, testing, and committing the work.

---

# Day 1: Unit Tests

## 1.1 What This Project Already Does Right

By Week 13, this repository has 125 tests across 15+ files. Rather than starting from a blank slate, read a handful critically: `tests/test_chunking.py`'s `test_chunk_text_rejects_overlap_not_smaller_than_chunk_size` tests one specific failure condition with one specific assertion — that's the shape a good unit test should have. Compare it to `tests/test_evaluation.py`'s `test_check_groundedness_rejects_invalid_response_shape`, whose docstring explains *why* the test uses `"not-a-bool"` instead of the more obvious-looking `"yes"` (§Day 2 of Week 12 found that pydantic silently coerces `"yes"` to `True`). A good test doesn't just pass — its failure, if it ever fails, tells you something specific.

## 1.2 One Assertion Idea Per Test

Most tests in this repository check one behavior, even when they contain multiple `assert` statements — `test_call_llm_sends_correct_request_shape` (Day 3) has four asserts, but all four check the same idea: "did the request get built correctly?" A test that checks two unrelated things (e.g., "the response parses correctly" *and* "the retry logic works") makes a failure ambiguous — you can't tell which behavior actually broke from the test name alone.

## Day 1 Activity

Pick three existing tests from `tests/` that you didn't write. For each, answer: if this test failed tomorrow, would the test's *name* alone tell you what broke, without reading its body?

---

# Day 2: Fixtures and Parameterization

## 2.1 From a Helper Function to a Fixture

Every test file that needed a small pre-populated ChromaDB collection used to define its own `_sample_collection(tmp_path, embedding_function)` helper — `test_rag.py` had one, and it duplicated logic already present in `test_vector_store.py`'s tests. This week formalizes it as a real pytest fixture in `conftest.py`:

```python
@pytest.fixture
def sample_collection(tmp_path, keyword_stub_embedding_function):
    collection = get_or_create_collection(tmp_path, "passages", keyword_stub_embedding_function)
    add_chunks(collection, [
        {"text": "AAPL revenue grew 8% this quarter.", "ticker": "AAPL", "chunk_index": 0},
        {"text": "The Fed raised interest rates.", "ticker": "MACRO", "chunk_index": 0},
    ])
    return collection
```

`sample_collection` depends on two other fixtures — the built-in `tmp_path` and this file's own `keyword_stub_embedding_function` — pytest resolves both automatically before your test runs. Every test in `test_rag.py` that used to call `_sample_collection(tmp_path, keyword_stub_embedding_function)` now just takes `sample_collection` as a parameter directly:

```python
def test_answer_question_returns_validated_answer_and_evidence(sample_collection) -> None:
    ...
```

## 2.2 Parametrized Tests, Verified Before Being Written

```python
@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(10, 2), (20, 5), (50, 0), (100, 25)],
)
def test_chunk_text_every_chunk_stays_within_size_limit(chunk_size: int, overlap: int) -> None:
    text = "x" * 237
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    assert all(len(chunk) <= chunk_size for chunk in chunks)
```

`@pytest.mark.parametrize` runs the same test body once per tuple — this is 4 real test cases, not 1 test copy-pasted 4 times with different literals. Before writing this test, all four `(chunk_size, overlap)` combinations were run manually against `chunk_text` to confirm the property actually holds (a length of 237 was chosen specifically because it isn't a clean multiple of any of the four `chunk_size` values) — the same "verify, then write it down" discipline this course has used since Week 9's id-collision bug.

## 2.3 When a Fixture Is Better Than a Parameter

Use a fixture for setup every test in a file needs (a database connection, a temp directory, a pre-populated collection). Use `@pytest.mark.parametrize` for the *inputs* a single test should be checked against. Mixing them up — parametrizing setup, or building a fixture around what's really a single test input — usually signals the wrong tool was reached for.

## Day 2 Activity

Find one more place in `tests/` where two or more files build up similar test data with a local helper function. Would formalizing it as a shared fixture in `conftest.py` reduce duplication, the way `sample_collection` did for `test_rag.py`?

---

# Day 3: Mocking External APIs

## 3.1 A Pattern, Copy-Pasted Six Times, Never Tested

Every example script since Week 6 has included the same ~20 lines: a direct `httpx` POST to Anthropic's Messages API, no SDK. It was never a library function — it lived only in `examples/*/*.py` files, which meant it was never actually unit-tested; the *code that calls* a `generate` function has been tested extensively (Weeks 7, 10, 11, 12), but the `_call_llm` function itself, the thing that actually builds the HTTP request, never was.

## 3.2 Extracting It, the Way Week 5 Extracted `EdgarClient`

```python
def call_llm(
    prompt: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
    transport: httpx.BaseTransport | None = None,
) -> str:
    api_key = api_key or os.environ["LLM_API_KEY"]
    model = model or os.environ["LLM_MODEL"]

    with httpx.Client(timeout=60.0, transport=transport) as client:
        response = client.post(ANTHROPIC_MESSAGES_URL, headers={...}, json={...})
        response.raise_for_status()
        data = response.json()
        for block in data["content"]:
            if block["type"] == "text":
                return block["text"]
        raise LLMResponseError(f"No text block in response: {data}")
```

`transport: httpx.BaseTransport | None = None` is exactly `EdgarClient`'s constructor parameter from Week 5 §4.2, applied here for the first time to an LLM call instead of a SEC EDGAR call. Passed through to `httpx.Client(transport=transport)`, it lets a test replace the real network with a plain Python function.

## 3.3 Testing With `httpx.MockTransport`

```python
def test_call_llm_finds_text_block_after_other_block_types() -> None:
    """Some models return a thinking block before the text block — content[0] would be wrong."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": [
            {"type": "thinking", "thinking": "reasoning..."},
            {"type": "text", "text": "The answer."},
        ]})

    result = call_llm("Hi", api_key="test-key", model="test-model", transport=httpx.MockTransport(handler))

    assert result == "The answer."
```

This is a real, meaningful test case, not a filler one — it's exactly why `call_llm` searches for the `"text"`-typed block instead of assuming `content[0]`, a detail every copy-pasted version of this function has carried since Week 17 but never had a test proving it mattered.

## 3.4 What This Doesn't Replace

`call_llm`'s tests confirm the HTTP request/response handling works correctly in isolation. They say nothing about whether a *real* Anthropic response would actually answer a question well — that's a different kind of check (Week 12's groundedness) at a different layer. Mocking the transport tests plumbing; it doesn't test intelligence.

## Day 3 Activity

Read `tests/test_llm_client.py`'s `test_call_llm_uses_env_vars_when_not_passed_explicitly` test. Explain why it uses `monkeypatch.setenv` rather than just setting `os.environ` directly, and what would go wrong for other tests in the same run if it didn't clean up after itself.

---

# Day 4: Continuous Integration

## 4.1 The Real Incident

```text
completed  failure  Add Week 12: evaluation...            Python tests  main  1m10s
completed  failure  Add Week 11: improved RAG...           Python tests  main  49s
completed  failure  Add Week 10: basic RAG...               Python tests  main  46s
```

Three failing runs in a row, found by running `gh run list` — not something anyone was watching for, just checked while preparing this lesson. `gh run view <id> --log-failed` showed why: `ruff check .` failed with 13 lint errors, none of them related to that week's actual changes — nested `with` statements from Week 5/18, unsorted imports from Week 17, `__enter__` methods that should return `Self` instead of the class name (a real type-checking nuance, not just style).

## 4.2 Why the Second Bug Was Invisible

`.github/workflows/tests.yml` ran `ruff check .` as a separate step *before* `pytest`. In GitHub Actions, a failed step stops the job by default — so `pytest` never ran, for three straight weeks. That hid a second, unrelated problem: the workflow's install step was `pip install -e ".[dev]"` — it never installed the `[rag]` extra Week 9 added. `tests/conftest.py` imports `chromadb` at module level, and conftest.py loads before *any* test file, rag-related or not. Reproduced locally:

```text
$ pip install -e ".[dev]"   # matching CI's exact install command
$ pytest
ImportError while loading conftest '.../tests/conftest.py'.
tests/conftest.py:12: in <module>
    from chromadb import Documents, EmbeddingFunction, Embeddings
E   ModuleNotFoundError: No module named 'chromadb'
```

Every single test in the repository — not just the rag-related ones — would have failed to even collect. This bug existed since Week 9, three weeks before it could have been *observed*, because the ruff failure was blocking the step that would have revealed it.

## 4.3 The Fix, and the Lesson In It

Two independent fixes: clean up the 13 real lint errors (mostly mechanical — combining nested `with` statements, sorting imports, annotating `__enter__` with `Self`), and add the missing extra:

```yaml
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev,rag]"
```

The actual lesson isn't "remember to add extras to CI" — it's that **a red CI run can be hiding a second red CI run**. Fixing the first failure you see isn't the end of the investigation; it's what lets you find out whether there's a second one underneath.

## 4.4 A Fourth Bug, Found by Fixing the First Three

Fixing §4.1–4.3's CI failure exposed a bigger problem, one severe enough that it wasn't really about CI at all. `tests/conftest.py` (Week 9 §2.2) imported `chromadb` unconditionally at module level — and `conftest.py` loads for *every* test in the repository, not just the `[rag]`-dependent ones. Confirmed directly:

```text
$ python3.11 -m venv .venv && source .venv/bin/activate
$ pip install -e ".[dev]"      # no [rag] — exactly what a Week 3 student would have
$ pytest
ImportError while loading conftest '.../tests/conftest.py'.
tests/conftest.py:12: in <module>
    from chromadb import Documents, EmbeddingFunction, Embeddings
E   ModuleNotFoundError: No module named 'chromadb'
```

Every test in the repository — `test_returns.py`, `test_analysis.py`, everything — failed to even collect. Not because those tests need `chromadb`, but because `conftest.py` does, and `conftest.py` loads first, unconditionally, for the whole session. Since this repository is one continuously-growing course (not one repo per week), a student on Week 3 already has Week 9–14's test files sitting in their checkout — this bug would have hit *any* student running `pytest` for the first time, at *any* week, the moment `conftest.py` was added.

The fix has two layers. First, `conftest.py` imports `chromadb` defensively and only defines its chromadb-dependent fixtures if the import succeeds:

```python
try:
    from chromadb import Documents, EmbeddingFunction, Embeddings
except ImportError:
    EmbeddingFunction = None  # [rag] extra not installed

if EmbeddingFunction is not None:
    class KeywordStubEmbeddingFunction(EmbeddingFunction):
        ...
```

Second, every test *file* that transitively needs `chromadb` (`test_vector_store.py`, `test_rag.py`, `test_query_expansion.py`, `test_retrieval_eval.py`, `test_api.py`) declares that up front:

```python
import pytest

pytest.importorskip("chromadb", reason="requires the [rag] extra: pip install -e '.[rag]'")

from ai_finance_course.vector_store import add_chunks, get_or_create_collection, query_collection
```

`pytest.importorskip` turns a missing dependency into a clean, reported **skip** — not a collection **error**. That distinction is the whole fix: a skip doesn't fail the run; an error does. Verified both ways: `pip install -e ".[dev]"` alone now gives `102 passed, 5 skipped`; adding `[rag]` and `[api]` gives `133 passed, 0 skipped`.

## 4.5 A Fifth, Smaller Example — Caught the Same Way

Building this week's own `examples/week-13/check_test_health.py` script hit the identical pattern in miniature: `subprocess.run(command, capture_output=True, text=True)` without an explicit `check=` argument is itself a real ruff error (`PLW1510`) — caught by running the script for real and reading its own output, not assumed clean because it looked simple. Even smaller: the notebook version's own last cell had an unsorted import block, caught because the notebook's first cell runs `ruff check .` against the *whole repository*, including itself.

## Day 4 Activity

Run `examples/week-13/check_test_health.py` yourself. If both checks pass, deliberately break one (comment out an import, or reorder one) and confirm the script reports `FAIL` and exits non-zero — the same signal that would block a real CI run.

---

# Week 13 Coding Lab

## Extending Test Coverage

This week's core code already exists and is tested — [`src/ai_finance_course/llm_client.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/src/ai_finance_course/llm_client.py), the `sample_collection` fixture in [`tests/conftest.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/tests/conftest.py), and [`examples/week-13/check_test_health.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/examples/week-13/check_test_health.py). Your lab work is to extend it:

- add at least one more `httpx.MockTransport` test for `call_llm` covering a case not already tested (e.g. a malformed JSON response, or a timeout);
- add at least one more parametrized test elsewhere in the codebase, verifying its property across real inputs before writing it down;
- run `check_test_health.py` and confirm both checks pass on your own machine.

### Required Features

- type hints and a docstring on every function you add, following Week 2 §3.2's comment rules;
- every new test's failure mode is specific enough that its name alone explains what broke;
- confirm `pytest` still passes, including all of `test_llm_client.py`;
- confirm `ruff check .` passes with zero errors — not just on your new files, the whole repository;
- all work committed and pushed to GitHub.

---

# Practice Exercises

## Exercise 1: Break `call_llm` on Purpose

Write a `httpx.MockTransport` handler that returns a 500 status code. Confirm `call_llm` raises `httpx.HTTPStatusError`, and explain in one sentence why `response.raise_for_status()` is what makes this work without any extra code in `call_llm` itself.

## Exercise 2: A Fixture With Teardown

Write a new pytest fixture using `yield` instead of `return` (e.g., one that creates a file, yields its path, then deletes it afterward). Explain what problem `yield`-style fixtures solve that `return`-style ones can't.

## Exercise 3: Parametrize an Existing Test

Find an existing non-parametrized test elsewhere in `tests/` that's really testing the same property against a single hardcoded input. Rewrite it as a parametrized test with at least 3 cases.

## Exercise 4: Reproduce the CI Incident Locally

Create a throwaway virtual environment, run `pip install -e ".[dev]"` (deliberately omitting `rag`), and confirm you get the exact `ModuleNotFoundError` this lesson describes. Then add `rag` and confirm it resolves.

## Exercise 5: Git Practice

Make separate commits for your new `call_llm` test, your new parametrized test, and any CI workflow changes.

---

# Common Mistakes

## Treating a passing local `pytest` run as proof CI will pass

§4.2 — CI installs different dependencies than whatever happens to already be in your local environment. `pip install -e ".[dev]"` locally, if you'd previously installed `[rag]` for an earlier week and never removed it, would hide the exact bug this week found.

## Fixing the first CI failure and assuming that's the whole problem

§4.2's core lesson — a failed step can hide a second failure in the step after it. Re-run the full pipeline after any CI fix, don't just confirm the one error you saw is gone.

## Importing an optional dependency unconditionally in `conftest.py`

§4.4 — `conftest.py` loads for every test in the repository, not just the ones that need what it imports. An unconditional `import chromadb` there broke `pytest` for the *entire* test suite for any environment without `[rag]` installed, not just the rag-specific tests. Guard the import, and let individual test files opt in with `pytest.importorskip`.

## Writing a fixture for something that's really a parametrize case

§2.3 — if the "setup" changes per test case rather than being shared across many tests, it's probably a parametrize input, not a fixture.

## Assuming `content[0]` is always the text block

§3.3 — some models return non-text blocks (like `thinking`) before the text block. Search by `type`, as `call_llm` does, or you'll intermittently return the wrong thing.

## Mocking the transport and calling it "fully tested"

§3.4 — `httpx.MockTransport` tests prove the HTTP plumbing works. It says nothing about whether a real model's real response would actually be a good answer — that's a different, separate kind of check.

---

# Interview Preparation

1. Walk through the real CI incident: what were the two bugs, and why was the second one invisible until the first was fixed?
2. Why does `call_llm` accept a `transport` parameter, and where else in this course has that exact pattern been used before?
3. What's the difference between a pytest fixture and a `@pytest.mark.parametrize` case, and when would you reach for each?
4. Why does `sample_collection` depend on `keyword_stub_embedding_function` instead of constructing its own embedding function inline?
5. Why does `call_llm` search for a `"text"`-typed content block instead of assuming `content[0]`?
6. What would you check first if a CI run failed but the exact same command passed locally?
7. Why is verifying a parametrized test's property manually, before writing the test, part of this course's established discipline rather than optional?
8. What's the difference between testing that an LLM call's HTTP plumbing works and testing that its output is actually good?

---

# Week 13 Quiz

## Multiple Choice

1. Why did this repository's CI fail for three weeks without anyone noticing?

   A. The tests were actually passing; GitHub Actions was misconfigured  
   B. A ruff lint failure blocked the pytest step from ever running, hiding a second bug behind it  
   C. There was no CI configured at all  
   D. The repository was private

2. What was the second, hidden bug?

   A. A syntax error in a test file  
   B. The CI install step never included the `[rag]` extra, so `chromadb` was missing and every test would fail to collect  
   C. The wrong Python version was configured  
   D. A missing API key

3. Why does `call_llm` accept a `transport` parameter?

   A. It's required by httpx  
   B. So tests can replace the real network with `httpx.MockTransport`, the same pattern Week 5 used for `EdgarClient`  
   C. To make requests faster  
   D. It doesn't need one

4. What's the main difference between a pytest fixture and `@pytest.mark.parametrize`?

   A. They're interchangeable  
   B. A fixture provides shared setup a test depends on; parametrize runs the same test body against multiple different input values  
   C. Fixtures are for unit tests, parametrize is for integration tests  
   D. Parametrize requires a fixture to work

5. Why does `call_llm` search for a `"text"`-typed content block instead of using `content[0]`?

   A. It's slower but more secure  
   B. Some models return non-text blocks (e.g. thinking) before the text block, and `content[0]` would return the wrong one  
   C. `content[0]` doesn't exist in the API  
   D. There's no difference

## Short Answer

6. Explain, in your own words, why "the first CI failure I see" isn't necessarily "the only CI failure."

7. Why does `sample_collection` composing `keyword_stub_embedding_function` matter, versus just constructing a new stub inline?

8. What real, specific reason justified writing `test_call_llm_finds_text_block_after_other_block_types` as its own test, rather than folding it into the basic "returns text" test?

9. Why was `text = "x" * 237` chosen specifically for the parametrized chunking tests, rather than a rounder number like 200?

10. What would you check, in order, if you inherited a project with a red CI badge and no explanation?

---

# Week 13 Project Submission Checklist

- [ ] You've read at least 3 existing tests critically and could explain what each one's failure would tell you.
- [ ] `examples/week-13/check_test_health.py` runs and both checks pass on your machine.
- [ ] You added at least one new `httpx.MockTransport` test and one new parametrized test.
- [ ] `pytest` passes, and `ruff check .` passes with zero errors across the whole repository.
- [ ] You can explain the real CI incident (§4.1–4.3) in your own words.
- [ ] All work is committed and pushed to GitHub.

---

# Week 13 Reflection

Write 200–300 words answering:

1. What did you build or extend this week?
2. Explain the real CI incident in your own words — both bugs, and why the second was hidden.
3. Describe one parametrized test you wrote and the real inputs you verified before writing it.
4. Why does mocking the transport layer test something different from mocking the `generate` function (Weeks 7/10/11/12's pattern)?
5. What would you improve about this week's test suite or CI workflow?

Save as:

```text
week13_reflection.md
```

---

# Key Terms

| Term | Definition |
|---|---|
| Fixture | Shared setup a test depends on, provided by pytest and reusable across many tests |
| Fixture composition | A fixture that itself depends on other fixtures, resolved automatically |
| Parametrization | Running the same test body against multiple different input values |
| `httpx.MockTransport` | A test tool that replaces the real network with a function you control |
| Continuous integration (CI) | Automatically running checks (lint, tests) on every push |
| Masked failure | A second bug that can't be observed because an earlier failure stops execution first |

---

# Week Summary

During Week 13, you:

- read this project's existing test suite critically, not just as a checklist to pass;
- formalized a duplicated test-setup helper into a real pytest fixture that composes another fixture;
- wrote parametrized tests, verifying their property against real inputs before writing them down;
- extracted `call_llm` from six weeks of copy-pasted example code and tested its actual HTTP handling with `httpx.MockTransport` for the first time;
- found, diagnosed, and fixed a real, three-week-old CI failure in this course's own repository — two separate bugs, one hiding behind the other.

---

# Suggested Reading

## Required

- pytest documentation, "Fixtures" and "Parametrizing tests"
- httpx documentation, "Mock Transports"

## Recommended

- GitHub Actions documentation, "Workflow syntax" — specifically how step failure affects subsequent steps by default

---

# Next Week

## Week 14: FastAPI

Week 14 introduces:

- exposing this project's RAG pipeline through `/health`, `/search`, and `/ask` endpoints;
- request and response validation with pydantic models, the same schemas already used throughout Weeks 7–12, now validating HTTP traffic instead of LLM output;
- connecting the actual `answer_question` pipeline (Week 10) behind a real endpoint;
- testing endpoints with FastAPI's `TestClient` — a different kind of test than anything built this week, since it exercises the whole request/response cycle, not an isolated function.

This week's `call_llm` and testing discipline both carry forward directly — Week 14's endpoint tests will use the exact same mocking reasoning, just one layer higher.
