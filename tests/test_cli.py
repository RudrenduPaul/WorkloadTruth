import json

from click.testing import CliRunner

from workloadtruth.cli import main


def test_classify_synthetic_json():
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "classify",
            "--backend",
            "synthetic",
            "--profile",
            "training",
            "--samples",
            "10",
            "--interval",
            "0",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["workload_type"] == "TRAINING"


def test_classify_experimental_fails_clearly():
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["classify", "--backend", "synthetic", "--experimental"],
    )
    assert result.exit_code != 0
    assert "not available" in str(result.output) + str(result.exception)


def test_watch_appends_to_log(tmp_path):
    log_file = tmp_path / "audit.log.jsonl"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "watch",
            "--backend",
            "synthetic",
            "--profile",
            "inference",
            "--interval",
            "0",
            "--window",
            "5",
            "--iterations",
            "2",
            "--log-file",
            str(log_file),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert log_file.exists()
    lines = log_file.read_text().splitlines()
    assert len(lines) == 2


def test_verify_log_on_valid_chain(tmp_path):
    log_file = tmp_path / "audit.log.jsonl"
    runner = CliRunner()
    runner.invoke(
        main,
        [
            "watch",
            "--backend",
            "synthetic",
            "--interval",
            "0",
            "--window",
            "5",
            "--iterations",
            "1",
            "--log-file",
            str(log_file),
        ],
    )

    verify_result = runner.invoke(main, ["verify-log", "--log-file", str(log_file), "--json"])
    assert verify_result.exit_code == 0
    payload = json.loads(verify_result.output)
    assert payload["valid"] is True


def test_benchmark_runs_quickly_in_ci():
    runner = CliRunner()
    result = runner.invoke(main, ["benchmark", "--trials", "3", "--window", "10", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["source"] == "synthetic"


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "workloadtruth" in result.output
