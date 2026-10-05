"""Unit tests for RAG evaluation dataset schemas and loaders."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rag.evaluation.datasets.loader import (
    from_rag_pipeline_output,
    load_from_dicts,
    load_from_json,
    to_ragas_dataset,
)
from rag.evaluation.datasets.schema import EvaluationDataset
from rag.evaluation.exceptions import DatasetValidationError
from rag.types.evaluation import EvaluationSample


@pytest.mark.unit
class TestEvaluationDataset:
    def test_add_and_iterate_samples(self) -> None:
        dataset = EvaluationDataset()
        sample = EvaluationSample(
            query="What is RAG?",
            answer="Retrieval Augmented Generation.",
            contexts=["RAG combines retrieval and generation."],
            ground_truth="RAG is Retrieval Augmented Generation.",
        )
        dataset.add_sample(sample)

        assert len(dataset) == 1
        assert dataset[0].query == "What is RAG?"
        assert list(iter(dataset))[0] == sample

    def test_validation_error_on_empty_query(self) -> None:
        dataset = EvaluationDataset()
        with pytest.raises(DatasetValidationError, match="non-empty query"):
            dataset.add_sample(EvaluationSample(query="", answer="answer"))

    def test_load_from_dicts(self) -> None:
        records = [
            {
                "query": "What is Python?",
                "answer": "A programming language.",
                "contexts": ["Python is high-level."],
                "ground_truth": "Python is a language.",
            }
        ]
        dataset = load_from_dicts(records)
        assert len(dataset) == 1
        assert dataset[0].query == "What is Python?"
        assert dataset[0].contexts == ["Python is high-level."]

    def test_load_from_dicts_invalid_type(self) -> None:
        with pytest.raises(DatasetValidationError, match="list of dictionary records"):
            load_from_dicts("not-a-list")  # type: ignore[arg-type]

    def test_load_from_json_string(self) -> None:
        json_str = json.dumps([
            {"query": "Query 1", "answer": "Answer 1", "contexts": ["Context 1"]}
        ])
        dataset = load_from_json(json_str)
        assert len(dataset) == 1
        assert dataset[0].query == "Query 1"

    def test_load_from_json_file(self, tmp_path: Path) -> None:
        file_path = tmp_path / "test_data.json"
        file_path.write_text(
            json.dumps([{"query": "File Q", "answer": "File A", "contexts": ["File C"]}]),
            encoding="utf-8",
        )
        dataset = load_from_json(file_path)
        assert len(dataset) == 1
        assert dataset[0].query == "File Q"

    def test_from_rag_pipeline_output(self) -> None:
        pipeline_output = {
            "query": "Test query",
            "answer": "Test answer",
            "context": "Built context block",
            "sources": [{"text": "Source snippet 1"}, "Source snippet 2"],
        }
        sample = from_rag_pipeline_output(pipeline_output, ground_truth="Expected truth")
        assert sample.query == "Test query"
        assert sample.answer == "Test answer"
        assert len(sample.contexts) == 2
        assert sample.contexts[0] == "Source snippet 1"
        assert sample.ground_truth == "Expected truth"

    def test_to_ragas_dataset(self) -> None:
        dataset = EvaluationDataset(
            samples=[
                EvaluationSample(
                    query="Q1",
                    answer="A1",
                    contexts=["C1"],
                    ground_truth="GT1",
                )
            ]
        )
        ragas_ds = to_ragas_dataset(dataset)
        assert len(ragas_ds) == 1
        assert ragas_ds[0].user_input == "Q1"
        assert ragas_ds[0].response == "A1"
        assert ragas_ds[0].retrieved_contexts == ["C1"]
        assert ragas_ds[0].reference == "GT1"
