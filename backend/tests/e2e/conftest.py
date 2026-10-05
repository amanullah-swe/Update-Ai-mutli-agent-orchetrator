"""Fixtures and test configuration for backend End-to-End (E2E) tests."""

from __future__ import annotations

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def e2e_client(migrated_database, clean_tables):
    """Clean TestClient for E2E scenarios."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def seeded_rag_document(db_session, synthetic_pdf_path: Path):
    """Seed a synthetic document into PostgreSQL pgvector for E2E testing."""
    from rag.ingestion.pipeline import IngestionPipeline
    from rag.chunking.overlap import OverlapChunker
    from rag.vectorstores.pgvector import PGVectorStore

    # Ingest synthetic PDF
    pipeline = IngestionPipeline()
    document = pipeline.run(synthetic_pdf_path)

    # Chunk
    chunker = OverlapChunker(chunk_size=400, chunk_overlap=50)
    chunks = chunker.chunk(document)

    # Deterministic 384-dim embeddings
    for idx, chunk in enumerate(chunks):
        chunk.embedding = [0.05 * (idx + 1)] * 384

    store = PGVectorStore(session=db_session)
    store.add_chunks(chunks)

    return {
        "document_id": document.document_id,
        "page_count": document.page_count,
        "chunks": chunks,
    }
