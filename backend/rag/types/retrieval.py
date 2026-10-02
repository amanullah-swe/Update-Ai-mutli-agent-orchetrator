"""Domain models representing retrieval queries and search results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rag.types.chunk import Chunk


@dataclass
class RetrievalQuery:
    text: str
    top_k: int = 5
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float
    retriever: str = ""

    @property
    def content(self) -> str:
        return self.chunk.content

    @property
    def document_id(self) -> str:
        return self.chunk.document_id

    @property
    def page_number(self) -> int | None:
        return self.chunk.page_number


@dataclass
class SearchResult:
    query: str
    chunks: list[RetrievedChunk] = field(default_factory=list)
