"""Exceptions for the RAG evaluation subsystem."""

from __future__ import annotations

from rag.core.exceptions import RAGError


class EvaluationError(RAGError):
    """Base exception for all RAG evaluation failures."""


class LLMJudgeError(EvaluationError):
    """Raised when the judge LLM encounters an API or execution failure."""


class MetricComputationError(EvaluationError):
    """Raised when an individual metric evaluation fails."""


class DatasetValidationError(EvaluationError):
    """Raised when an evaluation dataset or sample is invalid or incomplete."""
