"""End-to-end RAG Evaluator coordinating retrieval and generation metrics."""

from __future__ import annotations

from typing import Any, Sequence

from rag.core.registry import register
from rag.evaluation.base import BaseEvaluator
from rag.evaluation.generation.evaluator import GenerationEvaluator
from rag.evaluation.metrics.context import ContextPrecisionMetric, ContextRecallMetric
from rag.evaluation.metrics.faithfulness import FaithfulnessMetric
from rag.evaluation.metrics.judge import (
    build_judge_embeddings,
    build_judge_llm,
    resolve_judge_config,
)
from rag.evaluation.metrics.relevancy import AnswerRelevancyMetric
from rag.evaluation.retrieval.evaluator import RetrievalEvaluator
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


def _build_summary(
    total_samples: int, scores: dict[str, float], model_info: dict[str, str]
) -> dict[str, Any]:
    """Generate summary diagnostics for the evaluation report."""
    ragas_score = round(sum(scores.values()) / max(len(scores), 1), 4)
    return {
        "total_samples": total_samples,
        "ragas_score": ragas_score,
        "judge_model": model_info.get("model", ""),
        "embedding_model": model_info.get("embedding_model", ""),
        "evaluated_metrics": list(scores.keys()),
    }


@register("evaluator", "ragas")
@register("evaluator", "default")
class RAGEvaluator(BaseEvaluator):
    """End-to-end RAG Evaluator assessing both retrieval and generation stages."""

    def __init__(
        self,
        judge_llm: Any | None = None,
        embeddings: Any | None = None,
        context_precision: ContextPrecisionMetric | None = None,
        context_recall: ContextRecallMetric | None = None,
        faithfulness: FaithfulnessMetric | None = None,
        answer_relevancy: AnswerRelevancyMetric | None = None,
    ) -> None:
        all_metrics_injected = (
            context_precision is not None
            and context_recall is not None
            and faithfulness is not None
            and answer_relevancy is not None
        )
        if all_metrics_injected:
            self.llm = judge_llm
            self.embeddings = embeddings
        else:
            self.llm = judge_llm or build_judge_llm()
            self.embeddings = embeddings or build_judge_embeddings()

        self.retrieval_evaluator = RetrievalEvaluator(
            judge_llm=self.llm,
            context_precision=context_precision,
            context_recall=context_recall,
        )
        self.generation_evaluator = GenerationEvaluator(
            judge_llm=self.llm,
            embeddings=self.embeddings,
            faithfulness=faithfulness,
            answer_relevancy=answer_relevancy,
        )

    def evaluate_sample(self, sample: EvaluationSample) -> EvaluationResult:
        """Run full evaluation across retrieval and generation for a single sample."""
        retrieval_res = self.retrieval_evaluator.evaluate_sample(sample)
        generation_res = self.generation_evaluator.evaluate_sample(sample)

        all_metrics: list[EvaluationMetric] = []
        all_metrics.extend(retrieval_res.metrics)
        all_metrics.extend(generation_res.metrics)

        return EvaluationResult(
            query=sample.query,
            answer=sample.answer,
            ground_truth=sample.ground_truth,
            metrics=all_metrics,
        )

    def evaluate_batch(
        self, samples: Sequence[EvaluationSample]
    ) -> EvaluationReport:
        """Evaluate a batch of samples and generate a comprehensive evaluation report."""
        results = [self.evaluate_sample(s) for s in samples]
        scores = _compute_aggregates(results)

        _, model, emb_model, _ = resolve_judge_config()
        summary = _build_summary(
            total_samples=len(samples),
            scores=scores,
            model_info={"model": model, "embedding_model": emb_model},
        )

        return EvaluationReport(samples=results, scores=scores, summary=summary)
