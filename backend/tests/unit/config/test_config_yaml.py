"""Unit tests: Settings reads configs/<env>.yaml.

Regression for the REPO_ROOT bug (parents[3] resolved to backend/, so the YAML
layer never loaded). These assertions fail against the old path.
"""

from __future__ import annotations

import pytest

from app.core.config import Settings

_RAG_VARS = (
    "RAG_ENVIRONMENT",
    "RAG_DATABASE_URL",
    "RAG_CORS_ORIGINS",
    "RAG_CHAT_PROVIDER",
    "RAG_MOCK_TOKEN_DELAY_MS",
    "RAG_LLM_PROVIDER",
    "RAG_LLM_MODEL",
    "RAG_LLM_API_KEY",
)


@pytest.fixture()
def yaml_settings(monkeypatch):
    """A Settings built purely from configs/testing.yaml (no env/.env masks)."""
    for var in _RAG_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("RAG_ENVIRONMENT", "testing")
    return Settings(_env_file=None)


def test_yaml_layer_loads_testing_config(yaml_settings) -> None:
    settings = yaml_settings
    # These are the values configs/testing.yaml sets — the "development"
    # defaults would survive only if YAML never loaded.
    assert settings.environment == "testing"
    assert (
        settings.database_url
        == "postgresql+psycopg://rag:rag@localhost:5432/rag_learning_test"
    )
    assert settings.chat_provider == "mock"


def test_llm_section_loads_from_yaml(yaml_settings) -> None:
    settings = yaml_settings
    assert settings.llm_provider == "openrouter"
    assert settings.llm_model == "deepseek/deepseek-v4-flash-0731"
    assert settings.llm_api_key == ""


def test_env_var_overrides_yaml(monkeypatch) -> None:
    # Build from YAML first, then layer a RAG_* env var on top (ADR-003 priority).
    for var in _RAG_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("RAG_ENVIRONMENT", "testing")
    monkeypatch.setenv("RAG_LLM_MODEL", "some/other-model")
    settings = Settings(_env_file=None)
    assert settings.llm_model == "some/other-model"
    # Everything not overridden still comes from YAML.
    assert settings.llm_provider == "openrouter"
    assert settings.chat_provider == "mock"


def test_yaml_layer_ignores_unaliased_keys(yaml_settings) -> None:
    """chunking:/retrieval: stay inert until the RAG pipeline aliases them."""
    assert not hasattr(yaml_settings, "chunking")
    assert not hasattr(yaml_settings, "retrieval")