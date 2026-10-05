"""Unit tests for query transformers."""

from __future__ import annotations

import pytest

from rag.core.registry import build_component
from rag.query.passthrough import PassThroughQueryTransformer


@pytest.mark.unit
class TestQueryTransformers:
    def test_passthrough_query_transformer(self) -> None:
        transformer = PassThroughQueryTransformer()
        assert transformer.transform("sample query") == "sample query"
        assert transformer.transform("") == ""

    def test_registry_lookup_for_query_transformation(self) -> None:
        obj_none = build_component("query_transformation", "none")
        assert isinstance(obj_none, PassThroughQueryTransformer)

        obj_pt = build_component("query_transformation", "passthrough")
        assert isinstance(obj_pt, PassThroughQueryTransformer)
