"""Configuration for sec_thesis, loaded from environment variables (.env).

Rule 14 (CLAUDE.md): no API keys or secrets are hardcoded here — everything
that varies by environment is read from os.environ, following the same
python-dotenv pattern as ai_finance_course (Week 5 Sec. 1.2).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


class Settings(BaseModel):
    """All configuration sec_thesis needs, gathered in one place."""

    sec_user_agent: str
    cache_dir: Path = Path("data/raw")
    duckdb_path: Path = Path("data/processed/sec_thesis.duckdb")
    request_delay_seconds: float = 0.2
    max_retries: int = 3
    backoff_seconds: float = 1.0


def load_settings() -> Settings:
    """Load settings from the environment (reads .env if present).

    Raises:
        KeyError: If SEC_USER_AGENT isn't set — a loud, immediate error
            rather than silently sending unidentified requests to SEC.
    """
    load_dotenv()
    return Settings(
        sec_user_agent=os.environ["SEC_USER_AGENT"],
        cache_dir=Path(os.environ.get("SEC_THESIS_CACHE_DIR", "data/raw")),
        duckdb_path=Path(
            os.environ.get("SEC_THESIS_DB_PATH", "data/processed/sec_thesis.duckdb")
        ),
    )
