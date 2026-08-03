# Week 15: a minimal, reproducible deployment image for the Week 14 API.
#
# python:3.12-slim matches the Python version already pinned in
# .github/workflows/tests.yml — the same "test what you'll actually run"
# reasoning as Week 13's CI fixes. Only the [rag,api] extras are
# installed: no [dev] tools (pytest, ruff) belong in a production image.
FROM python:3.12-slim

WORKDIR /app

# Copy dependency metadata first so Docker's layer cache can skip the
# (slow) pip install step on rebuilds that only change application code.
COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir -e ".[rag,api]"

# Pre-download the embedding model at build time, not startup time. Found
# live: without this, the container's first startup took ~75s and needed
# real internet access to reach huggingface.co, with several retries
# after a DNS/network hiccup — a "fully reproducible local deployment"
# (this week's own required output) shouldn't depend on that. This
# download step itself still needs network access (nothing is cached
# yet) — HF_HUB_OFFLINE is set *after*, not before, or the download
# fails outright (found live: `OSError: couldn't connect ... and
# couldn't find them in the cached files` — offline mode with nothing
# cached yet has nothing to fall back to).
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Baking the weights in was not enough by itself — also found live:
# huggingface_hub still phones home on every load to check for updates
# even when the model is already cached, unless told not to.
# HF_HUB_OFFLINE=1 disables that check for every container started from
# this image. Verified with `docker run --network none`: without this
# line the container still retried and failed against huggingface.co for
# ~30s before falling back to the local cache; with it, startup uses the
# cache immediately, no network attempt at all.
ENV HF_HUB_OFFLINE=1

# Only the sample passages are needed at runtime — the startup step
# (api.py's lifespan) indexes them if the collection is empty. Real
# filing data (data/raw/, data/processed/) is never baked into the image.
COPY data/sample/ data/sample/

EXPOSE 8000

CMD ["uvicorn", "ai_finance_course.api:app", "--host", "0.0.0.0", "--port", "8000"]
