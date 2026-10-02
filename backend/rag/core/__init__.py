"""Core infrastructure for pluggable RAG strategies."""

from rag.core.base import BaseComponent
from rag.core.exceptions import (
    ComponentNotFoundError,
    IngestionError,
    RAGError,
    RetrievalError,
    StrategyRegistrationError,
)
from rag.core.registry import (
    build_component,
    get_component_class,
    list_components,
    register,
)

__all__ = [
    "BaseComponent",
    "ComponentNotFoundError",
    "IngestionError",
    "RAGError",
    "RetrievalError",
    "StrategyRegistrationError",
    "build_component",
    "get_component_class",
    "list_components",
    "register",
]
