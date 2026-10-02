"""Default context builder injecting source metadata and delimiters."""

from __future__ import annotations

from rag.context.base import BaseContextBuilder
from rag.core.registry import register
from rag.types.retrieval import RetrievedChunk


@register("context_builder", "default")
class DefaultContextBuilder(BaseContextBuilder):
    """Formats retrieved chunks with structured source attribution blocks."""

    def __init__(self, separator: str = "\n\n---\n\n"):
        self.separator = separator

    def build_context(self, chunks: list[RetrievedChunk], max_tokens: int | None = None) -> str:
        if not chunks:
            return ""

        formatted_blocks = []
        for i, item in enumerate(chunks, start=1):
            doc_id = item.document_id
            page = f"Page {item.page_number}" if item.page_number else "N/A"
            header = f"[Source {i} | Document: {doc_id} | {page}]"
            formatted_blocks.append(f"{header}\n{item.content}")

        return self.separator.join(formatted_blocks)
