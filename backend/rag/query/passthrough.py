"""Pass-through query transformer (identity)."""

from __future__ import annotations

from rag.core.registry import register
from rag.query.base import BaseQueryTransformer


@register("query_transformation", "none")
@register("query_transformation", "passthrough")
class PassThroughQueryTransformer(BaseQueryTransformer):
    """Returns the query unaltered."""

    def transform(self, query: str) -> str:
        return query
