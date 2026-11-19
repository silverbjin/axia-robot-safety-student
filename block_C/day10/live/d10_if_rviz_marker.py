#!/usr/bin/env python3
"""D10 synthetic IF score -> read-only RViz Marker, independent from robot safety.

Subscribes ONLY to /axia/education/diagnostics, publishes ONLY a TEXT_VIEW_FACING
visualization Marker. Never commands robots. Source timestamps are trace-local,
not /clock, DDS latency, actual sensor data or certified emergency stop evidence.
Importable/testable without ROS; ROS imports are contained in main().
"""
from __future__ import annotations
import argparse
import math
import time

INPUT_TOPIC = "/axia/education/diagnostics"
OUTPUT_TOPIC = "/axia/education/d10_if_marker"
EXPECTED_MODEL = "D10_ISOLATION_FOREST"

def format_education_status(message, hardware_id, pairs):
    """Return (three-line display, color name), or None for non-D10 data.

    Pairs contain string key/value fields from a DiagnosticStatus.
    No trust is placed in the diagnostic level alone.
    """
    vals = dict(pairs)
    if not message.startswith("EDUCATION ONLY / NON-CERTIFIED: "):
        return None
    if hardware_id != "SYNTHETIC_NO_HARDWARE":
        return None
    if vals.get("model_id") != EXPECTED_MODEL:
        return None
    if vals.get("control_authority") != "False" or vals.get("certified_estop") != "False":
        return None
    level = message.rsplit(": ", 1)[-1]
    if level not in ("NORMAL", "CAUTION", "WARNING", "INSUFFICIENT_DATA"):
        return None
    trace = vals.get("trace_id", "")
    if not trace or len(trace) > 36 or not all(c.isalnum() or c == "_" for c in trace):
        return None
    event_id = vals.get("event_id", "")
    if not event_id.startswith(EXPECTED_MODEL + ":" + trace + ":"):
        return None
    window = event_id.rsplit(":", 1)[-1]
    if not window.isdigit():
        return None
    try:
        stamp = int(vals["source_timestamp_ns"])
        if stamp < 0:
            return None
    except (ValueError, TypeError, KeyError):
        return None
    if level == "INSUFFICIENT_DATA":
        if vals.get("risk_score") or vals.get("threshold"):
            return None
        score_text = "NO SCORE / QUALITY INVALID"
    else:
        try:
            score = float(vals["risk_score"])
            threshold = float(vals["threshold"])
            if not math.isfinite(score) or not math.isfinite(threshold) or threshold <= 0:
                return None
        except (ValueError, TypeError, KeyError):
            return None
        score_text = f"risk={score:.4f} / cutoff={threshold:.4f}"
    return (f"SYNTHETIC IF REPLAY - NO ROBOT CONTROL\n"
            f"{trace} W{window} t={stamp/1e9:.1f}s | {level}\n"
            f"{score_text} | NOT AN E-STOP",
            {"NORMAL":"teal","CAUTION":"amber","WARNING":"red",
             "INSUFFICIENT_DATA":"gray"}[level])

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--self-check", action="store_true")
    p.add_argument("--frame-id", default="base_link")
    p.add_argument("--stale-sec", type=float, default=3.0)
    args = p.parse_args(argv)
    if args.self_check:
        print("D10_RVIZ_MARKER_STATIC_OK ROS_NOT_RUN GAZEBO_NOT_RUN NO_CONTROL")
        return 0
    if not (0.5 <= args.stale_sec <= 30):
        p.error("stale-sec must be between 0.5 and 30 (display freshness only)")
    if args.frame_id not in ("base_link", "odom"):
        p.error("frame-id must be base_link or odom")
    import rclpy
    from rclpy.node import Node
    from diagnostic_msgs.msg import DiagnosticArray
    from visualization_msgs.msg import Marker
    class Viewer(Node):
        def __init__(self):
            super().__init__("axia_d10_educational_marker")
            self.pub = self.create_publisher(Marker, OUTPUT_TOPIC, 10)
            self.sub = self.create_subscription(DiagnosticArray, INPUT_TOPIC, self.got, 10)
            self.last_wall = None
            self.last_payload = None
            self.stale_displayed = False
            self.timer = self.create_timer(0.5, self.tick)
            print("D10_RVIZ_MARKER_READY "
                  f"input={INPUT_TOPIC} output={OUTPUT_TOPIC} "
                  "synthetic=true control_authority=false", flush=True)
        def render(self, text, color):
            m = Marker()
            # Stamp 0 asks RViz to transform at the latest available time.
            m.header.frame_id = args.frame_id
            m.header.stamp.sec = 0
            m.header.stamp.nanosec = 0
            m.ns = "axia_d10_education_only"
            m.id = 10
            m.type = Marker.TEXT_VIEW_FACING
            m.action = Marker.ADD
            m.pose.position.x = 0.0
            m.pose.position.y = 0.0
            m.pose.position.z = 1.05
            m.pose.orientation.w = 1.0
            m.scale.z = 0.16
            m.color.a = 1.0
            r, g, b = {
                "teal": (0.2, 0.95, 0.8),
                "amber": (1.0, 0.75, 0.15),
                "red": (1.0, 0.25, 0.25),
                "gray": (0.7, 0.72, 0.75),
            }[color]
            m.color.r, m.color.g, m.color.b = r, g, b
            m.text = text
            self.pub.publish(m)
        def got(self, msg):
            if not msg.status:
                return
            st = msg.status[0]
            value = format_education_status(
                st.message, st.hardware_id, ((kv.key, kv.value) for kv in st.values)
            )
            if value is None:
                return
            self.last_wall = time.monotonic()
            self.last_payload = value
            self.stale_displayed = False
            self.render(*value)
            print("D10_RVIZ_EVENT " +
                  value[0].splitlines()[1].replace(" | ", " "), flush=True)
        def tick(self):
            if self.last_wall is None:
                return
            if not self.stale_displayed and time.monotonic() - self.last_wall > args.stale_sec:
                self.render("SYNTHETIC IF REPLAY PAUSED / NO NEW EDUCATION EVENTS\n"
                            "DISPLAY STALE (NOT A SAFETY TTL)", "gray")
                self.stale_displayed = True
    rclpy.init()
    node = Viewer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
