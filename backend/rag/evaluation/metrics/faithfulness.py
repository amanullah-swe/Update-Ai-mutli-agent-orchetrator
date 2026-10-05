"""Faithfulness metric using Ragas."""

from __future__ import annotations

from typing import Any

from ragas import SingleTurnSample
from ragas.metrics.collections.faithfulness import Faithfulness

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


class FaithfulnessMetric(BaseEvaluationMetric):
    """Measures factual consistency of the answer against retrieved context."""

    def __init__(
        self,
        judge_llm: Any | None = None,
        ragas_metric: Any | None = None,
    ) -> None:
        if ragas_metric is not None:
            self._metric = ragas_metric
        else:
            self._llm = judge_llm or build_judge_llm()
            self._metric = Faithfulness(llm=self._llm)

    @property
    def name(self) -> str:
        return "faithfulness"

    def compute(self, sample: EvaluationSample) -> EvaluationMetric:
        """Compute faithfulness score synchronously."""
        if not sample.answer.strip():
            return EvaluationMetric(name=self.name, score=0.0, details={"reason": "Empty answer."})
        if not sample.contexts:
            return EvaluationMetric(name=self.name, score=0.0, details={"reason": "No context to ground answer."})

        try:
            ragas_sample = _to_ragas_sample(sample)
            score = self._metric.score(ragas_sample)
            return EvaluationMetric(name=self.name, score=float(score))
        except Exception as exc:
            raise MetricComputationError(f"Failed to compute faithfulness: {exc}") from exc

    async def compute_async(self, sample: EvaluationSample) -> EvaluationMetric:
        """Compute faithfulness score asynchronously."""
        if not sample.answer.strip():
            return EvaluationMetric(name=self.name, score=0.0, details={"reason": "Empty answer."})
        if not sample.contexts:
            return EvaluationMetric(name=self.name, score=0.0, details={"reason": "No context to ground answer."})

        try:
            ragas_sample = _to_ragas_sample(sample)
            score = await self._metric.ascore(ragas_sample)
            return EvaluationMetric(name=self.name, score=float(score))
        except Exception as exc:
            raise MetricComputationError(f"Failed to compute faithfulness: {exc}") from exc
