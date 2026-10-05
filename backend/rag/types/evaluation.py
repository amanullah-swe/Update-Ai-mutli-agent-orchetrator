"""Domain models representing evaluation metrics, samples, and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluationMetric:
    """Individual metric name, score, and optional diagnostic metadata."""

    name: str
    score: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """Evaluation output for a single turn or query."""

    query: str
    answer: str
    ground_truth: str | None = None
    metrics: list[EvaluationMetric] = field(default_factory=list)

    def get_metric_score(self, name: str) -> float | None:
        """Helper to get a specific metric score by name."""
        for metric in self.metrics:
            if metric.name == name:
                return metric.score
        return None


@dataclass
class EvaluationSample:
    """Input payload representing a single turn to be evaluated."""

    query: str
    answer: str
    contexts: list[str] = field(default_factory=list)
    ground_truth: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationReport:
    """Aggregated evaluation report over a dataset."""

    samples: list[EvaluationResult] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
