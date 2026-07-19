import json

from workloadtruth.audit_log import (
    GENESIS_HASH,
    append_entry,
    build_entry,
    last_hash,
    verify_chain,
)


def _make_entry(prev_hash, timestamp=1.0):
    return build_entry(
        timestamp=timestamp,
        gpu_index=0,
        workload_type="TRAINING",
        confidence=0.9,
        reasons=["test reason"],
        features={"avg_gpu_util_pct": 88.0},
        prev_hash=prev_hash,
    )


def test_verify_chain_on_missing_file(tmp_path):
    log_path = tmp_path / "workloadtruth.log.jsonl"
    is_valid, message, count = verify_chain(log_path)
    assert is_valid is True
    assert count == 0


def test_append_and_verify_chain(tmp_path):
    log_path = tmp_path / "workloadtruth.log.jsonl"

    prev = last_hash(log_path)
    assert prev == GENESIS_HASH

    entry1 = _make_entry(prev, timestamp=1.0)
    append_entry(log_path, entry1)

    prev2 = last_hash(log_path)
    assert prev2 == entry1.entry_hash

    entry2 = _make_entry(prev2, timestamp=2.0)
    append_entry(log_path, entry2)

    is_valid, message, count = verify_chain(log_path)
    assert is_valid is True
    assert count == 2


def test_tampered_entry_is_detected(tmp_path):
    log_path = tmp_path / "workloadtruth.log.jsonl"
    entry1 = _make_entry(GENESIS_HASH, timestamp=1.0)
    append_entry(log_path, entry1)

    lines = log_path.read_text().splitlines()
    record = json.loads(lines[0])
    record["confidence"] = 0.01  # tamper with the content, keep the old hash
    log_path.write_text(json.dumps(record) + "\n")

    is_valid, message, count = verify_chain(log_path)
    assert is_valid is False
    assert "entry_hash mismatch" in message


def test_broken_chain_link_is_detected(tmp_path):
    log_path = tmp_path / "workloadtruth.log.jsonl"
    entry1 = _make_entry(GENESIS_HASH, timestamp=1.0)
    append_entry(log_path, entry1)

    # Append a second entry whose prev_hash doesn't match entry1's hash.
    bogus_entry = _make_entry("f" * 64, timestamp=2.0)
    append_entry(log_path, bogus_entry)

    is_valid, message, count = verify_chain(log_path)
    assert is_valid is False
    assert "prev_hash mismatch" in message
