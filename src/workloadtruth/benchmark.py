"""Evasion-robustness benchmark suite.

Measures the rule-based classifier's accuracy against SyntheticBackend
traces, both "clean" and under the documented evasion transform (see
telemetry/synthetic_backend.py). This is WorkloadTruth's core
differentiation artifact: arXiv:2606.19262 measured a real accuracy drop
under obfuscation (98.2% clean, 43-87% evasive) on real GPU hardware and a
dataset that was never published. This benchmark runs the same *kind* of
test, on synthetic data, on whatever machine `workloadtruth benchmark` is
invoked on.

The numbers this benchmark produces are NOT comparable to the paper's --
different data, different (and much simpler) hardware simulation, no shared
ground truth. Report them side by side in the README, labeled separately,
never blended into one number. This is a binding rule from this project's
own anti-sycophancy audit, not a style preference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from workloadtruth.classifier.rules import classify
from workloadtruth.telemetry.synthetic_backend import SyntheticBackend
from workloadtruth.types import WorkloadType

_PROFILE_TO_EXPECTED = {
    "training": WorkloadType.TRAINING,
    "inference": WorkloadType.INFERENCE,
    "idle": WorkloadType.IDLE,
}


@dataclass(frozen=True)
class BenchmarkCell:
    profile: str
    evasion: bool
    trials: int
    correct: int

    @property
    def accuracy(self) -> float:
        return self.correct / self.trials if self.trials else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "evasion": self.evasion,
            "trials": self.trials,
            "correct": self.correct,
            "accuracy": round(self.accuracy, 4),
        }


@dataclass(frozen=True)
class BenchmarkReport:
    cells: list[BenchmarkCell]
    window_size: int
    trials_per_cell: int

    @property
    def clean_accuracy(self) -> float:
        clean_cells = [c for c in self.cells if not c.evasion]
        total = sum(c.trials for c in clean_cells)
        correct = sum(c.correct for c in clean_cells)
        return correct / total if total else 0.0

    @property
    def evasion_accuracy(self) -> float:
        evasive_cells = [c for c in self.cells if c.evasion]
        total = sum(c.trials for c in evasive_cells)
        correct = sum(c.correct for c in evasive_cells)
        return correct / total if total else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": "synthetic",
            "note": (
                "Measured against documented synthetic GPU telemetry traces, "
                "not live NVIDIA hardware. Not comparable to arXiv:2606.19262's "
                "real-hardware numbers -- see benchmark.py module docstring."
            ),
            "window_size": self.window_size,
            "trials_per_cell": self.trials_per_cell,
            "clean_accuracy": round(self.clean_accuracy, 4),
            "evasion_accuracy": round(self.evasion_accuracy, 4),
            "cells": [c.to_dict() for c in self.cells],
        }


def run_benchmark(
    trials_per_cell: int = 50, window_size: int = 30, base_seed: int = 1000
) -> BenchmarkReport:
    cells: list[BenchmarkCell] = []
    for profile, expected in _PROFILE_TO_EXPECTED.items():
        for evasion in (False, True):
            correct = 0
            for trial in range(trials_per_cell):
                seed = base_seed + hash((profile, evasion, trial)) % 100_000
                backend = SyntheticBackend(profile=profile, evasion=evasion, seed=seed)
                samples = [backend.sample(gpu_index=0) for _ in range(window_size)]
                result = classify(samples)
                if result.workload_type == expected:
                    correct += 1
            cells.append(
                BenchmarkCell(
                    profile=profile, evasion=evasion, trials=trials_per_cell, correct=correct
                )
            )
    return BenchmarkReport(cells=cells, window_size=window_size, trials_per_cell=trials_per_cell)
