from typing import Any

from workloadtruth.telemetry.base import TelemetryBackend
from workloadtruth.telemetry.synthetic_backend import SyntheticBackend

__all__ = ["TelemetryBackend", "SyntheticBackend", "get_backend"]


def get_backend(name: str, **kwargs: Any) -> TelemetryBackend:
    """Resolve a telemetry backend by name.

    Adding a new GPU vendor (AMD ROCm, Intel Level Zero, etc.) means
    implementing TelemetryBackend and registering it here -- the classifier
    and CLI never need to change.
    """
    if name == "synthetic":
        return SyntheticBackend(**kwargs)
    if name == "nvml":
        from workloadtruth.telemetry.nvml_backend import NVMLBackend

        return NVMLBackend(**kwargs)
    raise ValueError(f"Unknown telemetry backend: {name!r}. Expected 'synthetic' or 'nvml'.")
