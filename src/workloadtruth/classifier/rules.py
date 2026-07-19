"""Rule-based workload classifier.

This is the default (and, in v0.1, the only shipped) classifier. It is a
transparent, documented heuristic, not a trained model -- every threshold
below is a constant you can read, challenge, and override, not a black box.
See the README's "How classification works" section for why v0.1 ships
this instead of the ML classifier arXiv:2606.19262 describes:
without the paper's training dataset (not published) or real GPU hardware
in this project's build environment, an from-scratch ML classifier would be
an unvalidated claim, not a measured one. This module is intentionally the
inspectable alternative.

Feature intuition (same rationale as synthetic_backend.py's profile design,
kept in sync deliberately):

- Training: sustained high, low-variance GPU utilization; memory usage
  trending upward across the sampling window (activations, gradient
  buffers, optimizer state accumulating); low-variance, near-ceiling power
  draw.
- Inference: bursty, high-variance GPU utilization tracking request
  arrival; flat memory usage (resident weights, no growing training state);
  high-variance power draw.
- Idle: near-zero utilization and power draw across the whole window.
"""

from __future__ import annotations

from workloadtruth.types import ClassificationResult, TelemetrySample, WorkloadType

# Idle detection
IDLE_GPU_UTIL_PCT = 5.0
IDLE_POWER_WATTS = 50.0

# Training signal thresholds
TRAINING_MIN_AVG_GPU_UTIL_PCT = 65.0
TRAINING_MAX_GPU_UTIL_STD_PCT = 15.0
TRAINING_MIN_MEM_GROWTH_MIB_PER_SAMPLE = 5.0
TRAINING_MAX_POWER_STD_WATTS = 25.0

# Inference signal thresholds
INFERENCE_MAX_AVG_GPU_UTIL_PCT = 70.0
INFERENCE_MIN_GPU_UTIL_STD_PCT = 12.0
INFERENCE_MIN_POWER_STD_WATTS = 20.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    variance = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return float(variance**0.5)


