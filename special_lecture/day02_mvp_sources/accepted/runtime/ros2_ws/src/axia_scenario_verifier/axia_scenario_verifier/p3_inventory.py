"""Review an Owner file/hash inventory, never treating it as ROS/Gazebo proof."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re

HEX64 = re.compile(r"^[a-f0-9]{64}$")
G00_BAG = re.compile(r"(?:^|/)g00_run_(0[1-3])/cold_run_01/rosbag2/rosbag2_0[.]db3$")
EXPECTED_IDS = (
    "S01_P0_G00_RUN7", "S01_P1_G00_FROZEN_LKG",
    "S02_P2_G07_L2_PUBLIC", "S03_P1_G04_SCAN_NINE",
    "S04_P3_SYNTHETIC_PNU", "S05_P1_G03_RECOVERY",
)
STATUSES = {"HASH_INVENTORY_ONLY_RAW_NOT_REVIEWED", "LOCAL_ANCHORS_NOT_FOUND",
            "PUBLIC_CI_REFERENCE_ONLY", "SYNTHETIC_L0_REFERENCE_ONLY"}
HASH_STATUSES = {"HASH_COMPUTED_NOT_ATTESTED", "HASH_SKIPPED_FILE_TOO_LARGE",
                 "FILE_UNREADABLE", "FILE_COUNT_LIMIT_REACHED", "SYMLINK_SKIPPED"}


def relative(value):
    if not isinstance(value, str) or not value or chr(92) in value or chr(0) in value:
        raise ValueError("invalid relative path")
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or str(p) != value or value.startswith("./"):
        raise ValueError("inventory path escapes home or is not normalized")
    return value


def inspect_inventory(path: Path, registry_path: Path) -> dict:
    """Fail closed on malformed, forged or stale metadata; no raw inspection."""
    original = path.read_bytes()
    doc = json.loads(original.decode("utf-8"))
    expected_registry = hashlib.sha256(registry_path.read_bytes()).hexdigest()
    if doc.get("schema") != "axia_p3_owner_readonly_inventory_v1" or doc.get(
            "inventory_source_registry_sha256") != expected_registry:
        raise ValueError("inventory registry SHA256 or schema mismatch")
    for flag in ("raw_reviewed", "formal_accepted", "goal_sent",
                 "fault_injected", "certified_estop"):
        if doc.get(flag) is not False:
            raise ValueError("inventory cannot claim activity or acceptance")
    records = doc.get("records")
    if not isinstance(records, list) or len(records) != len(EXPECTED_IDS):
        raise ValueError("expected exactly six evidence source records")
    by_id = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("invalid evidence record")
        rid = record.get("record_id")
        if (rid not in EXPECTED_IDS or rid in by_id or record.get("status") not in STATUSES
                or record.get("gate_accepted") is not False):
            raise ValueError("unrecognized, duplicate or accepted evidence record")
        anchors = record.get("anchors")
        if not isinstance(anchors, list) or len(anchors) > 100:
            raise ValueError("invalid Owner anchors")
        for anchor in anchors:
            if not isinstance(anchor, dict) or anchor.get("raw_reviewed") is not False:
                raise ValueError("raw proof cannot be inferred from inventory")
            root = relative(anchor.get("root_relative_to_home"))
            files = anchor.get("candidate_files")
            if not isinstance(files, list) or len(files) > 10000:
                raise ValueError("invalid candidate file list")
            if anchor.get("hash_matches_report") not in (None, True, False):
                raise ValueError("invalid checksum comparison")
            for entry in files:
                if not isinstance(entry, dict):
                    raise ValueError("invalid candidate entry")
                rel = relative(entry.get("relative_path"))
                if rel != root and not rel.startswith(root.rstrip("/") + "/"):
                    raise ValueError("candidate path outside Owner root")
                digest = entry.get("sha256")
                status = entry.get("hash_status")
                if status not in HASH_STATUSES:
                    raise ValueError("unknown hash status")
                if digest is not None:
                    if (not isinstance(digest, str) or not HEX64.fullmatch(digest)
                            or status != "HASH_COMPUTED_NOT_ATTESTED"):
                        raise ValueError("untrusted claimed SHA256")
        by_id[rid] = record
    if set(by_id) != set(EXPECTED_IDS):
        raise ValueError("missing evidence record")

    def files_of(rid):
        for anchor in by_id[rid]["anchors"]:
            yield from anchor["candidate_files"]

    p0 = by_id["S01_P0_G00_RUN7"]
    p1 = by_id["S01_P1_G00_FROZEN_LKG"]
    p0_expected = "90f786f7aa50f0e9d47ac242e2ce3276264616e498c68f873e5eaf905b78dfde"
    p0_found = any(f.get("sha256") == p0_expected and f["relative_path"].endswith(".tar.gz")
                   for f in files_of("S01_P0_G00_RUN7"))
    shared_roots = ({a["root_relative_to_home"] for a in p0["anchors"]} &
                    {a["root_relative_to_home"] for a in p1["anchors"]})
    if shared_roots and not p0_found:
        p0_status = "P0_REPORT_ARCHIVE_UNMATCHED_DUPLICATE_P1_ROOT"
    elif p0_found:
        p0_status = "P0_REPORT_ARCHIVE_HASH_MATCH_NOT_RAW_REVIEWED"
    else:
        p0_status = "P0_REPORT_ARCHIVE_NOT_FOUND"

    bags = {}
    for item in files_of("S01_P1_G00_FROZEN_LKG"):
        m = G00_BAG.search(item["relative_path"])
        if m and item["hash_status"] == "HASH_COMPUTED_NOT_ATTESTED":
            bags[m.group(1)] = item["sha256"]
    unique = len(set(bags.values()))
    observations = {
        "S01_P0_G00_RUN7": p0_status,
        "S01_P1_G00_FROZEN_LKG": (
            "THREE_DIFFERENT_G00_DB3_HASHES_NOT_BEHAVIOR_PROOF"
            if len(bags) == unique == 3 else "G00_DB3_COUNT_OR_UNIQUENESS_UNVERIFIED"),
        "S02_P2_G07_L2_PUBLIC": "PRIOR_PUBLIC_GAZEBO_L2_REFERENCE_NO_GOAL",
        "S03_P1_G04_SCAN_NINE": "REVIEW_INDEX_FILES_ONLY_NO_RAW_TOPICS",
        "S04_P3_SYNTHETIC_PNU": "SYNTHETIC_L0_ONLY",
        "S05_P1_G03_RECOVERY": "RECOVERY_SIDECAR_METADATA_ONLY",
    }
    result = []
    for rid in EXPECTED_IDS:
        rec = by_id[rid]
        nfiles = sum(len(a["candidate_files"]) for a in rec["anchors"])
        obs = observations[rid]
        if rid in ("S03_P1_G04_SCAN_NINE", "S05_P1_G03_RECOVERY") and nfiles == 0:
            obs = "OWNER_INDEX_MISSING"
        result.append({
            "record_id": rid, "scenario_id": rec["scenario_id"],
            "observation": obs, "anchor_count": len(rec["anchors"]),
            "file_count": nfiles,
            "unique_g00_bag_sha256_count": unique if rid == "S01_P1_G00_FROZEN_LKG" else None,
            "owner_raw_reviewed": False, "gate_accepted": False,
        })
    return {
        "schema": "axia_p3_inventory_assessment_v1",
        "inventory_sha256": hashlib.sha256(original).hexdigest(),
        "registry_sha256": expected_registry,
        "basis": "OWNER_FILE_HASH_INVENTORY_ONLY",
        "raw_reviewed": False,
        "demo_package_ready": False,
        "formal_accepted": False,
        "formal_gates": {g: "NOT_ACCEPTED" for g in ("G08", "G09", "G10", "G11")},
        "records": result,
    }
