"""Context Precision and Context Recall metrics using Ragas."""

from __future__ import annotations

from typing import Any

from ragas import SingleTurnSample
from ragas.metrics.collections.context_precision import ContextPrecision
from ragas.metrics.collections.context_recall import ContextRecall

from rag.evaluation.exceptions import MetricComputationError
from rag.evaluation.metrics.base import BaseEvaluationMetric
from rag.evaluation.metrics.judge import build_judge_llm
from rag.types.evaluation import EvaluationMetric, EvaluationSample


def _to_ragas_sample(sample: EvaluationSample) -> SingleTurnSample:
    """Convert an internal EvaluationSample to a Ragas SingleTurnSample."""
    return SingleTurnSample(
        user_input=sample.query,
        response=sample.answer,
        retrieved_contexts=sample.contexts or [],
        reference=sample.ground_truth or "",
    )


class ContextPrecisionMetric(BaseEvaluationMetric):
    """Measures signal-to-noise ratio: whether relevant contexts appear at the top."""

    def __init__(
        self,
        judge_llm: Any | None = None,
        ragas_metric: Any | None = None,
    ) -> None:
        if ragas_metric is not None:
            self._metric = ragas_metric
        else:
            self._llm = judge_llm or build_judge_llm()
            self._metric = ContextPrecision(llm=self._llm)

    @property
    def name(self) -> str:
        return "context_precision"

    def compute(self, sample: EvaluationSample) -> EvaluationMetric:
        """Compute context precision score synchronously."""
        if not sample.contexts:
            return EvaluationMetric(name=self.name, score=0.0, details={"reason": "No contexts provided."})

        try:
            ragas_sample = _to_ragas_sample(sample)
            score = self._metric.score(ragas_sample)
            return EvaluationMetric(name=self.name, score=float(score))
        except Exception as exc:
            raise MetricComputationError(f"Failed to compute context precision: {exc}") from exc

    async def compute_async(self, sample: EvaluationSample) -> EvaluationMetric:
        """Compute context precision score asynchronously."""
        if not sample.contexts:
            return EvaluationMetric(name=self.name, score=0.0, details={"reason": "No contexts provided."})

        try:
            ragas_sample = _to_ragas_sample(sample)
            score = await self._metric.ascore(ragas_sample)
            return EvaluationMetric(name=self.name, score=float(score))
        except Exception as exc:
            raise MetricComputationError(f"Failed to compute context precision: {exc}") from exc


class ContextRecallMetric(BaseEvaluationMetric):
    """Measures retrieval completeness: whether contexts contain all reference facts."""

    def __init__(
        self,
        judge_llm: Any | None = None,
        ragas_metric: Any | None = None,
    ) -> None:
        if ragas_metric is not None:
            self._metric = ragas_metric
        else:
            self._llm = judge_llm or build_judge_llm()
            self._metric = ContextRecall(llm=self._llm)

    @property
    def name(self) -> str:
        return "context_recall"

    def compute(self, sample: EvaluationSample) -> EvaluationMetric:
        """Compute context recall score synchronously."""
        if not sample.ground_truth:
            return EvaluationMetric(name=self.name, score=0.0, details={"reason": "Ground truth is required for context recall."})
        if not sample.contexts:
            return EvaluationMetric(name=self.name, score=0.0, details={"reason": "No contexts provided."})

        try:
            ragas_sample = _to_ragas_sample(sample)
            score = self._metric.score(ragas_sample)
            return EvaluationMetric(name=self.name, score=float(score))
        except Exception as exc:
            raise MetricComputationError(f"Failed to compute context recall: {exc}") from exc

    async def compute_async(self, sample: EvaluationSample) -> EvaluationMetric:
        """Compute context recall score asynchronously."""
        if not sample.ground_truth:
            return EvaluationMetric(name=self.name, score=0.0, details={"reason": "Ground truth is required for context recall."})
        if not sample.contexts:
            return EvaluationMetric(name=self.name, score=0.0, details={"reason": "No contexts provided."})

        try:
            ragas_sample = _to_ragas_sample(sample)
            score = await self._metric.ascore(ragas_sample)
            return EvaluationMetric(name=self.name, score=float(score))
        except Exception as exc:
            raise MetricComputationError(f"Failed to compute context recall: {exc}") from exc
