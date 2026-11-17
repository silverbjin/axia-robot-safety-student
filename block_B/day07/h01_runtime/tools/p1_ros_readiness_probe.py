"""Read-only live Jazzy readiness probe. No goal or Twist is ever published."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
import time

from p1_clock_guard import wait_for_clock_progress


def initial_clock_wait_budget(phase: str, requested_sec: float, *, env=None) -> float:
    """Bound ONLY initial clock discovery, not operating safety TTL.

    Normal P1/P2/Owner clock discovery is capped at 45s. A CI-only real
    Gazebo G07 Goal may take 90s to cold-start in GitHub's container; all
    subsequent localization/navigation clock rechecks retain their 15s cap.
    A missing authorization bit keeps the original bounds unchanged.
    """
    if env is None:
        env = os.environ
    exact_ci_g07 = (
        hasattr(env, "get")
        and env.get("GITHUB_ACTIONS") == "true"
        and env.get("AXIA_G07_CI_SIM_GOAL_ALLOWED") == "1"
        and env.get("AXIA_P0_SIM_ONLY") == "1"
        and env.get("AXIA_P2_G07_PHYSICAL_PREFLIGHT") == "1"
    )
    cap = (90.0 if exact_ci_g07 else 45.0) if phase == "clock" else 15.0
    return min(cap, requested_sec)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True, choices=("clock", "localization", "navigation"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=35)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = {"phase": args.phase, "status": "BLOCKED", "observations": {},
              "gate_accepted": False, "certified_estop_verified": False}

    def finish(code, reason):
        result["reason"] = reason
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps({"status": result["status"], "reason": reason}))
        return code

    if os.environ.get("AXIA_P0_SIM_ONLY") != "1" or not os.environ.get("GZ_PARTITION"):
        return finish(2, "SIMULATION_MARKERS_MISSING")
    if args.timeout <= 0:
        return finish(2, "INVALID_TIMEOUT")
    import rclpy
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    from rclpy.time import Time
    from sensor_msgs.msg import LaserScan
    from nav_msgs.msg import Odometry
    from geometry_msgs.msg import PoseWithCovarianceStamped

    rclpy.init()
    node = Node("axia_p1_smoke_probe_" + args.phase,
                parameter_overrides=[Parameter("use_sim_time", value=True)],
                automatically_declare_parameters_from_overrides=True)
    watchers = []
    try:
        clock_ok, clock = wait_for_clock_progress(
            node, timeout_sec=initial_clock_wait_budget(args.phase, args.timeout, env=os.environ))
        result["observations"]["clock"] = clock
        if not clock_ok:
            return finish(2, clock["status"])
        if args.phase == "clock":
            result["status"] = "READY"
            return finish(0, "CLOCK_READY")

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT,
                         durability=DurabilityPolicy.VOLATILE)
        counters = {"scan": 0, "odom": 0, "amcl_pose": 0}
        moving = []
        def on_scan(message):
            if message.header.frame_id and message.ranges:
                counters["scan"] += 1
        def on_odom(message):
            counters["odom"] += 1
            v = message.twist.twist.linear
            w = message.twist.twist.angular
            speed = math.hypot(v.x, v.y)
            moving.append({"linear_mps": round(speed, 4),
                           "angular_radps": round(abs(w.z), 4)})
        def on_amcl(message):
            if message.header.frame_id == "map":
                counters["amcl_pose"] += 1
        watchers.append(node.create_subscription(LaserScan, "/scan", on_scan, qos))
        watchers.append(node.create_subscription(Odometry, "/odom", on_odom, qos))
        # Nav2 AMCL publishes /amcl_pose as RELIABLE + TRANSIENT_LOCAL
        # (confirmed by the actual Gazebo CI rosbag). A volatile late
        # subscriber misses the single initialization pose at rest.
        amcl_qos = QoSProfile(
            depth=1, reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )
        watchers.append(node.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", on_amcl, amcl_qos))

        from tf2_ros import Buffer, TransformListener
        buffer = Buffer()
        listener = TransformListener(buffer, node, spin_thread=False)
        action = None
        if args.phase == "navigation":
            from nav2_msgs.action import NavigateToPose
            from rclpy.action import ActionClient
            action = ActionClient(node, NavigateToPose, "/navigate_to_pose")

        began = time.monotonic()
        tf_ready = False
        action_ready = False
        while time.monotonic() - began < args.timeout:
            rclpy.spin_once(node, timeout_sec=0.15)
            try:
                tf_ready = buffer.can_transform("map", "base_link", Time())
            except Exception:
                tf_ready = False
            if action is not None:
                action_ready = action.server_is_ready()
            evidence_ready = (tf_ready and all(n > 0 for n in counters.values())
                              and (args.phase != "navigation" or action_ready))
            if evidence_ready and len(moving) >= 4:
                break

        result["observations"].update({
            "message_counts": counters, "map_to_base_tf": tf_ready,
            "navigate_to_pose_action_ready": action_ready if action else None,
            "odom_velocity_samples": moving[-20:],
        })
        if not tf_ready:
            return finish(2, "MAP_BASE_TF_UNAVAILABLE")
        if any(n <= 0 for n in counters.values()):
            return finish(2, "SENSOR_OR_AMCL_MISSING")
        if action is not None and not action_ready:
            return finish(2, "NAV2_ACTION_SERVER_NOT_READY")
        if len(moving) < 4:
            return finish(2, "ODOM_STATIONARY_EVIDENCE_INSUFFICIENT")
        # Smoke must not command motion, and unexpected motion fails closed.
        if any(x["linear_mps"] > 0.05 or x["angular_radps"] > 0.15 for x in moving[-4:]):
            return finish(2, "UNEXPECTED_SIMULATION_MOTION")
        result["status"] = "READY"
        return finish(0, "SIMULATION_READINESS_CONFIRMED_NO_GOAL")
    except Exception as exc:
        result["observations"]["exception"] = repr(exc)
        return finish(4, "PROBE_EXCEPTION")
    finally:
        for subscription in watchers:
            node.destroy_subscription(subscription)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
