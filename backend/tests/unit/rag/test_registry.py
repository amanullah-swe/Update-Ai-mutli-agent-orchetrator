"""Unit tests for the component registry."""

import pytest

from rag.core.exceptions import ComponentNotFoundError, StrategyRegistrationError
from rag.core.registry import (
    build_component,
    clear_registry,
    get_component_class,
    list_components,
    register,
)


@pytest.fixture(autouse=True)
def isolated_registry():
    """Start each test with a clean registry, restore after."""
    clear_registry()
    yield
    clear_registry()


def test_register_and_retrieve_class():
    @register("test_kind", "my_strategy")
    class MyStrategy:
        pass

    cls = get_component_class("test_kind", "my_strategy")
    assert cls is MyStrategy


def test_build_component_instantiates():
    @register("test_kind", "simple")
    class SimpleStrategy:
        def __init__(self, value: int = 0):
            self.value = value

    obj = build_component("test_kind", "simple", value=42)
    assert isinstance(obj, SimpleStrategy)
    assert obj.value == 42


def test_unknown_component_raises_clear_error():
    with pytest.raises(ComponentNotFoundError) as exc_info:
        get_component_class("chunking", "nonexistent_strategy")

    err = exc_info.value
    assert "nonexistent_strategy" in str(err)
    assert err.kind == "chunking"
    assert err.name == "nonexistent_strategy"


def test_list_components_for_kind():
    @register("embeddings", "alpha")
    class A:
        pass

    @register("embeddings", "beta")
    class B:
        pass

    names = list_components("embeddings")
    assert "alpha" in names
    assert "beta" in names


def test_list_components_all():
    @register("kind_a", "strat_1")
    class S1:
        pass

    @register("kind_b", "strat_2")
    class S2:
        pass

    all_comps = list_components()
    assert "kind_a" in all_comps
    assert "kind_b" in all_comps


def test_duplicate_same_class_is_allowed():
    @register("chunking", "dup_test")
    @register("chunking", "dup_test")
    class DupStrategy:
        pass

    cls = get_component_class("chunking", "dup_test")
    assert cls is DupStrategy


def test_lookup_is_case_insensitive_and_strips_whitespace():
    @register("  ChunkKind  ", "  MyStrat  ")
    class UpperStrategy:
        pass

    cls = get_component_class("chunkKind", "myStrat")
    assert cls is UpperStrategy
