#!/usr/bin/env python3
"""Failing-G07 case identity & historical evidence verifier; offline L0 ONLY."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DAY02 = Path(__file__).resolve().parents[1]
MANIFEST = DAY02 / "FAILED_MVP_MANIFEST.json"
FIXTURE = DAY02 / "evidence/OBSERVED_L2_0OF2_SANITIZED.json"

def blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def validate(root=ROOT, manifest=MANIFEST, fixture=FIXTURE):
    errs = []
    try:
        m=json.loads(manifest.read_text(encoding="utf-8"))
        x=json.loads(fixture.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"status":"L0_FAILED_CASE_CONTRACT_FAIL","errors":[type(exc).__name__],
                "simulated_runs":0,"goals_sent":0,"release_accepted":False,"checked_runtime_blobs":0}
    if m.get("schema") != "axia.day02.failed_g07_native_case.v1":
        errs.append("BAD_MANIFEST_SCHEMA")
    if m.get("failed_student_source_sha") != "a04f9a7da8d54bbd9f944d05388792cb706adf28":
        errs.append("SOURCE_PIN_DRIFT")
    if m.get("failed_public_workflow_sha") != "8e03ac0a912ca9b81bdddda70212e52e6d804389":
        errs.append("CI_SOURCE_PIN_DRIFT")
    if m.get("failed_run_id") != 44914827138 or m.get("actual_moving_l2_result") != "FAIL_0_OF_2":
        errs.append("HISTORIC_L2_STATUS_MISMATCH")
    if m.get("authorized_for_owner_release") is not False or m.get("moving_l2_pass") is not False:
        errs.append("MISLABELED_RELEASE")
    if m.get("owner_l3") != "NOT_RUN" or m.get("certified_estop") is not False:
        errs.append("MISLABELED_ACCEPTANCE")
    if m.get("first_failure_policy") != "FIRST_SAFETY_TRANSITION_AND_TIMING_BOUNDARY":
        errs.append("MISSING_FIRST_BOUNDARY_POLICY")
    if x.get("evidence_type") != "SANITIZED_EXCERPT_OF_HISTORIC_RUN_NOT_SIMULATION":
        errs.append("FIXTURE_PROVENANCE_INVALID")
    if x.get("run_id") != m.get("failed_run_id") or x.get("source_student_sha") != m.get("failed_student_source_sha"):
        errs.append("FIXTURE_SOURCE_MISMATCH")
    if x.get("root_cause") != "UNDETERMINED" or m.get("root_cause") != "UNDETERMINED":
        errs.append("UNSUPPORTED_CAUSALITY_CLAIM")
    try:
        c1, c2 = x["cycle1"], x["cycle2"]
        if not (c1["scan_callback_max_ms"] > 300 and c1["clock_callback_max_ms"] > 300
                and c1["odom_callback_max_ms"] > 300 and c1["goal_sent"] is False
                and c2["first_blocking_odom_ms"] > 300
                and c2["cmd_vel_pre_guard_max_ms"] > 120 and c2["goal_sent"] is True):
            errs.append("FIRST_TIMING_BREACH_NOT_REPRODUCED_FROM_RECORD")
    except (KeyError, TypeError):
        errs.append("MALFORMED_FIRST_TIMING_RECORD")
    locked=m.get("locked_runtime_blobs")
    if not isinstance(locked,dict) or len(locked)!=8:
        errs.append("INVALID_BLOB_COUNT")
        locked={}
    matched=0
    for relative, expected in locked.items():
        if (not isinstance(relative,str) or not relative.startswith("block_B/day07/h01_runtime/")
                or ".." in Path(relative).parts):
            errs.append("INVALID_BLOB_PATH")
            continue
        path=root/relative
        if not path.is_file():
            errs.append("MISSING_SOURCE:"+relative)
        elif blob_sha(path)!=expected:
            errs.append("BLOB_DRIFT:"+relative)
        else:
            matched+=1
    forbidden=[str(p.relative_to(DAY02)) for p in DAY02.rglob("*")
               if p.is_file() and (p.name.lower().startswith(("solution","hidden_test","instructor_secret"))
               or p.suffix.lower() in (".db3",".onnx",".pt"))]
    if forbidden:
        errs.append("PRIVATE_FILE_IN_STUDENT_RELEASE:"+",".join(forbidden))
    return {
        "status":"L0_FAILED_CASE_SOURCE_AND_EVIDENCE_PASS" if not errs else "L0_FAILED_CASE_CONTRACT_FAIL",
        "source_sha":m.get("failed_student_source_sha"),
        "historic_actual_moving_l2":"FAIL_0_OF_2_NOT_RERUN",
        "root_cause":"UNDETERMINED",
        "checked_runtime_blobs":matched,
        "expected_runtime_blobs":len(locked),
        "simulated_runs":0,"goals_sent":0,"release_accepted":False,
        "errors":errs,
    }

def main():
    ap=argparse.ArgumentParser(description="Offline failed-case custody audit, never sends a Goal")
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    result=validate()
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    return 0 if result["status"]=="L0_FAILED_CASE_SOURCE_AND_EVIDENCE_PASS" else 2

if __name__=="__main__":
    sys.exit(main())
