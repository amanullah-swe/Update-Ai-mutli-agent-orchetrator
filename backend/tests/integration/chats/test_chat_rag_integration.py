"""Integration tests: WebSocket chat messaging with RAG pipeline and PGVector citations."""

from __future__ import annotations

import uuid
import pytest

from app.features.chats.models import Message
from app.features.chats.schemas import Source
from orchestrator.chat_orchestrator import ChatOrchestrator
from orchestrator.llm_client import MockLLMClient
from rag.context.builder import DefaultContextBuilder
from rag.generation.llm import OpenRouterGenerator
from rag.pipeline import RAGPipeline
from rag.query.passthrough import PassThroughQueryTransformer
from rag.reranking.noop import NoOpReranker
from rag.retrieval.dense import DenseRetriever
from rag.types.chunk import Chunk, ChunkType
from rag.vectorstores.pgvector import PGVectorStore


@pytest.mark.integration
class TestChatRAGIntegration:
    def test_websocket_turn_with_real_pgvector_rag(
        self, client, db_session, monkeypatch
    ) -> None:
        # 1. Seed PostgreSQL pgvector with test chunk
        store = PGVectorStore(session=db_session)
        test_doc_id = f"doc-{uuid.uuid4().hex[:8]}"
        test_chunk = Chunk(
            id=f"c-{uuid.uuid4().hex[:8]}",
            document_id=test_doc_id,
            content="FastAPI backend integrates with pgvector for semantic retrieval.",
            chunk_type=ChunkType.TEXT,
            page_number=1,
            metadata={"title": "RAG Manual"},
            embedding=[0.05] * 384,
        )
        store.add_chunks([test_chunk])

        # 2. Build real RAG pipeline with mock embedder
        class MockEmbeddingModel:
            dimension = 384
            def embed_text(self, text: str) -> list[float]:
                return [0.05] * 384

        retriever = DenseRetriever(vector_store=store, embedding_model=MockEmbeddingModel())
        rag_pipeline = RAGPipeline(
            query_transformer=PassThroughQueryTransformer(),
            retriever=retriever,
            reranker=NoOpReranker(),
            context_builder=DefaultContextBuilder(),
            generator=OpenRouterGenerator(),
        )

        # 3. Patch build_chat_orchestrator in ws.py to attach this RAG pipeline
        import app.features.chats.ws as ws_module
        def patched_builder(settings):
            return ChatOrchestrator(MockLLMClient(), rag_pipeline=rag_pipeline)

        monkeypatch.setattr(ws_module, "build_chat_orchestrator", patched_builder)

        # 4. Create chat
        chat_resp = client.post("/api/chats", json={"title": "RAG Integration Test"})
        assert chat_resp.status_code == 201
        chat_id = chat_resp.json()["id"]

        # 5. Connect WebSocket and ask question that needs RAG
        with client.websocket_connect(f"/api/chats/{chat_id}/ws") as ws:
            assert ws.receive_json()["type"] == "ready"

            # Send question containing signal "search"
            ws.send_json({"type": "user_message", "content": "search document for pgvector"})

            frames = []
            while True:
                frame = ws.receive_json()
                frames.append(frame)
                if frame["type"] == "message_end":
                    break

            # Verify frame sequence
            types = [f["type"] for f in frames]
            assert "sources" in types

            sources_frame = next(f for f in frames if f["type"] == "sources")
            sources = sources_frame["sources"]
            assert len(sources) >= 1
            assert sources[0]["document_id"] == test_doc_id
            assert sources[0]["chunk_id"] == test_chunk.id

        # 6. Verify transcript in database has sources JSON persisted
        db_messages = (
            db_session.query(Message)
            .where(Message.conversation_id == uuid.UUID(chat_id))
            .order_by(Message.created_at)
            .all()
        )
        assert len(db_messages) == 2
        assistant_msg = db_messages[1]
        assert assistant_msg.role == "assistant"
        assert assistant_msg.sources is not None
        assert assistant_msg.sources[0]["chunk_id"] == test_chunk.id

        # 7. Verify GET /api/chats/{chat_id} endpoint returns the sources
        get_resp = client.get(f"/api/chats/{chat_id}")
        assert get_resp.status_code == 200
        get_body = get_resp.json()
        assert len(get_body["messages"]) == 2
        assert get_body["messages"][1]["sources"][0]["chunk_id"] == test_chunk.id
