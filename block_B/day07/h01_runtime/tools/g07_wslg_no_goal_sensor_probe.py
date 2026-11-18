#!/usr/bin/env python3
"""Read-only G07 PRE-GOAL physical LaserScan/ROS delivery truth on WSL2.

Same G07 Waffle 10Hz LiDAR and original .75m/1.2m/300ms safety contract.
The tool creates ONLY ROS subscriptions; never sends Goal, Twist, Fault or
Gazebo set_pose. Output is NO_GOAL/NOT_ESTOP even when sensor window clears.
"""
import argparse
import json
import math
import os
from pathlib import Path
import statistics
import time

from p2_g07_owner_pregoal_l2 import near_ring_fraction, diagnose_pregoal_baseline
from p2_g07_relocated_no_goal_probe import sector_min

SCAN_TTL_SEC = .300
FRONT_MIN_M = .75
SIDE_MIN_M = 1.20
MIN_MESSAGES = 20


def assess_window(records):
    """Fail closed using host callback RECEIPT, not mixed simulation/header time.

    Pure testable rule, exactly the G07 pre-goal geometry limits; no
    in-place modification of any scan data and no conversion of unsafe into safe.
    """
    safe = records.get("safety", [])
    raw = records.get("raw", [])
    odom = records.get("odom", [])
    clock = records.get("clock", [])
    metrics = {}
    reasons = []
    for name, rows in (("safety", safe), ("raw", raw)):
        if len(rows) < MIN_MESSAGES:
            reasons.append(name.upper() + "_MESSAGES_MISSING")
        gaps = [b["recv"] - a["recv"] for a, b in zip(rows, rows[1:])]
        stamp_gaps = [b["stamp"] - a["stamp"] for a, b in zip(rows, rows[1:])]
        max_gap = max(gaps) if gaps else None
        max_stamp_gap = max(stamp_gaps) if stamp_gaps else None
        if (max_gap is None or max_gap > SCAN_TTL_SEC
                or any(g <= 0 for g in gaps)):
            reasons.append(name.upper() + "_RECEIPT_TTL_300MS_BLOCKED")
        if not stamp_gaps or any(g <= 0 for g in stamp_gaps):
            reasons.append(name.upper() + "_SOURCE_STAMP_NOT_MONOTONIC")
        metrics[name] = {
            "count": len(rows),
            "max_receipt_gap_sec": round(max_gap, 6) if max_gap is not None else None,
            "max_source_stamp_delta_sec": round(max_stamp_gap, 6) if max_stamp_gap is not None else None,
            "first_receipt_ttl_breach_at_index": next(
                (i + 1 for i, gap in enumerate(gaps) if gap > SCAN_TTL_SEC), None),
        }
    if len(safe) < MIN_MESSAGES:
        reasons.append("PREG0AL_CLEAR_SAMPLES_NOT_PROVEN")
    else:
        clear = [row for row in safe if row["front"] > FRONT_MIN_M
                 and row["side"] > SIDE_MIN_M]
        if len(clear) != len(safe):
            reasons.append("OWNER_PREGOAL_NOT_CLEAR_BEFORE_FIXTURE")
        metrics["safety"]["clear_count"] = len(clear)
        metrics["safety"]["front_median_m"] = round(statistics.median(x["front"] for x in safe), 6)
        metrics["safety"]["side_median_m"] = round(statistics.median(x["side"] for x in safe), 6)
        fractions = [row["near"] for row in safe if row["near"] is not None]
        metrics["safety"]["near_ring_fraction_median"] = (
            round(statistics.median(fractions), 6) if fractions else None)
        metrics["safety"]["all_azimuths_near_unexplained"] = (
            bool(fractions) and statistics.median(fractions) >= .95)
    if len(odom) < 3:
        reasons.append("ODOM_STATIONARY_UNPROVEN")
    elif any(abs(x["vx"]) >= .015 or abs(x["wz"]) >= .05 for x in odom):
        reasons.append("ODOM_NOT_STATIONARY_NO_GOAL")
    if len(clock) < 2 or clock[-1] <= clock[0] or any(b <= a for a, b in zip(clock, clock[1:])):
        reasons.append("CLOCK_TIME_NOT_MONOTONIC")
    return {
        "schema": "axia_g07_wslg_no_goal_sensor_truth_v1",
        "status": "NO_GOAL_SENSOR_WINDOW_CLEAR_CANDIDATE" if not reasons else "NO_GOAL_SENSOR_UNSAFE_HOLD",
        "reasons": list(dict.fromkeys(reasons)),
        "metrics": metrics,
        "odom_count": len(odom),
        "clock_count": len(clock),
        "scan_ttl_limit_sec": SCAN_TTL_SEC,
        "original_front_m_strict_greater_than": FRONT_MIN_M,
        "original_side_m_strict_greater_than": SIDE_MIN_M,
        "goal_sent": False,
        "fixture_moved": False,
        "fault_injected": False,
        "certified_estop": False,
        "wslg_renderer_causality_proven": False,
        "owner_l3_accepted": False,
        "window_does_not_prove_extended_owner_ttl_stability": True,
    }


