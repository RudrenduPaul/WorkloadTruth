# Security Policy

## Reporting a vulnerability

Please report security issues privately via [GitHub Security
Advisories](https://github.com/RudrenduPaul/WorkloadTruth/security/advisories/new)
rather than a public issue. Include:

- A description of the vulnerability and its impact
- Steps to reproduce
- The affected version(s)

You should receive an initial response within 5 business days. We'll work
with you to confirm the issue, assess severity, and coordinate a fix and
disclosure timeline.

## Scope

WorkloadTruth reads GPU telemetry (utilization, memory, power) and
classifies it locally. It does not inspect workload contents (model
weights, training data, prompts, or completions). In scope for security
reports:

- The CLI, its telemetry backends, and the classifier
- The hash-chained audit log (`workloadtruth.log.jsonl`) and its integrity
  guarantees
- The MCP server (`workloadtruth mcp`)
- The npm launcher shim

## Supported versions

Only the latest published release on PyPI/npm receives security fixes.
