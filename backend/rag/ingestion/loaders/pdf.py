"""PDF loader using PyMuPDF (fitz)."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import pymupdf

from rag.core.exceptions import IngestionError
from rag.core.registry import register
from rag.ingestion.loaders.base import BaseDocumentLoader


@register("loader", "pdf")
class PDFLoader(BaseDocumentLoader):
    """Loads PDF documents using PyMuPDF."""

    def load(self, source: str | Path | BinaryIO) -> pymupdf.Document:
        if isinstance(source, (str, Path)):
            path = Path(source)
            if not path.exists():
                raise IngestionError(f"PDF file not found: {path}")
            if path.suffix.lower() != ".pdf":
                raise IngestionError(f"File is not a PDF: {path}")
            try:
                return pymupdf.open(str(path))
            except Exception as exc:
                raise IngestionError(f"Failed to open PDF {path}: {exc}") from exc
        else:
            try:
                content = source.read()
                return pymupdf.open(stream=content, filetype="pdf")
            except Exception as exc:
                raise IngestionError(f"Failed to open PDF stream: {exc}") from exc
