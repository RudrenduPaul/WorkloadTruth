# Changelog

## 0.1.1 -- 2026-07-19

Docs-only release. README gets a real demo GIF, a table of contents, a
dedicated "What is WorkloadTruth" section, and 3 more FAQ entries
(comparison, platform compatibility, licensing). No code changes.

## 0.1.0 -- 2026-07-19

Initial release.

- `workloadtruth classify` -- one-shot GPU workload classification
  (TRAINING / INFERENCE / IDLE) from telemetry.
- `workloadtruth watch` -- continuous classification with a hash-chained
  local audit log (`workloadtruth.log.jsonl`).
- `workloadtruth benchmark` -- evasion-robustness benchmark against
  documented synthetic telemetry traces.
- `workloadtruth verify-log` -- verify the audit log's hash chain hasn't
  been tampered with.
- `workloadtruth mcp` -- MCP server exposing classify/benchmark/verify-log
  as agent-callable tools.
- Rule-based classifier only (transparent, documented thresholds). No ML
  classifier shipped yet -- see README's "How classification works."
- NVML backend (real NVIDIA hardware, `nvml` extra) and synthetic backend
  (no GPU required, used for tests and the benchmark suite).
- `.well-known/agent.json` for A2A agent discovery.
- Published to PyPI and npm as `workloadtruth-cli`.
