"""Unit tests for PDFLoader and PDFParser."""

from __future__ import annotations

import io
from pathlib import Path
import pytest

from rag.core.exceptions import IngestionError
from rag.ingestion.loaders.pdf import PDFLoader
from rag.ingestion.parsers.pdf import PDFParser


@pytest.mark.unit
class TestPDFLoaderAndParser:
    def test_pdf_loader_from_file_path(self, synthetic_pdf_path: Path) -> None:
        loader = PDFLoader()
        pdf_doc = loader.load(synthetic_pdf_path)
        assert len(pdf_doc) == 2
        pdf_doc.close()

    def test_pdf_loader_from_stream(self, synthetic_pdf_bytes: bytes) -> None:
        loader = PDFLoader()
        stream = io.BytesIO(synthetic_pdf_bytes)
        pdf_doc = loader.load(stream)
        assert len(pdf_doc) == 2
        pdf_doc.close()

    def test_pdf_loader_missing_file_raises(self, tmp_path: Path) -> None:
        loader = PDFLoader()
        with pytest.raises(IngestionError, match="PDF file not found"):
            loader.load(tmp_path / "missing.pdf")

    def test_pdf_loader_wrong_extension_raises(self, tmp_path: Path) -> None:
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a pdf")
        loader = PDFLoader()
        with pytest.raises(IngestionError, match="File is not a PDF"):
            loader.load(txt_file)

    def test_pdf_parser_generates_canonical_document(
        self, synthetic_pdf_path: Path
    ) -> None:
        loader = PDFLoader()
        raw_doc = loader.load(synthetic_pdf_path)

        parser = PDFParser(extract_tables=True, extract_graphics=True)
        doc = parser.parse(raw_doc, document_id="custom_test_doc")
        raw_doc.close()

        assert doc.document_id == "custom_test_doc"
        assert doc.page_count == 2
        assert len(doc.pages) == 2

        # Page 1 validation
        p1 = doc.pages[0]
        assert p1.page_number == 1
        assert "Architecture" in p1.text
        assert len(p1.blocks) >= 1
        assert p1.blocks[0].bbox is not None
        assert len(p1.blocks[0].bbox) == 4

        # Page 2 validation
        p2 = doc.pages[1]
        assert p2.page_number == 2
        assert "Embeddings" in p2.text
