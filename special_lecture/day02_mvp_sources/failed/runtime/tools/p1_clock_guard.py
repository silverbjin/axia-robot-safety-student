"""Observe the real Gazebo /clock topic using wall-monotonic deadlines.

FIX-04: a single node.get_clock().now() reading is not evidence of an
advancing simulation. Read the ROS Clock messages, require consecutive
positive advances, and keep a structured failure record.
"""
from __future__ import annotations

import time


class ClockProgress:
    def __init__(self, min_advances: int = 2):
        if min_advances < 1:
            raise ValueError("min_advances must be positive")
        self.min_advances = min_advances
        self.count = 0
        self.advances = 0
        self.regression = False
        self.first_positive_ns = None
        self.last_ns = None

    def observe(self, stamp_ns: int) -> None:
        stamp_ns = int(stamp_ns)
        self.count += 1
        if stamp_ns < 0:
            self.regression = True
            return
        if stamp_ns == 0:
            return
        if self.first_positive_ns is None:
            self.first_positive_ns = stamp_ns
        elif self.last_ns is not None:
            if stamp_ns < self.last_ns:
                self.regression = True
            elif stamp_ns > self.last_ns:
                self.advances += 1
        self.last_ns = stamp_ns

    def verdict(self) -> dict:
        if self.regression:
            status = "CLOCK_REGRESSION"
        elif self.count == 0:
            status = "CLOCK_MISSING"
        elif self.first_positive_ns is None or self.advances < self.min_advances:
            status = "CLOCK_STALLED"
        else:
            status = "CLOCK_READY"
        return {
            "status": status,
            "topic": "/clock",
            "samples": self.count,
            "advances": self.advances,
            "first_positive_ns": self.first_positive_ns,
            "last_ns": self.last_ns,
            "regression": self.regression,
            "min_advances": self.min_advances,
        }


def wait_for_clock_progress(node, timeout_sec: float = 12.0, min_advances: int = 2):
    """Return (bool, diagnostic) while spinning the *same* actual ROS node.

    The publisher in the supplied field evidence is RELIABLE/VOLATILE;
    a BEST_EFFORT/VOLATILE subscriber is compatible. All deadlines use
    time.monotonic(), not Gazebo time which may be stalled or uninitialized.
    """
    if timeout_sec <= 0:
        raise ValueError("timeout_sec must be positive")
    import rclpy
    from rosgraph_msgs.msg import Clock
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

    observer = ClockProgress(min_advances=min_advances)
    qos = QoSProfile(
        depth=20, reliability=ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.VOLATILE
    )

    def on_clock(message):
        observer.observe(message.clock.sec * 1_000_000_000 + message.clock.nanosec)

    subscription = node.create_subscription(Clock, "/clock", on_clock, qos)
    began = time.monotonic()
    deadline = began + timeout_sec
    try:
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=min(0.2, max(0.0, deadline - time.monotonic())))
            status = observer.verdict()["status"]
            if status in ("CLOCK_READY", "CLOCK_REGRESSION"):
                break
    finally:
        node.destroy_subscription(subscription)
    report = observer.verdict()
    report["elapsed_wall_sec"] = round(time.monotonic() - began, 3)
    report["subscriber_qos"] = "BEST_EFFORT/VOLATILE/depth=20"
    report["node_sim_time_ns"] = int(node.get_clock().now().nanoseconds)
    # A valid topic stream is necessary but the node's TimeSource must
    # also have synchronized its own sim-time clock before stamping poses.
    if report["status"] == "CLOCK_READY" and report["node_sim_time_ns"] <= 0:
        report["status"] = "NODE_SIM_TIME_UNSYNCHRONIZED"
    return report["status"] == "CLOCK_READY", report
