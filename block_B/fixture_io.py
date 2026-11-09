"""Block B synthetic-data reader. Adapted from the Block A checksum *pattern*.

Pure Python; no ROS graph, velocity publisher, model or hardware dependency.
SHA256SUMS detects tampering, but is not a provenance/authenticity proof.
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import re
from pathlib import Path

FILES = ("detections.csv", "depth_samples.json", "scenario_manifest.json")
SOURCE = "SYNTHETIC_COURSE_FIXTURE"


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-standard JSON constant: {value}")


def load_fixtures(folder: str | Path) -> tuple[list[dict[str, str]], dict]:
    """Return (raw CSV detections, depth JSON); fail closed for bad schema/hash."""
    root = Path(folder)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Fixture directory unavailable or symlinked")
    checksum = root / "SHA256SUMS"
    if checksum.is_symlink() or not checksum.is_file():
        raise ValueError("Missing fixture SHA256SUMS")
    hashes: dict[str, str] = {}
    for line in checksum.read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_.-]+)", line)
        if match is None or match.group(2) in hashes:
            raise ValueError("Malformed or duplicate checksum entry")
        hashes[match.group(2)] = match.group(1)
    if set(hashes) != set(FILES):
        raise ValueError("Unexpected fixture checksum inventory")
    raw: dict[str, bytes] = {}
    for name in FILES:
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Fixture missing or symlinked: {name}")
        data = path.read_bytes()
        if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), hashes[name]):
            raise ValueError(f"Fixture hash mismatch: {name}")
        raw[name] = data
    def parse(name: str) -> dict:
        value = json.loads(raw[name].decode("utf-8"), parse_constant=_reject_constant)
        if not isinstance(value, dict):
            raise ValueError("Expected JSON object")
        return value
    manifest = parse("scenario_manifest.json")
    if (manifest.get("source") != SOURCE or manifest.get("schema_version") != 1
            or manifest.get("files") != list(FILES[:2])
            or manifest.get("license") != "CC0-1.0"):
        raise ValueError("Untrusted or unsupported fixture manifest")
    depth = parse("depth_samples.json")
    if (depth.get("source") != SOURCE or depth.get("schema_version") != 1
            or depth.get("unit") != "m" or depth.get("aligned_to_rgb") is not True
            or not isinstance(depth.get("samples"), list)):
        raise ValueError("Untrusted or unaligned depth fixture")
    text = raw["detections.csv"].decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    expected = ["frame_id", "stamp_s", "category", "confidence", "x1", "y1", "x2", "y2", "image_width", "image_height"]
    if reader.fieldnames != expected:
        raise ValueError("Invalid detections.csv schema")
    detections = list(reader)
    if not detections or any(None in row or None in row.values() for row in detections):
        raise ValueError("Missing detection values")
    return detections, depth
