"""Unit tests for the OverlapChunker (the active chunking strategy)."""

import pytest

from rag.chunking.overlap import OverlapChunker
from rag.types.chunk import Chunk, ChunkType
from rag.types.document import Document, Page, TableBlock


def _make_doc(text: str, tables: list | None = None) -> Document:
    page = Page(
        page_number=1,
        text=text,
        tables=tables or [],
    )
    return Document(document_id="test_doc", page_count=1, pages=[page])


SAMPLE_TEXT = (
    "The RAG pipeline processes documents in several stages. "
    "First, the document is loaded and parsed into a structured format. "
    "Then the text is cleaned and normalized for downstream use.\n\n"
    "In the chunking stage, text is split into smaller, retrieval-friendly pieces. "
    "Different strategies offer different trade-offs between chunk coherence and coverage. "
    "The OverlapChunker splits on a fixed character size with a configurable overlap window.\n\n"
    "This ensures every important sentence appears in at least one chunk even when it spans "
    "a boundary. Tables are converted to Markdown and stored as separate TABLE-type chunks."
)


def _assert_valid_chunks(chunks: list[Chunk], document_id: str = "test_doc") -> None:
    assert len(chunks) > 0, "Expected at least one chunk"
    for c in chunks:
        assert isinstance(c, Chunk), f"Expected Chunk, got {type(c)}"
        assert c.id, "Chunk must have a non-empty id"
        assert c.document_id == document_id
        assert c.content.strip(), "Chunk content must not be empty"
        assert c.page_number == 1


class TestOverlapChunker:
    def test_produces_chunks_from_text(self):
        doc = _make_doc(SAMPLE_TEXT)
        chunks = OverlapChunker(chunk_size=200, chunk_overlap=50).chunk(doc)
        _assert_valid_chunks(chunks)

    def test_all_text_chunks_have_correct_type(self):
        doc = _make_doc(SAMPLE_TEXT)
        chunks = OverlapChunker(chunk_size=300, chunk_overlap=50).chunk(doc)
        text_chunks = [c for c in chunks if c.chunk_type == ChunkType.TEXT]
        assert len(text_chunks) > 0

    def test_empty_page_produces_no_chunks(self):
        doc = _make_doc("")
        assert OverlapChunker().chunk(doc) == []

    def test_strategy_metadata_set(self):
        doc = _make_doc(SAMPLE_TEXT)
        chunks = OverlapChunker(chunk_size=200).chunk(doc)
        for c in chunks:
            assert c.metadata.get("strategy") == "overlap"

    def test_chunk_ids_are_unique(self):
        doc = _make_doc(SAMPLE_TEXT)
        chunks = OverlapChunker(chunk_size=150, chunk_overlap=30).chunk(doc)
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids)), "Chunk IDs must be unique"

    def test_respects_chunk_size_approximately(self):
        doc = _make_doc(SAMPLE_TEXT)
        chunks = OverlapChunker(chunk_size=150, chunk_overlap=0).chunk(doc)
        for c in chunks:
            # Allow slight overshoot from the trailing strip
            assert len(c.content) <= 160

    def test_table_chunks_rendered_as_markdown(self):
        rows = [["Name", "Score"], ["Alice", "95"], ["Bob", "82"]]
        table = TableBlock(id="t1", rows=rows, row_count=3, column_count=2)
        doc = _make_doc("", tables=[table])
        chunks = OverlapChunker().chunk(doc)
        table_chunks = [c for c in chunks if c.chunk_type == ChunkType.TABLE]
        assert len(table_chunks) == 1
        assert "| Name | Score |" in table_chunks[0].content
        assert "| --- |" in table_chunks[0].content
        assert "| Alice | 95 |" in table_chunks[0].content

    def test_text_and_table_chunks_together(self):
        rows = [["A", "B"], ["1", "2"]]
        table = TableBlock(id="t1", rows=rows, row_count=2, column_count=2)
        doc = _make_doc(SAMPLE_TEXT, tables=[table])
        chunks = OverlapChunker(chunk_size=300).chunk(doc)
        types = {c.chunk_type for c in chunks}
        assert ChunkType.TEXT in types
        assert ChunkType.TABLE in types

    def test_overlap_produces_more_chunks_than_no_overlap(self):
        doc = _make_doc(SAMPLE_TEXT)
        no_overlap = OverlapChunker(chunk_size=200, chunk_overlap=0).chunk(doc)
        with_overlap = OverlapChunker(chunk_size=200, chunk_overlap=100).chunk(doc)
        assert len(with_overlap) >= len(no_overlap)

    def test_multi_page_document(self):
        pages = [
            Page(page_number=i, text=f"Page {i} content. " * 20)
            for i in range(1, 4)
        ]
        doc = Document(document_id="multi", page_count=3, pages=pages)
        chunks = OverlapChunker(chunk_size=200, chunk_overlap=50).chunk(doc)
        page_numbers = {c.page_number for c in chunks}
        assert page_numbers == {1, 2, 3}, "Must produce chunks for all pages"

    def test_registered_as_overlap_and_fixed_size(self):
        from rag.core.registry import build_component
        c1 = build_component("chunking", "overlap")
        c2 = build_component("chunking", "fixed_size")
        assert isinstance(c1, OverlapChunker)
        assert isinstance(c2, OverlapChunker)
