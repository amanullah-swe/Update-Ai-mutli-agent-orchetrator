"""Base evaluator interface for RAG evaluation strategies."""

from __future__ import annotations

from abc import abstractmethod
from typing import Sequence

from rag.core.base import BaseComponent
from rag.types.evaluation import EvaluationReport, EvaluationResult, EvaluationSample


class BaseEvaluator(BaseComponent):
    """Abstract base class that all RAG evaluators implement."""

    @abstractmethod
    def evaluate_sample(self, sample: EvaluationSample) -> EvaluationResult:
        """Evaluate a single RAG sample.

        Args:
            sample: The user query, retrieved contexts, generated answer, and reference.

        Returns:
            EvaluationResult containing computed metric scores.
        """

    @abstractmethod
    def evaluate_batch(
        self, samples: Sequence[EvaluationSample]
    ) -> EvaluationReport:
        """Evaluate a sequence of RAG samples and return an aggregated report.

        Args:
            samples: Sequence of EvaluationSample instances.

        Returns:
            EvaluationReport containing per-sample results and aggregate scores.
        """
