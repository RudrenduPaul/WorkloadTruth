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
        """Classify the current GPU workload as TRAINING, INFERENCE, or IDLE.

        `backend` is "nvml" (real hardware, requires an NVIDIA GPU + driver)
        or "synthetic" (documented synthetic traces, no GPU required --
        useful for testing agent integrations). `profile` only applies to
        the synthetic backend ("training"/"inference"/"idle").
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
        """Run the evasion-robustness benchmark against synthetic telemetry.

        Returns per-profile accuracy under clean and evasion-obfuscated
        conditions. Explicitly synthetic -- not comparable to any
        real-hardware benchmark, see the returned "note" field.
        """
        from workloadtruth.benchmark import run_benchmark as _run_benchmark

        return _run_benchmark(trials_per_cell=trials, window_size=window).to_dict()

    @app.tool()
    def verify_audit_log(log_file: str = str(DEFAULT_LOG_PATH)) -> dict[str, Any]:
        """Verify the hash chain of the local audit log has not been tampered with."""
        is_valid, message, count = verify_chain(Path(log_file))
        return {"valid": is_valid, "message": message, "entries": count}

    return app


def run_server(default_backend: str = "nvml") -> None:
    app = build_app(default_backend=default_backend)
    app.run()
