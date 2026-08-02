# Week 14: FastAPI

**Course:** Practical AI Engineering for Finance  
**Audience:** Senior undergraduate students  
**Schedule:** 1 hour per day, 4 days per week  
**Week Theme:** Exposing Week 9's retrieval and Week 10's RAG pipeline through a real, documented web API — `/health`, `/search`, `/ask`

---

## Week Overview

Everything this week's API does already exists as a tested Python function: `query_collection` (Week 9) and `answer_question` (Week 10). FastAPI's job is to expose them over HTTP with request/response validation, not to reimplement any of the underlying logic. The collection and the LLM call are both wired in as **dependencies** (`Depends(...)`) rather than hardcoded — the same "pass it in, don't hardcode it" instinct as every injected `generate` callable since Week 7, now expressed through FastAPI's own dependency-injection system.

**Live-verified against a real running server, not just `TestClient`:** [`examples/week-14/call_api.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/examples/week-14/call_api.py) starts a real `uvicorn` server in a background thread and calls it over a real TCP socket with `httpx` — `/health` and `/search` both return real, correct results this way. That live run also caught a real bug in the example script itself: `/ask` returned a `500` (correctly — no `LLM_API_KEY` in this sandbox) with an empty body, and the script's first version crashed trying to parse that empty body as JSON. Fixed in §4.3.

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Weekly Schedule](#weekly-schedule)
- [Day 1: API Endpoints and Schemas](#day-1-api-endpoints-and-schemas)
- [Day 2: Request and Response Validation](#day-2-request-and-response-validation)
- [Day 3: Connecting the RAG Pipeline](#day-3-connecting-the-rag-pipeline)
- [Day 4: Testing Endpoints](#day-4-testing-endpoints)
- [Week 14 Coding Lab](#week-14-coding-lab)
- [Practice Exercises](#practice-exercises)
- [Common Mistakes](#common-mistakes)
- [Interview Preparation](#interview-preparation)
- [Week 14 Quiz](#week-14-quiz)
- [Week 14 Project Submission Checklist](#week-14-project-submission-checklist)
- [Week 14 Reflection](#week-14-reflection)
- [Key Terms](#key-terms)
- [Week Summary](#week-summary)
- [Suggested Reading](#suggested-reading)
- [Next Week](#next-week)

---

# Learning Objectives

By the end of Week 14, you should be able to:

- Design a FastAPI route with a pydantic request model and a pydantic `response_model`.
- Explain what FastAPI's `Depends(...)` does, and why route functions shouldn't construct their own dependencies inline.
- Wire an existing, tested Python function (not new logic) behind an HTTP endpoint.
- Distinguish a `422` validation error from a `502`/`500` runtime error, and explain what causes each.
- Test FastAPI endpoints with `TestClient` and `app.dependency_overrides`, without hitting a real vector store or a real LLM.
- Run a real HTTP server in a script and call it with a real HTTP client, not just an in-process test client.

---

# Weekly Schedule

| Day | Topic | Main Deliverable |
|---|---|---|
| Day 1 | API endpoints and schemas | Understanding the three routes and their pydantic models |
| Day 2 | Request and response validation | Confirming `422` behavior on bad input |
| Day 3 | Connect the RAG pipeline | `/ask` wired to `answer_question`, live-verified |
| Day 4 | Test endpoints | A full `TestClient` test suite with dependency overrides |

Each class follows the same session structure as Weeks 1–13: review and setup, new concept, guided practice, testing, and committing the work.

---

# Day 1: API Endpoints and Schemas

## 1.1 Three Routes, One Already-Tested Pipeline Behind Each

```python
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/search", response_model=list[SearchResult])
def search(request: SearchRequest, collection: Collection = Depends(get_collection)) -> list[SearchResult]:
    ...

@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, collection=Depends(get_collection), generate=Depends(get_generate)) -> AskResponse:
    ...
