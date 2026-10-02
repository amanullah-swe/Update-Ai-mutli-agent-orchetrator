"""PostgreSQL + pgvector vector store implementation."""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from rag.core.exceptions import RetrievalError
from rag.core.registry import register
from rag.types.chunk import Chunk, ChunkType
from rag.types.retrieval import RetrievedChunk
from rag.vectorstores.base import BaseVectorStore
from rag.vectorstores.models import ChunkModel


@register("vectorstore", "pgvector")
class PGVectorStore(BaseVectorStore):
    """VectorStore implementation backed by PostgreSQL and pgvector."""

    def __init__(
        self,
        session_factory: Callable[[], Session] | None = None,
        session: Session | None = None,
    ):
        self._session = session
        self._session_factory = session_factory or SessionLocal

    def _get_session(self) -> Session:
        if self._session is not None:
            return self._session
        return self._session_factory()

    def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return

        session = self._get_session()
        should_close = self._session is None

        try:
            records = []
            for chunk in chunks:
                record = ChunkModel(
                    id=chunk.id,
                    document_id=chunk.document_id,
                    content=chunk.content,
                    chunk_type=(
                        chunk.chunk_type.value
                        if isinstance(chunk.chunk_type, ChunkType)
                        else str(chunk.chunk_type)
                    ),
                    page_number=chunk.page_number,
                    chunk_metadata=chunk.metadata,
                    embedding=chunk.embedding,
                )
                records.append(record)

            # Upsert or merge
            for record in records:
                session.merge(record)

            session.commit()
        except Exception as exc:
            session.rollback()
            raise RetrievalError(f"Failed to add chunks to pgvector: {exc}") from exc
        finally:
            if should_close:
                session.close()

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        session = self._get_session()
        should_close = self._session is None

        try:
            # Cosine distance ordering: chunk.embedding.cosine_distance(query_embedding)
            distance = ChunkModel.embedding.cosine_distance(query_embedding)
            stmt = select(ChunkModel, distance.label("distance")).order_by("distance").limit(top_k)

            if filters and "document_id" in filters:
                stmt = stmt.where(ChunkModel.document_id == filters["document_id"])

            results = session.execute(stmt).all()

            retrieved: list[RetrievedChunk] = []
            for model, dist in results:
                # Cosine similarity = 1 - cosine distance
                sim = 1.0 - float(dist) if dist is not None else 0.0
                chunk = Chunk(
                    id=model.id,
                    document_id=model.document_id,
                    content=model.content,
                    chunk_type=model.chunk_type,
                    page_number=model.page_number,
                    metadata=model.chunk_metadata,
                    embedding=model.embedding,
                )
                retrieved.append(
                    RetrievedChunk(
                        chunk=chunk,
                        score=sim,
                        retriever="pgvector",
                    )
                )

            return retrieved
        except Exception as exc:
            raise RetrievalError(f"Vector search failed: {exc}") from exc
        finally:
            if should_close:
                session.close()

    def delete_by_document(self, document_id: str) -> None:
        session = self._get_session()
        should_close = self._session is None

        try:
            stmt = delete(ChunkModel).where(ChunkModel.document_id == document_id)
            session.execute(stmt)
            session.commit()
        except Exception as exc:
            session.rollback()
            raise RetrievalError(f"Failed to delete chunks for document {document_id}: {exc}") from exc
        finally:
            if should_close:
                session.close()
