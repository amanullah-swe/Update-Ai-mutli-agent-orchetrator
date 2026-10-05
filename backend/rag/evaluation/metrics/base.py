"""Base interface for individual RAG evaluation metrics."""

from __future__ import annotations

from abc import ABC, abstractmethod

from rag.types.evaluation import EvaluationMetric, EvaluationSample


class BaseEvaluationMetric(ABC):
    """Abstract base class for all RAG evaluation metrics."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this metric."""

    @abstractmethod
    def compute(self, sample: EvaluationSample) -> EvaluationMetric:
        """Compute the metric score synchronously for a single sample.

        Args:
            sample: Input containing query, answer, contexts, and ground_truth.

        Returns:
            EvaluationMetric with name, numeric score (0.0 to 1.0), and details.
        """

    @abstractmethod
    async def compute_async(self, sample: EvaluationSample) -> EvaluationMetric:
        """Compute the metric score asynchronously for a single sample."""
