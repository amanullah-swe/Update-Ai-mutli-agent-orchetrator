"""Domain model representing a retrieval chunk."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    SECTION = "section"
    PARENT = "parent"
    CHILD = "child"
    IMAGE_CAPTION = "image_caption"


@dataclass
class Chunk:
    id: str
    document_id: str
    content: str
    chunk_type: ChunkType | str = ChunkType.TEXT
    page_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if isinstance(self.chunk_type, Enum):
            data["chunk_type"] = self.chunk_type.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Chunk:
        chunk_type = data.get("chunk_type", ChunkType.TEXT)
        if isinstance(chunk_type, str):
            try:
                chunk_type = ChunkType(chunk_type)
            except ValueError:
                pass
        return cls(
            id=data["id"],
            document_id=data["document_id"],
            content=data["content"],
            chunk_type=chunk_type,
            page_number=data.get("page_number"),
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
        )
