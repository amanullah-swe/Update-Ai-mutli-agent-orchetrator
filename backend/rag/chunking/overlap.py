"""Fixed-size sliding character overlap chunker."""

from __future__ import annotations

from rag.chunking.base import BaseChunker
from rag.core.registry import register
from rag.types.chunk import Chunk, ChunkType
from rag.types.document import Document


@register("chunking", "overlap")
@register("chunking", "fixed_size")
class OverlapChunker(BaseChunker):
    """Chunks text into uniform character lengths with specified overlap, handling tables."""

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, document: Document) -> list[Chunk]:
        chunks: list[Chunk] = []
        step = max(1, self.chunk_size - self.chunk_overlap)

        for page in document.pages:
            text = page.text.strip()
            chunk_idx = 0

            # 1. Text chunks
            if text:
                for i in range(0, len(text), step):
                    window = text[i : i + self.chunk_size].strip()
                    if not window:
                        continue

                    chunk_id = f"{document.document_id}_p{page.page_number}_c{chunk_idx}"
                    chunks.append(
                        Chunk(
                            id=chunk_id,
                            document_id=document.document_id,
                            content=window,
                            chunk_type=ChunkType.TEXT,
                            page_number=page.page_number,
                            metadata={
                                "strategy": "overlap",
                                "chunk_index": chunk_idx,
                            },
                        )
                    )
                    chunk_idx += 1
                    if i + self.chunk_size >= len(text):
                        break

            # 2. Table chunks
            for table_idx, table in enumerate(page.tables):
                content = self._table_to_markdown(table.rows)
                if content:
                    chunk_id = f"{document.document_id}_p{page.page_number}_tbl{table_idx}"
                    chunks.append(
                        Chunk(
                            id=chunk_id,
                            document_id=document.document_id,
                            content=content,
                            chunk_type=ChunkType.TABLE,
                            page_number=page.page_number,
                            metadata={
                                "strategy": "overlap",
                                "table_index": table_idx,
                            },
                        )
                    )

        return chunks

    def _table_to_markdown(self, rows: list[list[str]]) -> str:
        if not rows:
            return ""
        lines = []
        header = rows[0]
        lines.append("| " + " | ".join(str(c) for c in header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        for row in rows[1:]:
            lines.append("| " + " | ".join(str(c) for c in row) + " |")
        return "\n".join(lines)
