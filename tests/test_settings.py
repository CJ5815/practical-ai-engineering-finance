"""Tests for settings.py."""

from __future__ import annotations

from pathlib import Path

from ai_finance_course.settings import load_settings


def test_load_settings_defaults_when_env_vars_unset(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("PERSIST_PATH", raising=False)
    monkeypatch.delenv("COLLECTION_NAME", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = load_settings()

    assert settings.llm_api_key is None
    assert settings.llm_model is None
    assert settings.persist_path == Path("data/processed/chroma")
    assert settings.collection_name == "sample_passages"
    assert settings.log_level == "INFO"


def test_load_settings_reads_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("PERSIST_PATH", "/tmp/custom-chroma")
    monkeypatch.setenv("COLLECTION_NAME", "custom_passages")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = load_settings()

    assert settings.llm_api_key == "test-key"
    assert settings.llm_model == "test-model"
    assert settings.persist_path == Path("/tmp/custom-chroma")
    assert settings.collection_name == "custom_passages"
    assert settings.log_level == "DEBUG"
