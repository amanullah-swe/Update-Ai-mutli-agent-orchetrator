"""Dataset schemas and collections for RAG evaluation."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field

from rag.evaluation.exceptions import DatasetValidationError
from rag.types.evaluation import EvaluationSample


@dataclass
class EvaluationDataset:
    """A collection of EvaluationSample instances for batch evaluation."""

    samples: list[EvaluationSample] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.samples)

    def __iter__(self) -> Iterator[EvaluationSample]:
        return iter(self.samples)

    def __getitem__(self, index: int) -> EvaluationSample:
        return self.samples[index]

    def add_sample(self, sample: EvaluationSample) -> None:
        """Add and validate an evaluation sample."""
        self._validate_sample(sample)
        self.samples.append(sample)

    def extend(self, samples: Sequence[EvaluationSample]) -> None:
        """Extend the dataset with multiple validated samples."""
        for sample in samples:
            self.add_sample(sample)

    @staticmethod
    def _validate_sample(sample: EvaluationSample) -> None:
        """Validate sample fields."""
        if not isinstance(sample, EvaluationSample):
            raise DatasetValidationError("Expected an EvaluationSample instance.")
        if not sample.query or not sample.query.strip():
            raise DatasetValidationError("EvaluationSample must have a non-empty query.")
