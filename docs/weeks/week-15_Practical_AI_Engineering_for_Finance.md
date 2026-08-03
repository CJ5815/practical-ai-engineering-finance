# Week 15: Deployment

**Course:** Practical AI Engineering for Finance
**Audience:** Senior undergraduate students
**Schedule:** 1 hour per day, 4 days per week
**Week Theme:** Turning Week 14's API into something someone else can actually run — consolidated configuration, structured logging, and a real, live-verified Docker deployment

---

## Week Overview

Week 14 built a working API. Week 15 makes it *runnable by someone who isn't you*: configuration read from one place instead of scattered `os.environ` calls, structured logging so a deployed process's behavior is visible without a debugger attached, and a container image that produces a working, searchable API from `docker build` + `docker run` alone — no separate indexing step, no hidden setup instructions.

**Live-verified against a real Docker container, not just `docker build` succeeding:** every claim in this lesson was checked against an actual running container — `docker run --network none` to prove the image has no hidden network dependency at startup, real `curl`/`httpx` calls against `/health`, `/search`, and `/ask`, and `docker logs` inspected directly for the exact log lines this lesson describes. That process surfaced four real, working bugs, not hypothetical ones:

1. **A 75-second, network-dependent cold start** (§3.2) — the embedding model wasn't baked into the image, so the first request downloaded it from `huggingface.co`.
2. **A subtler "phone home" check that survived fix #1** (§3.3) — even with the model cached in the image, `huggingface_hub` still checked for updates on every load unless explicitly told not to.
3. **A logging middleware that silently dropped exactly the requests most worth logging** (§2.3) — an unhandled exception skipped the middleware's own logging line entirely, found only by checking a real deployed container's logs after a request that should have failed.
4. **A stale deployed image that looked identical to the fixed one** (§3.4) — after fixing bug #3, re-testing against a container still running the *old* image made it look like the fix hadn't worked. The bug wasn't in the code the second time — it was in *which build* was actually running.

