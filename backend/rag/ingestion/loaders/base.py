"""Base interface for document loaders."""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Any, BinaryIO

from rag.core.base import BaseComponent


class BaseDocumentLoader(BaseComponent):
    """Abstract base class for loading documents from filesystem or streams."""

    @abstractmethod
    def load(self, source: str | Path | BinaryIO) -> Any:
        """Load document content from a path or stream into a format consumable by a parser."""
        pass
