#!/usr/bin/env python3
"""Read-only D05 LIVE monitor; relies on unchanged PRIVATE D05 range Observer.

Never calculates substitute range or publishes ROS messages.
Checks actual registered RGB/Depth, upstream YOLO, and private status data.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import time

RGB = "/axia/d05/rgbd/image"
DEPTH = "/axia/d05/rgbd/depth_image"
DETECT = "/yolo/cam0/detections"
STATUS = "/axia/d05/person_range_status"


def run(phase: str, timeout: float) -> dict:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Image
    from std_msgs.msg import String
    from yolo_msgs.msg import DetectionArray

    class Monitor(Node):
        def __init__(self):
            super().__init__("axia_d05_live_readonly_monitor")
            self.rgb = []
            self.depth = []
            self.yolo_count = 0
            self.person_count = 0
            self.valid = []
            self.unknown = []
            self.first_reason = None
            self.create_subscription(Image, RGB, self.on_rgb, qos_profile_sensor_data)
            self.create_subscription(Image, DEPTH, self.on_depth, qos_profile_sensor_data)
            self.create_subscription(DetectionArray, DETECT, self.on_yolo, qos_profile_sensor_data)
            self.create_subscription(String, STATUS, self.on_status, 10)

        def on_rgb(self, msg):
            if len(self.rgb) < 40:
                self.rgb.append((msg.header.frame_id, msg.width, msg.height,
                                 msg.header.stamp.sec*10**9+msg.header.stamp.nanosec))

        def on_depth(self, msg):
            if len(self.depth) < 40:
                self.depth.append((msg.header.frame_id, msg.width, msg.height,
                                   msg.header.stamp.sec*10**9+msg.header.stamp.nanosec,
                                   msg.encoding))

        def on_yolo(self, msg):
            self.yolo_count += 1
            self.person_count += sum(1 for d in msg.detections
                                     if str(d.class_name).lower() == "person")

        def on_status(self, msg):
            try:
                data = json.loads(msg.data)
            except (ValueError, TypeError):
                return
            state, reason = data.get("status"), data.get("reason")
            if self.first_reason is None:
                self.first_reason = [state, reason]
            if (state == "VALID" and isinstance(data.get("distance_m"), (float,int))
                    and math.isfinite(data["distance_m"])
                    and data.get("valid_fraction", 0) >= .5
                    and data.get("frame_stamp_ns",0) > 0
                    and len(self.valid) < 180):
                self.valid.append({"distance_m":data["distance_m"],
                                   "frame_stamp_ns":data["frame_stamp_ns"],
                                   "valid_fraction":data["valid_fraction"]})
            if state == "UNKNOWN" and data.get("distance_m") is None:
                self.unknown.append(reason)

        def verdict(self):
            pairs = [(r,d) for r in self.rgb for d in self.depth
                     if r[0] == d[0] and r[1:3] == d[1:3] == (640,480)
                     and r[3] > 0 and abs(r[3]-d[3]) <= 50_000_000
                     and d[4] == "32FC1"]
            seen = {d["frame_stamp_ns"]:d["distance_m"] for d in self.valid}
            distances = list(seen.values())
            delta = max(distances)-min(distances) if len(distances)>=2 else 0.0
            if phase == "moving":
                passed = bool(pairs and self.yolo_count and self.person_count
                              and len(distances)>=2 and delta>=.15)
                status = "PASS_REAL_RGBD_YOLO_PERSON_DISTANCE_TREND" if passed else "BLOCKED_MOVING"
            else:
                # Depth bridge has been killed BEFORE launching this monitor.
                # No new Depth image should be received, RGB and YOLO remain live.
                passed = bool(self.rgb and self.yolo_count
                              and "STALE_INPUT" in self.unknown and not self.depth)
                status = "PASS_REAL_DEPTH_LOSS_UNKNOWN" if passed else "BLOCKED_DEPTH_LOSS"
            return {
                "status":status, "passed":passed,"phase":phase,
                "registered_rgbd_pairs":len(pairs), "rgb_frames":len(self.rgb),
                "depth_frames":len(self.depth),"yolo_frames":self.yolo_count,
                "person_count":self.person_count,"valid_samples":len(distances),
                "min_distance_m":min(distances) if distances else None,
                "max_distance_m":max(distances) if distances else None,
                "distance_delta_m":delta,"unknown_reasons":self.unknown[-20:],
                "first_status_reason":self.first_reason,"source":"ACTUAL_ROS_GAZEBO",
                "goal_sent":False, "cmd_vel_published":False,
                "certified_estop":False,
            }

    rclpy.init()
    node = Monitor()
    try:
        until = time.monotonic() + min(max(timeout, 1), 200)
        result = node.verdict()
        while time.monotonic() < until and not result["passed"]:
            rclpy.spin_once(node,timeout_sec=.35)
            result=node.verdict()
        return result
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main() -> int:
    cli=argparse.ArgumentParser()
    cli.add_argument("--phase",choices=("moving","depth-loss"),required=True)
    cli.add_argument("--timeout",type=float,default=120)
    cli.add_argument("--out",type=Path,required=True)
    args=cli.parse_args()
    result=run(args.phase,args.timeout)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("D05_LIVE_VERDICT="+json.dumps(result,ensure_ascii=False),flush=True)
    return 0 if result["passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
