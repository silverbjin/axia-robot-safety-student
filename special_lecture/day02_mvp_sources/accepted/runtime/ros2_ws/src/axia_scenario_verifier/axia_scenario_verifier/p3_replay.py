"""Validate normalized, hash-linked offline replay; no physical provenance claims."""
import hashlib
import json
import math
from pathlib import Path


def read_replay(directory: Path, scenario: dict) -> list[dict]:
    """Raw JSONL equality + SHA is an integrity check, NOT proof of real L2/L3."""
    base = directory.resolve()
    if not base.is_dir():
        raise ValueError("replay directory missing")
    sid = scenario["scenario_id"]
    meta_path = (base / (sid + ".json")).resolve()
    if not meta_path.is_relative_to(base) or not meta_path.is_file():
        raise ValueError("missing replay manifest")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if (meta.get("schema") != "axia_p3_replay_v1" or meta.get("scenario_id") != sid
            or meta.get("source_sha") != scenario["source_sha"]):
        raise ValueError("replay provenance mismatch")
    raw = meta.get("raw_path")
    if not isinstance(raw, str) or not raw.endswith(".jsonl") or Path(raw).is_absolute():
        raise ValueError("invalid raw JSONL path")
    path = (base / raw).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        raise ValueError("raw JSONL missing or outside replay directory")
    data = path.read_bytes()
    actual_sha = hashlib.sha256(data).hexdigest()
    if meta.get("raw_sha256") != actual_sha:
        raise ValueError("raw SHA256 mismatch")
    events = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    if not events:
        raise ValueError("empty replay")
    last = -math.inf
    for event in events:
        if not isinstance(event, dict) or not isinstance(event.get("event"), str):
            raise ValueError("invalid replay event")
        t = event.get("t_sec")
        if type(t) not in (int, float) or not math.isfinite(t) or t < 0 or t <= last:
            raise ValueError("non-increasing or invalid replay timestamp")
        last = t
    return events


def check_sequence(sid: str, events: list[dict]) -> tuple[bool, str]:
    names = [e["event"] for e in events]
    if "AUTO_RESUME" in names or "UNAPPROVED_GOAL" in names:
        return False, "UNAUTHORIZED_MOTION"
    expected = {
        "S01": ("OWNER_GOAL_APPROVED", "TF_READY", "ODOM_MOVING", "NAV2_GOAL_SUCCEEDED"),
        "S02": ("CLEAR", "SLOW", "STOP"),
        "S03": ("OWNER_FAULT_APPROVED", "SCAN_FAULT", "DIAG_ERROR", "SW_STOP_LATCHED"),
        "S05": ("SW_STOP_LATCHED", "REARM_REJECTED", "RESET_OK", "OWNER_REARM_APPROVED", "REARM_OK", "NO_AUTO_RESUME"),
    }.get(sid)
    if not expected:
        return False, "NO_REPLAY_ORACLE"
    positions = [next((i for i, e in enumerate(names) if e == key), -1) for key in expected]
    if -1 in positions or positions != sorted(positions) or len(set(positions)) != len(positions):
        return False, "MISSING_OR_OUT_OF_ORDER_EVENT"
    if sid == "S01" and ("UNEXPECTED_STOP" in names or "NAV2_GOAL_FAILED" in names):
        return False, "GOAL_OR_STOP_FAILURE"
    if sid == "S02":
        stages = [events[i] for i in positions]
        vals = [s.get("scan_front_m") for s in stages]
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in vals):
            return False, "SENSOR_MEASUREMENT_MISSING"
        if not vals[0] > vals[1] > vals[2] or stages[-1].get("cmd_zero") is not True:
            return False, "STOP_MEASUREMENT_UNPROVEN"
    return True, "L0_REPLAY_SEQUENCE_ONLY"
