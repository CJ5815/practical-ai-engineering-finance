"""Configuration for the Week 14 API, loaded from environment variables (.env).

Same pattern as sec_thesis/config.py (Week 18) — one place that reads
os.environ, everything else takes a Settings object instead of reaching
for os.environ itself. Before this week, api.py and llm_client.py each
read LLM_API_KEY/LLM_MODEL from the environment independently; scattered
os.environ reads are fine for a handful of example scripts, but a
deployed service benefits from one place to see (and change) every
configuration value.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


class Settings(BaseModel):
    """All configuration the API needs, gathered in one place."""

    llm_api_key: str | None = None
    llm_model: str | None = None
    persist_path: Path = Path("data/processed/chroma")
    collection_name: str = "sample_passages"
    log_level: str = "INFO"


def load_settings() -> Settings:
    """Load settings from the environment (reads .env if present).

    llm_api_key/llm_model are optional here, unlike sec_thesis's required
    sec_user_agent — /health and /search work with no LLM key at all;
    only /ask needs one, and it fails loudly at call time (llm_client's
    own os.environ["LLM_API_KEY"] fallback) rather than at startup, so
    the whole service isn't unusable just because /ask isn't configured.
    """
    load_dotenv()
    return Settings(
        llm_api_key=os.environ.get("LLM_API_KEY"),
        llm_model=os.environ.get("LLM_MODEL"),
        persist_path=Path(os.environ.get("PERSIST_PATH", "data/processed/chroma")),
        collection_name=os.environ.get("COLLECTION_NAME", "sample_passages"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
