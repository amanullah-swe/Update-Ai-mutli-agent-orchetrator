"""Typed application settings.

Loaded once at startup from ``configs/<environment>.yaml`` (lowest priority),
overlaid by ``.env`` and environment variables (``RAG_*`` wins). Components
receive the resolved ``Settings`` via dependency injection and never read YAML
or env vars themselves (build decision #3).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Type

import yaml
from pydantic import Field
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


def _find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / "configs").is_dir() and (parent / "backend").is_dir():
            return parent
    return Path(__file__).resolve().parents[3]


REPO_ROOT = _find_repo_root()

# Map a dotted YAML path to the Settings field it populates. Keys not listed
# here (e.g. future RAG ``chunking:``/``retrieval:`` strategy sections) are
# ignored today and none of the Settings fields construct them.
_YAML_ALIASES: dict[tuple[str, ...], str] = {
    ("app", "name"): "app_name",
    ("app", "environment"): "environment",
    ("app", "debug"): "debug",
    ("app", "version"): "version",
    ("database", "url"): "database_url",
    ("cors", "origins"): "cors_origins",
    ("chat", "provider"): "chat_provider",
    ("chat", "mock", "token_delay_ms"): "mock_token_delay_ms",
    ("llm", "provider"): "llm_provider",
    ("llm", "model"): "llm_model",
    ("llm", "api_key"): "llm_api_key",
    ("embedding", "provider"): "embedding_provider",
    ("embedding", "model"): "embedding_model",
    ("embedding", "dimension"): "embedding_dimension",
    ("embedding", "api_key"): "embedding_api_key",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- app -------------------------------------------------------------
    app_name: str = "rag-learning-platform"
    environment: str = "development"
    debug: bool = False
    version: str = "0.1.0"

    # --- database --------------------------------------------------------
    database_url: str = (
        "postgresql+psycopg://rag:rag@localhost:5432/rag_learning"
    )

    # --- http ------------------------------------------------------------
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- chat -------------------------------------------------------------
    chat_provider: str = "mock"  # mock | openrouter; dev/prod YAML set openrouter
    mock_token_delay_ms: int = 0  # dev YAML sets 25; tests keep 0

    # --- llm --------------------------------------------------------------
    llm_provider: str = "openrouter"  # CLAUDE.md provider convention (reserved; seam is chat.provider)
    llm_model: str = "qwen/qwen3.8-27b:free"
    llm_api_key: str = ""  # from env RAG_LLM_API_KEY only; never commit a real key

    # --- embedding --------------------------------------------------------
    embedding_provider: str = "openrouter"
    embedding_model: str = "sentence-transformers/all-minilm-l6-v2"
    embedding_dimension: int = 384
    embedding_api_key: str = ""  # defaults to llm_api_key if empty

    def yaml_file(self) -> Path:
        return REPO_ROOT / "configs" / f"{self.environment}.yaml"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Priority: init > env > dotenv > yaml file
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlSettingsSource(settings_cls),
        )


class YamlSettingsSource(PydanticBaseSettingsSource):
    """Reads ``configs/<RAG_ENVIRONMENT>.yaml`` as the lowest-priority source."""

    def __init__(self, settings_cls: type[BaseSettings]) -> None:
        super().__init__(settings_cls)
        self._data = self._load_yaml()

    def _load_yaml(self) -> dict[str, Any]:
        environment = os.getenv("RAG_ENVIRONMENT", "development")
        path = REPO_ROOT / "configs" / f"{environment}.yaml"
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        return _flatten(raw, aliases=_YAML_ALIASES)

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        return self._data.get(field_name), field_name, False

    def __call__(self) -> dict[str, Any]:
        return dict(self._data)


def _flatten(data: dict[str, Any], aliases: dict[tuple[str, ...], str]) -> dict[str, Any]:
    """Flatten nested YAML into Settings field names via the alias table."""
    out: dict[str, Any] = {}
    stack: list[tuple[tuple[str, ...], Any]] = [((), data)]
    while stack:
        prefix, value = stack.pop()
        if isinstance(value, dict):
            stack.extend(((*prefix, k), v) for k, v in value.items())
            continue
        field_name = aliases.get(prefix)
        if field_name is not None:
            out[field_name] = value
    return out


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the process-wide Settings (cached after first construction)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


get_app_settings = get_settings

