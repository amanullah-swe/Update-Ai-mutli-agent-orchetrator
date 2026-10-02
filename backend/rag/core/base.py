"""Base component definition for swappable RAG strategies."""

from __future__ import annotations

from abc import ABC


class BaseComponent(ABC):
    """Abstract base class that all pluggable RAG components inherit from."""

    def initialize(self) -> None:
        """Optional hook called upon component initialization."""
        pass

    def shutdown(self) -> None:
        """Optional hook called during teardown or system shutdown."""
        pass
