"""Synthetic telemetry backend.

Generates GPU telemetry traces from documented statistical profiles instead
of reading real hardware. This exists for two honest reasons, not as a
substitute for real measurement:

1. Unit testing the classifier without requiring NVIDIA hardware in CI.
2. Powering `workloadtruth benchmark` on machines with no GPU (including the
   machine this project was built on). Benchmark output produced by this
   backend is always labeled "synthetic" -- see benchmark.py -- and must
   never be presented as a live-hardware accuracy measurement.

Profile design rationale (documented so the numbers are inspectable, not
asserted):

- TRAINING: sustained high GPU utilization (large matmul-heavy forward/
  backward passes keep SMs busy), memory usage grows in a step pattern
  (activations + gradient buffers + optimizer state accumulate, then drop at
  checkpoint boundaries), power draw stays near the sustained-load ceiling
  with low variance.
- INFERENCE: bursty GPU utilization driven by request arrival (idle between
  requests, a short spike to serve one), memory usage is comparatively flat
  (model weights resident, no growing gradient/optimizer state), power draw
  has high variance tracking the request bursts.
- IDLE: near-zero utilization and power draw, flat low memory (driver/CUDA
  context overhead only).

These are simplified textbook characterizations, not fit to any real dataset
-- the honest limitation to disclose is that real-world workloads (small
inference batches with periodic re-warming, gradient-accumulation training
with long low-utilization gaps, mixed inference+LoRA-finetuning servers) can
blur these boundaries. The classifier's rule thresholds and this generator's
profiles are documented in the same place (this file and rules.py) so both
can be inspected and challenged together.
"""

from __future__ import annotations

import random

from workloadtruth.telemetry.base import TelemetryBackend
from workloadtruth.types import TelemetrySample

_PROFILES = {
    "training": {
        "gpu_util_mean": 88.0,
        "gpu_util_std": 4.0,
        "mem_util_mean": 70.0,
        "mem_util_std": 6.0,
        "mem_base_mib": 18000.0,
        "mem_growth_mib_per_sample": 120.0,
        "mem_ceiling_mib": 38000.0,
        "power_mean_watts": 340.0,
        "power_std_watts": 12.0,
        "process_count": 1,
    },
    "inference": {
        "gpu_util_mean": 35.0,
        "gpu_util_std": 28.0,
        "mem_util_mean": 22.0,
        "mem_util_std": 5.0,
        "mem_base_mib": 9000.0,
        "mem_growth_mib_per_sample": 0.0,
        "mem_ceiling_mib": 9500.0,
        "power_mean_watts": 160.0,
        "power_std_watts": 55.0,
        "process_count": 1,
    },
    "idle": {
        "gpu_util_mean": 1.0,
        "gpu_util_std": 1.0,
        "mem_util_mean": 0.5,
        "mem_util_std": 0.5,
        "mem_base_mib": 400.0,
        "mem_growth_mib_per_sample": 0.0,
        "mem_ceiling_mib": 400.0,
        "power_mean_watts": 35.0,
        "power_std_watts": 5.0,
        "process_count": 0,
    },
}

MEMORY_TOTAL_MIB = 40960.0  # A100 40GB, used as the fixed reference card


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class SyntheticBackend(TelemetryBackend):
    """Generates telemetry from a named profile ("training"/"inference"/"idle").

    `evasion` applies a documented obfuscation transform meant to defeat a
    naive classifier: it caps utilization swings, injects artificial idle
    gaps into a training profile, and flattens memory growth -- modeling an
    operator deliberately trying to make a training job telemetry-resemble
    inference. This is what `workloadtruth benchmark` uses to measure the
    classifier's evasion-robustness gap, the same property arXiv:2606.19262
    reports a real accuracy drop against (43-87%) -- WorkloadTruth's own
    number, measured against this synthetic evasion transform, is reported
    separately in the README and must never be presented as the same
    measurement.
    """

    def __init__(self, profile: str = "training", evasion: bool = False, seed: int | None = None):
        if profile not in _PROFILES:
            raise ValueError(
                f"Unknown synthetic profile: {profile!r}. Expected one of {list(_PROFILES)}."
            )
        self.profile_name = profile
        self.evasion = evasion
        self._rng = random.Random(seed)
        self._sample_index = 0
        self._t0 = 0.0

    def device_count(self) -> int:
        return 1

    def sample(self, gpu_index: int = 0) -> TelemetrySample:
        p = _PROFILES[self.profile_name]
        gpu_util = self._rng.gauss(p["gpu_util_mean"], p["gpu_util_std"])
        mem_util = self._rng.gauss(p["mem_util_mean"], p["mem_util_std"])
        power = self._rng.gauss(p["power_mean_watts"], p["power_std_watts"])
        mem_used = p["mem_base_mib"] + p["mem_growth_mib_per_sample"] * self._sample_index
        mem_used = min(mem_used, p["mem_ceiling_mib"])
        process_count = int(p["process_count"])

        if self.evasion:
            # Cap utilization swings and flatten memory growth to mimic an
            # operator deliberately disguising a training job as inference.
            gpu_util = _clamp(gpu_util, 0.0, 55.0)
            mem_used = min(mem_used, p["mem_base_mib"] * 1.1)
            if self._sample_index % 4 == 0:
                gpu_util *= 0.2  # inject an artificial idle gap

        self._sample_index += 1
        timestamp = self._t0 + self._sample_index

        return TelemetrySample(
            timestamp=timestamp,
            gpu_index=gpu_index,
            gpu_utilization_pct=_clamp(gpu_util, 0.0, 100.0),
            memory_utilization_pct=_clamp(mem_util, 0.0, 100.0),
            memory_used_mib=_clamp(mem_used, 0.0, MEMORY_TOTAL_MIB),
            memory_total_mib=MEMORY_TOTAL_MIB,
            power_draw_watts=max(0.0, power),
            process_count=process_count,
        )

    def close(self) -> None:
        return None
