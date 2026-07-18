import httpx
import pytest

from sec_thesis.config import Settings
from sec_thesis.sec_client import SECClient, SECClientError


def _settings(tmp_path, **overrides) -> Settings:
    kwargs = {
        "sec_user_agent": "Test test@example.com",
        "cache_dir": tmp_path / "cache",
        "request_delay_seconds": 0.0,
        "backoff_seconds": 0.01,
        "max_retries": 2,
    }
    kwargs.update(overrides)
    return Settings(**kwargs)


def test_get_json_success(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"name": "DEMO Corp"})

    with SECClient(_settings(tmp_path), transport=httpx.MockTransport(handler)) as client:
        data = client.get_json("https://data.sec.gov/example.json")

    assert data == {"name": "DEMO Corp"}


def test_get_json_uses_cache(tmp_path) -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json={"name": "DEMO Corp"})

    with SECClient(_settings(tmp_path), transport=httpx.MockTransport(handler)) as client:
        client.get_json("https://data.sec.gov/example.json")
        client.get_json("https://data.sec.gov/example.json")

    assert calls["count"] == 1


def test_retries_on_429_then_succeeds(tmp_path) -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"ok": True})

    with SECClient(_settings(tmp_path), transport=httpx.MockTransport(handler)) as client:
        data = client.get_json("https://data.sec.gov/example.json")

    assert calls["count"] == 2
    assert data == {"ok": True}


def test_404_raises_without_retry(tmp_path) -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(404, json={"error": "not found"})

    with SECClient(_settings(tmp_path), transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SECClientError, match="404"):
            client.get_json("https://data.sec.gov/missing.json", use_cache=False)

    assert calls["count"] == 1


def test_download_caches_file(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>filing</html>")

    with SECClient(_settings(tmp_path), transport=httpx.MockTransport(handler)) as client:
        path = client.download("https://www.sec.gov/example-filing.htm")

    assert path.exists()
    assert path.read_bytes() == b"<html>filing</html>"
