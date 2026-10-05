"""RAG evaluation subsystem using Ragas and LLM-as-a-Judge."""

from __future__ import annotations

from rag.evaluation.base import BaseEvaluator
from rag.evaluation.datasets import (
    EvaluationDataset,
    from_rag_pipeline_output,
    load_from_dicts,
    load_from_json,
    to_ragas_dataset,
)
from rag.evaluation.end_to_end import RAGEvaluator
from rag.evaluation.exceptions import (
    DatasetValidationError,
    EvaluationError,
    LLMJudgeError,
    MetricComputationError,
)
from rag.evaluation.generation import GenerationEvaluator
from rag.evaluation.metrics import (
    AnswerRelevancyMetric,
    BaseEvaluationMetric,
    ContextPrecisionMetric,
    ContextRecallMetric,
    FaithfulnessMetric,
    build_judge_embeddings,
    build_judge_llm,
    resolve_judge_config,
)
from rag.evaluation.retrieval import RetrievalEvaluator
from rag.types.evaluation import (
    EvaluationMetric,
    EvaluationReport,
    EvaluationResult,
    EvaluationSample,
)

__all__ = [
    "BaseEvaluator",
    "RAGEvaluator",
    "RetrievalEvaluator",
    "GenerationEvaluator",
    "EvaluationDataset",
    "EvaluationSample",
    "EvaluationReport",
    "EvaluationResult",
    "EvaluationMetric",
    "BaseEvaluationMetric",
    "ContextPrecisionMetric",
    "ContextRecallMetric",
    "FaithfulnessMetric",
    "AnswerRelevancyMetric",
    "build_judge_llm",
    "build_judge_embeddings",
    "resolve_judge_config",
    "load_from_dicts",
    "load_from_json",
    "from_rag_pipeline_output",
    "to_ragas_dataset",
    "EvaluationError",
    "LLMJudgeError",
    "MetricComputationError",
    "DatasetValidationError",
]
