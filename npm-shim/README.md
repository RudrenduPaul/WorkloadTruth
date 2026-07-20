# workloadtruth-cli

**Classify a GPU workload as `TRAINING`, `INFERENCE`, or `IDLE` from telemetry alone. No code changes to the workload, no self-reported job labels.**

![WorkloadTruth classifying a synthetic training workload, then running the evasion-robustness benchmark](https://raw.githubusercontent.com/RudrenduPaul/WorkloadTruth/main/docs/demo.gif)

This npm package is a thin launcher, not a reimplementation. WorkloadTruth's actual classifier is Python (NVML access via `pynvml`/`nvidia-ml-py` is the mature, official way to read NVIDIA GPU telemetry). This package locates and execs the real `workloadtruth` binary installed from PyPI, so `npx workloadtruth-cli` works for npm-first agent tooling without duplicating the classifier in two languages.

## Install

```bash
# 1. Install the real implementation from PyPI
pip install "workloadtruth-cli[nvml]"   # real NVIDIA GPU telemetry
# or: pip install workloadtruth-cli     # synthetic backend only, no GPU required

# 2. Use the npm launcher
npx workloadtruth-cli classify --backend synthetic --profile training --samples 10 --interval 0
```

If step 1 is skipped, the launcher prints clear instructions instead of failing silently.

## Why does a GPU-telemetry classifier need this

Every mainstream GPU scheduler (run:ai, Slurm, Kubernetes GPU operators) asks a job's owner to *declare* whether it's training or inference at submission time. None of them check. WorkloadTruth reads GPU telemetry (utilization, memory pattern, power draw) and answers the question independently, catching cost-misallocated or unauthorized workload changes today, and doubling as the first open, installable implementation of a real academic research thread on verifying AI training runs from hardware telemetry (arXiv:2606.19262, ICML 2026, cited as direct prior art).

## Full documentation

CLI reference, the evasion-robustness benchmark (including the honest 0% accuracy gap it found), the MCP server for agent tool-calling, and the FAQ all live in the main repo:

**[github.com/RudrenduPaul/WorkloadTruth](https://github.com/RudrenduPaul/WorkloadTruth)**

## License

[Apache 2.0](https://github.com/RudrenduPaul/WorkloadTruth/blob/main/LICENSE)
