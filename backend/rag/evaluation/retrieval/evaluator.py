"""Retrieval stage evaluator assessing Context Precision and Context Recall."""

from __future__ import annotations

from typing import Any, Sequence

from rag.evaluation.base import BaseEvaluator
from rag.evaluation.metrics.context import ContextPrecisionMetric, ContextRecallMetric
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


class RetrievalEvaluator(BaseEvaluator):
    """Evaluates the retrieval stage using Context Precision and Context Recall."""

    def __init__(
        self,
        judge_llm: Any | None = None,
        context_precision: ContextPrecisionMetric | None = None,
        context_recall: ContextRecallMetric | None = None,
    ) -> None:
        self.context_precision = context_precision or ContextPrecisionMetric(judge_llm=judge_llm)
        self.context_recall = context_recall or ContextRecallMetric(judge_llm=judge_llm)

    def evaluate_sample(self, sample: EvaluationSample) -> EvaluationResult:
        """Evaluate retrieval performance for a single sample."""
        metrics: list[EvaluationMetric] = [
            self.context_precision.compute(sample),
            self.context_recall.compute(sample),
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
        """Evaluate a batch of samples and aggregate retrieval metrics."""
        results = [self.evaluate_sample(s) for s in samples]
        scores = _compute_aggregates(results)
        summary = {
            "total_samples": len(samples),
            "stage": "retrieval",
            "metrics": ["context_precision", "context_recall"],
        }
        return EvaluationReport(samples=results, scores=scores, summary=summary)
