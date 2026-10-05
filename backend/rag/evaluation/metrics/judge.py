"""OpenRouter LLM Judge and Embeddings factories for Ragas metrics."""

from __future__ import annotations

from typing import Any

from openai import OpenAI
from ragas.embeddings import OpenAIEmbeddings
from ragas.llms import llm_factory

DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_JUDGE_MODEL = "qwen/qwen3.8-27b:free"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-minilm-l6-v2"


def resolve_judge_config() -> tuple[str, str, str, str]:
    """Resolve API key, judge model, embedding model, and base URL from Settings."""
    api_key = ""
    model = DEFAULT_JUDGE_MODEL
    embedding_model = DEFAULT_EMBEDDING_MODEL
    base_url = DEFAULT_OPENROUTER_BASE_URL

    try:
        from app.core.config import get_settings

        settings = get_settings()
        api_key = getattr(settings, "llm_api_key", "")
        model = getattr(settings, "llm_model", DEFAULT_JUDGE_MODEL)
        embedding_model = getattr(
            settings, "embedding_model", DEFAULT_EMBEDDING_MODEL
        )
    except Exception:
        pass

    return api_key, model, embedding_model, base_url


def build_judge_llm(
    api_key: str | None = None,
    model: str | None = None,
    base_url: str = DEFAULT_OPENROUTER_BASE_URL,
    client: OpenAI | None = None,
) -> Any:
    """Build a Ragas-compatible judge LLM backed by OpenRouter.

    Args:
        api_key: OpenRouter API key (defaults to resolved settings).
        model: Target model name (defaults to qwen/qwen3.8-27b:free).
        base_url: Base URL for OpenRouter API.
        client: Optional preconfigured OpenAI client (useful for unit testing).

    Returns:
        Configured Ragas InstructorLLM instance.
    """
    resolved_key, resolved_model, _, _ = resolve_judge_config()
    final_key = api_key if api_key is not None else resolved_key
    final_model = model if model is not None else resolved_model

    if client is None:
        client = OpenAI(
            api_key=final_key or "missing-key",
            base_url=base_url.rstrip("/"),
        )

    return llm_factory(model=final_model, client=client)


def build_judge_embeddings(
    api_key: str | None = None,
    model: str | None = None,
    base_url: str = DEFAULT_OPENROUTER_BASE_URL,
    client: OpenAI | None = None,
) -> OpenAIEmbeddings:
    """Build a Ragas-compatible OpenAIEmbeddings model backed by OpenRouter.

    Args:
        api_key: OpenRouter API key (defaults to resolved settings).
        model: Embedding model name (defaults to sentence-transformers/all-minilm-l6-v2).
        base_url: Base URL for OpenRouter API.
        client: Optional preconfigured OpenAI client.

    Returns:
        Configured Ragas OpenAIEmbeddings instance.
    """
    resolved_key, _, resolved_emb_model, _ = resolve_judge_config()
    final_key = api_key if api_key is not None else resolved_key
    final_model = model if model is not None else resolved_emb_model

    if client is None:
        client = OpenAI(
            api_key=final_key or "missing-key",
            base_url=base_url.rstrip("/"),
        )

    return OpenAIEmbeddings(model=final_model, client=client)