Every one of these is a real category of deployment bug, not a contrived teaching example — which is the point of this week.

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Weekly Schedule](#weekly-schedule)
- [Day 1: Configuration and Secrets](#day-1-configuration-and-secrets)
- [Day 2: Logging and Dependency Management](#day-2-logging-and-dependency-management)
- [Day 3: Deployment Options](#day-3-deployment-options)
- [Day 4: Deployment Documentation](#day-4-deployment-documentation)
- [Week 15 Coding Lab](#week-15-coding-lab)
- [Practice Exercises](#practice-exercises)
- [Common Mistakes](#common-mistakes)
- [Interview Preparation](#interview-preparation)
- [Week 15 Quiz](#week-15-quiz)
- [Week 15 Project Submission Checklist](#week-15-project-submission-checklist)
- [Week 15 Reflection](#week-15-reflection)
- [Key Terms](#key-terms)
- [Week Summary](#week-summary)
- [Suggested Reading](#suggested-reading)
- [Next Week](#next-week)

---

# Learning Objectives

By the end of Week 15, you should be able to:

- Consolidate configuration into one `Settings` object loaded from environment variables, instead of reading `os.environ` ad hoc in multiple places.
- Add structured request logging to a FastAPI app, and explain why a middleware that logs *after* `call_next` can silently skip failed requests.
- Write a `Dockerfile` that produces a working image from a clean build, ordering layers so dependency installs are cached across code-only changes.
- Diagnose a network-dependent container startup using `docker run --network none`, and fix it by baking dependencies (model weights) into the image at build time.
- Explain why an environment variable's *position* in a `Dockerfile` can matter as much as its value.
- Distinguish "the code changed" from "the deployed artifact changed" — and know how to check which one is actually true.

---

# Weekly Schedule

| Day | Topic | Main Deliverable |
|---|---|---|
| Day 1 | Configuration and secrets | `settings.py`, one `Settings` object read from `.env` |
| Day 2 | Logging and dependency management | Request-logging middleware, a startup indexing step, `pyproject.toml` extras |
| Day 3 | Deployment options | A `Dockerfile` + `docker-compose.yml`, live-verified with `docker run --network none` |
| Day 4 | Deployment documentation | Written instructions someone else could follow from a clean checkout |

Each class follows the same session structure as Weeks 1–14: review and setup, new concept, guided practice, testing, and committing the work.

---

# Day 1: Configuration and Secrets

## 1.1 One `Settings` Object, Not `os.environ` Scattered Everywhere

```python
class Settings(BaseModel):
    llm_api_key: str | None = None
    llm_model: str | None = None
    persist_path: Path = Path("data/processed/chroma")
    collection_name: str = "sample_passages"
    log_level: str = "INFO"

def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        llm_api_key=os.environ.get("LLM_API_KEY"),
        llm_model=os.environ.get("LLM_MODEL"),
        persist_path=Path(os.environ.get("PERSIST_PATH", "data/processed/chroma")),
        collection_name=os.environ.get("COLLECTION_NAME", "sample_passages"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
```

Week 14's `api.py` read `PERSIST_PATH`/`COLLECTION_NAME` as module-level constants and called `call_llm` directly with no explicit key/model handling — fine for one file, but it doesn't scale to a deployed service where configuration needs to be inspectable, testable, and documented in one place. `settings.py` mirrors the exact pattern `sec_thesis/config.py` (Week 18) already established: a `Settings(BaseModel)` plus a `load_settings()` function that reads `os.environ` once, with defaults for everything that has a sensible one.

## 1.2 `python-dotenv` — Local `.env`, Never Committed

`load_dotenv()` reads a local `.env` file into `os.environ` if one exists, and does nothing if it doesn't — meaning the same `load_settings()` code works identically whether configuration comes from a local `.env` file (development) or real environment variables set by a deployment platform (production). `.env` has been gitignored since early in this course; nothing changes there this week except that *more* configuration now flows through it.

## 1.3 `get_settings()` Is Cached, Like `get_collection()`

```python
@lru_cache
def get_settings() -> Settings:
    return load_settings()
```

Same reasoning as Week 14 §3.1's `get_collection`: `load_settings()` isn't expensive, but there's no reason to re-read and re-validate environment variables on every single request when the values can't change during the process's lifetime.

## 1.4 A Startup Step That Removes a Manual Setup Command

```python
def _ensure_sample_index(collection: Collection) -> None:
    if collection.count() > 0:
        logger.info("Collection already has %d chunks; skipping startup indexing.", collection.count())
        return
    passages = json.loads(SAMPLE_PASSAGES_PATH.read_text(encoding="utf-8"))
    for passage in passages:
        metadata = {"ticker": passage["ticker"], "doc_type": passage["doc_type"]}
        chunks = chunk_document(passage["text"], metadata, chunk_size=500, overlap=50)
        add_chunks(collection, chunks)
    logger.info("Indexed %d chunks from %d sample passages on startup.", collection.count(), len(passages))

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(get_settings().log_level)
    _ensure_sample_index(get_collection())
    yield
```

Week 14's API required running `examples/week-09/build_passage_index.py` separately before `/search` had anything to return. That's a fine assumption for local development, but this week's required output is "a fully reproducible local deployment" — someone running `docker build` + `docker run` for the first time shouldn't need a second, undocumented command just to get a non-empty collection. `_ensure_sample_index` takes `collection` as an explicit parameter rather than reaching for `get_collection()` itself — the same "pass it in, don't reach for it" reasoning behind every `Depends(...)` since Week 14 — which is exactly what makes it directly testable with a stub collection, no monkeypatching required (`test_ensure_sample_index_indexes_when_empty`, `test_ensure_sample_index_skips_when_already_populated`).

**A real, important detail about `lifespan`:** it only runs when `TestClient` is used as a context manager — `with TestClient(app) as client:` — not on a plain `TestClient(app)`. This was verified directly with a small standalone script before relying on it. It's *why* this course's existing `client` fixture (`yield TestClient(app)`, no `with`) has never accidentally triggered a real embedding-model load during `pytest` — and why the tests for `_ensure_sample_index` call it directly, rather than trying to trigger it indirectly through the app's lifespan.

## Day 1 Activity

Read `src/ai_finance_course/settings.py` and `tests/test_settings.py` in full. Then delete your local `.env` file's `LOG_LEVEL` line (or comment it out) and confirm `load_settings().log_level` still returns `"INFO"` — the default, not a crash.

---

# Day 2: Logging and Dependency Management

## 2.1 `logging.basicConfig`, Not `print`

```python
def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
```

Every previous week's scripts used `print` freely — fine for a script you run and read once. A deployed service runs unattended; its only record of what happened is whatever it wrote to its logs. `logging` (not `print`) gives every line a timestamp, a level, and the name of the logger that emitted it, which matters once you're reading logs from a container you can't attach a debugger to.

## 2.2 Request Logging as Middleware

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.monotonic() - start) * 1000
        logger.exception(
            "%s %s -> unhandled exception (%.1fms)", request.method, request.url.path, duration_ms
        )
        raise
    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        "%s %s -> %s (%.1fms)", request.method, request.url.path, response.status_code, duration_ms
    )
    return response
```

`@app.middleware("http")` wraps every request: it runs before the route handler, calls `call_next(request)` to actually handle the request, and runs again after. The straightforward first version of this function has no `try/except` at all — just `response = await call_next(request)` followed by the `logger.info(...)` call. That version has a real bug, found only by testing against a real deployed container. Read on.

## 2.3 A Real Bug: the Success-Path Log Line Never Runs on Failure

Testing `/ask` against the real running container (no `LLM_API_KEY` set in this sandbox — the same, expected failure mode as Week 14 §3.3) produced the correct `500 Internal Server Error` response. But `docker logs` showed only uvicorn's own generic `Exception in ASGI application` traceback — never the request-logging middleware's own line. The reason: the *unwrapped* version of `log_requests` has its `logger.info(...)` call positioned **after** `await call_next(request)`. When `ask()` raises an uncaught `KeyError` (from `call_llm`'s `os.environ["LLM_API_KEY"]` lookup — a missing API key, not an invalid LLM response, so it never reaches Week 14 §3.2's `502` handling), that exception propagates straight out of `call_next`, skipping every line after it in the middleware function — including the one that was supposed to log the request.

This is a genuinely important, general lesson: **code placed after a call that can raise doesn't run on the exception path**, and a logging strategy that only covers the success path is exactly backwards — a request that crashed is the one you most need a record of. The fix wraps `call_next` in `try/except Exception`, logs via `logger.exception(...)` (which includes the full traceback, not just the message), and re-raises so FastAPI's normal error handling still produces the `500` response.

## 2.4 Testing the Fix Required Understanding `TestClient`'s Exception Behavior

```python
def test_log_requests_middleware_logs_unhandled_exceptions(client, sample_collection, caplog) -> None:
    app.dependency_overrides[get_collection] = lambda: sample_collection

    def raises_key_error(prompt: str) -> str:
        raise KeyError("LLM_API_KEY")

    app.dependency_overrides[get_generate] = lambda: raises_key_error

    with caplog.at_level(logging.ERROR, logger="ai_finance_course.api"), pytest.raises(KeyError):
        client.post("/ask", json={"query": "Did revenue grow?"})

    assert any("unhandled exception" in record.message for record in caplog.records)
```

`TestClient`, with its default settings, **re-raises** an unhandled route exception rather than converting it into a `500` response object with an inspectable `.status_code` — verified directly with a small standalone script before writing this test. That's why the test wraps the `client.post(...)` call in `pytest.raises(KeyError)` instead of asserting on a response status code, and checks `caplog.records` (pytest's built-in fixture for capturing log output) instead.

## 2.5 Dependency Management for a Deployment, Not Just Development

`pyproject.toml`'s `[rag,api]` extras (from Weeks 9 and 14) are exactly what the deployed image needs — no `[dev]` tools like `pytest` or `ruff` belong in a production image. `.dockerignore` (new this week) excludes `.venv/`, `__pycache__/`, `.git/`, `docs/`, `notebooks/`, `examples/`, and both `data/raw/` and `data/processed/` from the build context — the deployed image should contain code and the small `data/sample/` fixtures it needs to self-index, nothing else.

## Day 2 Activity

Run `pytest tests/test_api.py -v -k middleware` and read both passing tests. Then temporarily remove the `try/except` from `log_requests` yourself, re-run `test_log_requests_middleware_logs_unhandled_exceptions`, and confirm it now fails — proof the test actually catches the regression it's named for.

---

# Day 3: Deployment Options

## 3.1 A Layer-Cache-Friendly `Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir -e ".[rag,api]"
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
ENV HF_HUB_OFFLINE=1
COPY data/sample/ data/sample/
EXPOSE 8000
CMD ["uvicorn", "ai_finance_course.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

`python:3.12-slim` matches the Python version already pinned in `.github/workflows/tests.yml` (Week 13) — the same "test what you'll actually run" reasoning as that week's CI fixes. Copying `pyproject.toml` and `src/` *before* `RUN pip install` is deliberate: Docker caches each layer, and if only application code changes between builds (not dependencies), the slow `pip install` layer is skipped entirely on rebuild.

## 3.2 A Real Bug: a 75-Second, Network-Dependent Cold Start

The first successful build (with real, pinned `torch==2.2.2`/`transformers`/`sentence-transformers`/`numpy<2`, confirmed to resolve correctly on genuine Linux inside the container, not just macOS) produced an image that took **~75 seconds** on its first request, logging repeated `ReadTimeoutError`/`MaxRetryError`/`NameResolutionError` warnings trying to reach `huggingface.co`. The root cause: `SentenceTransformerEmbeddingFunction` only downloads its model the first time it's actually used, which in the original Dockerfile meant *at first request time*, not build time. Fixed by adding a `RUN` step that imports and instantiates the model during the build itself, so the weights are already inside the image layer before the container ever starts:

```dockerfile
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

## 3.3 A Subtler Bug: Baking In the Model Wasn't Enough

Verifying with `docker run --network none` — deliberately giving the container *zero* network access, not just a slow connection — showed the container still attempted (and retried five times with exponential backoff, ~20–30 seconds total) to reach `huggingface.co` before falling back to the cached model. `huggingface_hub` checks for updates on every model load by default, even when the model is already cached locally. The fix is one line — but its **position** in the Dockerfile matters:

```dockerfile
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
ENV HF_HUB_OFFLINE=1
```

Setting `HF_HUB_OFFLINE=1` **before** the download step breaks the build outright: `OSError: We couldn't connect to 'https://huggingface.co' to load the files, and couldn't find them in the cached files` — offline mode with nothing cached yet has nothing to fall back to. The download step genuinely needs real network access (nothing is cached before it runs); offline mode should apply only at container *runtime*, after the model is already baked in. Re-verified with `docker run --network none` after moving the line: startup dropped to well under one second of real application work, fully network-independent — confirmed directly from the container's own timestamped logs (embedding-model load to `"Indexed 8 chunks..."` in under a second).

## 3.4 A Real Bug: the Fix That Looked Like It Didn't Work

After fixing the middleware (§2.3), rebuilding, and re-testing against `/ask`, the "unhandled exception" log line still didn't appear — even though the equivalent `pytest` test passed. The instinct here could easily have been "the fix doesn't actually work in real deployment, only in `TestClient`." The real cause was simpler and more common: `docker exec week15-test grep -n "except Exception" /app/src/ai_finance_course/api.py` showed the **running container was still using the old, unwrapped middleware** — the image had been built once, earlier in the session, and the container was never rebuilt after the middleware fix landed in `api.py`. The container's `docker inspect --format '{{.Created}}'` timestamp predated the source file's last edit. Rebuilding the image and re-running the exact same test confirmed the fix works correctly: `docker logs` showed `... ERROR ai_finance_course.api POST /ask -> unhandled exception (64.9ms)`, exactly as designed.

**The general lesson:** "I fixed the code" and "the thing that's running reflects the fix" are two different claims. A stale deployed artifact that predates a fix will silently reproduce the old bug, and nothing about that failure looks different from the fix genuinely not working — the only way to tell them apart is to check what's actually running (`docker inspect`, or just rebuilding and re-running before concluding anything).

## 3.5 `docker-compose.yml` — the Reproducible Local Deployment

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - chroma-data:/app/data/processed

volumes:
  chroma-data:
```

`docker compose up -d --build` is this week's required output: one command, from a clean checkout, produces a working, searchable API — no separate indexing step (§1.4), no manually-run model download (§3.2–3.3). The named `chroma-data` volume persists the indexed collection across container restarts, so re-running `docker compose up` doesn't re-index from scratch every time (`_ensure_sample_index`'s `collection.count() > 0` check makes that skip visible in the logs, not just implicit).

## Day 3 Activity

Run `docker build -t ai-finance-api:local .` yourself, then `docker run --network none ai-finance-api:local` in one terminal and, in another, confirm you *cannot* reach it (no port was published) — then re-run with `-p 8000:8000` and confirm `/health` responds. Read the full startup logs and find the line that proves the embedding model loaded from cache, not from the network.

---

# Day 4: Deployment Documentation

## 4.1 What "Deployment Documentation" Actually Means Here

Not a design document — instructions specific enough that someone with a clean checkout of this repository, and nothing else, could get a working API running. That means stating: what to install (Docker, nothing else — the whole point of containerizing), what file to create (`.env`, from `.env.example`, never committed), what command to run (`docker compose up -d --build`), and how to confirm it worked (`curl http://localhost:8000/health`).

## 4.2 Documenting Failure Modes, Not Just the Happy Path

Week 14 §3.3 already established that a client script needs to handle the server's error responses, not just its success responses. Deployment documentation needs the same discipline in the other direction: what does it look like when `/ask` returns `500` because `.env` is missing `LLM_API_KEY`? What does `docker compose logs api` show in that case (§2.3's `unhandled exception` line, with a full traceback)? Someone deploying this for the first time will hit that exact failure — documenting it turns a confusing crash into an expected, quickly-diagnosed configuration gap.

## 4.3 Live-Verifying the Deployed API, Not Just the Build

`examples/week-15/call_deployed_api.py` calls the real, already-running container over real HTTP — a direct parallel to Week 14's `call_api.py`, but pointed at a genuinely separate deployed process instead of an in-process server started by the script itself:

```python
BASE_URL = "http://localhost:8000"

def _check_server_is_up() -> None:
    try:
        httpx.get(f"{BASE_URL}/health", timeout=5.0).raise_for_status()
    except httpx.HTTPError:
        print(f"Could not reach {BASE_URL}. Start the container first:\n\n    docker compose up -d --build\n")
        raise SystemExit(1) from None
```

Checking the server is reachable *before* making real requests, with a specific, actionable error message, is itself part of documenting the deployment — a `ConnectError` with no context is a much worse first experience than a message that says exactly what command fixes it.

## Day 4 Activity

Write a short `DEPLOYMENT.md` (or a "Deployment" section in the README) covering: prerequisites, the exact commands to run, how to confirm success, and what the documented `/ask`-without-an-API-key failure looks like in both the HTTP response and the logs. Then hand it to someone else (a classmate, or just reread it after a day away) and see if anything is missing.

---

# Week 15 Coding Lab

## Extending the Deployment

This week's core code already exists and is tested — [`src/ai_finance_course/settings.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/src/ai_finance_course/settings.py), [`src/ai_finance_course/logging_config.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/src/ai_finance_course/logging_config.py), [`Dockerfile`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/Dockerfile), and [`docker-compose.yml`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/docker-compose.yml). Your lab work is to extend it:

- add a new `Settings` field (e.g. `request_timeout_seconds`) read from an environment variable with a sensible default, and write a test for both the default and the overridden case, following `tests/test_settings.py`'s pattern;
- add a `/version` endpoint that returns a hardcoded version string from `Settings`, and confirm the middleware logs it correctly;
- rebuild the Docker image after your changes and confirm — genuinely, by checking `docker inspect`'s creation timestamp against your file's last edit, per §3.4 — that the running container reflects your new code, not a stale build.

### Required Features

- type hints and a docstring on every function you add, following Week 2 §3.2's comment rules;
- new `Settings` fields have defaults, so `load_settings()` never crashes on a missing environment variable;
- confirm `pytest` still passes, including both middleware tests (`test_log_requests_middleware_logs_request_details`, `test_log_requests_middleware_logs_unhandled_exceptions`);
- `LLM_API_KEY`/`LLM_MODEL` (and any new secrets) live only in your own `.env`, never hard-coded or committed;
- all work committed and pushed to GitHub.

---

# Practice Exercises

## Exercise 1: Reproduce the Cold-Start Bug Yourself

Comment out the model pre-download `RUN` step in a local copy of the `Dockerfile`, rebuild, and time how long the first `/health` request takes compared to the fixed version. Write one sentence explaining, from the logs, exactly what the container was doing during that gap.

## Exercise 2: A Health Check That Checks Something

Extend `/health` to also confirm the collection is reachable (e.g., call `.count()` on it) and return `503` if it isn't — the same idea as Week 14's Exercise 1, now specifically relevant because a deployed container's health check is what an orchestrator (or a human) uses to decide if it's actually working.

## Exercise 3: Log Level as Configuration

Set `LOG_LEVEL=DEBUG` in `.env`, rebuild, and confirm (via `docker compose logs api`) that log output changes accordingly. What would go wrong if `LOG_LEVEL` were hardcoded instead of read from `Settings`?

## Exercise 4: Diagnosing a Stale Container From the Outside

Without looking at source code, using only `docker exec` and `docker inspect`, write down the steps you'd take to determine whether a running container reflects the latest committed code — the same diagnostic that resolved §3.4's bug.

## Exercise 5: Git Practice

Make separate commits for `settings.py`/`logging_config.py`, the `Dockerfile`/`docker-compose.yml`, and your deployment documentation.

---

# Common Mistakes

## Reading `os.environ` directly in multiple files

§1.1 — consolidate into one `Settings` object and one `load_settings()` function. Configuration scattered across files is configuration nobody can find or test in one place.

## Logging only on the success path

§2.3 — code placed after an `await` that can raise doesn't run when it does raise. A request-logging middleware that can't log a failed request is missing the exact case it matters most for.

## Downloading dependencies (model weights, packages) at container startup instead of build time

§3.2 — a "fully reproducible local deployment" (this week's required output) shouldn't depend on network access being available and fast every time a container starts.

## Assuming a cached dependency means zero network activity

§3.3 — some libraries check for updates on every load even when a local cache exists. `docker run --network none` is how you actually prove there's no hidden network dependency, rather than assuming it from "it seemed fast."

## Setting an offline-mode environment variable before the thing it disables has ever run once

§3.3 — `ENV HF_HUB_OFFLINE=1` before the model download breaks the build; after it, the download still gets real network access while every later container run doesn't need it.

## Concluding a fix "doesn't work" without checking whether the fix is actually what's running

§3.4 — a stale image or container reproduces the old bug perfectly, and that failure looks identical to the fix being wrong. Rebuild and re-check what's actually deployed before concluding the fix failed.

---

# Interview Preparation

1. Walk through why `settings.py` exists as one consolidated file instead of `os.environ.get(...)` calls scattered across `api.py`.
2. Explain the original request-logging middleware bug (§2.3) — why did the success-path log line never run for a failed request, and what's the general principle behind the fix?
3. Why does `TestClient` re-raise an unhandled exception rather than turning it into an inspectable `500` response, and how did that change how the regression test (§2.4) had to be written?
4. Walk through both Docker bugs found in this week (§3.2, §3.3) — why wasn't baking the model into the image enough by itself?
5. Why does `ENV HF_HUB_OFFLINE=1`'s position in the `Dockerfile` matter, not just its value?
6. Describe the §3.4 bug — what made it look like the middleware fix wasn't working, and how was the real cause actually diagnosed?
7. What's the difference between `docker run --network none` and just "the container seemed to start fast" as evidence that there's no hidden network dependency?
8. Why does `_ensure_sample_index` take `collection` as a parameter instead of calling `get_collection()` internally?

---

# Week 15 Quiz

## Multiple Choice

1. Why is `ENV HF_HUB_OFFLINE=1` placed *after* the model pre-download `RUN` step in the `Dockerfile`?

   A. Environment variable order never matters in Docker
   B. The download step still needs real network access; offline mode should only apply at container runtime, once the model is already cached
   C. `ENV` instructions must always come last
   D. It reduces the image size

2. What does `docker run --network none` prove that a normal `docker run` doesn't?

   A. That the container starts faster
   B. That the container has zero network dependency at startup — not just a fast one, but genuinely none
   C. That the image is smaller
   D. Nothing — it's equivalent to a normal run

3. Why did the original `log_requests` middleware fail to log requests that raised an unhandled exception?

   A. `logging` doesn't support error-level messages
   B. Its `logger.info(...)` call was positioned after `await call_next(request)`, which never returns if an exception propagates through it
   C. FastAPI blocks logging during exceptions
   D. The logger wasn't configured

4. In §3.4, what turned out to be the actual cause of the middleware fix "not working" against the deployed container?

   A. The fix itself was wrong
   B. `TestClient` and real deployments behave completely differently for exception handling
   C. The running container was still using an old image built before the fix — a stale deployed artifact, not a code bug
   D. Docker doesn't support middleware

5. Why does `_ensure_sample_index` take `collection` as an explicit parameter rather than calling `get_collection()` itself?

   A. It's required by FastAPI
   B. So it's directly testable with a stub collection, without monkeypatching — the same "pass it in, don't reach for it" reasoning as every `Depends(...)`
   C. `get_collection()` doesn't exist yet at that point in the file
   D. There's no real reason; it's a style preference

## Short Answer

6. Explain, in your own words, why a "fully reproducible local deployment" (this week's required output) is a stronger claim than "the Docker build succeeds."

7. What's the practical difference between `TestClient` re-raising an unhandled exception and a real deployed server returning a `500` with no body? Why did the regression test in §2.4 need to account for this?

8. Describe, step by step, how you would determine whether a running container reflects the latest code on disk — without assuming the answer either way.

9. Why does copying `pyproject.toml` and `src/` before `RUN pip install` in the `Dockerfile` matter for rebuild speed?

10. If you were deploying this API somewhere other than your own machine tomorrow, what's one question this week's lesson doesn't answer that you'd need to research first?

---

# Week 15 Project Submission Checklist

- [ ] `settings.py` consolidates all configuration into one `Settings` object, loaded via `load_settings()`.
- [ ] Request logging middleware logs both successful and failed requests — confirmed via both `pytest` and a real deployed container's logs.
- [ ] `docker compose up -d --build` produces a working API from a clean checkout, with no manual indexing step.
- [ ] You've verified (via `docker run --network none` or equivalent) that the container has no hidden network dependency at startup.
- [ ] You've confirmed, using `docker inspect` or an equivalent check, that the container you tested actually reflects your latest code.
- [ ] `examples/week-15/call_deployed_api.py` runs against the real deployed container and you've read its output for both success and failure cases.
- [ ] Deployment documentation exists and covers at least one documented failure mode, not just the happy path.
- [ ] `pytest` passes, including both middleware tests.
- [ ] `LLM_API_KEY`/`LLM_MODEL` are set only in your own `.env` (never committed).
- [ ] All work is committed and pushed to GitHub.

---

# Week 15 Reflection

Write 200–300 words answering:

1. What did you build or extend this week?
2. Explain, using the §2.3 middleware bug as the example, why "logs only on success" is a design mistake and not just an edge case.
3. Describe the §3.2/§3.3 Docker bugs and what they taught you about the difference between "it's cached" and "it never touches the network."
4. Describe the §3.4 bug — how did you (or would you) tell the difference between "the fix is wrong" and "the deployed artifact is stale"?
5. What would you improve about this week's deployment before handing it to someone else to run?

Save as:

```text
week15_reflection.md
```

---

# Key Terms

| Term | Definition |
|---|---|
| `Settings` | A single consolidated object holding all configuration, loaded once from environment variables |
| Structured logging | Log output with a consistent, parseable format (timestamp, level, logger name, message), not ad hoc `print` |
| Layer cache | Docker's mechanism for skipping unchanged build steps on rebuild, based on file-content hashes |
| Cold start | The time a container or process takes to become ready to serve its first real request |
| `--network none` | A `docker run` flag that gives a container zero network access, used to prove (not assume) it has no hidden network dependency |
| Stale artifact | A deployed image or running container that predates a fix already made in source code |

---

# Week Summary

During Week 15, you:

- consolidated configuration into one `Settings` object, loaded from `.env` via `load_dotenv()`, mirroring `sec_thesis`'s own config pattern from Week 18;
- added structured request logging, found and fixed a real bug where unhandled exceptions silently skipped the middleware's own logging line, and verified the fix against a real deployed container, not just `pytest`;
- wrote a `Dockerfile` and `docker-compose.yml` producing a fully reproducible local deployment, and found and fixed two real, distinct network-dependency bugs at container startup using `docker run --network none` as genuine verification, not assumption;
- discovered — and correctly diagnosed, rather than assumed away — that a fix which passes tests can still appear broken if the deployed artifact being tested predates it;
- wrote deployment documentation covering both the happy path and a real, expected failure mode.

---

# Suggested Reading

## Required

- Docker documentation, "Dockerfile best practices" (layer caching, `.dockerignore`)
- Python `logging` documentation, "Logging HOWTO"

## Recommended

- Hugging Face Hub documentation, "Environment variables" (`HF_HUB_OFFLINE` and related offline-mode behavior)
- Starlette documentation, "Middleware" (the `BaseHTTPMiddleware` `call_next` pattern this week's logging middleware is built on)

---

# Next Week

## Week 16: Capstone

Week 16 shifts from weekly, scaffolded lessons to an independent capstone project — applying everything built across Weeks 1–15 (prompting, retrieval, RAG, evaluation, testing, and now deployment) to a project of your own design and scope.
