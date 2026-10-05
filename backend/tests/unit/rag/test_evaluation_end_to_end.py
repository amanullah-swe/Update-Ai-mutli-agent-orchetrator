"""Unit tests for the end-to-end RAGEvaluator and component registry."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rag.core.registry import build_component
from rag.evaluation.end_to_end.evaluator import RAGEvaluator
from rag.evaluation.metrics.context import ContextPrecisionMetric, ContextRecallMetric
from rag.evaluation.metrics.faithfulness import FaithfulnessMetric
from rag.evaluation.metrics.relevancy import AnswerRelevancyMetric
from rag.types.evaluation import EvaluationMetric, EvaluationSample


@pytest.mark.unit
class TestRAGEvaluator:
    def test_registry_resolution(self) -> None:
        mock_cp = MagicMock(spec=ContextPrecisionMetric)
        mock_cr = MagicMock(spec=ContextRecallMetric)
        mock_f = MagicMock(spec=FaithfulnessMetric)
        mock_ar = MagicMock(spec=AnswerRelevancyMetric)

        evaluator_ragas = build_component(
            "evaluator",
            "ragas",
            context_precision=mock_cp,
            context_recall=mock_cr,
            faithfulness=mock_f,
            answer_relevancy=mock_ar,
        )
        assert isinstance(evaluator_ragas, RAGEvaluator)

        evaluator_default = build_component(
            "evaluator",
            "default",
            context_precision=mock_cp,
            context_recall=mock_cr,
            faithfulness=mock_f,
            answer_relevancy=mock_ar,
        )
        assert isinstance(evaluator_default, RAGEvaluator)

    def test_evaluate_sample_coordinates_all_metrics(self) -> None:
        mock_cp = MagicMock(spec=ContextPrecisionMetric)
        mock_cp.compute.return_value = EvaluationMetric(name="context_precision", score=0.8)

        mock_cr = MagicMock(spec=ContextRecallMetric)
        mock_cr.compute.return_value = EvaluationMetric(name="context_recall", score=0.9)

        mock_f = MagicMock(spec=FaithfulnessMetric)
        mock_f.compute.return_value = EvaluationMetric(name="faithfulness", score=0.95)

        mock_ar = MagicMock(spec=AnswerRelevancyMetric)
        mock_ar.compute.return_value = EvaluationMetric(name="answer_relevancy", score=0.85)

        evaluator = RAGEvaluator(
            context_precision=mock_cp,
            context_recall=mock_cr,
            faithfulness=mock_f,
            answer_relevancy=mock_ar,
        )

        sample = EvaluationSample(
            query="What is RAG?",
            answer="Retrieval Augmented Generation.",
            contexts=["RAG pairs retrieval with generative models."],
            ground_truth="RAG is Retrieval Augmented Generation.",
        )

        result = evaluator.evaluate_sample(sample)
        assert result.query == "What is RAG?"
        assert len(result.metrics) == 4
        assert result.get_metric_score("context_precision") == 0.8
        assert result.get_metric_score("context_recall") == 0.9
        assert result.get_metric_score("faithfulness") == 0.95
        assert result.get_metric_score("answer_relevancy") == 0.85

    def test_evaluate_batch_produces_full_report(self) -> None:
        mock_cp = MagicMock(spec=ContextPrecisionMetric)
        mock_cp.compute.side_effect = [
            EvaluationMetric(name="context_precision", score=0.8),
            EvaluationMetric(name="context_precision", score=1.0),
        ]

        mock_cr = MagicMock(spec=ContextRecallMetric)
        mock_cr.compute.side_effect = [
            EvaluationMetric(name="context_recall", score=0.7),
            EvaluationMetric(name="context_recall", score=0.9),
        ]

        mock_f = MagicMock(spec=FaithfulnessMetric)
        mock_f.compute.side_effect = [
            EvaluationMetric(name="faithfulness", score=1.0),
            EvaluationMetric(name="faithfulness", score=0.9),
        ]

        mock_ar = MagicMock(spec=AnswerRelevancyMetric)
        mock_ar.compute.side_effect = [
            EvaluationMetric(name="answer_relevancy", score=0.8),
            EvaluationMetric(name="answer_relevancy", score=0.9),
        ]

        evaluator = RAGEvaluator(
            context_precision=mock_cp,
            context_recall=mock_cr,
            faithfulness=mock_f,
            answer_relevancy=mock_ar,
        )

        samples = [
            EvaluationSample(query="Q1", answer="A1", contexts=["C1"], ground_truth="GT1"),
            EvaluationSample(query="Q2", answer="A2", contexts=["C2"], ground_truth="GT2"),
        ]

        report = evaluator.evaluate_batch(samples)
        assert len(report.samples) == 2
        assert report.scores["context_precision"] == 0.9
        assert report.scores["context_recall"] == 0.8
        assert report.scores["faithfulness"] == 0.95
        assert report.scores["answer_relevancy"] == 0.85

        assert report.summary["total_samples"] == 2
        assert "ragas_score" in report.summary
        assert set(report.summary["evaluated_metrics"]) == {
            "context_precision",
            "context_recall",
            "faithfulness",
            "answer_relevancy",
        }
