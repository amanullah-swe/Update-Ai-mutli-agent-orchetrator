"""Integration tests for the document indexing CLI script."""

from __future__ import annotations

from pathlib import Path
import pytest
from sqlalchemy import select

from rag.embeddings.openrouter import OpenRouterEmbeddings
from rag.vectorstores.models import ChunkModel
from scripts.index_document import run_indexing


@pytest.mark.integration
class TestIndexDocumentScript:
    def test_run_indexing_success(
        self, synthetic_pdf_path: Path, db_session, monkeypatch
    ) -> None:
        # Mock OpenRouterEmbeddings.embed_batch to avoid remote network dependency
        def mock_embed_batch(self, texts, batch_size=64):
            return [[0.05] * 384 for _ in texts]

        monkeypatch.setattr(OpenRouterEmbeddings, "embed_batch", mock_embed_batch)

        # Run indexing
        run_indexing(synthetic_pdf_path)

        # Verify chunks table in PostgreSQL
        chunks = db_session.execute(
            select(ChunkModel).order_by(ChunkModel.page_number)
        ).scalars().all()

        assert len(chunks) >= 2
        pages = {c.page_number for c in chunks}
        assert 1 in pages and 2 in pages
        assert all(len(c.embedding) == 384 for c in chunks)
        assert any("Architecture" in c.content for c in chunks)

    def test_run_indexing_missing_file_exits(self, tmp_path: Path) -> None:
        missing_pdf = tmp_path / "does_not_exist.pdf"
        with pytest.raises(SystemExit) as exc_info:
            run_indexing(missing_pdf)
        assert exc_info.value.code == 1
