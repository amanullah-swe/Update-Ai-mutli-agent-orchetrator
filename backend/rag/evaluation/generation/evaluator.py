"""Generation stage evaluator assessing Faithfulness and Answer Relevancy."""

from __future__ import annotations

from typing import Any, Sequence

from rag.evaluation.base import BaseEvaluator
from rag.evaluation.metrics.faithfulness import FaithfulnessMetric
from rag.evaluation.metrics.relevancy import AnswerRelevancyMetric
from rag.types.evaluation import (
    EvaluationMetric,
    EvaluationReport,
    EvaluationResult,
    EvaluationSample,
)


def _compute_aggregates(results: list[EvaluationResult]) -> dict[str, float]:
    """Calculate average metric scores across evaluated results."""
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}

    for res in results:
        for metric in res.metrics:
            totals[metric.name] = totals.get(metric.name, 0.0) + metric.score
            counts[metric.name] = counts.get(metric.name, 0) + 1

    return {
        name: round(totals[name] / counts[name], 4)
        for name in totals
        if counts[name] > 0
    }


class GenerationEvaluator(BaseEvaluator):
    """Evaluates the generation stage using Faithfulness and Answer Relevancy."""

    def __init__(
        self,
        judge_llm: Any | None = None,
        embeddings: Any | None = None,
        faithfulness: FaithfulnessMetric | None = None,
        answer_relevancy: AnswerRelevancyMetric | None = None,
    ) -> None:
        self.faithfulness = faithfulness or FaithfulnessMetric(judge_llm=judge_llm)
        self.answer_relevancy = answer_relevancy or AnswerRelevancyMetric(
            judge_llm=judge_llm, embeddings=embeddings
        )

    def evaluate_sample(self, sample: EvaluationSample) -> EvaluationResult:
        """Evaluate generation performance for a single sample."""
        metrics: list[EvaluationMetric] = [
            self.faithfulness.compute(sample),
            self.answer_relevancy.compute(sample),
        ]
        return EvaluationResult(
            query=sample.query,
            answer=sample.answer,
            ground_truth=sample.ground_truth,
            metrics=metrics,
        )

    def evaluate_batch(
        self, samples: Sequence[EvaluationSample]
    ) -> EvaluationReport:
        """Evaluate a batch of samples and aggregate generation metrics."""
        results = [self.evaluate_sample(s) for s in samples]
        scores = _compute_aggregates(results)
        summary = {
            "total_samples": len(samples),
            "stage": "generation",
            "metrics": ["faithfulness", "answer_relevancy"],
        }
        return EvaluationReport(samples=results, scores=scores, summary=summary)
