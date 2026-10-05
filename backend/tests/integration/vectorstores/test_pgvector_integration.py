"""Integration tests for PGVectorStore with real PostgreSQL and pgvector."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from rag.types.chunk import Chunk, ChunkType
from rag.vectorstores.models import ChunkModel
from rag.vectorstores.pgvector import PGVectorStore


@pytest.mark.integration
class TestPGVectorStoreIntegration:
    def test_add_chunks_and_query_pgvector(self, db_session) -> None:
        store = PGVectorStore(session=db_session)

        # Clear existing chunks for isolation
        store.delete_by_document("test-doc-1")

        vec1 = [1.0] + [0.0] * 383
        vec2 = [0.0, 1.0] + [0.0] * 382

        chunk1 = Chunk(
            id="chunk-aligned",
            document_id="test-doc-1",
            content="Document on deep learning architectures.",
            chunk_type=ChunkType.TEXT,
            page_number=1,
            metadata={"source": "deep_learning.pdf"},
            embedding=vec1,
        )
        chunk2 = Chunk(
            id="chunk-orthogonal",
            document_id="test-doc-1",
            content="Document on database indexing strategies.",
            chunk_type=ChunkType.TEXT,
            page_number=2,
            metadata={"source": "databases.pdf"},
            embedding=vec2,
        )

        store.add_chunks([chunk1, chunk2])

        # Verify rows stored in database
        count = db_session.execute(
            select(ChunkModel).where(ChunkModel.document_id == "test-doc-1")
        ).scalars().all()
        assert len(count) == 2

        # Query aligned with vec1
        query_vec = [1.0] + [0.0] * 383
        results = store.search(query_vec, top_k=2, filters={"document_id": "test-doc-1"})

        assert len(results) == 2
        # First chunk should be chunk-aligned with score close to 1.0
        assert results[0].chunk.id == "chunk-aligned"
        assert pytest.approx(results[0].score, abs=0.01) == 1.0

        # Second chunk should be chunk-orthogonal with score close to 0.0
        assert results[1].chunk.id == "chunk-orthogonal"
        assert pytest.approx(results[1].score, abs=0.01) == 0.0

    def test_upsert_chunk_updates_record(self, db_session) -> None:
        store = PGVectorStore(session=db_session)
        store.delete_by_document("test-doc-upsert")

        vec = [0.5] * 384
        c = Chunk(
            id="chunk-upsert-1",
            document_id="test-doc-upsert",
            content="Initial text content",
            chunk_type=ChunkType.TEXT,
            embedding=vec,
        )
        store.add_chunks([c])

        # Re-add with modified content
        c_modified = Chunk(
            id="chunk-upsert-1",
            document_id="test-doc-upsert",
            content="Updated text content",
            chunk_type=ChunkType.TEXT,
            embedding=vec,
        )
        store.add_chunks([c_modified])

        row = db_session.execute(
            select(ChunkModel).where(ChunkModel.id == "chunk-upsert-1")
        ).scalar_one()
        assert row.content == "Updated text content"

    def test_search_with_document_filter(self, db_session) -> None:
        store = PGVectorStore(session=db_session)
        store.delete_by_document("doc-alpha")
        store.delete_by_document("doc-beta")

        vec = [0.2] * 384
        c_alpha = Chunk(id="ca", document_id="doc-alpha", content="Alpha text", embedding=vec)
        c_beta = Chunk(id="cb", document_id="doc-beta", content="Beta text", embedding=vec)

        store.add_chunks([c_alpha, c_beta])

        results = store.search(vec, top_k=5, filters={"document_id": "doc-alpha"})
        assert len(results) == 1
        assert results[0].chunk.document_id == "doc-alpha"

    def test_delete_by_document(self, db_session) -> None:
        store = PGVectorStore(session=db_session)
        vec = [0.1] * 384
        c1 = Chunk(id="del-1", document_id="to-delete-doc", content="Text", embedding=vec)
        c2 = Chunk(id="keep-1", document_id="to-keep-doc", content="Text", embedding=vec)

        store.add_chunks([c1, c2])
        store.delete_by_document("to-delete-doc")

        remaining = db_session.execute(
            select(ChunkModel).where(ChunkModel.document_id.in_(["to-delete-doc", "to-keep-doc"]))
        ).scalars().all()

        assert len(remaining) == 1
        assert remaining[0].document_id == "to-keep-doc"
