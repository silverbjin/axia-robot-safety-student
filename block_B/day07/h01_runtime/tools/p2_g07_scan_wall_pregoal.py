#!/usr/bin/env python3
"""Read-only same-Gazebo-session G07 NO_GOAL Scan wall/sim cadence preflight.

Owner/CI opt-in only. NEVER publishes Goal, cmd_vel or changes params/TTL.
A ROS Scan receive stamp cannot prove Gazebo-native publisher/bridge latency.
"""
import argparse
from collections import deque
import json
import math
from pathlib import Path
import time

SCAN_LIMIT_MS=300.0
HEADER_SIM_LIMIT_MS=150.0
MIN_PAIRS=15
WINDOW_SEC=12.0
WARMUP_SEC=2.0

def _ok_num(v):
    return type(v) in (int,float) and math.isfinite(v)

def assess_pregoal_samples(samples, *, window_sec=WINDOW_SEC):
    """Only same-domain timestamp differences; result can never send Goal."""
    result=dict(schema="axia.g07.scan_wall_pregoal.v1",status="HOLD",
                first_failure="SCAN_PREFLIGHT_INSUFFICIENT_EVIDENCE",
                goal_sent=False,certified_estop=False,
                scan_wall_limit_ms=SCAN_LIMIT_MS,
                sensor_sim_period_limit_ms=HEADER_SIM_LIMIT_MS,
                native_gazebo_publication_boundary="NOT_MEASURED",
                scan_generation_vs_bridge_root_cause="UNDETERMINED",
                window_sec=window_sec,topic_results={})
    for topic in ("scan","safety_scan"):
        points=samples.get(topic,[]) if isinstance(samples,dict) else []
        if not isinstance(points,list) or len(points)<MIN_PAIRS+1:
            return result
        if any(not isinstance(p,(list,tuple)) or len(p)!=2
               or not (_ok_num(p[0]) and _ok_num(p[1])) for p in points):
            return result
        intervals=[((b[0]-a[0])*1000,(b[1]-a[1])*1000,a[0],b[0])
                   for a,b in zip(points,points[1:])]
        if any(w<=0 or s<=0 for w,s,_,_ in intervals):
            result["first_failure"]="SCAN_PREFLIGHT_CLOCK_OR_STAMP_REGRESSION"
            return result
        max_wall=max(w for w,_,_,_ in intervals)
        max_sim=max(s for _,s,_,_ in intervals)
        first=next(((round(a,9),round(b,9),round(w,6),round(s,6))
                   for w,s,a,b in intervals if w>SCAN_LIMIT_MS or s>HEADER_SIM_LIMIT_MS),None)
        result["topic_results"][topic]=dict(
            pairs=len(intervals),max_wall_gap_ms=round(max_wall,6),
            max_header_sim_gap_ms=round(max_sim,6),
            first_violation=first)
        if first is not None:
            result["first_failure"]="SCAN_PREFLIGHT_300MS_OR_HEADER_PERIOD_BREACH"
            return result
        if points[-1][0]-points[0][0]<min(window_sec*.8,9):
            result["first_failure"]="SCAN_PREFLIGHT_WINDOW_INSUFFICIENT"
            return result
    clocks=samples.get("clock",[]) if isinstance(samples,dict) else []
    odom=samples.get("odom",[]) if isinstance(samples,dict) else []
    if (len(clocks)<4 or len(odom)<4 or
        any(not _ok_num(p[0]) or not _ok_num(p[1]) for p in clocks)):
        result["first_failure"]="SCAN_PREFLIGHT_CLOCK_ODOM_ABSENT"
        return result
    elapsed=clocks[-1][0]-clocks[0][0]
    sim_elapsed=clocks[-1][1]-clocks[0][1]
    if elapsed<=0 or sim_elapsed<=0:
        result["first_failure"]="SCAN_PREFLIGHT_CLOCK_INVALID"
        return result
    result["local_window_rtf_estimate"]=round(sim_elapsed/elapsed,6)
    result["clock_sample_count"]=len(clocks)
    result["odom_sample_count"]=len(odom)
    result["status"]="PASS_SCOPED_RECEIVED_SCAN_ONLY"
    result["first_failure"]="NONE"
    return result

def run(output,window_sec=WINDOW_SEC):
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan
    from nav_msgs.msg import Odometry
    from rosgraph_msgs.msg import Clock
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    records={name:deque(maxlen=400) for name in ("scan","safety_scan","clock","odom")}
    def scan_cb(name):
        def cb(msg):
            records[name].append((time.monotonic(),
                msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9))
        return cb
    def clock_cb(msg):
        records["clock"].append((time.monotonic(),
            msg.clock.sec+msg.clock.nanosec*1e-9))
    def odom_cb(msg):
        records["odom"].append((time.monotonic(),
            msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9))
    rclpy.init()
    node=rclpy.create_node("axia_g07_scan_wall_pregoal_ro")
    subs=[node.create_subscription(LaserScan,"/scan",scan_cb("scan"),qos_profile_sensor_data),
          node.create_subscription(LaserScan,"/safety/scan",scan_cb("safety_scan"),qos_profile_sensor_data),
          node.create_subscription(Clock,"/clock",clock_cb,qos_profile_sensor_data),
          node.create_subscription(Odometry,"/odom",odom_cb,qos_profile_sensor_data)]
    t0=time.monotonic()
    try:
        while time.monotonic()-t0<WARMUP_SEC:
            rclpy.spin_once(node,timeout_sec=.04)
        for rows in records.values():rows.clear()
        t1=time.monotonic()
        while time.monotonic()-t1<window_sec:
            rclpy.spin_once(node,timeout_sec=.04)
        report=assess_pregoal_samples({k:list(v) for k,v in records.items()},
                                      window_sec=window_sec)
    finally:
        for sub in subs:node.destroy_subscription(sub)
        node.destroy_node()
        rclpy.try_shutdown()
    output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    if report["status"]!="PASS_SCOPED_RECEIVED_SCAN_ONLY":
        print("AXIA_G07_PREGOAL_SCAN_WALL=HOLD "+report["first_failure"],flush=True)
        return 3
    print("AXIA_G07_PREGOAL_SCAN_WALL=PASS_SCOPED_RECEIVED_SCAN_ONLY L3_NOT_RUN",flush=True)
    return 0

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        return run(args.output)
    except Exception as exc:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(dict(
            status="HOLD",goal_sent=False,
            first_failure="SCAN_PREFLIGHT_OBSERVER_EXCEPTION",
            exception_type=type(exc).__name__,certified_estop=False))+"\n")
        print("AXIA_G07_PREGOAL_SCAN_WALL=HOLD SCAN_PREFLIGHT_OBSERVER_EXCEPTION",flush=True)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
