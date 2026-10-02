"""Base interface for document cleaners."""

from __future__ import annotations

from abc import abstractmethod

from rag.core.base import BaseComponent
from rag.types.document import Document


class BaseDocumentCleaner(BaseComponent):
    """Abstract base class for cleaning and normalizing document text and structure."""

    @abstractmethod
    def clean(self, document: Document) -> Document:
        """Clean and return the normalized document."""
        pass
