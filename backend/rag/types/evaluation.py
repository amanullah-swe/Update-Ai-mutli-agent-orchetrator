"""Domain models representing evaluation metrics and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluationMetric:
    name: str
    score: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    query: str
    answer: str
    ground_truth: str | None = None
    metrics: list[EvaluationMetric] = field(default_factory=list)