def _linear_slope_per_sample(values: list[float]) -> float:
    """Least-squares slope of `values` against sample index (0, 1, 2, ...)."""
    n = len(values)
    if n < 2:
        return 0.0
    xs = [float(i) for i in range(n)]
    x_mean = _mean(xs)
    y_mean = _mean(values)
    numerator = sum((xs[i] - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((xs[i] - x_mean) ** 2 for i in range(n))
    return numerator / denominator if denominator else 0.0


def extract_features(samples: list[TelemetrySample]) -> dict[str, float]:
    gpu_util = [s.gpu_utilization_pct for s in samples]
    mem_used = [s.memory_used_mib for s in samples]
    power = [s.power_draw_watts for s in samples]

    return {
        "avg_gpu_util_pct": _mean(gpu_util),
        "std_gpu_util_pct": _stdev(gpu_util),
        "mem_growth_mib_per_sample": _linear_slope_per_sample(mem_used),
        "avg_power_watts": _mean(power),
        "std_power_watts": _stdev(power),
        "avg_process_count": _mean([float(s.process_count) for s in samples]),
    }


def classify(samples: list[TelemetrySample]) -> ClassificationResult:
    if not samples:
        raise ValueError("classify() requires at least one telemetry sample")

    gpu_index = samples[0].gpu_index
    window_seconds = samples[-1].timestamp - samples[0].timestamp if len(samples) > 1 else 0.0
    features = extract_features(samples)

    if (
        features["avg_gpu_util_pct"] <= IDLE_GPU_UTIL_PCT
        and features["avg_power_watts"] <= IDLE_POWER_WATTS
    ):
        return ClassificationResult(
            workload_type=WorkloadType.IDLE,
            confidence=1.0 - (features["avg_gpu_util_pct"] / IDLE_GPU_UTIL_PCT) * 0.3,
            gpu_index=gpu_index,
            window_seconds=window_seconds,
            sample_count=len(samples),
            reasons=[
                f"avg GPU utilization {features['avg_gpu_util_pct']:.1f}% "
                f"<= idle threshold {IDLE_GPU_UTIL_PCT}%",
                f"avg power draw {features['avg_power_watts']:.1f}W "
                f"<= idle threshold {IDLE_POWER_WATTS}W",
            ],
            features=features,
        )

    training_votes: list[str] = []
    inference_votes: list[str] = []

    if features["avg_gpu_util_pct"] >= TRAINING_MIN_AVG_GPU_UTIL_PCT:
        training_votes.append(
            f"avg GPU utilization {features['avg_gpu_util_pct']:.1f}% "
            f">= training threshold {TRAINING_MIN_AVG_GPU_UTIL_PCT}%"
        )
    if features["std_gpu_util_pct"] <= TRAINING_MAX_GPU_UTIL_STD_PCT:
        training_votes.append(
            f"low GPU utilization variance (std={features['std_gpu_util_pct']:.1f}) "
            f"<= training ceiling {TRAINING_MAX_GPU_UTIL_STD_PCT}"
        )
    if features["mem_growth_mib_per_sample"] >= TRAINING_MIN_MEM_GROWTH_MIB_PER_SAMPLE:
        training_votes.append(
            f"memory growing {features['mem_growth_mib_per_sample']:.1f} MiB/sample "
            f">= training threshold {TRAINING_MIN_MEM_GROWTH_MIB_PER_SAMPLE}"
        )
    if features["std_power_watts"] <= TRAINING_MAX_POWER_STD_WATTS:
        training_votes.append(
            f"low power-draw variance (std={features['std_power_watts']:.1f}W) "
            f"<= training ceiling {TRAINING_MAX_POWER_STD_WATTS}W"
        )

    if features["avg_gpu_util_pct"] <= INFERENCE_MAX_AVG_GPU_UTIL_PCT:
        inference_votes.append(
            f"avg GPU utilization {features['avg_gpu_util_pct']:.1f}% "
            f"<= inference ceiling {INFERENCE_MAX_AVG_GPU_UTIL_PCT}%"
        )
    if features["std_gpu_util_pct"] >= INFERENCE_MIN_GPU_UTIL_STD_PCT:
        inference_votes.append(
            f"bursty GPU utilization (std={features['std_gpu_util_pct']:.1f}) "
            f">= inference threshold {INFERENCE_MIN_GPU_UTIL_STD_PCT}"
        )
    if features["mem_growth_mib_per_sample"] < TRAINING_MIN_MEM_GROWTH_MIB_PER_SAMPLE:
        inference_votes.append(
            f"flat memory usage ({features['mem_growth_mib_per_sample']:.1f} MiB/sample) "
            f"< training threshold {TRAINING_MIN_MEM_GROWTH_MIB_PER_SAMPLE}"
        )
    if features["std_power_watts"] >= INFERENCE_MIN_POWER_STD_WATTS:
        inference_votes.append(
            f"bursty power draw (std={features['std_power_watts']:.1f}W) "
            f">= inference threshold {INFERENCE_MIN_POWER_STD_WATTS}W"
        )

    total_votes = 4
    if len(training_votes) > len(inference_votes):
        workload_type = WorkloadType.TRAINING
        reasons = training_votes
        confidence = len(training_votes) / total_votes
    elif len(inference_votes) > len(training_votes):
        workload_type = WorkloadType.INFERENCE
        reasons = inference_votes
        confidence = len(inference_votes) / total_votes
    else:
        workload_type = WorkloadType.UNKNOWN
        reasons = [
            "training and inference signals tied "
            f"({len(training_votes)} votes each) -- inconclusive"
        ]
        confidence = 0.5

    return ClassificationResult(
        workload_type=workload_type,
        confidence=confidence,
        gpu_index=gpu_index,
        window_seconds=window_seconds,
        sample_count=len(samples),
        reasons=reasons,
        features=features,
    )
