"""Unit tests for the Ingestion pipeline (loader, parser, cleaner)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rag.ingestion.cleaners.text_cleaner import TextCleaner
from rag.ingestion.pipeline import IngestionPipeline
from rag.types.document import Document, Page, TextBlock


def _make_test_document() -> Document:
    return Document(
        document_id="test_doc",
        page_count=1,
        pages=[
            Page(
                page_number=1,
                text="  Hello   world  \n\n\n   Extra lines  \n\n",
                blocks=[
                    TextBlock(id="b1", text="  Hello   world  \n\n\n"),
                    TextBlock(id="b2", text="   Extra lines  \n\n"),
                ],
            )
        ],
    )


class TestTextCleaner:
    def test_normalizes_whitespace(self):
        doc = _make_test_document()
        cleaner = TextCleaner()
        cleaned = cleaner.clean(doc)
        assert "  " not in cleaned.pages[0].text

    def test_removes_excessive_newlines(self):
        doc = _make_test_document()
        cleaner = TextCleaner()
        cleaned = cleaner.clean(doc)
        assert "\n\n\n" not in cleaned.pages[0].text

    def test_blocks_also_cleaned(self):
        doc = _make_test_document()
        cleaner = TextCleaner()
        cleaned = cleaner.clean(doc)
        for block in cleaned.pages[0].blocks:
            assert "  " not in block.text

    def test_empty_text_survives(self):
        doc = Document(
            document_id="empty",
            pages=[Page(page_number=1, text="", blocks=[])],
        )
        cleaned = TextCleaner().clean(doc)
        assert cleaned.pages[0].text == ""


class TestIngestionPipeline:
    def test_run_uses_loader_parser_cleaner(self):
        """Verify the pipeline calls load → parse → clean in order."""
        mock_loader = MagicMock()
        mock_parser = MagicMock()
        mock_cleaner = MagicMock()

        raw_doc = MagicMock()
        canonical_doc = _make_test_document()
        cleaned_doc = _make_test_document()

        mock_loader.load.return_value = raw_doc
        mock_parser.parse.return_value = canonical_doc
        mock_cleaner.clean.return_value = cleaned_doc

        pipeline = IngestionPipeline(
            loader=mock_loader,
            parser=mock_parser,
            cleaner=mock_cleaner,
        )

        result = pipeline.run("/fake/path/doc.pdf")

        mock_loader.load.assert_called_once_with("/fake/path/doc.pdf")
        mock_parser.parse.assert_called_once_with(raw_doc, document_id=None)
        mock_cleaner.clean.assert_called_once_with(canonical_doc)
        assert result is cleaned_doc

    def test_run_closes_raw_doc(self):
        """The pipeline must close the raw document handle."""
        mock_loader = MagicMock()
        mock_parser = MagicMock()
        mock_cleaner = MagicMock()

        raw_doc = MagicMock()
        raw_doc.close = MagicMock()

        mock_loader.load.return_value = raw_doc
        mock_parser.parse.return_value = _make_test_document()
        mock_cleaner.clean.return_value = _make_test_document()

        pipeline = IngestionPipeline(
            loader=mock_loader,
            parser=mock_parser,
            cleaner=mock_cleaner,
        )
        pipeline.run("/fake/path.pdf")
        raw_doc.close.assert_called_once()
