"""Week 15: call the REAL deployed Docker container over HTTP.

Unlike Week 14's call_api.py (which starts an in-process uvicorn server in
a background thread), this script assumes the API is already running as a
real, separate process in a real container — the actual "deployment" this
week is about. Start it first:

    docker compose up -d --build

Then run this file:

    python examples/week-15/call_deployed_api.py

No LLM_API_KEY is needed for /health or /search — the container's startup
lifespan (api.py's _ensure_sample_index) indexes data/sample/passages.json
automatically, so /search has real data to query without running Week 9's
build_passage_index.py first. /ask needs LLM_API_KEY and LLM_MODEL in the
.env file docker-compose.yml passes into the container (env_file: .env) —
without it, /ask returns 500, which this script treats as an expected,
documented outcome (same handling as Week 14's call_api.py §4.3), not a
bug to crash on.
"""

from __future__ import annotations

import sys

import httpx

BASE_URL = "http://localhost:8000"


def _check_server_is_up() -> None:
    try:
        httpx.get(f"{BASE_URL}/health", timeout=5.0).raise_for_status()
    except httpx.HTTPError:
        print(
            f"Could not reach {BASE_URL}. Start the container first:\n\n"
            "    docker compose up -d --build\n",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


def main() -> None:
    _check_server_is_up()

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        health = client.get("/health")
        print(f"GET /health -> {health.status_code} {health.json()}")

        query = "did the company beat earnings expectations?"
        search = client.post("/search", json={"query": query, "n_results": 3})
        print(f"\nPOST /search -> {search.status_code}")
        for result in search.json():
            print(f"  [{result['distance']:.3f}] ({result['ticker']}) {result['text']}")

        ask = client.post("/ask", json={"query": query, "n_results": 3})
        print(f"\nPOST /ask -> {ask.status_code}")
        if ask.status_code == 200:
            body = ask.json()
            print(f"  answer: {body['answer']}")
            print(f"  citations: {body['citations']}")
        else:
            print(f"  {ask.text or '(no response body — check LLM_API_KEY/LLM_MODEL in .env)'}")

    print("\nRequest logs (including any unhandled exceptions) are visible via:")
    print("    docker compose logs api")


if __name__ == "__main__":
    main()
