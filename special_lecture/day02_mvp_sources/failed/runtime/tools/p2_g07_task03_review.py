"""Formal Task03 PUBLIC CI post-run review: actual SAME Goal, NO fake ROS.

Reads the original runner's real native ECM report, ROS callback ledger and
SQLite bag READ-ONLY; publishes only bounded numeric SHA256 custody.
"""
import argparse
import json
import sys
from pathlib import Path

from p2_g07_task03_contract import (
    audit_bag_14,audit_goal_terminal,audit_guard_internal_cm_age,
    audit_native_ecm_contact,
)
from d06.diagnostic.g07_task02_strict_gate import assess as assess_real_cm120

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--positive-root",type=Path,required=True)
    p.add_argument("--motion-root",type=Path,required=True)
    p.add_argument("--positive-witness",type=Path,required=True)
    p.add_argument("--motion-witness",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    verdict={"schema":"axia.g07.task03.formal_public_native_l2_v1",
             "status":"TASK03_FORMAL_PUBLIC_L2_HOLD",
             "first_failure":"REQUIRED_NATIVE_ORIGINAL_MISSING",
             "contact_zero_proven":False,"original_bag_14_topic_custody_proven":False,
             "exact_goal_terminal_proven":False,"guard_internal_cm_age_proven":False,
             "task04_owner_wsl2_l3_accepted":False,
             "certified_estop":False,"axia_mvp_demo_accepted":False}
    try:
        positive=json.loads(a.positive_witness.read_text(encoding="utf-8"))
        motion=json.loads(a.motion_witness.read_text(encoding="utf-8"))
        r=a.motion_root
        report=json.loads((r/"g07_ci_moving/ci_moving_goal_result.json").read_text())
        shutdown=json.loads((r/"g07_ordered_shutdown.json").read_text())
        audit=json.loads((r/"g07_shutdown_audit.json").read_text())
        events=[json.loads(l) for l in
          (r/"g07_ci_moving/actual_ros_events.jsonl").read_text().splitlines()]
        if len(events)>120000:
            raise ValueError("TOO_MANY_OBSERVER_EVENTS")
        goal=[e for e in events if e.get("kind")=="owner_goal_published"]
        end=[e for e in events if e.get("kind")=="task03_motion_window_end"]
        if len(goal)!=1 or len(end)!=1 or end[0]["t"]<=goal[0]["t"]:
            raise ValueError("GOAL_WINDOW_NOT_BOUND")
        start_t=goal[0]["t"];end_t=end[0]["t"]
        sim_start=[e["ns"] for e in events
                   if e.get("kind")=="clock" and start_t<=e.get("t",-1)<=end_t]
        sim_end=[e["ns"] for e in events
                 if e.get("kind")=="clock" and start_t<=e.get("t",-1)<=end_t]
        if len(sim_start)<10 or sim_start[0]>=sim_end[-1]:
            raise ValueError("SIM_CLOCK_GOAL_WINDOW_NOT_BOUND")
        contact=audit_native_ecm_contact(positive,motion,
                 goal_sim_ns=sim_start[0],stop_sim_ns=sim_end[-1])
        cm120=assess_real_cm120(report,events)
        bag=audit_bag_14(r/"rosbag2")
        guard=audit_guard_internal_cm_age(events,goal_start=start_t,window_end=end_t)
        uuid=report.get("goal_uuid")
        goal_result=report.get("task03_exact_goal_terminal",{})
        terminal=audit_goal_terminal(
            uuid,0 if report.get("goal_cancel_ack") else -1,
            [report.get("goal_cancel_uuid")] if report.get("goal_cancel_uuid") else [],
            report.get("goal_cancel_status"),
            report.get("guard_latched"))
        checks={
           "native_contact":contact["status"],
           "actual_cm120":cm120["status"],
           "bag_14_topic":bag["status"],
           "guard_internal_age":guard["status"],
           "goal_terminal":terminal["status"],
           "one_goal_runtime":report.get("status"),
           "managed_nav2_shutdown":shutdown.get("status"),
           "cm_child_clean_exit":audit.get("status"),
        }
        verdict["checks"]=checks
        verdict["first_failure"]=next((k+"="+v for k,v in checks.items() if
         (k=="native_contact" and v!="S02_NATIVE_ECM_GOAL_WINDOW_CONTACT_ZERO_PASS")
         or (k=="actual_cm120" and v!="TASK02_PUBLIC_L2_NUMERICAL_CANDIDATE")
         or (k=="bag_14_topic" and v!="ACTUAL_SQLITE_14_TOPIC_CUSTODY_PASS")
         or (k=="guard_internal_age" and v!="GUARD_NATIVE_CM_AGE_TTL150_PASS")
         or (k=="goal_terminal" and v!="EXACT_GOAL_UUID_TERMINAL_CANCELED_PASS")
         or (k=="one_goal_runtime" and v!="CI_GAZEBO_MOVING_GOAL_CANDIDATE")
         or (k=="managed_nav2_shutdown" and v!="NAV2_LIFECYCLE_SHUTDOWN_ACK")
         or (k=="cm_child_clean_exit" and v!="SHUTDOWN_CLEAN_CANDIDATE")),
         "NONE")
        verdict.update(
          contact_zero_proven=contact.get("contact_zero_proven",False),
          cm120_exact_source_observer_proven=(
              cm120["status"]=="TASK02_PUBLIC_L2_NUMERICAL_CANDIDATE"),
          cm120={"status":cm120["status"],
                 "source_gap_max_ms":cm120.get("source_gap_max_ms"),
                 "observer_gap_max_ms":cm120.get("observer_gap_max_ms"),
                 "actual_publisher_pairs":cm120.get("actual_publisher_pairs")},
          original_bag_14_topic_custody_proven=bag["status"]=="ACTUAL_SQLITE_14_TOPIC_CUSTODY_PASS",
          exact_goal_terminal_proven=terminal["terminal_verified"],
          guard_internal_cm_age_proven=guard["status"]=="GUARD_NATIVE_CM_AGE_TTL150_PASS",
          contact=contact,
          guard={"status":guard["status"],"max_cm_age_ms":guard["max_cm_age_ms"],
                 "samples":guard["samples"]},
          bag={"status":bag["status"],"counts":bag["topic_message_counts"],
               "sqlite_sha256":bag["sqlite_sha256"],
               "metadata_sha256":bag.get("metadata_sha256")},
          goal_uuid=uuid if isinstance(uuid,str) and len(uuid)==32 else None,
          owner_runner_rc=0,
          public_only=True)
        if verdict["first_failure"]=="NONE" and all((
          report.get("guard_latched") is False,
          report.get("first_timing_violation") is None,
          report.get("max_cm_interval_sec",999)<=.12,
          report.get("max_guard_interval_sec",999)<=.15,
          report.get("max_scan_interval_sec",999)<=.3,
          report.get("max_odom_interval_sec",999)<=.3,
          report.get("max_clock_interval_sec",999)<=.3,
          report.get("odom_stopped_dwell_sec",0)>=1.0,
          shutdown.get("navigation_ack") is True,
          shutdown.get("localization_ack") is True,
          audit.get("cm_exit_code")==0,
        )):
            verdict["status"]="TASK03_PUBLIC_L2_FORMAL_EVIDENCE_PASS_SCOPED"
        elif verdict["first_failure"]=="NONE":
            verdict["first_failure"]="FIRST_SAFETY_TIMING_OR_SHUTDOWN_BREACH"
    except (OSError,ValueError,TypeError,KeyError,IndexError) as exc:
        verdict["first_failure"]="READ_ONLY_EVIDENCE_"+type(exc).__name__
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(verdict,sort_keys=True,indent=2)+"\n")
    safe={k:verdict.get(k) for k in
          ("status","first_failure","contact_zero_proven",
           "original_bag_14_topic_custody_proven","exact_goal_terminal_proven",
           "guard_internal_cm_age_proven")}
    print("AXIA_G07_TASK03_FORMAL_PUBLIC_VERDICT "+json.dumps(safe,sort_keys=True),
          flush=True)
    print("AXIA_MVP_DEMO_ACCEPTED=HOLD CERTIFIED_ESTOP=false OWNER_WSL2_NOT_RUN",
          flush=True)
    return 0 if verdict["status"]=="TASK03_PUBLIC_L2_FORMAL_EVIDENCE_PASS_SCOPED" else 3

if __name__=="__main__":
    sys.exit(main())
