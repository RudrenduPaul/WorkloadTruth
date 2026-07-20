# WorkloadTruth

**Classify a GPU workload as `TRAINING`, `INFERENCE`, or `IDLE` from telemetry alone. No code changes to the workload, no self-reported job labels.**

[![CI](https://github.com/RudrenduPaul/WorkloadTruth/actions/workflows/ci.yml/badge.svg)](https://github.com/RudrenduPaul/WorkloadTruth/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/workloadtruth-cli)](https://pypi.org/project/workloadtruth-cli/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](pyproject.toml)

![WorkloadTruth classifying a synthetic training workload, then running the evasion-robustness benchmark](https://raw.githubusercontent.com/RudrenduPaul/WorkloadTruth/main/docs/demo.gif)

Every GPU scheduler in common use today, including [run:ai](https://docs.run.ai/v2.20/Researcher/workloads/inference/inference-overview/), Slurm, and Kubernetes GPU operators, asks you to *declare* whether a job is training or inference at submission time. None of them check. WorkloadTruth reads GPU telemetry (utilization, memory pattern, power draw) and answers the question independently, so a mislabeled or misbehaving job doesn't go unnoticed.

## Table of contents

- [Quick summary](#quick-summary)
- [Install](#install)
- [Quickstart](#quickstart)
- [How classification works](#how-classification-works)
- [Benchmark](#benchmark)
- [CLI reference](#cli-reference)
- [Agent-native (MCP + A2A)](#agent-native-mcp--a2a)
- [Audit log](#audit-log)
- [Why two registries](#why-two-registries)
- [Comparison](#comparison)
- [What is WorkloadTruth, and why does it exist](#what-is-workloadtruth-and-why-does-it-exist)
- [Relationship to prior research](#relationship-to-prior-research)
- [What WorkloadTruth is not](#what-workloadtruth-is-not)
- [FAQ](#faq)

## Quick summary

- **Install:** `pip install "workloadtruth-cli[nvml]"` for real GPU access, or `pip install workloadtruth-cli` to try it with the synthetic backend, no GPU needed
- **Use it for:** catching cost-misallocated GPU jobs (a job billed as low-priority "inference" that's actually running full training) and unauthorized workload changes (an inference endpoint that starts training on live traffic without sign-off)
- **What it's not:** a compliance or regulatory-audit tool. No regulation currently requires this kind of monitoring, see [What WorkloadTruth is not](#what-workloadtruth-is-not) below
- **Prior art:** builds on and cites [arXiv:2606.19262](https://arxiv.org/abs/2606.19262) (ICML 2026), see [Relationship to prior research](#relationship-to-prior-research)

## Install

```bash
# Real NVIDIA GPU telemetry (requires an NVIDIA driver on the host)
pip install "workloadtruth-cli[nvml]"

# Try it without a GPU, using the synthetic backend
pip install workloadtruth-cli

# npm launcher (thin wrapper around the PyPI package, see "Why two registries")
npx workloadtruth-cli --help
```

## Quickstart

```bash
# No GPU required. Classify a synthetic "training" telemetry trace.
$ workloadtruth classify --backend synthetic --profile training --samples 10 --interval 0
workload_type : TRAINING
confidence    : 1.00
gpu_index     : 0
samples       : 10 over 9.0s
reasons:
  - avg GPU utilization 87.8% >= training threshold 65.0%
  - low GPU utilization variance (std=3.4) <= training ceiling 15.0
  - memory growing 120.0 MiB/sample >= training threshold 5.0
  - low power-draw variance (std=9.4W) <= training ceiling 25.0W

# Real hardware
$ workloadtruth classify --backend nvml --samples 10 --interval 1 --json
```

`--json` on every command switches to machine-readable output for scripts and agents.

## How classification works

WorkloadTruth ships a **rule-based classifier only** in v0.1: a set of documented, inspectable thresholds over four features extracted from a telemetry window (average and variance of GPU utilization, memory-growth slope, average and variance of power draw). Every threshold lives as a named constant in [`src/workloadtruth/classifier/rules.py`](src/workloadtruth/classifier/rules.py) with a comment explaining its intuition. Nothing is a black box.

`--experimental` (an ML-based classifier) is present as a flag but fails loudly with an explanation rather than shipping a fake result. [arXiv:2606.19262](https://arxiv.org/abs/2606.19262)'s trained model and dataset were never published, and this project has no NVIDIA GPU in its build environment to collect real training data. An ML classifier ships here only once it's trained on a real, disclosed dataset and independently shown to beat the rule-based baseline, not before.

## Benchmark

`workloadtruth benchmark` measures the classifier's accuracy against documented synthetic GPU telemetry traces (see [`synthetic_backend.py`](src/workloadtruth/telemetry/synthetic_backend.py) for the exact profile parameters), both clean and under a deliberate evasion transform that mimics an operator disguising a training job as inference (capping utilization swings, flattening memory growth, injecting artificial idle gaps).

**This is run on synthetic data, not live NVIDIA hardware, so it is not directly comparable to arXiv:2606.19262's real-hardware numbers.** Both are reported below, side by side, never blended into one figure.

| | arXiv:2606.19262 (real hardware, NVML) | WorkloadTruth v0.1 (synthetic traces, 300 trials/cell) |
|---|---|---|
| Clean accuracy | 98.2% | 100.0% |
| Evasion accuracy | 43-87% | 66.7% overall |

The overall evasion number hides the real finding. Broken out by workload type, WorkloadTruth's rule-based classifier is currently **completely fooled on evasive training workloads (0% accuracy)**, while staying accurate on evasive inference and idle traces (100% each). Capping GPU utilization alone is enough to make a training job read as inference to this classifier today.

| Profile | Clean accuracy | Evasion accuracy |
|---|---|---|
| Training | 100.0% | **0.0%** |
| Inference | 100.0% | 100.0% |
| Idle | 100.0% | 100.0% |

This is the concrete, disclosed gap the benchmark suite exists to surface and track, not a footnote. A rule-based classifier that only looks at utilization variance is trivially evadable. Closing this gap, through multi-signal fusion or a real trained classifier once data exists, is the roadmap, not a solved problem. Reproduce it yourself:

```bash
workloadtruth benchmark --trials 300 --window 30 --json
```

## CLI reference

```
$ workloadtruth --help
Usage: workloadtruth [OPTIONS] COMMAND [ARGS]...

  Classify a GPU workload as INFERENCE, TRAINING, or IDLE from telemetry
  alone.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  benchmark   Run the evasion-robustness benchmark against synthetic...
  classify    One-shot classification of the current GPU workload.
  mcp         Start an MCP server exposing classify/benchmark/verify-log...
  verify-log  Verify the hash chain of a local audit log has not been...
  watch       Continuously classify and append hash-chained entries to...
```

| Command | Purpose |
|---|---|
| `classify` | One-shot classification. `--backend synthetic\|nvml`, `--json` for machine-readable output. |
| `watch` | Continuous classification; appends a hash-chained entry to a local audit log on every window. |
| `benchmark` | Runs the evasion-robustness benchmark (see above). |
| `verify-log` | Re-derives every audit-log entry's hash and confirms the chain hasn't been tampered with. |
| `mcp` | Starts an MCP server (stdio) exposing `classify_workload`, `run_benchmark`, `verify_audit_log` as agent-callable tools. Requires `pip install "workloadtruth-cli[mcp]"` on Python 3.10+ (see below). |

Every command supports `--json`. Full flag reference: `workloadtruth <command> --help`.

## Agent-native (MCP + A2A)

```bash
pip install "workloadtruth-cli[mcp]"
workloadtruth mcp
```

The `mcp` package itself requires Python 3.10+, stricter than WorkloadTruth's own 3.9 floor. Every other feature (`classify`, `watch`, `benchmark`, `verify-log`) works on Python 3.9.

Exposes three tools over stdio MCP: `classify_workload`, `run_benchmark`, `verify_audit_log`. A `.well-known/agent.json` manifest is shipped at the repo root for A2A-style discovery, listing both the CLI and MCP interfaces and the packages that provide them.

## Audit log

`workloadtruth watch` appends a hash-chained entry to `workloadtruth.log.jsonl` on every classification window. Each entry's hash covers its own content plus the previous entry's hash, so any edit, reorder, or deletion after the fact breaks the chain from that point forward. `workloadtruth verify-log` re-derives every hash and reports the first broken link, if any.

This proves what was classified, when, and that the local record hasn't been silently altered afterward. **It does not prove the classification itself was correct**, and it is not evidence of regulatory compliance. See below.

## Why two registries

WorkloadTruth's implementation is Python. NVML access (`pynvml`/`nvidia-ml-py`) is the mature, official way to read NVIDIA GPU telemetry, and it's also what the closest prior art ([arXiv:2606.19262](https://arxiv.org/abs/2606.19262)) uses. The npm package (`workloadtruth-cli`) is a thin launcher, not a reimplementation. It locates and execs the real `workloadtruth` binary installed from PyPI, so `npx workloadtruth-cli` works for npm-first agent tooling without duplicating the classifier in two languages.

## Comparison

| | WorkloadTruth | NVIDIA DCGM / `dcgm-exporter` | run:ai | Weights & Biases |
|---|---|---|---|---|
| Reads GPU telemetry | Yes (via NVML) | Yes (source) | Yes | Yes |
| Classifies workload type automatically | **Yes** | No, exposes raw metrics only | No, workload type is user-declared at job submission | No, training-run-scoped by design, no classification |
| Local, hash-chained audit trail | Yes | No | No | No |
| Evasion-robustness benchmark | Yes (documented, reproducible) | N/A | N/A | N/A |
| Requires an NVIDIA GPU | Only for the `nvml` backend; the `synthetic` backend works without one | Yes | Yes | No (general system metrics) |

Checked directly against each project's own documentation: [DCGM exporter docs](https://docs.nvidia.com/datacenter/dcgm/latest/gpu-telemetry/dcgm-exporter.html), [run:ai inference overview](https://docs.run.ai/v2.20/Researcher/workloads/inference/inference-overview/), [W&B system metrics docs](https://docs.wandb.ai/models/ref/python/experiments/system-metrics). None of these classify workload type from telemetry alone. That gap is what WorkloadTruth fills.

## What is WorkloadTruth, and why does it exist

WorkloadTruth is an open-source command-line tool and MCP server that classifies a running GPU workload as `TRAINING`, `INFERENCE`, or `IDLE` using only GPU-level telemetry (utilization, memory pattern, power draw), with no changes to the workload's own code and no reliance on a self-reported job label.

It exists because every mainstream GPU scheduler asks the job's owner to declare its type at submission time and never checks that declaration against what the hardware is actually doing. That gap has two real consequences: cost misallocation (a job scheduled at low-priority "inference" pricing that is actually running full training) and unauthorized workload changes (an inference endpoint that quietly starts training on live traffic). WorkloadTruth closes that verification gap today, and doubles as the first open, installable implementation of a real academic research thread on verifying AI training runs from hardware telemetry (see below).

## Relationship to prior research

WorkloadTruth's core technique, classifying training vs. non-training GPU activity from telemetry, is not novel. It's the direct application of a real, active research thread:

1. Yonadav Shavit (Harvard), [*"What does it take to catch a Chinchilla?"*](https://arxiv.org/abs/2303.11341) (2023): proposed hardware-level "training transcripts" for verifying large training runs.
2. GovAI, [*"Computing Power and the Governance of AI"*](https://www.governance.ai/analysis/computing-power-and-the-governance-of-ai) (2024): surveyed compute-governance mechanisms, explicitly framed as exploratory, not endorsed policy.
3. [*"Hardware-Enabled Mechanisms for Verifying Responsible AI Development"*](https://arxiv.org/abs/2505.03742) (2025): hardware-security researchers proposing on-chip attestation.
4. Rahman & Tajdari, [*"Detecting Hidden ML Training With Zero-Overhead Telemetry"*](https://arxiv.org/abs/2606.19262) (ICML 2026 Technical AI Governance workshop): a working NVML-telemetry classifier, 98.2% accurate on unobfuscated workloads, the direct prior art for this project's core classification technique.

**What WorkloadTruth adds:** as of this project's own research (2026-07-19), no open-source, installable implementation of this research thread existed, only academic prototypes. WorkloadTruth is that packaging: a real CLI, an MCP server, a hash-chained audit log, and a reproducible evasion-robustness benchmark, built in the open. It does not claim to improve on the paper's classification technique. See the benchmark section above: the current rule-based classifier is considerably more evadable than the paper's ML approach on the one axis it measures.

## What WorkloadTruth is not

- **Not a compliance or regulatory-audit tool.** No law currently requires inference/training classification or reporting. Any future claim otherwise will name the specific enacted regulation; none exists as of this writing.
- **Not a content inspector.** WorkloadTruth reads GPU-level signals only (utilization, memory, power). It never inspects model weights, training data, prompts, or completions.
- **Not proof of "compliant" or "safe" operation.** The audit log proves what was classified and when, and that the record wasn't altered afterward, not that the classification was correct or that any policy was followed.

## FAQ

**Does this need an NVIDIA GPU?**
Only for the `nvml` backend. `--backend synthetic` runs the full classifier and CLI against documented synthetic traces, no GPU required. Useful for trying the tool or for CI.

**Can it classify AMD or Intel GPU workloads?**
Not in v0.1. The telemetry layer is a pluggable interface (`TelemetryBackend`) specifically so a new vendor backend (AMD ROCm, Intel Level Zero) can be added without touching the classifier. See [CONTRIBUTING.md](CONTRIBUTING.md).

**Is the classifier accurate enough to bill or penalize someone based on its output?**
Not yet, and the benchmark section above is the honest reason why: 0% accuracy on evasive training workloads today. Treat `workload_type` as a signal to investigate, not a verdict.

**Why not just use the ML classifier from the paper?**
Its trained weights and dataset were never published. Reimplementing an ML classifier without real training data would produce an unvalidated accuracy claim, not a measured one. See [How classification works](#how-classification-works).

**How is this different from run:ai or NVIDIA DCGM?**
run:ai and DCGM both expose or use GPU telemetry, but neither classifies workload type from that telemetry. run:ai relies entirely on the label the job's owner declares at submission; DCGM just exposes raw utilization and memory metrics for something else to interpret. WorkloadTruth is the layer that actually looks at the telemetry and answers the question. See the [comparison table](#comparison).

**Does this work on Windows, macOS, and Linux?**
The `synthetic` backend runs anywhere Python 3.9+ runs, including this project's own macOS build environment (which has no NVIDIA GPU). The `nvml` backend requires an NVIDIA GPU and driver, which in practice means Linux or Windows with NVIDIA hardware; NVML itself is not available on macOS.

**What license is this under, and can I use it commercially?**
Apache 2.0. Commercial use, modification, and redistribution are all permitted under its terms; see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security issues: see [SECURITY.md](SECURITY.md).

## License

[Apache 2.0](LICENSE)
