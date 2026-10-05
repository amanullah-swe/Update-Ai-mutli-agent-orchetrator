"""Unit tests for RAG evaluation metrics."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from rag.evaluation.exceptions import MetricComputationError
from rag.evaluation.metrics.context import ContextPrecisionMetric, ContextRecallMetric
from rag.evaluation.metrics.faithfulness import FaithfulnessMetric
from rag.evaluation.metrics.judge import resolve_judge_config
from rag.evaluation.metrics.relevancy import AnswerRelevancyMetric
from rag.types.evaluation import EvaluationSample


@pytest.mark.unit
class TestEvaluationMetrics:
    def test_resolve_judge_config(self) -> None:
        api_key, model, emb_model, base_url = resolve_judge_config()
        assert "openrouter.ai" in base_url
        assert isinstance(model, str) and len(model) > 0
        assert "minilm" in emb_model

    def test_context_precision_returns_zero_on_empty_contexts(self) -> None:
        metric = ContextPrecisionMetric(ragas_metric=MagicMock())
        sample = EvaluationSample(query="Q", answer="A", contexts=[], ground_truth="GT")
        result = metric.compute(sample)
        assert result.name == "context_precision"
        assert result.score == 0.0
        assert "No contexts" in result.details.get("reason", "")

    def test_context_precision_successful_computation(self) -> None:
        mock_ragas = MagicMock()
        mock_ragas.score.return_value = 0.85

        metric = ContextPrecisionMetric(ragas_metric=mock_ragas)
        sample = EvaluationSample(query="Q", answer="A", contexts=["C1"], ground_truth="GT")
        result = metric.compute(sample)
        assert result.name == "context_precision"
        assert result.score == 0.85

    @pytest.mark.asyncio
    async def test_context_precision_async_computation(self) -> None:
        mock_ragas = MagicMock()
        mock_ragas.ascore = AsyncMock(return_value=0.9)

        metric = ContextPrecisionMetric(ragas_metric=mock_ragas)
        sample = EvaluationSample(query="Q", answer="A", contexts=["C1"], ground_truth="GT")
        result = await metric.compute_async(sample)
        assert result.name == "context_precision"
        assert result.score == 0.9

    def test_context_precision_raises_on_error(self) -> None:
        mock_ragas = MagicMock()
        mock_ragas.score.side_effect = RuntimeError("Judge API crash")

        metric = ContextPrecisionMetric(ragas_metric=mock_ragas)
        sample = EvaluationSample(query="Q", answer="A", contexts=["C1"], ground_truth="GT")
        with pytest.raises(MetricComputationError, match="Failed to compute context precision"):
            metric.compute(sample)

    def test_context_recall_requires_ground_truth(self) -> None:
        metric = ContextRecallMetric(ragas_metric=MagicMock())
        sample = EvaluationSample(query="Q", answer="A", contexts=["C1"], ground_truth=None)
        result = metric.compute(sample)
        assert result.name == "context_recall"
        assert result.score == 0.0
        assert "Ground truth is required" in result.details.get("reason", "")

    def test_context_recall_successful_computation(self) -> None:
        mock_ragas = MagicMock()
        mock_ragas.score.return_value = 0.92

        metric = ContextRecallMetric(ragas_metric=mock_ragas)
        sample = EvaluationSample(query="Q", answer="A", contexts=["C1"], ground_truth="GT")
        result = metric.compute(sample)
        assert result.name == "context_recall"
        assert result.score == 0.92

    def test_faithfulness_empty_answer_returns_zero(self) -> None:
        metric = FaithfulnessMetric(ragas_metric=MagicMock())
        sample = EvaluationSample(query="Q", answer="", contexts=["C1"])
        result = metric.compute(sample)
        assert result.name == "faithfulness"
        assert result.score == 0.0

    def test_faithfulness_empty_contexts_returns_zero(self) -> None:
        metric = FaithfulnessMetric(ragas_metric=MagicMock())
        sample = EvaluationSample(query="Q", answer="Some answer", contexts=[])
        result = metric.compute(sample)
        assert result.name == "faithfulness"
        assert result.score == 0.0

    def test_faithfulness_successful_computation(self) -> None:
        mock_ragas = MagicMock()
        mock_ragas.score.return_value = 0.95

        metric = FaithfulnessMetric(ragas_metric=mock_ragas)
        sample = EvaluationSample(query="Q", answer="Accurate answer", contexts=["Context text"])
        result = metric.compute(sample)
        assert result.name == "faithfulness"
        assert result.score == 0.95

    def test_answer_relevancy_empty_answer_returns_zero(self) -> None:
        metric = AnswerRelevancyMetric(ragas_metric=MagicMock())
        sample = EvaluationSample(query="Q", answer="   ", contexts=["C1"])
        result = metric.compute(sample)
        assert result.name == "answer_relevancy"
        assert result.score == 0.0

    def test_answer_relevancy_successful_computation(self) -> None:
        mock_ragas = MagicMock()
        mock_ragas.score.return_value = 0.88

        metric = AnswerRelevancyMetric(ragas_metric=mock_ragas)
        sample = EvaluationSample(query="What is X?", answer="X is Y.", contexts=["C1"])
        result = metric.compute(sample)
        assert result.name == "answer_relevancy"
        assert result.score == 0.88
