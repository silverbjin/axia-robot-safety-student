#!/usr/bin/env python3
"""Read-only student D04 Gazebo→ROS RGB→C++ yolo_ros runtime sampler.

No commands, actions, /cmd_vel, fault injection or safety-stop verdict.
Uses sensor-data QoS for camera/debug/scan; reliable for detection arrays.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from rclpy.node import Node
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, LaserScan
from yolo_msgs.msg import DetectionArray


class Observer(Node):
    def __init__(self):
        super().__init__("axia_d04_student_read_only_observer")
        self.camera_frames = 0
        self.scan_frames = 0
        self.debug_frames = 0
        self.detection_frames = 0
        self.people = 0
        self.best_score = 0.0
        self.center_samples: list[tuple[float, float]] = []
        self.create_subscription(Image, "/camera/image_raw",
                                 self.camera, qos_profile_sensor_data)
        self.create_subscription(LaserScan, "/scan",
                                 self.scan, qos_profile_sensor_data)
        self.create_subscription(Image, "/yolo/cam0/debug_image",
                                 self.debug, qos_profile_sensor_data)
        self.create_subscription(DetectionArray, "/yolo/cam0/detections",
                                 self.detect, 10)

    def camera(self, message):
        if message.width > 0 and message.height > 0 and message.data:
            self.camera_frames += 1

    def scan(self, message):
        if message.ranges:
            self.scan_frames += 1

    def debug(self, message):
        if message.width > 0 and message.height > 0 and message.data:
            self.debug_frames += 1

    def detect(self, message):
        self.detection_frames += 1
        for person in message.detections:
            if person.class_name.lower() != "person":
                continue
            if not 0.0 <= person.score <= 1.0:
                continue
            self.people += 1
            self.best_score = max(self.best_score, float(person.score))
            self.center_samples.append((float(person.bbox.center.position.x),
                                        float(person.bbox.center.position.y)))

    @property
    def passed(self):
        return (self.camera_frames >= 2 and self.scan_frames >= 1
                and self.detection_frames >= 1 and self.debug_frames >= 1
                and self.people >= 1)

    def snapshot(self):
        moving = False
        if len(self.center_samples) >= 2:
            fst = self.center_samples[0]
            moving = any(abs(x - fst[0]) + abs(y - fst[1]) > 8 for x, y in self.center_samples)
        return {
            "camera_frames": self.camera_frames, "scan_frames": self.scan_frames,
            "yolo_detection_frames": self.detection_frames,
            "yolo_debug_frames": self.debug_frames, "person_detections": self.people,
            "best_person_confidence": self.best_score,
            "bbox_motion_observed": moving,
            "person_detected": self.people >= 1,
            "status": "D04_STUDENT_LIVE_PASS" if self.passed else "D04_STUDENT_LIVE_INCOMPLETE",
            "sim_only": True, "read_only": True, "goal_sent": False,
            "ros_gazebo_real_execution": self.passed,
            "safety_ttl_verified": False, "certified_estop": False,
        }


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--timeout", type=float, default=150)
    cli.add_argument("--out", type=Path, required=True)
    args = cli.parse_args()
    rclpy.init()
    node = Observer()
    deadline = time.monotonic() + max(1.0, min(args.timeout, 240))
    try:
        while time.monotonic() < deadline and not node.passed:
            rclpy.spin_once(node, timeout_sec=0.4)
        result = node.snapshot()
    finally:
        node.destroy_node()
        rclpy.shutdown()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print("D04_STUDENT_LIVE_EVIDENCE=" + str(args.out), flush=True)
    print("D04_STUDENT_LIVE_COUNTS=" + json.dumps(result), flush=True)
    if result["status"] == "D04_STUDENT_LIVE_PASS":
        print("D04_STUDENT_PERSON_DETECTED confidence=" +
              str(result["best_person_confidence"]), flush=True)
        print("D04_STUDENT_GAZEBO_YOLO_LIVE_PASS NO_GOAL NO_SAFETY_TTL", flush=True)
        return 0
    print("D04_STUDENT_GAZEBO_YOLO_LIVE_BLOCKED: inspect first missing input and logs",
          flush=True)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
