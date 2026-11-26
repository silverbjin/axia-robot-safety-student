#!/usr/bin/env python3
"""H01 passive ROS safety callback evidence; NO Goal, NO motor publisher.

This is NOT an in-motion Supervisor→CM→Guard causal TTL acceptance. It
captures real ROS callback receipts and detects the FIRST period violation
under the same Gazebo/Nav2 preflight and resource load. A simulated Goal
may only be separately admitted once all physical safety gates succeed.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from d07_h01_live_ttl import assess_callback_gaps
from d07_h01_sensor_stamp_timing import compare_sensor_stamps_and_receipts
from p2_g07_ci_moving_goal_oracle import cm_rmw_provenance, cm_upstream_rmw_gap_window
from p2_l3_live_session import Observer

GRAPH={
    "final":[["axia_base_command_guard","geometry_msgs/msg/Twist"]],
    "cm":[["collision_monitor","geometry_msgs/msg/Twist"]],
    "supervisor":[["axia_safety_supervisor","geometry_msgs/msg/Twist"]],
}


def check(args):
    required={"GITHUB_ACTIONS":"true","ROS_DISTRO":"jazzy",
              "AXIA_P0_SIM_ONLY":"1","AXIA_G07_CI_SIM_GOAL_ALLOWED":"1",
              "AXIA_D07_H01_CI_ALLOWED":"1",
              "AXIA_D07_H01_TTL_DIAGNOSTIC_ONLY":"1",
              "AXIA_G07_OWNER_STARTUP_PARITY":"1"}
    if any(os.environ.get(k)!=v for k,v in required.items()):
        raise RuntimeError("H01_PASSIVE_REAL_ROS_CI_ONLY")
    if any(os.environ.get(k)=="1" for k in (
        "AXIA_D07_H01_CONTACT_CALIBRATION_ONLY",
        "AXIA_D07_H01_GEOMETRY_ONLY",
        "AXIA_P3_S01_CI_GOAL_ALLOWED",
        "AXIA_P3_S03_CI_COMPOUND_ALLOWED",
        "AXIA_P3_S04_CI_PNU_ALLOWED",
        "AXIA_P3_S05_CI_GOAL_ALLOWED")):
        raise RuntimeError("H01_TTL_WITH_OTHER_MOTION_SCOPE_DENIED")
    if not os.environ.get("GZ_PARTITION","").startswith("axia_p2_"):
        raise RuntimeError("H01_TTL_UNISOLATED_GAZEBO")
    repo=Path(__file__).resolve().parents[1]
    actual=subprocess.check_output(["git","-c","safe.directory="+str(repo),
                   "-C",str(repo),"rev-parse","HEAD"],text=True,timeout=5).strip()
    if len(args.source_sha)!=40 or actual!=args.source_sha:
        raise RuntimeError("H01_PRIVATE_SOURCE_PIN_MISMATCH")
    start=json.loads(args.startup.read_text())
    pre=json.loads(args.pregoal.read_text())
    if not (start.get("status")=="SMOKE_READY"
            and start.get("goal_sent") is False
            and start.get("fault_injected") is False
            and pre.get("status")=="P2_G07_OWNER_PREGOAL_L2_READY_NO_GOAL"
            and pre.get("goal_sent") is False
            and pre.get("stationary_odom_checked") is True):
        raise RuntimeError("H01_NO_GOAL_LIVE_STARTUP_NOT_PROVEN")


def run(args):
    check(args)
    args.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    result={"status":"H01_LIVE_TTL_HOLD_NO_GOAL","source_sha":args.source_sha,
            "reason":"START","goal_sent":False,"motion_admitted":False,
            "actual_causal_delivery_verified":False,
            "actual_header_age_verified":False,"first_ttl_violation":None,
            "certified_estop":False,"owner_l3_accepted":False}
    def save():
        (args.output/"ttl_no_goal.json").write_text(
            json.dumps(result,sort_keys=True,indent=2)+"\n")
    save()
    import rclpy
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    rclpy.init()
    node=Node("axia_d07_h01_passive_real_ttl_only",
              parameter_overrides=[Parameter("use_sim_time",value=True)],
              automatically_declare_parameters_from_overrides=True)
    observer=Observer(node,args.output,buffered_evidence=True,periodic_flush_sec=.75,
                      sensor_header_ledger=True)
    ex=MultiThreadedExecutor(num_threads=2)
    ex.add_node(node)
    worker=threading.Thread(target=ex.spin,daemon=True)
    worker.start()
    try:
        # Graph identity is independent of publish rate and must match exactly.
        graph=None
        deadline=time.monotonic()+10.
        while time.monotonic()<deadline:
            snap=observer.snapshot(include_graph=True)
            graph={
                "final":[list(x) for x in snap["final_publishers"]],
                "cm":[list(x) for x in snap["cm_publishers"]],
                "supervisor":[list(x) for x in snap["supervisor_publishers"]],
            }
            if graph==GRAPH and snap.get("clock_advancing"):
                break
            time.sleep(.2)
        result["exclusive_command_graph"]=graph==GRAPH
        result["observed_graph"]=graph
        if graph!=GRAPH:
            raise RuntimeError("H01_REAL_FINAL_COMMAND_GRAPH_INVALID")
        # Measure only this fixed post-start observation interval, not prior
        # lifecycle/startup events. Retain first/last silent TTL boundaries.
        # This does not certify CM->Guard causal transfer or Goal readiness.
        window_start=time.monotonic()
        time.sleep(6.)
        window_end=time.monotonic()
        observer.flush_events()
        rows=[json.loads(row) for row in
              (args.output/"actual_ros_events.jsonl").read_text().splitlines()
              if row.strip()]
        rows=[row for row in rows
              if window_start<=row["t"]<=window_end]
        timing=assess_callback_gaps(
            rows,observation_window={"start":window_start,"end":window_end})
        # Real sensor Header uses ROS simulated clock; receipt uses host
        # monotonic clock. Compare only intervals, never absolute ages.
        sensor_stamp=compare_sensor_stamps_and_receipts(rows)
        result["sensor_stamp_diagnostic"]=sensor_stamp
        print("AXIA_D07_H01_SENSOR_HEADER_RECEIPT_FIRST_BOUNDARY "+
              json.dumps({
                  "status":sensor_stamp["status"],
                  "first_receipt_limit_crossing":
                      sensor_stamp.get("first_receipt_limit_crossing"),
                  "first_source_header_limit_crossing":
                      sensor_stamp.get("first_source_header_limit_crossing"),
                  "metrics":sensor_stamp.get("metrics",{}),
                  "actual_causal_delivery_verified":False,
                  "actual_header_age_verified":False,
                  "goal_sent":False,
              },sort_keys=True),flush=True)
        # Latest reviewed AXIA MVP G07 read-only RMW provenance oracles.
        # A passive/no-Goal CM stream can be silent. NO_CM_SOURCE_GAP_OBSERVED
        # is UNKNOWN, not a source/sink delivery PASS or motion permission.
        rmw=cm_rmw_provenance(
            rows,goal_start=window_start,end=window_end)
        upstream=cm_upstream_rmw_gap_window(
            rows,goal_start=window_start,end=window_end)
        first_rmw_boundary={
            "status":rmw["status"],
            "first_gap":rmw.get("first_gap"),
            "attribution":rmw["attribution"],
            "upstream_status":upstream["status"],
            "upstream_classification":upstream["classification"],
            "upstream_cm_source_gap_sec":upstream["cm_source_gap_sec"],
            "rmw_source_receive_proven":rmw["valid_rmw_samples"]>=2,
            "guard_safety_pass":False,
            "goal_sent":False,
        }
        result["first_rmw_boundary"]=first_rmw_boundary
        result["cm_upstream_rmw_diagnostic"]=upstream
        print("AXIA_D07_H01_MVP_RMW_FIRST_BOUNDARY_NO_GOAL "+
              json.dumps(first_rmw_boundary,sort_keys=True),flush=True)
        result.update(callback_diagnostic=timing,
                      first_ttl_violation=timing.get("first_ttl_violation"),
                      first_safety_transition=timing.get("first_safety_transition"),
                      status=("H01_PREGOAL_CALLBACK_PERIODS_ONLY_NO_GOAL"
                              if (timing["status"]=="CALLBACK_PERIODS_CANDIDATE_NO_GOAL"
                                  and sensor_stamp["status"]==
                                  "SENSOR_STAMP_RECEIPT_CANDIDATES_NO_GOAL")
                              else "H01_LIVE_TTL_HOLD_NO_GOAL"),
                      reason=timing["reason"],goal_sent=False,
                      actual_causal_delivery_verified=False,
                      actual_header_age_verified=False,
                      motion_admitted=False)
        save()
        print("AXIA_D07_H01_LIVE_CALLBACK_TTL "+
              json.dumps({"status":result["status"],
                          "first_ttl_violation":result["first_ttl_violation"],
                          "first_safety_transition":result["first_safety_transition"],
                          "callback_metrics":timing.get("callback_metrics",{}),
                          "missing_edges":timing.get("missing_edges",[]),
                          "actual_causal_delivery_verified":False,
                          "goal_sent":False},sort_keys=True),flush=True)
        if result["status"]!="H01_PREGOAL_CALLBACK_PERIODS_ONLY_NO_GOAL":
            raise RuntimeError("H01_FIRST_REAL_CALLBACK_PERIOD_OR_GRAPH_BOUNDARY")
        return 0
    except Exception as exc:
        result["status"]="H01_LIVE_TTL_HOLD_NO_GOAL"
        result["reason"]=type(exc).__name__+":"+str(exc)
        save()
        print("AXIA_D07_H01_FIRST_REAL_TTL_BOUNDARY "+result["reason"],
              flush=True)
        return 2
    finally:
        observer.flush_events()
        ex.shutdown(timeout_sec=3.)
        observer.close()
        node.destroy_node()
        rclpy.shutdown()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--startup",type=Path,required=True)
    p.add_argument("--pregoal",type=Path,required=True)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    return run(p.parse_args())


if __name__=="__main__":
    sys.exit(main())
