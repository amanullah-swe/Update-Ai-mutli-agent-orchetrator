"""Unit tests for OpenRouter remote embeddings."""

import json
from typing import Any
import httpx
import pytest

from rag.core.exceptions import RAGError
from rag.core.registry import build_component, clear_registry
from rag.embeddings.openrouter import OpenRouterEmbeddings
from rag.retrieval.dense import DenseRetriever
from rag.types.chunk import Chunk
from rag.types.retrieval import RetrievedChunk
from rag.vectorstores.base import BaseVectorStore


def _mock_embeddings_response(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content.decode("utf-8"))
    inputs = body.get("input", [])
    data = []
    for idx, text in enumerate(inputs):
        # Deterministic mock 384-dim vector
        vector = [0.1] * 384
        data.append({"index": idx, "embedding": vector})
    return httpx.Response(200, json={"data": data})


class TestOpenRouterEmbeddings:
    def test_default_initialization(self, monkeypatch):
        import app.core.config
        monkeypatch.setattr(app.core.config, "_settings", None)
        monkeypatch.setenv("RAG_LLM_API_KEY", "sk-test-key")
        monkeypatch.delenv("RAG_EMBEDDING_MODEL", raising=False)

        emb = OpenRouterEmbeddings()
        assert emb.api_key == "sk-test-key"
        assert emb.model_name == "sentence-transformers/all-minilm-l6-v2"
        assert emb.dimension == 384

    def test_explicit_initialization(self):
        emb = OpenRouterEmbeddings(
            api_key="sk-explicit",
            model_name="custom/model",
            dimension=768,
        )
        assert emb.api_key == "sk-explicit"
        assert emb.model_name == "custom/model"
        assert emb.dimension == 768

    def test_embed_text_returns_vector(self):
        client = httpx.Client(transport=httpx.MockTransport(_mock_embeddings_response))
        emb = OpenRouterEmbeddings(api_key="sk-test", client=client)

        vector = emb.embed_text("hello world")
        assert len(vector) == 384
        assert vector[0] == 0.1

    def test_embed_batch_returns_ordered_vectors(self):
        client = httpx.Client(transport=httpx.MockTransport(_mock_embeddings_response))
        emb = OpenRouterEmbeddings(api_key="sk-test", client=client)

        texts = ["first chunk", "second chunk", "third chunk"]
        vectors = emb.embed_batch(texts)
        assert len(vectors) == 3
        assert all(len(v) == 384 for v in vectors)

    def test_embed_batch_with_chunking(self):
        client = httpx.Client(transport=httpx.MockTransport(_mock_embeddings_response))
        emb = OpenRouterEmbeddings(api_key="sk-test", client=client)

        texts = [f"chunk {i}" for i in range(10)]
        vectors = emb.embed_batch(texts, batch_size=3)
        assert len(vectors) == 10
        assert all(len(v) == 384 for v in vectors)

    def test_empty_input_returns_empty_list(self):
        client = httpx.Client(transport=httpx.MockTransport(_mock_embeddings_response))
        emb = OpenRouterEmbeddings(api_key="sk-test", client=client)
        assert emb.embed_text("") != []  # empty string still gets embedded
        assert emb.embed_batch([]) == []

    def test_missing_api_key_raises_rag_error(self, monkeypatch):
        monkeypatch.delenv("RAG_LLM_API_KEY", raising=False)
        monkeypatch.delenv("RAG_EMBEDDING_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

        emb = OpenRouterEmbeddings(api_key="")
        with pytest.raises(RAGError, match="OpenRouter API key is missing"):
            emb.embed_text("test")

    def test_http_error_raises_rag_error(self):
        def _error_response(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "Internal Server Error"})

        client = httpx.Client(transport=httpx.MockTransport(_error_response))
        emb = OpenRouterEmbeddings(api_key="sk-test", client=client)

        with pytest.raises(RAGError, match="Failed to generate OpenRouter embeddings"):
            emb.embed_text("test")


class MockVectorStore(BaseVectorStore):
    def __init__(self):
        self.last_query_embedding = None

    def add_chunks(self, chunks):
        pass

    def search(self, query_embedding, top_k=5, filters=None):
        self.last_query_embedding = query_embedding
        return [
            RetrievedChunk(
                chunk=Chunk(id="c1", document_id="d1", content="mock doc"),
                score=0.95,
            )
        ]

    def delete_by_document(self, document_id):
        pass


class TestDenseRetrieverWithOpenRouter:
    def test_dense_retriever_defaults_to_openrouter(self):
        client = httpx.Client(transport=httpx.MockTransport(_mock_embeddings_response))
        emb = OpenRouterEmbeddings(api_key="sk-test", client=client)
        store = MockVectorStore()

        retriever = DenseRetriever(vector_store=store, embedding_model=emb)
        results = retriever.retrieve("query text", top_k=1)

        assert len(results) == 1
        assert results[0].chunk.id == "c1"
        assert len(store.last_query_embedding) == 384


def test_registry_has_openrouter_embeddings():
    import rag.embeddings
    obj = build_component("embedding", "openrouter", api_key="sk-test")
    assert isinstance(obj, OpenRouterEmbeddings)

    default_obj = build_component("embedding", "default", api_key="sk-test")
    assert isinstance(default_obj, OpenRouterEmbeddings)

    alias_obj = build_component("embedding", "sentence_transformer", api_key="sk-test")
    assert isinstance(alias_obj, OpenRouterEmbeddings)