def run(out, duration):
    if (os.environ.get("ROS_DISTRO") != "jazzy"
            or os.environ.get("AXIA_P0_SIM_ONLY") != "1"
            or os.environ.get("AXIA_G07_OWNER_SENSOR_TRUTH_NO_GOAL") != "1"
            or os.environ.get("AXIA_G07_CI_SIM_GOAL_ALLOWED", "0") != "0"
            or os.environ.get("AXIA_G07_TASK04_OWNER_MOVING_L3", "0") != "0"
            or (os.environ.get("GITHUB_ACTIONS") == "true"
                and os.environ.get("AXIA_G07_CI_SENSOR_TRUTH_NO_GOAL") != "1")
            or (os.environ.get("GITHUB_ACTIONS") != "true"
                and os.environ.get("AXIA_G07_CI_SENSOR_TRUTH_NO_GOAL", "0") != "0")
            or not os.environ.get("GZ_PARTITION", "").startswith("axia_p2_")):
        raise RuntimeError("G07_READONLY_NO_GOAL_WSL2_OWNER_SCOPE_INVALID")
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan
    from nav_msgs.msg import Odometry
    from rosgraph_msgs.msg import Clock
    out.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    rclpy.init()
    node = rclpy.create_node("axia_g07_wslg_no_goal_scan_truth")
    records = {"safety": [], "raw": [], "odom": [], "clock": []}
    first_scan_at = None

    def scan_callback(msg, kind):
        nonlocal first_scan_at
        front = [float(v) for i, v in enumerate(msg.ranges)
                 if abs(msg.angle_min + i * msg.angle_increment) <= .18
                 and type(v) in (float, int) and math.isfinite(v)
                 and msg.range_min <= v <= msg.range_max]
        side = sector_min(msg)
        if not front or side is None:
            return
        stamp = float(msg.header.stamp.sec) + msg.header.stamp.nanosec * 1e-9
        if not math.isfinite(stamp) or stamp <= 0:
            return
        now = time.monotonic()
        if first_scan_at is None:
            first_scan_at = now
        near, beams = near_ring_fraction(msg)
        records[kind].append({"recv": now, "stamp": stamp,
                              "front": min(front), "side": side,
                              "near": near, "beams": beams})

    def on_odom(msg):
        records["odom"].append({"vx": msg.twist.twist.linear.x,
                                 "wz": msg.twist.twist.angular.z})

    def on_clock(msg):
        stamp = float(msg.clock.sec) + msg.clock.nanosec * 1e-9
        # Store only advancing samples; duplicates do not imply progress.
        if stamp > 0 and (not records["clock"] or stamp > records["clock"][-1]):
            records["clock"].append(stamp)

    subs = [
        node.create_subscription(LaserScan, "/safety/scan",
                                 lambda m: scan_callback(m, "safety"), qos_profile_sensor_data),
        node.create_subscription(LaserScan, "/scan",
                                 lambda m: scan_callback(m, "raw"), qos_profile_sensor_data),
        node.create_subscription(Odometry, "/odom", on_odom, qos_profile_sensor_data),
        node.create_subscription(Clock, "/clock", on_clock, qos_profile_sensor_data),
    ]
    try:
        deadline = time.monotonic() + duration + 8
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.08)
            if first_scan_at and time.monotonic() - first_scan_at >= duration:
                break
        report = assess_window(records)
        report["duration_observed_sec"] = round(
            time.monotonic() - first_scan_at, 3) if first_scan_at else 0
        report["source_header_vs_host_receipt_distinct"] = True
        out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        print("AXIA_G07_WSLG_NO_GOAL_SENSOR_TRUTH " +
              json.dumps({"status": report["status"],
                          "reasons": report["reasons"],
                          "metrics": report["metrics"]},
                         sort_keys=True), flush=True)
        print("D06_GAZEBO_LIVE_RELEASE=HOLD CERTIFIED_ESTOP=false", flush=True)
        return 0 if report["status"] == "NO_GOAL_SENSOR_WINDOW_CLEAR_CANDIDATE" else 3
    finally:
        for sub in subs:
            node.destroy_subscription(sub)
        node.destroy_node()
        rclpy.shutdown()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--duration-sec", type=int, default=20)
    args = p.parse_args()
    if not 10 <= args.duration_sec <= 30:
        raise SystemExit("G07_NO_GOAL_SENSOR_PROBE_DURATION_OUT_OF_BOUNDS")
    try:
        return run(args.output, args.duration_sec)
    except (OSError, ValueError, RuntimeError) as exc:
        print("AXIA_G07_WSLG_NO_GOAL_SENSOR_PROBE_BLOCKED " +
              type(exc).__name__ + ":" + str(exc), flush=True)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
