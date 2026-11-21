"""AXIA D15 — read-only jrCIgoGl derived field evidence evaluator.

No ROS / Gazebo / Goal / cmd_vel; no raw WSL2 bag is included.
Numbers and statuses are reported by original public source, not remeasured.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
import re
from pathlib import Path

HERE=Path(__file__).resolve().parent
EVIDENCE=HERE/"fixtures/jrcigogl_public_derived.json"
BASELINE_ID="AXIA-G07-T04-DEMO-BASELINE-20261120-jrCIgoGl"
ORIGINAL_BLOB_SHA1="ae7d594b5452d96cc8802bc53bc8ad578fe99fb7"
STUDENT_SOURCE="5c7983598fa3bcd7148433a06f37a4e78b091273"
TAR_SHA="2d454845183704d8f53b50dcdbaa48446d1103bfa9f750cc3ce662d9af7684db"
ZIP_SHA="92c31af277bc7a64742540a2b9e5c99f13ded4cac51ae1bd1b76f3c16a4dd331"
THRESHOLDS_MS={
    "scan_gap_max_ms":300,
    "cm_source_gap_max_ms":120,
    "cm_observer_gap_max_ms":120,
    "guard_internal_cm_age_max_ms":150,
    "guard_status_gap_max_ms":150,
}
GOAL_UUID=re.compile(r"^[0-9a-f]{32}$")


def _finite_number(x):
    return type(x) in (int,float) and math.isfinite(x)


def _positive(x):
    return _finite_number(x) and x>0


def _true(v):
    return v is True


def load_evidence(path=EVIDENCE, *, verify_git_blob=True):
    path=Path(path)
    raw=path.read_bytes()
    if verify_git_blob:
        calc=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
        if calc!=ORIGINAL_BLOB_SHA1:
            raise ValueError("D15_DERIVED_FIXTURE_BLOB_SHA_MISMATCH")
    return json.loads(raw.decode("utf-8"))


def review_baseline(d):
    """Validate *published aggregate claims*; cannot infer first timestamp or raw proof."""
    if not isinstance(d,dict):
        raise ValueError("D15_INVALID_DERIVED_OBJECT")
    checks={}
    errors=[]
    checks["source_provenance"]=(
        d.get("schema")=="axia.g07.task04.owner_jrcigogl_derived_field_acceptance_v1"
        and d.get("run_id")=="jrCIgoGl" and d.get("tar_sha256")==TAR_SHA
        and d.get("zip_sha256")==ZIP_SHA and d.get("source_sha")==STUDENT_SOURCE
        and d.get("public_native_two_cycle_run")==44653465671
    )
    checks["field_numeric_21_of_21"]=(
        d.get("numeric_checks_pass")==21
        and d.get("numeric_checks_total")==21
        and d.get("first_failure")=="NONE"
        and d.get("manifest_entries_valid")==141
        and d.get("sqlite_quick_check")=="ok"
        and d.get("bag_topics")==14
        and d.get("bag_message_count")==50172
    )
    measures=("clear_front_m","slow_front_m","stop_front_m",
              "slow_supervised_vx_mps","slow_final_vx_mps",
              "stop_final_vx_mps","odom_movement_m","clear_odom_travel_m")
    valid=all(_finite_number(d.get(k)) for k in measures)
    checks["clear_slow_stop"]=bool(valid and
        d["clear_front_m"]>d["slow_front_m"]>d["stop_front_m"]>0
        and d["slow_supervised_vx_mps"]>d["slow_final_vx_mps"]>0
        and d["stop_final_vx_mps"]==0
        and d["clear_odom_travel_m"]>=0.12
        and d["odom_movement_m"]>=d["clear_odom_travel_m"]
        and _true(d.get("real_scan_fixture_ack"))
    )
    checks["goal_cancel"]=(
        _true(d.get("real_nav2_goal_executing"))
        and isinstance(d.get("goal_uuid"),str) and bool(GOAL_UUID.fullmatch(d["goal_uuid"]))
        and _true(d.get("exact_goal_uuid_cancelled"))
        and d.get("goal_cancel_status")==5
    )
    checks["odom_zero_dwell"]=(
        _finite_number(d.get("zero_dwell_sec"))
        and d["zero_dwell_sec"]>=1.0
    )
    for k,ceiling in THRESHOLDS_MS.items():
        value=d.get(k)
        if not (_finite_number(value) and 0<=value<=ceiling):
            errors.append(k)
    checks["reported_ttl_boundaries"]=not errors
    checks["guard_clock_and_shutdown"]=(
        d.get("guard_latched") is False
        and _true(d.get("nav_loc_ack"))
        and d.get("cm_process_exit_code")==0
        and all(d.get(k)==0 for k in (
            "clock_backward_pairs","pre_guard_rmw_source_backward_pairs",
            "supervised_rmw_source_backward_pairs"))
    )
    checks["scope_preserved"]=(
        d.get("raw_machine_status")=="HOLD_RAW_REVIEW_AND_VISUAL_PENDING"
        and d.get("raw_machine_l3_accepted") is False
        and d.get("visual_content_verified") is False
        and d.get("formal_safety_timing_accepted") is False
        and d.get("certified_estop") is False
        and _true(d.get("scope_education_numeric_baseline_accepted"))
        and _true(d.get("rviz_glsl_link_error_observed"))
        and d.get("post_goal_destroyable_warning_count")==2
        and d.get("intermittent_ci_guard_first_latch_root_cause_resolved") is False
    )
    for label,pass_ in checks.items():
        if not pass_:
            errors.append(label)
    return {
        "baseline_id":BASELINE_ID,
        "run_id":d.get("run_id"),
        "numeric_gate":"EDUCATION_NUMERIC_ACCEPTED" if all(checks.values()) else "NOT_ACCEPTED",
        "checks":checks,
        "failed_gates":errors,
        "threshold_ms":dict(THRESHOLDS_MS),
        "first_violation_timestamp":None,
        "first_violation_timestamp_reason":"NOT_PRESENT_IN_PUBLIC_AGGREGATE_DERIVED_EVIDENCE",
        "verification_level":"DERIVED_EVIDENCE_L0_FROM_PREVIOUS_WSL2_L3_NOT_NEW_RUNTIME",
        "raw_machine_status":d.get("raw_machine_status"),
        "formal_accepted":False,
        "certified_estop":False,
        "visual_verified":False,
        "owner_raw_reopened":False,
        "g07_real_human_detector_attested":False,
        "note":"A pass confirms published derived numbers/flags only; it does not independently reproduce rosbag, GUI pixels, temporal event order, or formal safety acceptance."
    }


def validate_g09_g10_separation():
    day13=HERE.parent/"day13/fixtures/cases.json"
    day14=HERE.parent/"day14/fixtures/policy_events.json"
    g10=HERE.parent/"day14/fixtures/g10_events.json"
    a=json.loads(day13.read_text())
    b=json.loads(day14.read_text())
    c=json.loads(g10.read_text())
    labels=sorted({s["expected"] for s in a["cases"]})
    valid=(a.get("schema")=="axia.block_d.d13.synthetic.v1"
       and b.get("schema")=="axia.block_d.d14.policy_events.v1"
       and c.get("schema")=="axia.block_d.d14.g10_educational_events.v1"
       and labels==["N","P","U"]
       and len(b["cases"])==16 and len(c["events"])==15)
    return {
        "safe_separation":valid,
        "g09_labels":labels,
        "g09_source":"D13_SYNTHETIC_FIXTURE_NOT_G07_REAL_CAMERA",
        "d14_policy_source":"D14_SYNTHETIC_OFFLINE_NOT_ACTUAL_SUPERVISOR",
        "g10_level":"SYNTHETIC_L0_ONLY",
        "g07_owner_human_detector_attested":False,
        "g07_real_owner_contains_g09_pnu_provenance":False,
        "previous_scoped_s04_actual_gazebo_run":43455456960,
        "previous_scoped_s04_note":"Separate synthetic G09 P/N/U -> real Supervisor/CM/Guard S04 L2 session. Not jrCIgoGl Owner run."
    }


def negative_counterexamples(d):
    """Educational mutations only; do not overwrite the immutable source."""
    modifications=[
       ("SCAN_301MS",{"scan_gap_max_ms":301.0},"scan_gap_max_ms"),
       ("GUARD_151MS",{"guard_internal_cm_age_max_ms":151.0},"guard_internal_cm_age_max_ms"),
       ("GOAL_WRONG",{"exact_goal_uuid_cancelled":False},"goal_cancel"),
       ("DWELL_0_5S",{"zero_dwell_sec":.5},"odom_zero_dwell"),
       ("FALSE_CERTIFICATION",{"certified_estop":True},"scope_preserved"),
    ]
    results=[]
    for name,fields,expected_gate in modifications:
        value=copy.deepcopy(d)
        value.update(fields)
        review=review_baseline(value)
        results.append({
            "case":name,"synthetic_mutation":fields,"expected_failed_gate":expected_gate,
            "detected":expected_gate in review["failed_gates"],
            "not_accepted":review["numeric_gate"]=="NOT_ACCEPTED",
            "scope":"EDUCATIONAL_INJECTED_NUMBERS_NOT_OBSERVED_OWNER_EVENTS",
        })
    return results
