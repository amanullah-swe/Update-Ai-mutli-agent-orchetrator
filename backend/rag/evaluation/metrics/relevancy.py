"""Answer Relevancy metric using Ragas."""

from __future__ import annotations

from typing import Any

from ragas import SingleTurnSample
from ragas.metrics.collections.answer_relevancy import AnswerRelevancy

from rag.evaluation.exceptions import MetricComputationError
from rag.evaluation.metrics.base import BaseEvaluationMetric
from rag.evaluation.metrics.judge import build_judge_embeddings, build_judge_llm
from rag.types.evaluation import EvaluationMetric, EvaluationSample


def _to_ragas_sample(sample: EvaluationSample) -> SingleTurnSample:
    """Convert an internal EvaluationSample to a Ragas SingleTurnSample."""
    return SingleTurnSample(
        user_input=sample.query,
        response=sample.answer,
        retrieved_contexts=sample.contexts or [],
        reference=sample.ground_truth or "",
    )


class AnswerRelevancyMetric(BaseEvaluationMetric):
    """Measures how directly the generated answer addresses the question."""

    def __init__(
        self,
        judge_llm: Any | None = None,
        embeddings: Any | None = None,
        ragas_metric: Any | None = None,
    ) -> None:
        if ragas_metric is not None:
            self._metric = ragas_metric
        else:
            self._llm = judge_llm or build_judge_llm()
            self._embeddings = embeddings or build_judge_embeddings()
            self._metric = AnswerRelevancy(llm=self._llm, embeddings=self._embeddings)

    @property
    def name(self) -> str:
        return "answer_relevancy"

    def compute(self, sample: EvaluationSample) -> EvaluationMetric:
        """Compute answer relevancy score synchronously."""
        if not sample.answer.strip():
            return EvaluationMetric(name=self.name, score=0.0, details={"reason": "Empty answer."})

        try:
            ragas_sample = _to_ragas_sample(sample)
            score = self._metric.score(ragas_sample)
            return EvaluationMetric(name=self.name, score=float(score))
        except Exception as exc:
            raise MetricComputationError(f"Failed to compute answer relevancy: {exc}") from exc

    async def compute_async(self, sample: EvaluationSample) -> EvaluationMetric:
        """Compute answer relevancy score asynchronously."""
        if not sample.answer.strip():
            return EvaluationMetric(name=self.name, score=0.0, details={"reason": "Empty answer."})

        try:
            ragas_sample = _to_ragas_sample(sample)
            score = await self._metric.ascore(ragas_sample)
            return EvaluationMetric(name=self.name, score=float(score))
        except Exception as exc:
            raise MetricComputationError(f"Failed to compute answer relevancy: {exc}") from exc
