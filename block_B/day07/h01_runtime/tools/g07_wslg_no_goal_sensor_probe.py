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
CLOCK_RTF_RECEIPT_MIN_STEP_SEC = .20


def analyze_timing_separately(records):
    """Read-only two-axis diagnosis, not safety admission or GPU proof.

    Measure sim progress against host monotonic receipt of SAME /clock topic
    inside the /safety/scan collection interval. Comparing scan header Hz to
    host callback Hz then distinguishes a slow simulator from a post-sim
    DDS/ROS scheduling delay. The all-angle near range verdict is INDEPENDENT.
    """
    safe = records.get("safety", [])
    clock = records.get("clock_receipts", [])
    metric = {
        "ros_clock_rtf": None,
        "sim_elapsed_sec": None,
        "wall_elapsed_sec": None,
        "safety_source_hz": None,
        "safety_wall_hz": None,
        "scan_wall_to_sim_rate_ratio": None,
        "timing_pattern": "RTF_UNMEASURED",
        "distance_unsafe_independent_of_rtf": (
            not safe or any(
                not math.isfinite(row.get("front", float("nan")))
                or not math.isfinite(row.get("side", float("nan")))
                or row["front"] <= FRONT_MIN_M
                or row["side"] <= SIDE_MIN_M for row in safe
            )
        ),
        "gpu_causality_proven": False,
        "source_rate_is_sim_time_not_wall_time": True,
        "clock_provenance": "ROS_CLOCK_HOST_MONOTONIC_RECEIPT",
    }
    if len(safe) < 2:
        return metric
    wall_span = safe[-1]["recv"] - safe[0]["recv"]
    sim_span = safe[-1]["stamp"] - safe[0]["stamp"]
    if not (math.isfinite(wall_span) and math.isfinite(sim_span)
            and wall_span > 0 and sim_span > 0):
        return metric
    count = len(safe) - 1
    metric["safety_wall_hz"] = round(count / wall_span, 6)
    metric["safety_source_hz"] = round(count / sim_span, 6)
    metric["scan_wall_to_sim_rate_ratio"] = round(sim_span / wall_span, 6)
    # Subsample /clock only over the scanner's identical wall window.
    # No comparison of wall epoch to sim stamp, no count-as-time shortcut.
    aligned = [row for row in clock
               if safe[0]["recv"] <= row["recv"] <= safe[-1]["recv"]
               and math.isfinite(row["recv"]) and math.isfinite(row["sim"])]
    if len(aligned) < 2:
        return metric
    clock_wall_span = aligned[-1]["recv"] - aligned[0]["recv"]
    clock_sim_span = aligned[-1]["sim"] - aligned[0]["sim"]
    if not (clock_wall_span > 0 and clock_sim_span > 0
            and all(b["recv"] > a["recv"] and b["sim"] > a["sim"]
                    for a, b in zip(aligned, aligned[1:]))):
        return metric
    rtf = clock_sim_span / clock_wall_span
    metric["ros_clock_rtf"] = round(rtf, 6)
    metric["wall_elapsed_sec"] = round(clock_wall_span, 6)
    metric["sim_elapsed_sec"] = round(clock_sim_span, 6)
    wall_hz, source_hz = metric["safety_wall_hz"], metric["safety_source_hz"]
    if rtf < .8:
        if (source_hz >= 8 and wall_hz < 6
                and abs(wall_hz / source_hz - rtf) <= max(.12, .35 * rtf)):
            metric["timing_pattern"] = "SIMULATION_SLOWDOWN_CONSISTENT"
        else:
            metric["timing_pattern"] = "RTF_LOW_WITH_OTHER_TIMING_UNRESOLVED"
    elif .8 <= rtf <= 1.2:
        metric["timing_pattern"] = (
            "POST_SIM_DELIVERY_OR_SCHEDULING_SUSPECT"
            if source_hz >= 8 and wall_hz < 6 else "RTF_NORMAL"
        )
    else:
        metric["timing_pattern"] = "RTF_FAST_OR_CLOCK_SKEW_UNRESOLVED"
    return metric



