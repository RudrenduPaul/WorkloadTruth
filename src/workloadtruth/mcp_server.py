"""MCP server: exposes WorkloadTruth as agent-callable tools.

Requires the `mcp` extra (`pip install "workloadtruth-cli[mcp]"`). Started
via `workloadtruth mcp` (stdio transport), so any MCP-compatible agent
runtime can call classify_workload / run_benchmark / verify_audit_log
directly instead of shelling out to the CLI and parsing text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from workloadtruth.audit_log import append_entry, build_entry, last_hash, verify_chain
from workloadtruth.classifier.rules import classify
from workloadtruth.telemetry import get_backend

DEFAULT_LOG_PATH = Path("workloadtruth.log.jsonl")


def build_app(default_backend: str = "nvml") -> FastMCP:
    app = FastMCP("workloadtruth")

    @app.tool()
    def classify_workload(
        backend: str = default_backend,
        profile: str = "training",
        gpu_index: int = 0,
        samples: int = 10,
        interval_seconds: float = 1.0,
        write_to_audit_log: bool = False,
    ) -> dict[str, Any]:
        """Classify what a GPU is *actually* doing right now (TRAINING, INFERENCE, or IDLE) from raw telemetry alone -- utilization, memory-growth slope, and power draw -- with no reliance on a job's self-reported label and no inspection of its code, weights, or data.

        Call this to catch cost misallocation (a job billed as low-priority
        "inference" that is really running full training) or an unauthorized
        workload change (an inference endpoint that quietly starts training
        on live traffic). Do not call it for compliance/regulatory reporting
        -- no such requirement exists for this signal, see the README's
        "What WorkloadTruth is not" section.

        Prerequisites: `backend="nvml"` (the default) requires an NVIDIA GPU
        and driver on the host running this MCP server, plus the `mcp`+`nvml`
        extras (`pip install "workloadtruth-cli[mcp,nvml]"`). `backend=
        "synthetic"` needs neither a GPU nor extra driver setup -- it replays
        a documented synthetic trace selected by `profile`, so use it to test
        agent integrations or CI without hardware.

        Side effects: read-only and safe to call repeatedly by default. It
        blocks for roughly `samples * interval_seconds` seconds while it
        collects telemetry (defaults: 10 x 1.0s = 10s), then returns. No
        network calls are made, ever. Setting `write_to_audit_log=True` is
        the one mutating path: it appends one hash-chained line to the local
        `workloadtruth.log.jsonl` file (each call adds a new entry, so this
        is not idempotent) -- everything else about the call is idempotent.
        If `backend="nvml"` is requested with no NVIDIA GPU/driver present,
        the call raises rather than returning a fabricated result.

        Parameters: `backend` -- "nvml" or "synthetic". `profile` -- one of
        "training"/"inference"/"idle", synthetic backend only. `gpu_index`
        -- which GPU to sample, 0-indexed, ignored for synthetic. `samples`
        -- telemetry samples to collect. `interval_seconds` -- delay between
        samples. `write_to_audit_log` -- append the result to the hash chain.
        Example calls: `{"backend": "synthetic", "profile": "training",
        "samples": 10, "interval_seconds": 0}` to try it with no GPU;
        `{"backend": "nvml", "samples": 20, "interval_seconds": 1.0,
        "write_to_audit_log": true}` for a real 20s hardware sample that
        also logs the result.

        Returns a dict with `workload_type` ("TRAINING"/"INFERENCE"/"IDLE"),
        `confidence` (0-1), `gpu_index`, `window_seconds`, `sample_count`,
        `reasons` (the specific thresholds that fired, e.g. "avg GPU
        utilization 82.3% >= 65.0% training threshold"), and `features`
        (the raw avg/std utilization, memory-growth, and power numbers the
        decision was based on -- nothing here is a black box).
        """
        backend_kwargs = {"profile": profile} if backend == "synthetic" else {}
        tb = get_backend(backend, **backend_kwargs)
        try:
            collected = list(tb.sample_window(gpu_index, samples, interval_seconds))
        finally:
            tb.close()

        result = classify(collected)

        if write_to_audit_log:
            prev = last_hash(DEFAULT_LOG_PATH)
            entry = build_entry(
                timestamp=collected[-1].timestamp,
                gpu_index=result.gpu_index,
                workload_type=result.workload_type.value,
                confidence=result.confidence,
                reasons=result.reasons,
                features=result.features,
                prev_hash=prev,
            )
            append_entry(DEFAULT_LOG_PATH, entry)

        return result.to_dict()

    @app.tool()
    def run_benchmark(trials: int = 50, window: int = 30) -> dict[str, Any]:
        """Measure the shipped rule-based classifier's accuracy against documented synthetic GPU telemetry, both clean and under a deliberate evasion transform that mimics an operator disguising a training job as inference.

        Call this to report or sanity-check classifier robustness (e.g.
        before citing accuracy numbers, or after changing a threshold in
        `classifier/rules.py`). Do not call it to classify a live workload
        -- use `classify_workload` for that; this tool never touches real
        GPU telemetry.

        Side effects: none. Purely computational, no files written, no
        network calls, no GPU access. Deterministic and idempotent -- the
        same `trials`/`window` arguments reproduce the same synthetic
        results every call. Runtime scales with `trials`; the defaults
        (50 trials, window 30) finish in a few seconds.

        Parameters: `trials` -- trials run per profile/evasion cell.
        `window` -- telemetry samples per classification window. Example
        calls: `{}` for the documented defaults; `{"trials": 200, "window":
        60}` for a slower, higher-confidence accuracy read.

        Returns a dict with `source` ("synthetic"), a `note` warning these
        numbers are not comparable to any real-hardware benchmark,
        `window_size`, `trials_per_cell`, `clean_accuracy`,
        `evasion_accuracy`, and `cells` (a list of per-profile,
        per-evasion-condition `{profile, evasion, trials, correct,
        accuracy}` breakdowns).
        """
        from workloadtruth.benchmark import run_benchmark as _run_benchmark

        return _run_benchmark(trials_per_cell=trials, window_size=window).to_dict()

    @app.tool()
    def verify_audit_log(log_file: str = str(DEFAULT_LOG_PATH)) -> dict[str, Any]:
        """Verify that a local WorkloadTruth audit log's hash chain is intact, i.e. no entry was edited, reordered, or deleted after it was written.

        Call this before trusting historical `classify_workload` /
        `workloadtruth watch` records for anything security- or
        billing-sensitive -- each log entry's hash covers its own content
        plus the previous entry's hash, so any tampering anywhere in the
        file breaks the chain from that point forward and this tool will
        report exactly where.

        Prerequisites: the file at `log_file` must exist and be a
        WorkloadTruth JSONL audit log (produced by `write_to_audit_log=True`
        on `classify_workload`, or by `workloadtruth watch`).

        Side effects: read-only. Opens and reads `log_file` from local disk;
        never writes, never makes a network call. Safe to call repeatedly
        and idempotent -- verifying an unmodified log always returns the
        same result.

        Parameters: `log_file` -- path to the JSONL audit log, defaults to
        `workloadtruth.log.jsonl` in the current working directory. Example
        call: `{"log_file": "workloadtruth.log.jsonl"}`.

        Returns a dict with `valid` (bool), `message` (str -- "chain OK" or
        a description of the first broken link found), and `entries` (int
        count of entries verified before any break).
        """
        is_valid, message, count = verify_chain(Path(log_file))
        return {"valid": is_valid, "message": message, "entries": count}

    return app


def run_server(default_backend: str = "nvml") -> None:
    app = build_app(default_backend=default_backend)
    app.run()
