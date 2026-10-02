"""Ingestion pipeline coordinating document loading, parsing, and cleaning."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from rag.core.exceptions import IngestionError
from rag.ingestion.cleaners.base import BaseDocumentCleaner
from rag.ingestion.cleaners.text_cleaner import TextCleaner
from rag.ingestion.loaders.base import BaseDocumentLoader
from rag.ingestion.loaders.pdf import PDFLoader
from rag.ingestion.parsers.base import BaseDocumentParser
from rag.ingestion.parsers.pdf import PDFParser
from rag.types.document import Document


class IngestionPipeline:
    """Orchestrates Loading -> Parsing -> Cleaning of documents."""

    def __init__(
        self,
        loader: BaseDocumentLoader | None = None,
        parser: BaseDocumentParser | None = None,
        cleaner: BaseDocumentCleaner | None = None,
    ):
        self.loader = loader or PDFLoader()
        self.parser = parser or PDFParser()
        self.cleaner = cleaner or TextCleaner()

    def run(
        self,
        source: str | Path | BinaryIO,
        document_id: str | None = None,
    ) -> Document:
        """Execute the ingestion pipeline on the given source."""
        raw = self.loader.load(source)
        try:
            document = self.parser.parse(raw, document_id=document_id)
            document = self.cleaner.clean(document)
            return document
        finally:
            if hasattr(raw, "close"):
                try:
                    raw.close()
                except Exception:
                    pass
