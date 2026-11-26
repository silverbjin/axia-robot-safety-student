"""G09 synthetic trace ROS 2 Jazzy L1 adapter.

Consumes locally supplied educational track fixture messages. It never subscribes
to a real person detector and never publishes /cmd_vel, Nav2 goals or fault
commands. Verdicts are NOT safety authority or formal G09 acceptance.
"""
from __future__ import annotations

import json

from rclpy.node import Node
from std_msgs.msg import String

from .p3_oracles import classify_time_indexed


class G09RosOracle(Node):
    def __init__(self) -> None:
        super().__init__("axia_p3_g09_fixture_oracle")
        self._last_seq = -1
        self._publisher = self.create_publisher(
            String, "/axia/p3/g09/verdict", 10)
        self._subscription = self.create_subscription(
            String, "/axia/p3/g09/fixture", self._receive, 10)

    def _receive(self, message: String) -> None:
        try:
            payload = json.loads(message.data)
        except (ValueError, TypeError, UnicodeError):
            return
        if not isinstance(payload, dict):
            return
        seq = payload.get("seq")
        if type(seq) is not int or seq < 0 or seq <= self._last_seq:
            return
        self._last_seq = seq
        verdict = classify_time_indexed(
            payload.get("robot_trajectory"),
            payload.get("person"),
            now_sec=payload.get("now_sec", float("nan")),
        )
        outgoing = String()
        outgoing.data = json.dumps({
            "seq": seq,
            "verdict": verdict,
            "scope": "SYNTHETIC_ROS_L1_NO_MOTION",
            "gate_accepted": False,
            "certified_estop": False,
            "goal_sent": False,
        }, sort_keys=True)
        self._publisher.publish(outgoing)
