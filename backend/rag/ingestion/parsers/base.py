"""Base interface for document parsers."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from rag.core.base import BaseComponent
from rag.types.document import Document


class BaseDocumentParser(BaseComponent):
    """Abstract base class for parsing loaded documents into canonical Document models."""

    @abstractmethod
    def parse(self, raw_data: Any, document_id: str | None = None) -> Document:
        """Parse raw document data (e.g. pymupdf.Document) into a canonical Document."""
        pass
