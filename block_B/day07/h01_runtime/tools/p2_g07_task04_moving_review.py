#!/usr/bin/env python3
"""Task04 one-run native Moving Goal read-only safety verdict.

Uses the existing Task03 SQLite, Goal, Guard and CM120 oracles. A new positive
Contact calibration is intentionally NOT rerun: the frozen Task03 calibration
remains historical evidence, not a second run contributing to this L2 PASS.
"""
import argparse
import json
import hashlib
import sys
from pathlib import Path
from p2_g07_task03_contract import audit_bag_14,audit_goal_terminal,audit_guard_internal_cm_age
from d06.diagnostic.g07_task02_strict_gate import assess as assess_cm120

def review(root,witness,expected_sha,gui_windows):
    result={"schema":"axia.g07.task04.single_native_moving_evidence_v1",
            "status":"HOLD","first_failure":"NOT_VERIFIED",
            "source_sha":expected_sha,"certified_estop":False,
            "owner_wsl2_l3_accepted":False,
            "axia_mvp_demo_accepted":False,
            "gui_windows_seen":gui_windows}
    try:
        report=json.loads((root/"g07_ci_moving/ci_moving_goal_result.json").read_text())
        shutdown=json.loads((root/"g07_ordered_shutdown.json").read_text())
        audit=json.loads((root/"g07_shutdown_audit.json").read_text())
        witness_data=json.loads(witness.read_text())
        rows=[json.loads(x) for x in
              (root/"g07_ci_moving/actual_ros_events.jsonl").read_text().splitlines()]
        assert 0<len(rows)<=120000,"RAW_EVENTS_INVALID"
        goals=[x for x in rows if x.get("kind")=="owner_goal_published"]
        ends=[x for x in rows if x.get("kind")=="task03_motion_window_end"]
        assert len(goals)==1 and len(ends)==1,"EXACT_ONE_GOAL_WINDOW"
        start,end=goals[0]["t"],ends[0]["t"]
        assert 0<=start<end,"MONOTONIC_GOAL_WINDOW"
        uuid=report.get("goal_uuid")
        observed_cancel=[x for x in rows if x.get("kind")=="action"
                         and x.get("uuid")==uuid and x.get("status")==5]
        assert len(observed_cancel)>=1,"ACTUAL_ACTION_CANCELED_ABSENT"
        terminal=audit_goal_terminal(
            uuid,0 if report.get("goal_cancel_ack") else -1,
            [report.get("goal_cancel_uuid")] if report.get("goal_cancel_uuid") else [],
            report.get("goal_cancel_status"),report.get("guard_latched"))
        bag=audit_bag_14(root/"rosbag2")
        guard=audit_guard_internal_cm_age(rows,goal_start=start,window_end=end)
        cm=assess_cm120(report,rows)
        clock=[x["ns"] for x in rows if x.get("kind")=="clock"
               and start<=x.get("t",-1)<=end and type(x.get("ns")) is int]
        native=(witness_data.get("sensor_found") is True
                and witness_data.get("report_complete") is True
                and witness_data.get("missing_iterations")==0
                and type(witness_data.get("observed_iterations")) is int
                and witness_data["observed_iterations"]>=20
                and witness_data.get("positive_contacts")==0
                and len(clock)>=10 and clock[0]<clock[-1]
                and witness_data.get("first_sim_ns",10**100)<=clock[0]
                and witness_data.get("last_sim_ns",-1)>=clock[-1])
        checks={
            "single_goal_actual_action":len(goals)==1 and bool(observed_cancel),
            "exact_goal_cancel":terminal["status"]=="EXACT_GOAL_UUID_TERMINAL_CANCELED_PASS",
            "sqlite_14":bag["status"]=="ACTUAL_SQLITE_14_TOPIC_CUSTODY_PASS",
            "cm_source_and_observer_120ms":cm["status"]=="TASK02_PUBLIC_L2_NUMERICAL_CANDIDATE",
            "guard_internal_150ms":guard["status"]=="GUARD_NATIVE_CM_AGE_TTL150_PASS",
            "s02_actual_native_contact_zero":native,
            "cli_shared_moving_result":report.get("status")=="CI_GAZEBO_MOVING_GOAL_CANDIDATE",
            "no_unexpected_guard_latch":report.get("guard_latched") is False,
            "first_timing_violation_none":report.get("first_timing_violation") is None,
            "odom_moved":report.get("observed_odom_moved_m",0)>.05,
            "odom_zero_dwell":report.get("odom_stopped_dwell_sec",0)>=1.0,
            "cm_callback_120ms":0<report.get("max_cm_interval_sec",999)<=.12,
            "guard_150ms":0<report.get("max_guard_interval_sec",999)<=.15,
            "scan_300ms":0<report.get("max_scan_interval_sec",999)<=.30,
            "odom_300ms":0<report.get("max_odom_interval_sec",999)<=.30,
            "clock_300ms":0<report.get("max_clock_interval_sec",999)<=.30,
            "nav_lifecycle_ack":shutdown.get("navigation_ack") is True,
            "loc_lifecycle_ack":shutdown.get("localization_ack") is True,
            "collision_monitor_child_clean":audit.get("cm_exit_code")==0,
            "both_actual_gui_windows":gui_windows==2,
            "exact_source_sha":report.get("source_sha")==expected_sha
        }
        result.update(checks=checks,first_failure=next((k for k,v in checks.items() if not v),"NONE"),
          cm120={"status":cm.get("status"),"source_gap_max_ms":cm.get("source_gap_max_ms"),
                 "observer_gap_max_ms":cm.get("observer_gap_max_ms"),
                 "actual_publisher_pairs":cm.get("actual_publisher_pairs")},
          guard_internal_cm_age_max_ms=guard.get("max_cm_age_ms"),
          goal_uuid=uuid if isinstance(uuid,str) and len(uuid)==32 else None,
          odom_moved_m=report.get("observed_odom_moved_m"),
          stopped_dwell_sec=report.get("odom_stopped_dwell_sec"),
          native_contact_count=witness_data.get("positive_contacts"),
          native_observed_iterations=witness_data.get("observed_iterations"),
          bag_topic_counts=bag.get("topic_message_counts"),
          bag_sqlite_sha256=bag.get("sqlite_sha256"),
          bag_metadata_sha256=bag.get("metadata_sha256"),
          native_contact_binary_sha256=witness_data.get("source_sha"),
          native_contact_positive_calibration_this_run=False)
        if result["first_failure"]=="NONE":
            result["status"]="TASK04_REAL_GAZEBO_MOVING_GUI_L2_SCOPED_PASS"
    except (OSError,ValueError,TypeError,IndexError,KeyError,AssertionError) as exc:
        result["first_failure"]="SOURCE_OR_EVIDENCE_"+type(exc).__name__+":"+str(exc)[:120]
    return result

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--motion-root",type=Path,required=True)
    p.add_argument("--witness",type=Path,required=True)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--gui-windows",type=int,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    v=review(a.motion_root,a.witness,a.source_sha,a.gui_windows)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n")
    print("AXIA_G07_TASK04_NATIVE_MOVING_GUI_VERDICT "+
          json.dumps({k:v.get(k) for k in ("status","first_failure","source_sha","gui_windows_seen")},
                     sort_keys=True),flush=True)
    print("AXIA_G07_TASK04_OWNER_MOVING_L3=NOT_RUN AXIA_MVP_DEMO_ACCEPTED=HOLD CERTIFIED_ESTOP=false")
    return 0 if v["status"]=="TASK04_REAL_GAZEBO_MOVING_GUI_L2_SCOPED_PASS" else 3

if __name__=="__main__":
    sys.exit(main())
