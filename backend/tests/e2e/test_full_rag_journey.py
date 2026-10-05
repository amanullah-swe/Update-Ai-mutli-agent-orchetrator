"""End-to-End Test: Full RAG user journey (Ingestion -> Chat Creation -> WS Streaming -> Citations -> Transcript)."""

from __future__ import annotations

import pytest

from orchestrator.chat_orchestrator import ChatOrchestrator
from orchestrator.llm_client import MockLLMClient
from rag.context.builder import DefaultContextBuilder
from rag.generation.llm import OpenRouterGenerator
from rag.pipeline import RAGPipeline
from rag.query.passthrough import PassThroughQueryTransformer
from rag.reranking.noop import NoOpReranker
from rag.retrieval.dense import DenseRetriever
from rag.vectorstores.pgvector import PGVectorStore


@pytest.mark.e2e
class TestFullRAGJourney:
    def test_complete_rag_journey(
        self, e2e_client, db_session, seeded_rag_document, monkeypatch
    ) -> None:
        doc_info = seeded_rag_document

        # 1. Wire RAG pipeline with PGVectorStore
        store = PGVectorStore(session=db_session)

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

        import app.features.chats.ws as ws_module
        monkeypatch.setattr(
            ws_module,
            "build_chat_orchestrator",
            lambda settings: ChatOrchestrator(MockLLMClient(), rag_pipeline=rag_pipeline),
        )

        # 2. User creates a chat via REST API
        create_resp = e2e_client.post("/api/chats", json={"title": "RAG Learning Flow"})
        assert create_resp.status_code == 201
        chat_data = create_resp.json()
        chat_id = chat_data["id"]
        assert chat_data["title"] == "RAG Learning Flow"

        # 3. User connects to WebSocket and sends question
        with e2e_client.websocket_connect(f"/api/chats/{chat_id}/ws") as ws:
            ready_frame = ws.receive_json()
            assert ready_frame["type"] == "ready"
            assert ready_frame["chat_id"] == chat_id

            # Ask question triggering RAG
            ws.send_json({
                "type": "user_message",
                "content": "search the document for RAG Platform Architecture",
            })

            frames = []
            while True:
                frame = ws.receive_json()
                frames.append(frame)
                if frame["type"] == "message_end":
                    break

            # 4. Verify frame sequence and content
            frame_types = [f["type"] for f in frames]
            assert frame_types[0] == "message"        # user ack
            assert frame_types[1] == "message_start"  # assistant start
            assert "token" in frame_types             # streamed tokens
            assert "sources" in frame_types           # citations
            assert frame_types[-1] == "message_end"   # completion ack

            sources_frame = next(f for f in frames if f["type"] == "sources")
            assert len(sources_frame["sources"]) >= 1
            citation = sources_frame["sources"][0]
            assert citation["document_id"] == doc_info["document_id"]
            assert citation["snippet"] is not None

        # 5. User re-fetches transcript via REST API
        detail_resp = e2e_client.get(f"/api/chats/{chat_id}")
        assert detail_resp.status_code == 200
        transcript = detail_resp.json()

        assert transcript["id"] == chat_id
        assert len(transcript["messages"]) == 2
        user_msg, assistant_msg = transcript["messages"]

        assert user_msg["role"] == "user"
        assert "RAG Platform Architecture" in user_msg["content"]

        assert assistant_msg["role"] == "assistant"
        assert assistant_msg["sources"] is not None
        assert len(assistant_msg["sources"]) >= 1
        assert assistant_msg["sources"][0]["document_id"] == doc_info["document_id"]
