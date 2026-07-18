"""A caching, rate-limited, retrying SEC HTTP client.

Deliberately standalone (see CLAUDE.md) rather than built on
ai_finance_course.edgar.EdgarClient, even though the retry/backoff shape
is similar — this package doesn't depend on the course's teaching package.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import httpx

from sec_thesis.config import Settings


class SECClientError(Exception):
    """Raised when SEC returns an error response, or retries are exhausted."""


class SECClient:
    """A configured client for SEC's data.sec.gov / www.sec.gov endpoints.

    Every request is rate-limited (rule 10), retried with backoff on
    transient failures, and cached to disk so re-running a command doesn't
    re-hit SEC for data it already has.
    """

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings
        self._client = httpx.Client(
            headers={"User-Agent": settings.sec_user_agent},
            timeout=15.0,
            transport=transport,
        )
        self._last_request_at = 0.0
        settings.cache_dir.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> SECClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._client.close()

    def _cache_path(self, url: str, suffix: str) -> Path:
        digest = hashlib.sha256(url.encode()).hexdigest()[:16]
        return self.settings.cache_dir / f"{digest}{suffix}"

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.settings.request_delay_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _request_with_retries(self, url: str) -> httpx.Response:
        """GET a URL, rate-limited and retried with backoff.

        Retries on 429/5xx and network errors; raises immediately on other
        4xx (e.g. 404), since retrying those can't help.
        """
        last_error = ""
        response: httpx.Response | None = None

        for attempt in range(self.settings.max_retries + 1):
            self._rate_limit()
            self._last_request_at = time.monotonic()
            try:
                response = self._client.get(url)
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                response = None
            else:
                if response.status_code < 400:
                    return response
                if response.status_code != 429 and response.status_code < 500:
                    raise SECClientError(
                        f"GET {url} failed with {response.status_code}: {response.text[:200]}"
                    )
                last_error = f"HTTP {response.status_code}"

            if attempt < self.settings.max_retries:
                retry_after = response.headers.get("Retry-After") if response is not None else None
                wait_seconds = (
                    float(retry_after)
                    if retry_after
                    else self.settings.backoff_seconds * (2**attempt)
                )
                time.sleep(wait_seconds)

        raise SECClientError(
            f"GET {url} failed after {self.settings.max_retries + 1} attempts: {last_error}"
        )

    def get_json(self, url: str, *, use_cache: bool = True) -> dict:
        """GET a JSON endpoint, using the on-disk cache when available."""
        cache_path = self._cache_path(url, ".json")
        if use_cache and cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        data = self._request_with_retries(url).json()
        cache_path.write_text(json.dumps(data), encoding="utf-8")
        return data

    def download(self, url: str, *, use_cache: bool = True) -> Path:
        """Download a document (e.g. a filing), caching it to disk.

        Returns:
            The local cache path the content was saved to.
        """
        cache_path = self._cache_path(url, ".html")
        if use_cache and cache_path.exists():
            return cache_path

        response = self._request_with_retries(url)
        cache_path.write_bytes(response.content)
        return cache_path
