"""WorkloadTruth CLI entry point."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import click

from workloadtruth import __version__
from workloadtruth.audit_log import append_entry, build_entry, last_hash, verify_chain
from workloadtruth.classifier.rules import classify
from workloadtruth.telemetry import get_backend
from workloadtruth.types import ClassificationResult

DEFAULT_LOG_PATH = Path("workloadtruth.log.jsonl")


def _echo_result(result: ClassificationResult, as_json: bool) -> None:
    if as_json:
        click.echo(json.dumps(result.to_dict(), indent=2))
        return
    click.echo(f"workload_type : {result.workload_type.value}")
    click.echo(f"confidence    : {result.confidence:.2f}")
    click.echo(f"gpu_index     : {result.gpu_index}")
    click.echo(f"samples       : {result.sample_count} over {result.window_seconds:.1f}s")
    click.echo("reasons:")
    for reason in result.reasons:
        click.echo(f"  - {reason}")


@click.group()
@click.version_option(version=__version__, prog_name="workloadtruth")
def main() -> None:
    """Classify a GPU workload as INFERENCE, TRAINING, or IDLE from telemetry alone."""


@main.command(name="classify")
@click.option(
    "--backend",
    type=click.Choice(["synthetic", "nvml"]),
    default="nvml",
    show_default=True,
    help="Telemetry source. 'synthetic' needs no GPU -- useful for trying the CLI.",
)
@click.option("--profile", default="training", help="Synthetic backend profile (synthetic only).")
@click.option("--gpu-index", default=0, show_default=True, type=int)
@click.option("--samples", default=10, show_default=True, type=int, help="Samples to collect.")
@click.option(
    "--interval", default=1.0, show_default=True, type=float, help="Seconds between samples."
)
@click.option(
    "--experimental", is_flag=True, help="Use the experimental ML classifier (not yet available)."
)
@click.option("--json", "as_json", is_flag=True, help="Machine-readable JSON output.")
def classify_cmd(
    backend: str,
    profile: str,
    gpu_index: int,
    samples: int,
    interval: float,
    experimental: bool,
    as_json: bool,
) -> None:
    """One-shot classification of the current GPU workload."""
    if experimental:
        from workloadtruth.classifier.experimental import classify_experimental

        classify_experimental()
        return

    backend_kwargs = {"profile": profile} if backend == "synthetic" else {}
    tb = get_backend(backend, **backend_kwargs)
    try:
        collected = list(tb.sample_window(gpu_index, samples, interval))
    finally:
        tb.close()

    result = classify(collected)
    _echo_result(result, as_json)


@main.command()
@click.option(
    "--backend",
    type=click.Choice(["synthetic", "nvml"]),
    default="nvml",
    show_default=True,
)
@click.option("--profile", default="training", help="Synthetic backend profile (synthetic only).")
@click.option("--gpu-index", default=0, show_default=True, type=int)
@click.option(
    "--interval", default=1.0, show_default=True, type=float, help="Seconds between samples."
)
@click.option(
    "--window", default=10, show_default=True, type=int, help="Samples per classification window."
)
@click.option(
    "--iterations",
    default=0,
    type=int,
    help="Stop after N classification windows (0 = run forever).",
)
@click.option(
    "--log-file",
    default=str(DEFAULT_LOG_PATH),
    show_default=True,
    type=click.Path(path_type=Path),
)
@click.option("--json", "as_json", is_flag=True, help="Machine-readable JSON output per window.")
def watch(
    backend: str,
    profile: str,
    gpu_index: int,
    interval: float,
    window: int,
    iterations: int,
    log_file: Path,
    as_json: bool,
) -> None:
    """Continuously classify and append hash-chained entries to the audit log."""
    backend_kwargs = {"profile": profile} if backend == "synthetic" else {}
    tb = get_backend(backend, **backend_kwargs)
    iteration = 0
    try:
        while True:
            collected = list(tb.sample_window(gpu_index, window, interval))
            result = classify(collected)
            prev = last_hash(log_file)
            entry = build_entry(
                timestamp=time.time(),
                gpu_index=result.gpu_index,
                workload_type=result.workload_type.value,
                confidence=result.confidence,
                reasons=result.reasons,
                features=result.features,
                prev_hash=prev,
            )
            append_entry(log_file, entry)
            _echo_result(result, as_json)
            iteration += 1
            if iterations and iteration >= iterations:
                break
    finally:
        tb.close()


@main.command()
@click.option(
    "--trials", default=50, show_default=True, type=int, help="Trials per profile/evasion cell."
)
@click.option(
    "--window", default=30, show_default=True, type=int, help="Samples per classification window."
)
@click.option("--json", "as_json", is_flag=True)
def benchmark(trials: int, window: int, as_json: bool) -> None:
    """Run the evasion-robustness benchmark against synthetic telemetry."""
    from workloadtruth.benchmark import run_benchmark

    report = run_benchmark(trials_per_cell=trials, window_size=window)
    if as_json:
        click.echo(json.dumps(report.to_dict(), indent=2))
        return

    click.echo("WorkloadTruth benchmark (synthetic telemetry -- see --json 'note' field)")
    click.echo(f"clean accuracy   : {report.clean_accuracy:.1%}")
    click.echo(f"evasion accuracy : {report.evasion_accuracy:.1%}")
    click.echo("")
    click.echo(f"{'profile':<12}{'evasion':<10}{'accuracy':<10}trials")
    for cell in report.cells:
        click.echo(f"{cell.profile:<12}{str(cell.evasion):<10}{cell.accuracy:<10.1%}{cell.trials}")


@main.command(name="verify-log")
@click.option(
    "--log-file",
    default=str(DEFAULT_LOG_PATH),
    show_default=True,
    type=click.Path(path_type=Path),
)
@click.option("--json", "as_json", is_flag=True)
def verify_log(log_file: Path, as_json: bool) -> None:
    """Verify the hash chain of a local audit log has not been tampered with."""
    is_valid, message, count = verify_chain(log_file)
    if as_json:
        click.echo(json.dumps({"valid": is_valid, "message": message, "entries": count}, indent=2))
    else:
        status = "OK" if is_valid else "TAMPERED"
        click.echo(f"[{status}] {message}")
    if not is_valid:
        sys.exit(1)


@main.command()
@click.option(
    "--backend",
    type=click.Choice(["synthetic", "nvml"]),
    default="nvml",
    show_default=True,
)
def mcp(backend: str) -> None:
    """Start an MCP server exposing classify/benchmark/verify-log as agent tools."""
    try:
        from workloadtruth.mcp_server import run_server
    except ImportError:
        click.echo(
            'The MCP server requires the "mcp" extra: pip install "workloadtruth-cli[mcp]"',
            err=True,
        )
        sys.exit(1)
    run_server(default_backend=backend)


if __name__ == "__main__":
    main()
