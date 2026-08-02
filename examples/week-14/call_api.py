"""Week 14: run the real FastAPI server and call it over real HTTP.

Requires LLM_API_KEY and LLM_MODEL in a .env file (see .env.example) for
/ask, which calls a real LLM. /health and /search need no API key at all.
Reuses the persistent collection Week 9 built (data/processed/chroma) —
run examples/week-09/build_passage_index.py first if you haven't already.

This starts a real uvicorn server in a background thread and talks to it
over a real TCP socket with httpx — not FastAPI's in-process TestClient
(that's what the test suite uses; this script demonstrates the actual
"small, documented web API" the week's objective asks for).

Run this file directly:

    python examples/week-14/call_api.py
"""

from __future__ import annotations

import threading
import time

import httpx
import uvicorn
from dotenv import load_dotenv

from ai_finance_course.api import app

HOST = "127.0.0.1"
PORT = 8014
BASE_URL = f"http://{HOST}:{PORT}"


def _run_server() -> None:
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def _wait_for_server(timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    with httpx.Client(base_url=BASE_URL) as client:
        while time.monotonic() < deadline:
            try:
                if client.get("/health").status_code == 200:
                    return
            except httpx.ConnectError:
                time.sleep(0.1)
    raise RuntimeError("Server did not start within the timeout.")


def main() -> None:
    load_dotenv()

    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()
    _wait_for_server()

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
            # A 500 here (not just 502/422) usually means LLM_API_KEY/LLM_MODEL
            # aren't set — a server misconfiguration, not a bad request — and
            # FastAPI's default unhandled-exception response has no JSON body.
            print(f"  {ask.text or '(no response body — check LLM_API_KEY/LLM_MODEL are set)'}")


if __name__ == "__main__":
    main()
