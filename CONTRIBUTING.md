# Contributing to WorkloadTruth

## Setup

```bash
git clone https://github.com/RudrenduPaul/WorkloadTruth.git
cd WorkloadTruth
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,mcp]"
```

## Before you open a PR

```bash
ruff check .
ruff format --check .
mypy src/workloadtruth
pytest --cov=workloadtruth --cov-report=term-missing --cov-fail-under=80
```

All four must pass. CI runs the same checks.

## Adding a new telemetry backend

WorkloadTruth's classifier and CLI depend only on the `TelemetryBackend`
interface in `src/workloadtruth/telemetry/base.py`, never on a specific
vendor SDK. To add a new GPU vendor (AMD ROCm, Intel Level Zero, a recorded
trace file):

1. Implement `TelemetryBackend` in a new module under `telemetry/`.
2. Register it in `telemetry/__init__.py`'s `get_backend()`.
3. Do not modify `classifier/rules.py`. If your backend produces
   `TelemetrySample` objects, the classifier already works with it.

## Changing the classifier's thresholds

The rule-based classifier in `classifier/rules.py` is deliberately
transparent: every threshold is a named module-level constant with a
comment explaining its intuition. If you change a threshold:

1. Re-run `workloadtruth benchmark` before and after your change and
   include both results in your PR description.
2. Update the README's benchmark table if the numbers change.
3. Never claim an accuracy number that wasn't produced by an actual
   `workloadtruth benchmark` run. Don't guess, measure.

## What this project will not accept

- Telemetry collection that reads workload *contents* (model weights,
  training data, prompts, completions). WorkloadTruth classifies workload
  *type* from GPU-level signals only. See `SECURITY.md`'s scope section.
- Any claim of regulatory compliance or "audit-ready" certification. No
  such regulation currently exists. See the README's "What WorkloadTruth
  is not" section.
