from workloadtruth.telemetry.synthetic_backend import MEMORY_TOTAL_MIB, SyntheticBackend


def test_sample_stays_within_bounds():
    backend = SyntheticBackend(profile="training", seed=42)
    for _ in range(50):
        sample = backend.sample(gpu_index=0)
        assert 0.0 <= sample.gpu_utilization_pct <= 100.0
        assert 0.0 <= sample.memory_utilization_pct <= 100.0
        assert 0.0 <= sample.memory_used_mib <= MEMORY_TOTAL_MIB
        assert sample.power_draw_watts >= 0.0


def test_deterministic_with_seed():
    a = SyntheticBackend(profile="inference", seed=7)
    b = SyntheticBackend(profile="inference", seed=7)
    samples_a = [a.sample(0) for _ in range(10)]
    samples_b = [b.sample(0) for _ in range(10)]
    assert [s.gpu_utilization_pct for s in samples_a] == [s.gpu_utilization_pct for s in samples_b]


def test_training_memory_grows_more_than_inference():
    training = SyntheticBackend(profile="training", seed=1)
    inference = SyntheticBackend(profile="inference", seed=1)

    training_samples = [training.sample(0) for _ in range(30)]
    inference_samples = [inference.sample(0) for _ in range(30)]

    training_growth = training_samples[-1].memory_used_mib - training_samples[0].memory_used_mib
    inference_growth = inference_samples[-1].memory_used_mib - inference_samples[0].memory_used_mib

    assert training_growth > inference_growth


def test_evasion_caps_utilization():
    backend = SyntheticBackend(profile="training", evasion=True, seed=3)
    samples = [backend.sample(0) for _ in range(30)]
    assert max(s.gpu_utilization_pct for s in samples) <= 60.0


def test_unknown_profile_raises():
    try:
        SyntheticBackend(profile="not-a-real-profile")
    except ValueError as exc:
        assert "Unknown synthetic profile" in str(exc)
    else:
        raise AssertionError("expected ValueError")
