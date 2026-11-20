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

def _first_gap_local_clock_rtf(clocks, previous_host, current_host):
    """Short matched HOST callback window; never subtract sim absolute epochs."""
    inside=[(wall,sim) for wall,sim in clocks
            if _ok_num(wall) and _ok_num(sim)
            and previous_host<=wall<=current_host]
    if len(inside)<2:
        return None
    host=inside[-1][0]-inside[0][0]
    sim=inside[-1][1]-inside[0][1]
    return round(sim/host,6) if host>0 and sim>=0 else None


def assess_pregoal_samples(samples, *, window_sec=WINDOW_SEC):
    """One read-only pre-Goal test; all first-violation numbers survive HOLD."""
    result=dict(schema="axia.g07.scan_wall_pregoal.v1",status="HOLD",
                first_failure="SCAN_PREFLIGHT_INSUFFICIENT_EVIDENCE",
                goal_sent=False,certified_estop=False,
                scan_wall_limit_ms=SCAN_LIMIT_MS,
                sensor_sim_period_limit_ms=HEADER_SIM_LIMIT_MS,
                native_gazebo_publication_boundary="NOT_MEASURED",
                scan_generation_vs_bridge_root_cause="UNDETERMINED",
                window_sec=window_sec,topic_results={},
                first_scan_timing_boundary=None,
                local_window_rtf_estimate=None)
    if not isinstance(samples,dict):
        return result
    clocks=samples.get("clock",[])
    odom=samples.get("odom",[])
    if (not isinstance(clocks,list) or not isinstance(odom,list)
            or len(clocks)<4 or len(odom)<4
            or any(not isinstance(p,(list,tuple)) or len(p)!=2 or
                   not _ok_num(p[0]) or not _ok_num(p[1]) for p in clocks)):
        result["first_failure"]="SCAN_PREFLIGHT_CLOCK_ODOM_ABSENT"
        return result
    elapsed=clocks[-1][0]-clocks[0][0]
    sim_elapsed=clocks[-1][1]-clocks[0][1]
    if elapsed<=0 or sim_elapsed<=0 or any(b[0]<=a[0] for a,b in zip(clocks,clocks[1:])):
        result["first_failure"]="SCAN_PREFLIGHT_CLOCK_INVALID"
        return result
    result["local_window_rtf_estimate"]=round(sim_elapsed/elapsed,6)
    result["clock_sample_count"]=len(clocks)
    result["odom_sample_count"]=len(odom)
    result["clock_max_wall_gap_ms"]=round(max(
        (b[0]-a[0])*1000 for a,b in zip(clocks,clocks[1:])),6)
    if all(isinstance(p,(list,tuple)) and len(p)==2 and _ok_num(p[0])
           for p in odom):
        result["odom_max_wall_gap_ms"]=round(max(
            (b[0]-a[0])*1000 for a,b in zip(odom,odom[1:])),6)
    # Gate the other hard real-time observer boundaries too. A Scan-only
    # success cannot mask 300ms Odom/Clock delivery loss on the same graph.
    if result.get("odom_max_wall_gap_ms",0)>=300 or result["clock_max_wall_gap_ms"]>=300:
        result["first_failure"]="SCAN_PREFLIGHT_CLOCK_ODOM_INTERVAL_BREACH"
        return result
    failures=[]
    for topic in ("scan","safety_scan"):
        points=samples.get(topic,[])
        if not isinstance(points,list) or len(points)<MIN_PAIRS+1:
            result["first_failure"]="SCAN_PREFLIGHT_INSUFFICIENT_EVIDENCE"
            return result
        if any(not isinstance(p,(list,tuple)) or len(p)!=2
               or not (_ok_num(p[0]) and _ok_num(p[1])) for p in points):
            return result
        intervals=[((b[0]-a[0])*1000,(b[1]-a[1])*1000,a[0],b[0],a[1],b[1])
                   for a,b in zip(points,points[1:])]
        if any(w<=0 or s<=0 for w,s,*_ in intervals):
            result["first_failure"]="SCAN_PREFLIGHT_CLOCK_OR_STAMP_REGRESSION"
            return result
        max_wall=max(w for w,*_ in intervals)
        max_sim=max(s for _,s,*_ in intervals)
        first=next(((a,b,w,s,hs0,hs1) for w,s,a,b,hs0,hs1 in intervals
                    if w>SCAN_LIMIT_MS or s>HEADER_SIM_LIMIT_MS),None)
        result["topic_results"][topic]=dict(
            pairs=len(intervals),max_wall_gap_ms=round(max_wall,6),
            max_header_sim_gap_ms=round(max_sim,6),
            first_violation=tuple(round(v,6) for v in first) if first else None)
        if first is not None:
            a,b,w,s,hs0,hs1=first
            failures.append(dict(
                topic=topic,previous_rx_host_monotonic=round(a,9),
                current_rx_host_monotonic=round(b,9),gap_ms=round(w,6),
                previous_header_sim=round(hs0,9),
                current_header_sim=round(hs1,9),
                header_sim_gap_ms=round(s,6),
                wall_limit_ms=SCAN_LIMIT_MS,sim_header_limit_ms=HEADER_SIM_LIMIT_MS,
                local_clock_rtf_estimate=_first_gap_local_clock_rtf(clocks,a,b),
                clock_callback_count_inside_gap=sum(a<=t<=b for t,_ in clocks),
                odom_callback_count_inside_gap=sum(
                    a<=p[0]<=b for p in odom
                    if isinstance(p,(tuple,list)) and len(p)>0 and _ok_num(p[0])),
                native_gazebo_publication_host_time="NOT_MEASURED"))
        if points[-1][0]-points[0][0]<min(window_sec*.8,9):
            result["first_failure"]="SCAN_PREFLIGHT_WINDOW_INSUFFICIENT"
            return result
    # 12s witness must span *this same window*. A /clock deque limited
    # to 400 samples dropped early data when Gazebo emitted ~100Hz.
    # Never treat a tail-only average RTF as the FIRST gap's local RTF.
    scan_start=min(samples[k][0][0] for k in ("scan","safety_scan"))
    scan_end=max(samples[k][-1][0] for k in ("scan","safety_scan"))
    coverage=(clocks[0][0]<=scan_start+.3 and
              clocks[-1][0]>=scan_end-.3)
    result["clock_coverage"]=("FULL_PREG0AL_WINDOW" if coverage
        else "INSUFFICIENT_FOR_FULL_PREG0AL_WINDOW")
    if failures:
        result["first_scan_timing_boundary"]=min(
            failures,key=lambda r:(r["current_rx_host_monotonic"],
                                   0 if r["topic"]=="scan" else 1))
        result["first_failure"]="SCAN_PREFLIGHT_300MS_OR_HEADER_PERIOD_BREACH"
        return result
    if not coverage:
        result["first_failure"]="SCAN_PREFLIGHT_CLOCK_RETENTION_INSUFFICIENT"
        return result
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
    records={name:deque(maxlen=4096 if name=="clock" else 400) for name in ("scan","safety_scan","clock","odom")}
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
        print("AXIA_G07_PREGOAL_SCAN_FIRST_NUMERIC "+
              json.dumps({"first_failure":report["first_failure"],
                          "first_scan_timing_boundary":report.get("first_scan_timing_boundary"),
                          "topic_results":report.get("topic_results"),
                          "local_window_rtf_estimate":report.get("local_window_rtf_estimate"),
                          "clock_max_wall_gap_ms":report.get("clock_max_wall_gap_ms"),
                          "clock_coverage":report.get("clock_coverage"),
                          "odom_max_wall_gap_ms":report.get("odom_max_wall_gap_ms")},
                         sort_keys=True),flush=True)
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