```

`/health` has no dependencies at all — it's a pure liveness check, nothing to fail. `/search` calls Week 9's `query_collection` directly; no LLM involved, retrieval only. `/ask` calls Week 10's `answer_question` — the only route that costs money per call, since it's the only one that reaches an LLM.

## 1.2 Pydantic Models on Both Sides

```python
class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    n_results: int = Field(default=3, ge=1, le=20)
    ticker: str | None = None

class SearchResult(BaseModel):
    text: str
    ticker: str | None
    doc_type: str | None
    distance: float
```

This is the same pattern Weeks 7–12 used for LLM output (`RAGAnswer`, `GroundednessCheck`) — a pydantic model constrains the shape of data. The difference this week is *where* it's enforced: HTTP request/response bodies, not an LLM's text response.

## Day 1 Activity

Read `src/ai_finance_course/api.py` in full. For each of the three routes, write one sentence: which existing, already-tested function does this route call, and what does the route itself actually add on top of it?

---

# Day 2: Request and Response Validation

## 2.1 A Bad Request Never Reaches Your Code

```python
def test_search_rejects_empty_query(client, sample_collection) -> None:
    app.dependency_overrides[get_collection] = lambda: sample_collection
    response = client.post("/search", json={"query": ""})
    assert response.status_code == 422
```

`query: str = Field(min_length=1)` means an empty-string query never reaches the `search` function body at all — FastAPI validates the request against `SearchRequest` before your code runs, and returns `422 Unprocessable Entity` automatically if it fails. This is the HTTP-layer equivalent of Week 7's pydantic validation on LLM output: catch the bad shape before anything downstream has to handle it.

## 2.2 `response_model` Enforces the Outgoing Shape Too

`response_model=list[SearchResult]` does the same validation in reverse — if a route function ever returned something that doesn't match `SearchResult`'s shape, FastAPI would raise before sending a malformed response to the client. Validation isn't just an incoming-request concern.

## 2.3 Reading FastAPI's Interactive Docs

Run the server (`uvicorn ai_finance_course.api:app --reload`) and open `http://127.0.0.1:8000/docs`. FastAPI generates this page directly from the pydantic models and route signatures — it's not hand-written documentation that can drift out of sync with the code, because it *is* the code.

## Day 2 Activity

Send a `/search` request with `n_results: 50` (above the `le=20` limit in `Field`). Confirm you get a `422`, and read the response body to see exactly which field failed and why.

---

# Day 3: Connecting the RAG Pipeline

## 3.1 Dependencies, Not Hardcoded Calls

```python
@lru_cache
def get_collection() -> Collection:
    return get_or_create_collection(PERSIST_PATH, COLLECTION_NAME)

def get_generate() -> Callable[[str], str]:
    return call_llm
```

`get_collection` is wrapped in `@lru_cache` deliberately — reconstructing `SentenceTransformerEmbeddingFunction` on every single request would reload the embedding model every time, which is slow. Caching means `get_or_create_collection` only actually runs once per process, no matter how many requests hit `/search` or `/ask`.

## 3.2 A Real Design Question: What Status Code for a Bad LLM Response?

```python
try:
    result, evidence = answer_question(request.query, collection, generate, n_results=request.n_results)
except ValueError as exc:
    raise HTTPException(status_code=502, detail=f"LLM response was invalid: {exc}") from exc
```

`answer_question` raises `ValueError` (via pydantic, Week 10 §3.3) when the LLM's response doesn't validate. `502 Bad Gateway` is the deliberate choice here, not `500`: a `500` means "this server's own code is broken"; a `502` means "this server depends on an upstream service, and that upstream service gave a bad response" — which is exactly what an invalid LLM response is. Getting this distinction right matters for anyone debugging the API later without reading its source.

## 3.3 A Real Bug, Found by Actually Running the Server

The first version of `examples/week-14/call_api.py` printed `ask.json()` unconditionally after checking `ask.status_code`. Running it for real (this sandbox has no `LLM_API_KEY`) produced a `500` — not the `502` from §3.2, since a missing environment variable raises `KeyError` inside `call_llm` itself, before `answer_question` ever gets a chance to catch anything as a `ValueError`. FastAPI's default response for an *unhandled* exception has **no JSON body at all**, and `ask.json()` crashed with a `JSONDecodeError` trying to parse an empty string. The fix:

