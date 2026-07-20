# Changelog

## 0.1.3 -- 2026-07-20 (npm only)

npm's published package had a thin, scoped-down README instead of the
full documentation (FAQ, benchmark, comparison table, CLI reference)
that ships to PyPI and GitHub -- a real completeness gap, not just a
style choice. npm-shim/README.md now is the exact same file as the
root README.md, single source of truth. No code changes.

## 0.1.2 -- 2026-07-19

Metadata-only release. Adds the second co-author (Sourav Nandy) to PyPI's
`authors`/`project.urls`, matching this maintainer's other published
`-cli` packages. No code changes.

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
