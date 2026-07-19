"""Shared types for WorkloadTruth."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WorkloadType(str, Enum):
    TRAINING = "TRAINING"
    INFERENCE = "INFERENCE"
    IDLE = "IDLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TelemetrySample:
    """One point-in-time reading from a GPU telemetry backend."""

    timestamp: float
    gpu_index: int
    gpu_utilization_pct: float
    memory_utilization_pct: float
    memory_used_mib: float
    memory_total_mib: float
    power_draw_watts: float
    process_count: int


@dataclass(frozen=True)
class ClassificationResult:
    workload_type: WorkloadType
    confidence: float
    gpu_index: int
    window_seconds: float
    sample_count: int
    reasons: list[str] = field(default_factory=list)
    features: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workload_type": self.workload_type.value,
            "confidence": round(self.confidence, 4),
            "gpu_index": self.gpu_index,
            "window_seconds": self.window_seconds,
            "sample_count": self.sample_count,
            "reasons": self.reasons,
            "features": {k: round(v, 4) for k, v in self.features.items()},
        }
