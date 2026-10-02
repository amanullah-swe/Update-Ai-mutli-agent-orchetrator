"""Exceptions for the RAG subsystem."""

from __future__ import annotations


class RAGError(Exception):
    """Base exception for all RAG pipeline errors."""


class ComponentNotFoundError(RAGError):
    """Raised when a requested strategy cannot be found in the registry."""

    def __init__(self, kind: str, name: str, available: list[str] | None = None):
        msg = f"Unknown {kind} strategy '{name}'."
        if available:
            msg += f" Available strategies: {', '.join(sorted(available))}"
        super().__init__(msg)
        self.kind = kind
        self.name = name
        self.available = available or []


class StrategyRegistrationError(RAGError):
    """Raised when an invalid strategy registration is attempted."""


class IngestionError(RAGError):
    """Raised when document loading, parsing, or cleaning fails."""


class RetrievalError(RAGError):
    """Raised when query retrieval or vector search fails."""
