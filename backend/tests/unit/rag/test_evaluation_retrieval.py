"""Unit tests for the RetrievalEvaluator."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rag.evaluation.metrics.context import ContextPrecisionMetric, ContextRecallMetric
from rag.evaluation.retrieval.evaluator import RetrievalEvaluator
from rag.types.evaluation import EvaluationMetric, EvaluationSample


@pytest.mark.unit
class TestRetrievalEvaluator:
    def test_evaluate_sample(self) -> None:
        mock_cp = MagicMock(spec=ContextPrecisionMetric)
        mock_cp.compute.return_value = EvaluationMetric(name="context_precision", score=0.8)

        mock_cr = MagicMock(spec=ContextRecallMetric)
        mock_cr.compute.return_value = EvaluationMetric(name="context_recall", score=0.9)

        evaluator = RetrievalEvaluator(
            context_precision=mock_cp,
            context_recall=mock_cr,
        )

        sample = EvaluationSample(
            query="Q",
            answer="A",
            contexts=["C1", "C2"],
            ground_truth="GT",
        )

        result = evaluator.evaluate_sample(sample)
        assert result.query == "Q"
        assert result.get_metric_score("context_precision") == 0.8
        assert result.get_metric_score("context_recall") == 0.9

    def test_evaluate_batch(self) -> None:
        mock_cp = MagicMock(spec=ContextPrecisionMetric)
        mock_cp.compute.side_effect = [
            EvaluationMetric(name="context_precision", score=0.8),
            EvaluationMetric(name="context_precision", score=1.0),
        ]

        mock_cr = MagicMock(spec=ContextRecallMetric)
        mock_cr.compute.side_effect = [
            EvaluationMetric(name="context_recall", score=0.6),
            EvaluationMetric(name="context_recall", score=0.8),
        ]

        evaluator = RetrievalEvaluator(
            context_precision=mock_cp,
            context_recall=mock_cr,
        )

        samples = [
            EvaluationSample(query="Q1", answer="A1", contexts=["C1"], ground_truth="GT1"),
            EvaluationSample(query="Q2", answer="A2", contexts=["C2"], ground_truth="GT2"),
        ]

        report = evaluator.evaluate_batch(samples)
        assert len(report.samples) == 2
        assert report.scores["context_precision"] == 0.9  # (0.8 + 1.0) / 2
        assert report.scores["context_recall"] == 0.7     # (0.6 + 0.8) / 2
        assert report.summary["total_samples"] == 2
        assert report.summary["stage"] == "retrieval"
