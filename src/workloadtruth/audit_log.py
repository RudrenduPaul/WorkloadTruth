"""Hash-chained local audit log.

Every `workloadtruth watch` classification event is appended to a local
JSONL file as a hash-chained entry: each entry's hash covers its own content
plus the previous entry's hash, so any edit, reorder, or deletion of a past
entry breaks the chain from that point forward and is detected by
`verify_chain`. This mirrors the audit-log pattern already shipped in this
portfolio's `auditreach`/`tokentrust` CLIs.

This proves what was classified and when, and that the local record hasn't
been silently altered after the fact. It does NOT prove the classification
itself was correct, and it does NOT constitute regulatory compliance
evidence -- no regulation currently requires this. See the README's "What
WorkloadTruth is not" section.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

GENESIS_HASH = "0" * 64


def _canonical_json(obj: dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class AuditLogEntry:
    timestamp: float
    gpu_index: int
    workload_type: str
    confidence: float
    reasons: list[str]
    features: dict[str, float]
    prev_hash: str
    entry_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _compute_entry_hash(payload: dict[str, Any], prev_hash: str) -> str:
    body = _canonical_json(payload) + prev_hash
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def build_entry(
    *,
    timestamp: float,
    gpu_index: int,
    workload_type: str,
    confidence: float,
    reasons: list[str],
    features: dict[str, float],
    prev_hash: str,
) -> AuditLogEntry:
    rounded_confidence = round(confidence, 4)
    rounded_features = {k: round(v, 4) for k, v in features.items()}
    payload: dict[str, Any] = {
        "timestamp": timestamp,
        "gpu_index": gpu_index,
        "workload_type": workload_type,
        "confidence": rounded_confidence,
        "reasons": reasons,
        "features": rounded_features,
    }
    entry_hash = _compute_entry_hash(payload, prev_hash)
    return AuditLogEntry(
        timestamp=timestamp,
        gpu_index=gpu_index,
        workload_type=workload_type,
        confidence=rounded_confidence,
        reasons=reasons,
        features=rounded_features,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
    )


def last_hash(log_path: Path) -> str:
    if not log_path.exists():
        return GENESIS_HASH
    last_line = None
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last_line = line
    if last_line is None:
        return GENESIS_HASH
    return str(json.loads(last_line)["entry_hash"])


def append_entry(log_path: Path, entry: AuditLogEntry) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(_canonical_json(entry.to_dict()) + "\n")


def verify_chain(log_path: Path) -> tuple[bool, str, int]:
    """Re-derive every entry's hash and check chain linkage.

    Returns (is_valid, message, entries_checked).
    """
    if not log_path.exists():
        return True, "log file does not exist yet -- nothing to verify", 0

    prev_hash = GENESIS_HASH
    count = 0
    with log_path.open("r", encoding="utf-8") as f:
        for line_number, raw_line in enumerate(f, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                return False, f"line {line_number}: invalid JSON ({exc})", count

            claimed_hash = record.get("entry_hash")
            claimed_prev = record.get("prev_hash")
            if claimed_prev != prev_hash:
                return (
                    False,
                    f"line {line_number}: prev_hash mismatch "
                    f"(expected {prev_hash}, found {claimed_prev})",
                    count,
                )

            payload = {k: v for k, v in record.items() if k not in ("prev_hash", "entry_hash")}
            recomputed = _compute_entry_hash(payload, prev_hash)
            if recomputed != claimed_hash:
                return (
                    False,
                    f"line {line_number}: entry_hash mismatch -- content was modified "
                    f"after being written (expected {recomputed}, found {claimed_hash})",
                    count,
                )

            prev_hash = claimed_hash
            count += 1

    return True, f"chain verified, {count} entries", count