```python
else:
    print(ask.text or "(no response body — check LLM_API_KEY/LLM_MODEL are set)")
```

The lesson: a script that only knows how to handle the happy path isn't done, even when the API's own error handling (§3.2) is solid — the *client* calling that API needs its own handling for the cases the server doesn't turn into a clean JSON error.

## Day 3 Activity

Deliberately trigger the `502` path: write a stub `generate` (via `app.dependency_overrides`) that returns invalid JSON, call `/ask` through `TestClient`, and confirm you get a `502` with a JSON body — not a `500` with an empty one, per §3.2's distinction.

---

# Day 4: Testing Endpoints

## 4.1 `TestClient` Plus `dependency_overrides`

```python
def test_ask_returns_answer_and_sources(client, sample_collection) -> None:
    app.dependency_overrides[get_collection] = lambda: sample_collection

    def stub_generate(prompt: str) -> str:
        return json.dumps({"answer": "Yes, revenue grew.", "citations": [1]})

    app.dependency_overrides[get_generate] = lambda: stub_generate

    response = client.post("/ask", json={"query": "Did revenue grow?", "n_results": 2})

    assert response.status_code == 200
```

`app.dependency_overrides` is a dict FastAPI checks before calling the real `get_collection`/`get_generate` — override an entry, and every route that depends on it gets your replacement instead, for the lifetime of the override. No real vector store on disk, no real API key, no network — the exact same testability principle as every injected `generate` callable since Week 7, just plugged into FastAPI's own mechanism instead of a plain function parameter.

## 4.2 A Real `yield`-Style Teardown Fixture

```python
@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()
```

This is Week 13 §Exercise 2, actually built and used: setup happens before `yield`, teardown happens after. Without the `app.dependency_overrides.clear()` in teardown, one test's stub `generate` could silently leak into the *next* test — `test_dependency_overrides_do_not_leak_between_tests` in `tests/test_api.py` checks exactly this isn't happening, not just that individual tests pass in isolation.

## 4.3 Live-Verifying Beyond `TestClient`

