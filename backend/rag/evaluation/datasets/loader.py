"""Dataset loading and transformation utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ragas import EvaluationDataset as RagasEvaluationDataset
from ragas import SingleTurnSample

from rag.evaluation.datasets.schema import EvaluationDataset
from rag.evaluation.exceptions import DatasetValidationError
from rag.types.evaluation import EvaluationSample


def load_from_dicts(records: list[dict[str, Any]]) -> EvaluationDataset:
    """Create an EvaluationDataset from a list of dictionaries."""
    if not isinstance(records, list):
        raise DatasetValidationError("Expected a list of dictionary records.")

    dataset = EvaluationDataset()
    for item in records:
        if not isinstance(item, dict):
            raise DatasetValidationError(f"Invalid record type: {type(item)}")
        query = item.get("query") or item.get("user_input") or ""
        answer = item.get("answer") or item.get("response") or ""
        contexts = item.get("contexts") or item.get("retrieved_contexts") or []
        ground_truth = item.get("ground_truth") or item.get("reference")
        metadata = item.get("metadata") or {}

        sample = EvaluationSample(
            query=str(query),
            answer=str(answer),
            contexts=[str(c) for c in contexts],
            ground_truth=str(ground_truth) if ground_truth is not None else None,
            metadata=dict(metadata),
        )
        dataset.add_sample(sample)
    return dataset


def load_from_json(file_path_or_str: str | Path) -> EvaluationDataset:
    """Load an EvaluationDataset from a JSON file path or a raw JSON string."""
    path = Path(file_path_or_str) if isinstance(file_path_or_str, (str, Path)) and Path(str(file_path_or_str)).exists() else None

    if path is not None and path.is_file():
        raw_text = path.read_text(encoding="utf-8")
    else:
        raw_text = str(file_path_or_str)

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise DatasetValidationError(f"Invalid JSON data: {exc}") from exc

    if not isinstance(data, list):
        raise DatasetValidationError("JSON root must be a list of records.")

    return load_from_dicts(data)


def from_rag_pipeline_output(
    pipeline_result: dict[str, Any], ground_truth: str | None = None
) -> EvaluationSample:
    """Construct an EvaluationSample directly from RAGPipeline.query output."""
    query = pipeline_result.get("query", "")
    answer = pipeline_result.get("answer", "")
    raw_sources = pipeline_result.get("sources", [])

    contexts: list[str] = []
    for source in raw_sources:
        if hasattr(source, "text"):
            contexts.append(str(source.text))
        elif isinstance(source, dict) and "text" in source:
            contexts.append(str(source["text"]))
        else:
            contexts.append(str(source))

    if not contexts and "context" in pipeline_result and pipeline_result["context"]:
        contexts.append(str(pipeline_result["context"]))

    return EvaluationSample(
        query=query,
        answer=answer,
        contexts=contexts,
        ground_truth=ground_truth,
    )


def to_ragas_dataset(dataset: EvaluationDataset) -> RagasEvaluationDataset:
    """Convert an internal EvaluationDataset into a native Ragas EvaluationDataset."""
    ragas_samples: list[SingleTurnSample] = []
    for sample in dataset.samples:
        ragas_samples.append(
            SingleTurnSample(
                user_input=sample.query,
                response=sample.answer,
                retrieved_contexts=sample.contexts or [],
                reference=sample.ground_truth or "",
            )
        )
    return RagasEvaluationDataset(samples=ragas_samples)
