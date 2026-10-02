"""Base interface for response generator strategies."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterator

from rag.core.base import BaseComponent


class BaseGenerator(BaseComponent):
    """Abstract base class for generating answers given user queries and context."""

    @abstractmethod
    def generate(self, query: str, context: str, **kwargs) -> str:
        """Generate a complete text answer."""
        pass

    @abstractmethod
    def generate_stream(self, query: str, context: str, **kwargs) -> Iterator[str]:
        """Stream generated text answer tokens."""
        pass