`TestClient` exercises the whole ASGI request/response cycle in-process — real validation, real routing, real dependency injection — but it never opens an actual TCP socket. `examples/week-14/call_api.py` (§ this week's overview) does: a real `uvicorn.run(...)` in a background thread, a real `httpx.Client` making a real HTTP request to `127.0.0.1:8014`. Both kinds of test matter — `TestClient` is what you'd want in a fast CI suite; a real running server is what proves the thing genuinely works as an HTTP service, not just as Python code that happens to be wrapped in FastAPI decorators.

## Day 4 Activity

Run `examples/week-14/call_api.py` yourself (with or without a real `LLM_API_KEY` — either way is informative). Confirm `/health` and `/search` succeed over the real socket, and read whatever `/ask` returns, whether that's a real answer or the graceful fallback message from §3.3.

---

# Week 14 Coding Lab

## Extending the API

This week's core code already exists and is tested — [`src/ai_finance_course/api.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/src/ai_finance_course/api.py) and [`examples/week-14/call_api.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/examples/week-14/call_api.py). Your lab work is to extend it:

- add a new query parameter or field to `SearchRequest` (e.g. a `doc_type` filter alongside `ticker`) and wire it through to `query_collection`'s `where` clause;
- write at least one new `TestClient` test for your new field, including a case that should fail validation;
- run `call_api.py` against a real running server and confirm your new field works over real HTTP, not just in `TestClient`.

### Required Features

- type hints and a docstring on every function you add, following Week 2 §3.2's comment rules;
- new request fields use `pydantic.Field` constraints where they make sense (min/max, required vs optional) rather than validating manually inside the route function;
- confirm `pytest` still passes, including `test_dependency_overrides_do_not_leak_between_tests`;
- `LLM_API_KEY`/`LLM_MODEL` are set in your own `.env`, never hard-coded or committed;
- all work committed and pushed to GitHub.

---

# Practice Exercises

## Exercise 1: A `/health` That Actually Checks Something

Extend `/health` to also confirm the collection is reachable (e.g., call `.count()` on it) and return `503` if it isn't. What's the trade-off of a liveness check that does more work versus one that's instant but less informative?

## Exercise 2: Rate Limiting `/ask`

`/ask` is the only route that costs money per call. Sketch (in comments or a short write-up, not necessarily working code) how you'd add a simple per-client rate limit specifically to `/ask` but not `/health` or `/search`.

## Exercise 3: A Combined Endpoint

Add a `/search_and_ask` endpoint that returns both the raw search results *and* the generated answer in one response, avoiding two separate round trips for a client that wants both.

## Exercise 4: Testing the Real Server, Not Just `TestClient`

Write your own version of `call_api.py`'s `_wait_for_server` polling pattern, and explain in one sentence why a fixed `time.sleep(2)` before the first request would be a worse choice.

## Exercise 5: Git Practice

Make separate commits for your new `SearchRequest` field, your new tests, and your live-verification run notes.

---

# Common Mistakes

## Hardcoding the collection or the LLM call inside a route function

§3.1 — use `Depends(...)`, the same reasoning as every injected callable since Week 7. A route that constructs its own dependencies can't be tested without hitting the real thing.

## Forgetting `@lru_cache` on an expensive dependency

§3.1 — without it, `get_collection` reloads the embedding model on every single request, which is needlessly slow.

## Returning `500` for a problem that isn't the server's own fault

§3.2 — an invalid upstream LLM response is a `502`, not a `500`. Getting this distinction right matters for whoever debugs this in production without reading the source.

## Assuming every error response has a JSON body

§3.3 — FastAPI's default unhandled-exception response has no body at all. A client that always calls `.json()` unconditionally will crash on exactly the errors it most needs to report clearly.

## Only testing with `TestClient`, never a real running server

§4.3 — `TestClient` proves your code is wired correctly. It doesn't prove the thing works as an actual HTTP service reachable over a real socket — that's a different, complementary check.

---

# Interview Preparation

1. Walk through what `Depends(get_collection)` actually does when a request hits `/search`.
2. Why is `get_collection` wrapped in `@lru_cache`, and what would break (or just slow down) without it?
3. Explain the difference between a `422`, a `502`, and a `500` in this week's API, with a concrete example of what triggers each.
4. Why does `app.dependency_overrides` let you test `/ask` without a real API key?
5. Walk through the real bug found in `call_api.py` (§3.3) — what happened, and why did checking `status_code` alone not prevent it?
6. Why does this week's test suite include both `TestClient` tests and a real-server example script, instead of just one or the other?
7. What does the `client` fixture's `yield`-then-teardown shape (§4.2) actually prevent?
8. Why does `/health` have no dependencies, while `/search` and `/ask` both depend on `get_collection`?

---

# Week 14 Quiz

## Multiple Choice

1. What does `response_model=list[SearchResult]` do?

   A. Nothing at runtime — it's just documentation  
   B. Validates that the route's return value matches SearchResult's shape before sending the response  
   C. Converts the response to XML  
   D. Requires a database connection

2. Why does `/search` return `422` for an empty query string?

   A. FastAPI always returns 422 for POST requests  
   B. `Field(min_length=1)` on SearchRequest rejects it before the route function ever runs  
   C. The collection is empty  
   D. It's a server configuration error

3. Why is a bad LLM response mapped to `502` rather than `500`?

   A. 502 is easier to remember  
   B. 502 signals "this server's upstream dependency failed," which is more specific and accurate than a generic 500  
   C. There's no real difference  
   D. 500 is reserved for database errors

4. What did the real bug in `call_api.py` reveal?

   A. FastAPI doesn't support error responses  
   B. Not every error response has a JSON body, and a client that assumes one will crash on exactly the errors it most needs to handle  
   C. httpx cannot make POST requests  
   D. The collection was corrupted

5. Why does the `client` pytest fixture use `yield` instead of `return`?

   A. `yield` is required for all fixtures  
   B. Code after `yield` runs as teardown, letting the fixture clean up `app.dependency_overrides` after each test  
   C. `return` doesn't work with TestClient  
   D. There's no difference between yield and return here

## Short Answer

6. Explain, in your own words, why `get_collection` and `get_generate` are functions passed to `Depends(...)` rather than global variables the route functions reference directly.

7. Why does testing with `TestClient` alone not fully prove the API "works," per §4.3?

8. What's the practical difference, for someone debugging a production incident, between seeing a `502` versus a `500` in their logs?

9. Why does `_wait_for_server` poll `/health` in a loop instead of using a fixed `time.sleep()`?

10. If you added a fourth endpoint tomorrow, what two things (from this week's pattern) would it need to be consistent with the other three?

---

# Week 14 Project Submission Checklist

- [ ] `/health`, `/search`, and `/ask` all exist and work when tested with `TestClient`.
- [ ] `/search` and `/ask` both use `Depends(...)` for the collection (and `/ask` for the LLM call too) rather than hardcoding either.
- [ ] Request validation (`422`) is confirmed working for at least one bad-input case.
- [ ] You extended `SearchRequest` with at least one new field and tested it.
- [ ] `examples/week-14/call_api.py` runs against a real server and you've read its output for both success and failure cases.
- [ ] `pytest` passes, including `test_dependency_overrides_do_not_leak_between_tests`.
- [ ] `LLM_API_KEY`/`LLM_MODEL` are set in your own `.env` (not committed).
- [ ] All work is committed and pushed to GitHub.

---

# Week 14 Reflection

Write 200–300 words answering:

1. What did you build or extend this week?
2. Explain FastAPI's dependency injection in your own words, using `get_collection` as the example.
3. Describe the real bug found in `call_api.py` and what it taught you about error handling on the client side, not just the server side.
4. Why does this week's test suite include both `TestClient` tests and a real running server, rather than just one?
5. What would you improve about this week's API design?

Save as:

```text
week14_reflection.md
```

---

# Key Terms

| Term | Definition |
|---|---|
| Dependency injection | Passing a required resource (e.g. a collection, an LLM call) into code from outside, rather than hardcoding it |
| `response_model` | A pydantic model FastAPI validates a route's return value against before sending the response |
| `422 Unprocessable Entity` | The status code for a request that fails validation before reaching your code |
| `502 Bad Gateway` | The status code for a failure caused by an upstream dependency, not the server itself |
| `TestClient` | FastAPI's in-process test client — exercises real routing/validation without a real socket |
| Dependency override | Replacing a FastAPI dependency with a stub for the duration of a test |

---

# Week Summary

During Week 14, you:

- exposed Week 9's retrieval and Week 10's RAG pipeline through `/health`, `/search`, and `/ask`;
- learned FastAPI's dependency-injection pattern, and why `@lru_cache` matters for an expensive dependency like an embedding model;
- made a deliberate, defensible choice between `502` and `500` for different failure causes;
- found and fixed a real bug in the example client script itself — not every error response has a JSON body;
- tested endpoints with `TestClient` and `app.dependency_overrides`, and separately live-verified the API as a real running HTTP service.

---

# Suggested Reading

## Required

- FastAPI documentation, "Dependencies" and "Testing"
- FastAPI documentation, "Handling Errors"

## Recommended

- Starlette documentation, "TestClient" (the library FastAPI's TestClient is built on)

---

# Next Week

## Week 15: Deployment

Week 15 introduces:

- configuration and secrets management for a deployed service, beyond a local `.env` file;
- logging and dependency management for production, not just development;
- deployment options for the API this week built;
- writing deployment documentation so someone else could actually run what you built.

This week's API is fully built and tested — Week 15 is about getting it running somewhere other than your own machine.
