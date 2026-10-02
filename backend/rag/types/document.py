"""Domain models representing parsed documents and structured page elements."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TextBlock:
    id: str
    text: str
    bbox: list[float] | None = None
    type: str = "text"


@dataclass
class TableBlock:
    id: str
    rows: list[list[Any]] = field(default_factory=list)
    row_count: int = 0
    column_count: int = 0
    bbox: list[float] | None = None
    type: str = "table"


@dataclass
class GraphicBlock:
    id: str
    bbox: list[float] | None = None
    items: list[Any] = field(default_factory=list)
    fill: Any = None
    color: Any = None
    width: float | None = None
    type: str = "graphic"


@dataclass
class ImageBlock:
    id: str
    format: str = "png"
    path: str | None = None
    width: int = 0
    height: int = 0
    type: str = "image"


@dataclass
class Page:
    page_number: int
    text: str = ""
    dimensions: dict[str, float] = field(default_factory=dict)
    blocks: list[TextBlock] = field(default_factory=list)
    tables: list[TableBlock] = field(default_factory=list)
    images: list[ImageBlock] = field(default_factory=list)
    graphics: list[GraphicBlock] = field(default_factory=list)


@dataclass
class Document:
    document_id: str
    page_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    pages: list[Page] = field(default_factory=list)

    def get_full_text(self) -> str:
        """Concatenate all page text separated by double newlines."""
        return "\n\n".join(page.text for page in self.pages if page.text.strip())

    def to_dict(self) -> dict[str, Any]:
        """Convert document to a nested dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Document:
        """Reconstruct a Document instance from a dictionary."""
        pages = []
        for p in data.get("pages", []):
            blocks = [
                TextBlock(**b) if isinstance(b, dict) else b
                for b in p.get("blocks", [])
            ]
            tables = [
                TableBlock(**t) if isinstance(t, dict) else t
                for t in p.get("tables", [])
            ]
            images = [
                ImageBlock(**img) if isinstance(img, dict) else img
                for img in p.get("images", [])
            ]
            graphics = [
                GraphicBlock(**g) if isinstance(g, dict) else g
                for g in p.get("graphics", [])
            ]
            pages.append(
                Page(
                    page_number=p.get("page_number", 1),
                    text=p.get("text", ""),
                    dimensions=p.get("dimensions", {}),
                    blocks=blocks,
                    tables=tables,
                    images=images,
                    graphics=graphics,
                )
            )

        return cls(
            document_id=data.get("document_id", "document"),
            page_count=data.get("page_count", len(pages)),
            metadata=data.get("metadata", {}),
            pages=pages,
        )
