"""PDF layout parser producing canonical Document models."""

from __future__ import annotations

from typing import Any

import pymupdf

from rag.core.registry import register
from rag.ingestion.parsers.base import BaseDocumentParser
from rag.types.document import (
    Document,
    GraphicBlock,
    Page,
    TableBlock,
    TextBlock,
)


@register("parser", "pdf")
class PDFParser(BaseDocumentParser):
    """Parses PyMuPDF documents into canonical Document structures with layout blocks."""

    def __init__(self, extract_tables: bool = True, extract_graphics: bool = False):
        self.extract_tables = extract_tables
        self.extract_graphics = extract_graphics

    def parse(self, raw_data: pymupdf.Document, document_id: str | None = None) -> Document:
        doc_id = document_id or self._create_document_id(raw_data)
        metadata = dict(raw_data.metadata) if raw_data.metadata else {}

        pages: list[Page] = []
        for page_number, page in enumerate(raw_data, start=1):
            page_data = self._parse_page(
                pdf=raw_data,
                page=page,
                page_number=page_number,
                document_id=doc_id,
            )
            pages.append(page_data)

        return Document(
            document_id=doc_id,
            page_count=len(raw_data),
            metadata=metadata,
            pages=pages,
        )

    def _parse_page(
        self,
        pdf: pymupdf.Document,
        page: pymupdf.Page,
        page_number: int,
        document_id: str,
    ) -> Page:
        dimensions = {
            "width": float(page.rect.width),
            "height": float(page.rect.height),
        }

        # 1. Text blocks
        blocks: list[TextBlock] = []
        page_text_accum = []
        text_blocks = page.get_text("blocks", sort=True)

        for block_index, block in enumerate(text_blocks):
            x0, y0, x1, y1, text, *rest = block
            clean_block_text = text.strip()
            if not clean_block_text:
                continue

            blocks.append(
                TextBlock(
                    id=f"{document_id}_p{page_number}_b{block_index}",
                    text=clean_block_text,
                    bbox=[float(x0), float(y0), float(x1), float(y1)],
                )
            )
            page_text_accum.append(clean_block_text)

        full_text = "\n\n".join(page_text_accum)

        # 2. Tables
        tables: list[TableBlock] = []
        if self.extract_tables:
            tables = self._extract_tables(page, page_number, document_id)

        # 3. Graphics
        graphics: list[GraphicBlock] = []
        if self.extract_graphics:
            graphics = self._extract_graphics(page, page_number, document_id)

        return Page(
            page_number=page_number,
            text=full_text,
            dimensions=dimensions,
            blocks=blocks,
            tables=tables,
            graphics=graphics,
        )

    def _extract_tables(
        self,
        page: pymupdf.Page,
        page_number: int,
        document_id: str,
    ) -> list[TableBlock]:
        tables: list[TableBlock] = []
        try:
            finder = page.find_tables()
            for index, table in enumerate(finder.tables):
                raw_rows = table.extract()
                if not raw_rows:
                    continue
                cleaned_rows = [
                    [cell.strip() if isinstance(cell, str) else cell for cell in row]
                    for row in raw_rows
                ]
                tables.append(
                    TableBlock(
                        id=f"{document_id}_p{page_number}_table{index}",
                        rows=cleaned_rows,
                        row_count=len(cleaned_rows),
                        column_count=len(cleaned_rows[0]) if cleaned_rows else 0,
                        bbox=[float(x) for x in table.bbox],
                    )
                )
        except Exception:
            # Table extraction errors should not crash full document ingestion
            pass
        return tables

    def _extract_graphics(
        self,
        page: pymupdf.Page,
        page_number: int,
        document_id: str,
    ) -> list[GraphicBlock]:
        graphics: list[GraphicBlock] = []
        try:
            drawings = page.get_drawings()
            for index, drawing in enumerate(drawings):
                rect = drawing.get("rect")
                bbox = (
                    [float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)]
                    if rect
                    else None
                )
                graphics.append(
                    GraphicBlock(
                        id=f"{document_id}_p{page_number}_graphic{index}",
                        bbox=bbox,
                        items=drawing.get("items", []),
                        fill=drawing.get("fill"),
                        color=drawing.get("color"),
                        width=drawing.get("width"),
                    )
                )
        except Exception:
            pass
        return graphics

    def _create_document_id(self, pdf: pymupdf.Document) -> str:
        metadata = pdf.metadata or {}
        title = metadata.get("title") or "document"
        safe = "".join(c.lower() if c.isalnum() else "_" for c in title)
        return safe.strip("_") or "document"
