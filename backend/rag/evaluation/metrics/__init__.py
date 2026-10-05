"""RAG evaluation metrics module."""

from __future__ import annotations

from rag.evaluation.metrics.base import BaseEvaluationMetric
from rag.evaluation.metrics.context import ContextPrecisionMetric, ContextRecallMetric
from rag.evaluation.metrics.faithfulness import FaithfulnessMetric
from rag.evaluation.metrics.judge import (
    build_judge_embeddings,
    build_judge_llm,
    resolve_judge_config,
)
from rag.evaluation.metrics.relevancy import AnswerRelevancyMetric

__all__ = [
    "BaseEvaluationMetric",
    "ContextPrecisionMetric",
    "ContextRecallMetric",
    "FaithfulnessMetric",
    "AnswerRelevancyMetric",
    "build_judge_llm",
    "build_judge_embeddings",
    "resolve_judge_config",
]
