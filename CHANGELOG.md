# Changelog

## 0.2.0 -- 2026-09-24

- Dependencies upgraded to the latest releases. The `mcp` optional extra now requires
  `mcp>=2.0.0` (previously capped below 2.0.0) and the MCP server is migrated to the
  mcp 2 API.
- Support floor changed: Python 3.9 is dropped, Python 3.10 or newer is now required.
- The npm launcher and the PyPI package both move to 0.2.0, and the `server.json`
  (previously 0.1.4) and `.well-known/agent.json` versions are synced to it.
- npm publishing moves to npm Trusted Publishing (OIDC), so no long-lived npm token is
  used. PyPI already publishes through Trusted Publishing.

## 0.1.5 -- 2026-08-11 (PyPI/GitHub), 2026-08-16 (npm)

PyPI/GitHub reached 0.1.5 first (2026-08-11): adds `server.json` for the Official MCP
Registry and improves MCP tool description quality. npm-shim caught up five days later
(2026-08-16): syncs its README to the root README's benchmark data, prior-research
framing, and honest scope disclosures, and adds the Product Hunt launch badge. No
functional CLI changes.

## 0.1.4 -- 2026-08-10 (PyPI/GitHub), 2026-07-21 (npm)

npm-shim reached 0.1.4 first (2026-07-21): adds Sourav Nandy as an npm contributor,
matching PyPI's existing `authors` listing, and republishes the shim to pick up the
fix. PyPI/GitHub caught up about three weeks later (2026-08-10): caps the `mcp`
optional dependency below 2.0.0 to avoid a breaking upstream API change, fixes
`requires-python` to match the `mcp` dependency's own floor, credits Sourav Nandy in
LICENSE, adds a CodeQL security-scanning workflow, adds the missing npm badge and
removes stale v0.1 version references from the README, refreshes the README's demo
GIFs, restructures the README for searchability, and documents the MCP server. No
functional CLI changes.

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
