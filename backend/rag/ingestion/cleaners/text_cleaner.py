"""Text cleaner normalizing whitespace, newlines, and artifacts."""

from __future__ import annotations

import re

from rag.core.registry import register
from rag.ingestion.cleaners.base import BaseDocumentCleaner
from rag.types.document import Document


@register("cleaner", "default")
@register("cleaner", "text")
class TextCleaner(BaseDocumentCleaner):
    """Normalizes whitespace, line breaks, and spacing in Document pages and blocks."""

    def clean(self, document: Document) -> Document:
        for page in document.pages:
            page.text = self._clean_text(page.text)
            for block in page.blocks:
                block.text = self._clean_text(block.text)

        return document

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        # Normalize horizontal whitespace
        text = re.sub(r"[ \t]+", " ", text)
        # Normalize multiple line breaks to max 2
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        # Remove spaces bordering newlines
        text = re.sub(r" *\n *", "\n", text)
        return text.strip()
