import pytest

from workloadtruth.classifier.rules import classify
from workloadtruth.telemetry.synthetic_backend import SyntheticBackend
from workloadtruth.types import WorkloadType


def _collect(profile, evasion=False, seed=0, count=30):
    backend = SyntheticBackend(profile=profile, evasion=evasion, seed=seed)
    return [backend.sample(0) for _ in range(count)]


def test_classifies_clean_training():
    result = classify(_collect("training", seed=1))
    assert result.workload_type == WorkloadType.TRAINING
    assert result.confidence > 0.5


def test_classifies_clean_inference():
    result = classify(_collect("inference", seed=1))
    assert result.workload_type == WorkloadType.INFERENCE


def test_classifies_idle():
    result = classify(_collect("idle", seed=1))
    assert result.workload_type == WorkloadType.IDLE


def test_empty_samples_raises():
    with pytest.raises(ValueError):
        classify([])


def test_result_serializes_to_dict():
    result = classify(_collect("training", seed=2))
    payload = result.to_dict()
    assert payload["workload_type"] == "TRAINING"
    assert isinstance(payload["reasons"], list)
    assert isinstance(payload["features"], dict)


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_clean_classification_reasonably_accurate(seed):
    """Sanity check across several seeds -- not a substitute for benchmark.py's
    full sweep, just a fast regression guard for CI."""
    training_result = classify(_collect("training", seed=seed))
    inference_result = classify(_collect("inference", seed=seed))
    idle_result = classify(_collect("idle", seed=seed))

    assert training_result.workload_type == WorkloadType.TRAINING
    assert inference_result.workload_type == WorkloadType.INFERENCE
    assert idle_result.workload_type == WorkloadType.IDLE
