"""Generation strategies."""

from rag.generation.base import BaseGenerator
from rag.generation.llm import OpenRouterGenerator

__all__ = ["BaseGenerator", "OpenRouterGenerator"]
