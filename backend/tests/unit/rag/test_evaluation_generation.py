"""Unit tests for the GenerationEvaluator."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rag.evaluation.generation.evaluator import GenerationEvaluator
from rag.evaluation.metrics.faithfulness import FaithfulnessMetric
from rag.evaluation.metrics.relevancy import AnswerRelevancyMetric
from rag.types.evaluation import EvaluationMetric, EvaluationSample


@pytest.mark.unit
class TestGenerationEvaluator:
    def test_evaluate_sample(self) -> None:
        mock_faith = MagicMock(spec=FaithfulnessMetric)
        mock_faith.compute.return_value = EvaluationMetric(name="faithfulness", score=0.95)

        mock_relevancy = MagicMock(spec=AnswerRelevancyMetric)
        mock_relevancy.compute.return_value = EvaluationMetric(name="answer_relevancy", score=0.88)

        evaluator = GenerationEvaluator(
            faithfulness=mock_faith,
            answer_relevancy=mock_relevancy,
        )

        sample = EvaluationSample(
            query="What is python?",
            answer="Python is a programming language.",
            contexts=["Python is a general purpose programming language."],
        )

        result = evaluator.evaluate_sample(sample)
        assert result.query == "What is python?"
        assert result.get_metric_score("faithfulness") == 0.95
        assert result.get_metric_score("answer_relevancy") == 0.88

    def test_evaluate_batch(self) -> None:
        mock_faith = MagicMock(spec=FaithfulnessMetric)
        mock_faith.compute.side_effect = [
            EvaluationMetric(name="faithfulness", score=1.0),
            EvaluationMetric(name="faithfulness", score=0.8),
        ]

        mock_relevancy = MagicMock(spec=AnswerRelevancyMetric)
        mock_relevancy.compute.side_effect = [
            EvaluationMetric(name="answer_relevancy", score=0.9),
            EvaluationMetric(name="answer_relevancy", score=0.7),
        ]

        evaluator = GenerationEvaluator(
            faithfulness=mock_faith,
            answer_relevancy=mock_relevancy,
        )

        samples = [
            EvaluationSample(query="Q1", answer="A1", contexts=["C1"]),
            EvaluationSample(query="Q2", answer="A2", contexts=["C2"]),
        ]

        report = evaluator.evaluate_batch(samples)
        assert len(report.samples) == 2
        assert report.scores["faithfulness"] == 0.9       # (1.0 + 0.8) / 2
        assert report.scores["answer_relevancy"] == 0.8    # (0.9 + 0.7) / 2
        assert report.summary["total_samples"] == 2
        assert report.summary["stage"] == "generation"
