"""Component registry and factory for strategy swapping.

Enforces the Core Architectural Rule:
Pipeline components are selected by name from configuration behind standard interfaces.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from rag.core.exceptions import ComponentNotFoundError, StrategyRegistrationError

T = TypeVar("T")

# Registry store: kind -> { name -> component_class }
_REGISTRY: dict[str, dict[str, type]] = {}


def register(kind: str, name: str) -> Callable[[type[T]], type[T]]:
    """Decorator to register a strategy class under a specific component kind.

    Example:
        @register("chunking", "recursive")
        class RecursiveChunker(BaseChunker):
            ...
    """
    clean_kind = kind.strip().lower()
    clean_name = name.strip().lower()

    def decorator(cls: type[T]) -> type[T]:
        if clean_kind not in _REGISTRY:
            _REGISTRY[clean_kind] = {}

        if clean_name in _REGISTRY[clean_kind]:
            existing = _REGISTRY[clean_kind][clean_name]
            if existing is not cls:
                raise StrategyRegistrationError(
                    f"Duplicate registration for kind='{clean_kind}', name='{clean_name}': "
                    f"{existing.__name__} vs {cls.__name__}"
                )

        _REGISTRY[clean_kind][clean_name] = cls
        return cls

    return decorator


def get_component_class(kind: str, name: str) -> type:
    """Look up a strategy class by kind and name."""
    clean_kind = kind.strip().lower()
    clean_name = name.strip().lower()

    if clean_kind not in _REGISTRY or clean_name not in _REGISTRY[clean_kind]:
        available = list(_REGISTRY.get(clean_kind, {}).keys())
        raise ComponentNotFoundError(clean_kind, clean_name, available)

    return _REGISTRY[clean_kind][clean_name]


def build_component(kind: str, name: str, **kwargs: Any) -> Any:
    """Instantiate a strategy component by kind and name, passing kwargs to __init__."""
    cls = get_component_class(kind, name)
    return cls(**kwargs)


def list_components(kind: str | None = None) -> dict[str, list[str]] | list[str]:
    """List registered component names for a specific kind or all kinds."""
    if kind is not None:
        clean_kind = kind.strip().lower()
        return sorted(list(_REGISTRY.get(clean_kind, {}).keys()))
    return {k: sorted(list(v.keys())) for k, v in _REGISTRY.items()}


def clear_registry() -> None:
    """Testing utility to reset registry state."""
    _REGISTRY.clear()
