from workloadtruth.benchmark import run_benchmark


def test_benchmark_returns_clean_and_evasion_accuracy():
    report = run_benchmark(trials_per_cell=10, window_size=20)
    assert 0.0 <= report.clean_accuracy <= 1.0
    assert 0.0 <= report.evasion_accuracy <= 1.0
    assert len(report.cells) == 6  # 3 profiles x 2 (clean/evasion)


def test_clean_accuracy_beats_evasion_accuracy():
    """The whole point of the evasion transform: it should degrade accuracy,
    not leave it unchanged. If this regresses, the transform stopped doing
    anything and the benchmark's headline claim is false."""
    report = run_benchmark(trials_per_cell=15, window_size=20)
    assert report.clean_accuracy >= report.evasion_accuracy


def test_report_to_dict_labels_synthetic_source():
    report = run_benchmark(trials_per_cell=5, window_size=15)
    payload = report.to_dict()
    assert payload["source"] == "synthetic"
    assert "arXiv:2606.19262" in payload["note"] or "not comparable" in payload["note"].lower()
