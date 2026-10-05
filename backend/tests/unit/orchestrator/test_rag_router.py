"""Unit tests for the RAG router heuristic decision logic."""

from __future__ import annotations

import pytest

from orchestrator.rag_router import _BYPASS_PREFIXES, _CONTEXT_SIGNALS, needs_rag


@pytest.mark.unit
class TestRAGRouter:
    @pytest.mark.parametrize(
        "query",
        [
            "",
            "   ",
            "\n\t",
            "hi",
            "hello",
            "hey",
            "thanks",
            "thank you",
            "hey bot",
            "hi there",
        ],
    )
    def test_chitchat_and_empty_bypasses_rag(self, query: str) -> None:
        assert needs_rag(query) is False

    @pytest.mark.parametrize(
        "signal",
        [
            "document",
            "documents",
            "doc",
            "file",
            "pdf",
            "uploaded",
            "indexed",
            "ingested",
            "knowledge base",
            "retrieve",
            "retrieval",
            "search",
            "find",
            "lookup",
            "look up",
            "fetch",
            "context",
            "sources",
            "citations",
            "latest",
            "recent",
            "update",
            "chunk",
            "chunks",
            "embedding",
            "vector",
            "pipeline",
        ],
    )
    def test_explicit_signals_trigger_rag(self, signal: str) -> None:
        query = f"Can you please {signal} the platform architecture?"
        assert needs_rag(query) is True

    @pytest.mark.parametrize(
        "prefix",
        [
            "what is ",
            "what's ",
            "who is ",
            "who's ",
            "define ",
            "explain ",
            "how does ",
            "why does ",
            "tell me about ",
        ],
    )
    def test_general_knowledge_bypass_prefixes(self, prefix: str) -> None:
        query = f"{prefix}photosynthesis in plants?"
        assert needs_rag(query) is False

    def test_signal_overrides_bypass_prefix(self) -> None:
        # Query starts with bypass prefix "what is ", but contains signal "document"
        # Step 2 (signals) runs before Step 3 (bypass prefixes) in needs_rag!
        query = "what is described in the document?"
        assert needs_rag(query) is True

    def test_case_and_whitespace_insensitivity(self) -> None:
        assert needs_rag("  SEARCH FOR THE CHUNKS   ") is True
        assert needs_rag("  HELLO THERE  ") is False

    def test_conservative_default(self) -> None:
        # A specific domain question that doesn't match a bypass prefix or signal
        query = "Compare convolutional filters against attention weights."
        assert needs_rag(query) is True
