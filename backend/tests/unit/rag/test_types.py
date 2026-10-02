"""Unit tests for RAG canonical domain types."""

from rag.types.chunk import Chunk, ChunkType
from rag.types.document import Document, Page, TextBlock, TableBlock
from rag.types.retrieval import RetrievalQuery, RetrievedChunk, SearchResult


def test_document_creation_and_full_text():
    p1 = Page(
        page_number=1,
        text="Introduction to RAG systems.",
        blocks=[TextBlock(id="b1", text="Introduction to RAG systems.")],
    )
    p2 = Page(
        page_number=2,
        text="Chapter 2: Retrieval Strategies.",
        blocks=[TextBlock(id="b2", text="Chapter 2: Retrieval Strategies.")],
    )
    doc = Document(document_id="doc_1", page_count=2, pages=[p1, p2])

    assert doc.document_id == "doc_1"
    assert doc.page_count == 2
    full_text = doc.get_full_text()
    assert "Introduction to RAG systems." in full_text
    assert "Chapter 2: Retrieval Strategies." in full_text

    # Serialization roundtrip
    d = doc.to_dict()
    reconstructed = Document.from_dict(d)
    assert reconstructed.document_id == doc.document_id
    assert len(reconstructed.pages) == 2
    assert reconstructed.pages[0].text == p1.text


def test_chunk_serialization():
    chunk = Chunk(
        id="c1",
        document_id="doc_1",
        content="Some chunk content",
        chunk_type=ChunkType.TEXT,
        page_number=1,
        metadata={"key": "val"},
        embedding=[0.1, 0.2, 0.3],
    )

    data = chunk.to_dict()
    assert data["chunk_type"] == "text"
    assert data["id"] == "c1"

    reconstructed = Chunk.from_dict(data)
    assert reconstructed.id == "c1"
    assert reconstructed.chunk_type == ChunkType.TEXT
    assert reconstructed.embedding == [0.1, 0.2, 0.3]


def test_retrieval_models():
    chunk = Chunk(id="c1", document_id="d1", content="Answer context", page_number=3)
    retrieved = RetrievedChunk(chunk=chunk, score=0.95, retriever="dense")

    assert retrieved.content == "Answer context"
    assert retrieved.document_id == "d1"
    assert retrieved.page_number == 3
    assert retrieved.score == 0.95

    query = RetrievalQuery(text="What is RAG?", top_k=3)
    result = SearchResult(query=query.text, chunks=[retrieved])
    assert result.query == "What is RAG?"
    assert len(result.chunks) == 1
