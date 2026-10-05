"""Unit tests for the OpenRouterGenerator."""

from __future__ import annotations

import httpx
import pytest

from rag.core.exceptions import RAGError
from rag.generation.llm import OpenRouterGenerator


@pytest.mark.unit
class TestOpenRouterGenerator:
    def test_simulated_answer_when_no_api_key(self) -> None:
        generator = OpenRouterGenerator(api_key="")
        answer = generator.generate("What is RAG?", "RAG is retrieval augmented generation.")
        assert "[Simulated Answer]" in answer
        assert "What is RAG?" in answer
        assert "retrieval augmented generation" in answer

    def test_generate_stream_yields_words(self) -> None:
        generator = OpenRouterGenerator(api_key="")
        stream = list(generator.generate_stream("What is RAG?", "Context text."))
        assert len(stream) > 1
        assert "".join(stream).strip() == generator.generate("What is RAG?", "Context text.").strip()

    def test_build_messages_with_and_without_context(self) -> None:
        generator = OpenRouterGenerator()
        msgs_ctx = generator._build_messages("my query", "my context")
        assert len(msgs_ctx) == 2
        assert "Context:\nmy context\n\nQuestion:\nmy query" == msgs_ctx[1]["content"]

        msgs_no_ctx = generator._build_messages("my query", "")
        assert msgs_no_ctx[1]["content"] == "my query"

    def test_generate_with_mock_http_response(self, monkeypatch) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "Real generated answer."}}]},
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        monkeypatch.setattr(httpx, "Client", lambda **kwargs: client)

        generator = OpenRouterGenerator(api_key="sk-test-key")
        answer = generator.generate("What is RAG?", "Context details.")
        assert answer == "Real generated answer."

    def test_generate_handles_http_failure(self, monkeypatch) -> None:
        def error_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "OpenRouter server error"})

        client = httpx.Client(transport=httpx.MockTransport(error_handler))
        monkeypatch.setattr(httpx, "Client", lambda **kwargs: client)

        generator = OpenRouterGenerator(api_key="sk-test-key")
        with pytest.raises(RAGError, match="OpenRouter generation failed"):
            generator.generate("Query", "Context")
