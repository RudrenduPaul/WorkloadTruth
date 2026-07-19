#!/usr/bin/env node
"use strict";

/**
 * npm launcher for the workloadtruth-cli PyPI package.
 *
 * WorkloadTruth's implementation is Python (NVML/pynvml is the mature,
 * official way to read NVIDIA GPU telemetry). This npm package exists so
 * `npx workloadtruth-cli` works for npm-first agent tooling, but it does
 * not bundle a Python reimplementation -- it locates and execs the real
 * `workloadtruth` binary installed from PyPI. This is a deliberate
 * cross-registry tradeoff, documented in the README, not an oversight.
 */

const { spawnSync } = require("node:child_process");

function findPythonCli() {
  const probe = process.platform === "win32" ? "where" : "which";
  const result = spawnSync(probe, ["workloadtruth"], { encoding: "utf8" });
  if (result.status === 0 && result.stdout.trim()) {
    return result.stdout.trim().split(/\r?\n/)[0];
  }
  return null;
}

function main() {
  const binPath = findPythonCli();

  if (!binPath) {
    process.stderr.write(
      [
        "workloadtruth-cli (npm) is a launcher for the Python implementation.",
        "",
        "The 'workloadtruth' command was not found on your PATH. Install it with:",
        "",
        '  pip install "workloadtruth-cli[nvml]"   # real NVIDIA GPU telemetry',
        '  pip install workloadtruth-cli           # synthetic backend only, no GPU required',
        "",
        "Then re-run this command.",
        "",
      ].join("\n")
    );
    process.exit(1);
  }

  const args = process.argv.slice(2);
  const result = spawnSync(binPath, args, { stdio: "inherit" });

  if (result.error) {
    process.stderr.write(`Failed to run workloadtruth: ${result.error.message}\n`);
    process.exit(1);
  }

  process.exit(result.status === null ? 1 : result.status);
}

main();
