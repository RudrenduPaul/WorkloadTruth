"""Real NVIDIA telemetry backend, via NVML (pynvml / nvidia-ml-py).

Requires the `nvml` extra (`pip install "workloadtruth-cli[nvml]"`) and an
NVIDIA driver on the host. Not exercised in CI or unit tests -- there is no
NVIDIA GPU in this project's build/test environment, so this module is
validated manually against real hardware, not covered by the test-coverage
gate (see pyproject.toml's `[tool.coverage.run]` omit list).
"""

from __future__ import annotations

import time

from workloadtruth.telemetry.base import TelemetryBackend
from workloadtruth.types import TelemetrySample

try:
    import pynvml
except ImportError as exc:  # pragma: no cover - exercised only without the extra installed
    raise ImportError(
        "The NVML backend requires the 'nvml' extra: pip install \"workloadtruth-cli[nvml]\""
    ) from exc


class NVMLBackend(TelemetryBackend):
    def __init__(self) -> None:
        pynvml.nvmlInit()
        self._device_count: int = int(pynvml.nvmlDeviceGetCount())

    def device_count(self) -> int:
        return self._device_count

    def sample(self, gpu_index: int) -> TelemetrySample:
        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        power_mw = pynvml.nvmlDeviceGetPowerUsage(handle)
        try:
            processes = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
            process_count = len(processes)
        except pynvml.NVMLError:
            process_count = 0

        return TelemetrySample(
            timestamp=time.time(),
            gpu_index=gpu_index,
            gpu_utilization_pct=float(util.gpu),
            memory_utilization_pct=float(util.memory),
            memory_used_mib=mem.used / (1024 * 1024),
            memory_total_mib=mem.total / (1024 * 1024),
            power_draw_watts=power_mw / 1000.0,
            process_count=process_count,
        )

    def close(self) -> None:
        pynvml.nvmlShutdown()
