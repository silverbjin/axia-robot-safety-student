#!/usr/bin/env python3
"""G07 relocated physical obstacle LaserScan cross-check in real Harmonic, NO GOAL.

This does not infer a model pose from set_pose ACK or claim collision truth.
The earlier gz model CLI timed out 3 times in actual CI. Use actual ROS
/safety/scan in the expected *side bearing* before and after native set_pose.
"""
from __future__ import annotations

import argparse
from collections import deque
import json
import math
import os
from pathlib import Path
import statistics
import time

from p2_l3_gz_fixture import move
from p2_g07_spawn_contract import official_tb3_spawn

# Static sandbox is unchanged; only this PRELOADED G07 injected cylinder moves.
# The new location lies near the center of the longer map (-2,-.5)->(-1.7,.7)
# route. The stationary Waffle is 0.773m away, not in collision.
DEMO_WORLD_POSE = (-1.81, 0.25)
BEARING_RAD = math.atan2(.75, .19)
EXPECTED_RELOCATED_SURFACE_M = (.55, .95)
MIN_BEARING_CHANGE_M = .15


def sector_min(scan, bearing=BEARING_RAD):
    """Use actual LaserScan angles/range limits; fail closed on bad fields."""
    inc = scan.angle_increment
    start = scan.angle_min
    lo, hi = scan.range_min, scan.range_max
    if any(type(v) not in (float, int) or not math.isfinite(v)
           for v in (inc, start, lo, hi, bearing)):
        return None
    if not (0 < inc < 1 and 0 <= lo < hi and -math.pi <= bearing <= math.pi):
        return None
    vals = []
    for idx, val in enumerate(scan.ranges):
        beam = start + idx * inc
        delta = math.atan2(math.sin(beam - bearing), math.cos(beam - bearing))
        if abs(delta) <= .12 and type(val) in (int, float) and math.isfinite(val):
            if lo <= val <= hi:
                vals.append(float(val))
    return min(vals) if vals else None


def run(output: Path) -> dict:
    if (os.environ.get("ROS_DISTRO") != "jazzy"
            or os.environ.get("AXIA_P0_SIM_ONLY") != "1"
            or not os.environ.get("GZ_PARTITION", "").startswith("axia_p2_")):
        raise ValueError("SIMULATION_ONLY_GZ_PARTITION_REQUIRED")
    if official_tb3_spawn() != (-2.0, -0.5, 0.0):
        raise ValueError("OFFICIAL_WORLD_SPAWN_CHANGED")

    import rclpy
    from sensor_msgs.msg import LaserScan
    from rclpy.qos import qos_profile_sensor_data
    rclpy.init()
    node = rclpy.create_node("axia_g07_relocated_no_goal_scan_probe")
    received = deque(maxlen=64)

    def on_scan(msg):
        val = sector_min(msg)
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if val is not None and type(stamp) in (int, float) and math.isfinite(stamp):
            received.append((time.monotonic(), stamp, val))

    subscription = node.create_subscription(
        LaserScan, "/safety/scan", on_scan, qos_profile_sensor_data)
    try:
        baseline_end = time.monotonic() + 6
        while time.monotonic() < baseline_end and len(received) < 3:
            rclpy.spin_once(node, timeout_sec=.15)
        if len(received) < 3:
            raise RuntimeError("G07_RELOCATION_PREMOVE_REAL_SCAN_UNAVAILABLE")
        baseline_rows = list(received)[-3:]
        baseline = statistics.median(x[2] for x in baseline_rows)
        last_ros_stamp = max(x[1] for x in baseline_rows)
        print("G07_RELOCATION_L2_PREMOVE_REAL_SCAN "
              f"sector_m={baseline:.3f} bearing_rad={BEARING_RAD:.3f}",
              flush=True)
        print("G07_RELOCATION_L2_SET_POSE_BEGIN", flush=True)
        ack = move(*DEMO_WORLD_POSE, demo_corridor=True)
        ack_at = time.monotonic()
        print("G07_RELOCATION_L2_SET_POSE_ACK", flush=True)
        threshold = baseline - MIN_BEARING_CHANGE_M
        consecutive = []
        observed = None
        deadline = time.monotonic() + 9
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.10)
            if not received:
                continue
            t, stamp, val = received[-1]
            if t <= ack_at or stamp <= last_ros_stamp:
                continue
            qualifies = (EXPECTED_RELOCATED_SURFACE_M[0] <= val <=
                         EXPECTED_RELOCATED_SURFACE_M[1] and val <= threshold)
            if qualifies and (not consecutive or stamp > consecutive[-1][1]):
                consecutive.append((t, stamp, val))
            elif not qualifies:
                consecutive.clear()
            if len(consecutive) >= 2:
                observed = statistics.median(x[2] for x in consecutive[-2:])
                break
        print("G07_RELOCATION_L2_LIDAR_AFTER_ACK "
              f"baseline={baseline:.3f} last={received[-1][2]:.3f} "
              f"qualified={observed is not None}", flush=True)
        if observed is None:
            raise RuntimeError("G07_RELOCATED_PHYSICAL_LIDAR_DELTA_NOT_PROVEN")
        report = {
            "status": "G07_RELOCATED_PHYSICAL_LIDAR_OBSERVED_NO_GOAL",
            "target_world_xy_from_set_pose": list(DEMO_WORLD_POSE),
            "model_pose_readback": False,
            "native_set_pose_ack": bool(ack),
            "physical_lidar_crosscheck": True,
            "bearing_rad": BEARING_RAD,
            "baseline_sector_m": baseline,
            "after_sector_m": observed,
            "observed_delta_m": baseline - observed,
            "ros_scan_stamp_progressed": True,
            "goal_sent": False, "fault_injected": False,
            "collision_ground_truth": False, "gate_accepted": False,
            "certified_estop": False, "moving_goal_l3": "NOT_RUN",
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                          encoding="utf-8")
        return report
    finally:
        node.destroy_subscription(subscription)
        node.destroy_node()
        rclpy.shutdown()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.output)
        print("P2_G07_REAL_GAZEBO_RELOCATED_LIDAR_L2_NO_GOAL "
              f"before={result['baseline_sector_m']:.3f} "
              f"after={result['after_sector_m']:.3f} "
              "L3_NOT_RUN CONTACT_GROUND_TRUTH_UNVERIFIED", flush=True)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print("P2_G07_RELOCATED_PROBE_BLOCKED: " +
              type(exc).__name__ + ": " + str(exc), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
