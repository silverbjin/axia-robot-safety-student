#!/usr/bin/env python3
"""Publish one explicitly approved INITIAL localization estimate in SIMULATION ONLY.

No Twist or NavigateToPose goal is ever published here. Map occupancy is
validated before a pose can be published. NOT a safety-rated localization proof.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

from p0_pose_policy import inspect_candidate_cells
from p1_clock_guard import wait_for_clock_progress


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--x", type=float, required=True)
    parser.add_argument("--y", type=float, required=True)
    parser.add_argument("--yaw", type=float, required=True)
    parser.add_argument("--radius", type=float, default=0.35)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ack-initial-pose", action="store_true")
    parser.add_argument("--amcl-service-ack", action="store_true",
                        help="Use official AMCL SetInitialPose service; require response, never infer localization")
    parser.add_argument("--diagnose-only", action="store_true",
                        help="Capture live map cell evidence; NEVER publish initial pose")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = {"result": "BLOCKED", "position": [args.x, args.y, args.yaw],
              "radius_clearance_m": args.radius, "scope": "simulation_initialpose_only"}

    def finish(message: str, code: int) -> int:
        result["reason"] = message
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(message)
        return code

    if args.ack_initial_pose and args.diagnose_only:
        return finish("INITIAL_POSE_BLOCKED: choose only one of --ack-initial-pose/--diagnose-only", 2)
    if not args.ack_initial_pose and not args.diagnose_only:
        return finish("INITIAL_POSE_BLOCKED: explicit --ack-initial-pose required", 2)
    if os.environ.get("AXIA_P0_SIM_ONLY") != "1" or not os.environ.get("GZ_PARTITION"):
        return finish("INITIAL_POSE_BLOCKED: isolated Gazebo simulation marker missing", 2)
    if any(not math.isfinite(v) for v in (args.x, args.y, args.yaw, args.radius)):
        return finish("INITIAL_POSE_BLOCKED: invalid coordinates", 2)

    import rclpy
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
    from nav_msgs.msg import OccupancyGrid
    from geometry_msgs.msg import PoseWithCovarianceStamped

    rclpy.init()
    node = Node(
        "axia_p0_initialpose",
        parameter_overrides=[Parameter("use_sim_time", value=True)],
        automatically_declare_parameters_from_overrides=True,
    )
    try:
        # Only ROS simulation time is permitted. Node initialized with -p use_sim_time:=true.
        if not node.get_parameter("use_sim_time").value:
            return finish("INITIAL_POSE_BLOCKED: use_sim_time not enabled", 2)
        data = []
        reliable_latched = QoSProfile(
            depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        sub = node.create_subscription(
            OccupancyGrid, "/map", lambda msg: data.append(msg), reliable_latched
        )
        deadline = time.monotonic() + 15
        while not data and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.5)
        if not data:
            return finish("INITIAL_POSE_BLOCKED: no live /map OccupancyGrid", 2)
        msg = data[-1]
        if msg.header.frame_id != "map":
            return finish("INITIAL_POSE_BLOCKED: map frame mismatch", 2)
        q = msg.info.origin.orientation
        origin_yaw = math.atan2(2 * (q.w * q.z + q.x * q.y),
                                1 - 2 * (q.y * q.y + q.z * q.z))
        cells = inspect_candidate_cells(
            x=args.x, y=args.y, radius=args.radius,
            width=msg.info.width, height=msg.info.height,
            resolution=msg.info.resolution,
            origin_x=msg.info.origin.position.x,
            origin_y=msg.info.origin.position.y,
            origin_yaw=origin_yaw,
            data=list(msg.data)
        )
        result["map_meta"] = {
            "width": msg.info.width, "height": msg.info.height,
            "resolution": msg.info.resolution,
            "frame_id": msg.header.frame_id,
            "origin_xy": [msg.info.origin.position.x, msg.info.origin.position.y],
            "origin_yaw": origin_yaw,
            "data_sha256": hashlib.sha256(
                bytes((int(v) & 0xff) for v in msg.data)
            ).hexdigest(),
        }
        result["candidate_cells"] = cells
        reasons = cells["reasons"]
        if args.diagnose_only:
            result["result"] = "DIAGNOSIS_ONLY"
            result["would_block"] = bool(reasons)
            return finish(
                "INITIAL_POSE_DIAGNOSIS_ONLY: no pose published; "
                + ("gate would BLOCK" if reasons else "grid gate would ALLOW"),
                0,
            )
        if reasons:
            return finish("INITIAL_POSE_BLOCKED: " + "; ".join(reasons), 2)
        clock_ready, clock_diag = wait_for_clock_progress(node, timeout_sec=12.0)
        result["clock_diagnostics"] = clock_diag
        if not clock_ready:
            return finish("INITIAL_POSE_BLOCKED: " + clock_diag["status"], 2)
        # Build exactly the same map-checked pose for either delivery protocol.
        # P0 staged startup requires --amcl-service-ack; P1 legacy Topic path
        # is intentionally preserved until its own integration regression.
        pose = PoseWithCovarianceStamped()
        pose.header.frame_id = "map"
        pose.pose.pose.position.x = args.x
        pose.pose.pose.position.y = args.y
        pose.pose.pose.orientation.z = math.sin(args.yaw / 2)
        pose.pose.pose.orientation.w = math.cos(args.yaw / 2)
        pose.pose.covariance[0] = 0.01
        pose.pose.covariance[7] = 0.01
        pose.pose.covariance[35] = 0.03
        if args.amcl_service_ack:
            # This is a delivery ACK only. The downstream AMCL/TF probe must
            # still establish /amcl_pose and map -> base_link before Navigation.
            from nav2_msgs.srv import SetInitialPose
            from p0_initialpose_delivery import wait_for_amcl_ack
            client = node.create_client(SetInitialPose, "/set_initial_pose")
            request = SetInitialPose.Request()
            pose.header.stamp = node.get_clock().now().to_msg()
            request.pose = pose
            delivery = wait_for_amcl_ack(
                node, client, request, spin_once=rclpy.spin_once,
                wait_sec=12.0, response_sec=12.0)
            # Record actual graph endpoint names to diagnose namespace differences.
            try:
                result["discovered_pose_services"] = [
                    name for name, types in node.get_service_names_and_types()
                    if "nav2_msgs/srv/SetInitialPose" in types
                ]
            except Exception as exc:
                result["service_graph_error"] = repr(exc)
            result["delivery"] = delivery
            if not delivery["acknowledged"]:
                return finish("INITIAL_POSE_BLOCKED: " + delivery["status"], 2)
            result["result"] = "POSE_DELIVERY_ACKNOWLEDGED"
            return finish(
                "INITIAL_POSE_DELIVERY_ACKNOWLEDGED: AMCL service response received; "
                "localization/TF NOT yet verified", 0)

        # Legacy P1 compatibility path. This is NOT acknowledgement.
        pub = node.create_publisher(PoseWithCovarianceStamped, "/initialpose", 10)
        for i in range(3):
            pose.header.stamp = node.get_clock().now().to_msg()
            pub.publish(pose)
            rclpy.spin_once(node, timeout_sec=0.25)
        result["result"] = "POSE_PUBLISHED"
        return finish("INITIAL_POSE_PUBLISHED: map cell clearance checked; Nav2 localization NOT yet accepted", 0)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