def correlate_first_raw_gap(records):
    """Diagnose FIRST raw callback breach without relaxing raw Scan TTL.

    A raw observer may start before the forwarded /safety/scan exists.
    Distinguish that warm-up boundary from a paired-stamp safety/receiver
    delay; never use this read-only hypothesis to authorize a Goal.
    """
    raw=records.get("raw",[])
    safe=records.get("safety",[])
    result={
        "first_gap_index":None,
        "first_gap_sec":None,
        "phase":"NO_RAW_TTL_BREACH",
        "hypothesis":"NOT_PROVEN",
        "raw_ttl_accepted":True,
        "upstream_lidar_fault_proven":False,
        "gpu_causality_proven":False,
    }
    idx=next((i for i in range(1,len(raw))
              if raw[i]["recv"]-raw[i-1]["recv"]>SCAN_TTL_SEC),None)
    if idx is None:return result
    result.update({
        "first_gap_index":idx,
        "first_gap_sec":round(raw[idx]["recv"]-raw[idx-1]["recv"],6),
        "raw_ttl_accepted":False,
        "phase":"NO_PAIRED_STAMP_EVIDENCE",
    })
    if not safe:return result
    if raw[idx]["stamp"] < safe[0]["stamp"]:
        result["phase"]="BEFORE_FIRST_SAFETY_SCAN"
        result["hypothesis"]="STARTUP_SUBSCRIPTION_OR_SIMULATION_BOUNDARY_SUSPECT"
        return result
    result["phase"]="BOTH_TOPIC_ACTIVE"
    keys=lambda rows:{round(x["stamp"],3):x for x in rows}
    matched=keys(safe)
    earlier=matched.get(round(raw[idx-1]["stamp"],3))
    later=matched.get(round(raw[idx]["stamp"],3))
    if earlier and later:
        gap=later["recv"]-earlier["recv"]
        result["paired_safety_receipt_gap_sec"]=round(gap,6)
        result["hypothesis"]=(
            "RAW_RECEIVER_PATH_DELAY_SUSPECT"
            if 0<gap<=SCAN_TTL_SEC else "MULTI_LAYER_RECEIPT_DELAY_UNRESOLVED"
        )
    return result


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
    records = {"safety": [], "raw": [], "odom": [], "clock": [],
               "clock_receipts": []}
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
        recv = time.monotonic()
        stamp = float(msg.clock.sec) + msg.clock.nanosec * 1e-9
        # ROS source /clock is simulated time. Host receipt is a distinct
        # monotonic clock; both are REQUIRED to observe actual RTF.
        if math.isfinite(stamp) and stamp > 0 and (
                not records["clock"] or stamp > records["clock"][-1]):
            records["clock"].append(stamp)
            # Sim clock can publish hundreds of messages per wall second.
            # Log host/RTF receipts sparsely so this read-only observer does
            # not steal executor slots from safety /scan subscribers.
            # Original monotonic source /clock validation is unchanged.
            if (not records["clock_receipts"] or
                    recv - records["clock_receipts"][-1]["recv"] >=
                    CLOCK_RTF_RECEIPT_MIN_STEP_SEC):
                records["clock_receipts"].append({"recv": recv, "sim": stamp})

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
        report["rtf_diagnostics"] = analyze_timing_separately(records)
        report["raw_first_gap_diagnostics"] = correlate_first_raw_gap(records)
        report["duration_observed_sec"] = round(
            time.monotonic() - first_scan_at, 3) if first_scan_at else 0
        report["source_header_vs_host_receipt_distinct"] = True
        out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        print("AXIA_G07_WSLG_NO_GOAL_SENSOR_TRUTH " +
              json.dumps({"status": report["status"],
                          "reasons": report["reasons"],
                          "metrics": report["metrics"],
                          "rtf_diagnostics": report["rtf_diagnostics"],
                          "raw_first_gap_diagnostics": report["raw_first_gap_diagnostics"]},
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
