"""Telemetry backend interface.

Every GPU vendor/data-source WorkloadTruth supports implements this one
interface. The classifier and CLI only ever depend on TelemetryBackend, never
on a specific vendor's SDK -- this is what lets a new backend (AMD ROCm,
Intel Level Zero, a recorded trace file) be added without touching
classification logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from workloadtruth.types import TelemetrySample


class TelemetryBackend(ABC):
    """Yields TelemetrySample readings for one or more GPUs."""

    @abstractmethod
    def device_count(self) -> int:
        """Number of GPUs this backend can read from."""

    @abstractmethod
    def sample(self, gpu_index: int) -> TelemetrySample:
        """Take one instantaneous reading from the given GPU."""

    def sample_window(
        self, gpu_index: int, count: int, interval_seconds: float
    ) -> Iterator[TelemetrySample]:
        """Take `count` readings, `interval_seconds` apart.

        Backends that already produce a fixed trace (e.g. SyntheticBackend in
        replay mode) may override this for determinism instead of sleeping.
        """
        import time

        for i in range(count):
            yield self.sample(gpu_index)
            if i < count - 1:
                time.sleep(interval_seconds)

    def close(self) -> None:
        """Release any backend resources. Default: no-op."""
        return None
