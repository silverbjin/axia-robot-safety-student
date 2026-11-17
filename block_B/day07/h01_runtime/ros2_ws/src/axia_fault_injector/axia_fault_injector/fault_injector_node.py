"""P1-T06 controlled LaserScan fault relay (education/simulation only).

Never publishes /clock, /cmd_vel, /cmd_vel_smoothed or final robot commands.
Fault services refuse mutations unless explicitly enabled. Source topic /scan
must have only the official simulator publisher in the final launch graph.
"""
from copy import deepcopy
import json

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from std_srvs.srv import Trigger

from .fault_policy import FaultMode, ScanFaultPlan, SCAN_IN, SCAN_OUT


class FaultInjectorNode(Node):
    def __init__(self, *, allow_fault_injection=False):
        super().__init__("axia_fault_injector")
        self.declare_parameter("allow_fault_injection", bool(allow_fault_injection))
        self._plan = ScanFaultPlan()
        self._published = 0
        self._dropped = 0
        self._errors = 0
        self._relay = self.create_publisher(LaserScan, SCAN_OUT, qos_profile_sensor_data)
        self.create_subscription(LaserScan, SCAN_IN, self._on_scan,
                                 qos_profile_sensor_data)
        self._status_pub = self.create_publisher(String, "/axia/fault/status", 10)
        for suffix, mode in (
            ("scan_normal", FaultMode.NORMAL),
            ("scan_drop", FaultMode.DROP_SCAN),
            ("scan_stale_stamp", FaultMode.STALE_STAMP),
            ("scan_future_stamp", FaultMode.FUTURE_STAMP),
        ):
            self.create_service(
                Trigger, "/axia/fault/" + suffix, self._handler(mode)
            )
        self.create_timer(0.2, self._status)
        self.get_logger().warning(
            "P1-T06 Fault Injector: scan-only, disabled by default; "
            "never use to drive a physical robot"
        )

    def _handler(self, mode):
        def change(_request, response):
            if not self.get_parameter("allow_fault_injection").value:
                response.success = False
                response.message = "FAULT_INJECTION_DISABLED"
                return response
            try:
                self._plan.select(mode)
                response.success = True
                response.message = self._plan.mode.value
            except ValueError as exc:
                response.success = False
                response.message = str(exc)
            return response
        return change

    def _on_scan(self, msg):
        stamp_ns = (int(msg.header.stamp.sec) * 1_000_000_000
                    + int(msg.header.stamp.nanosec))
        try:
            output_stamp = self._plan.output_stamp_ns(
                stamp_ns, now_ros_ns=self.get_clock().now().nanoseconds
            )
            if output_stamp is None:
                self._dropped += 1
                return
            forwarded = deepcopy(msg)
            forwarded.header.stamp.sec = output_stamp // 1_000_000_000
            forwarded.header.stamp.nanosec = output_stamp % 1_000_000_000
            self._relay.publish(forwarded)
            self._published += 1
        except (ValueError, OverflowError) as exc:
            self._errors += 1
            self.get_logger().error("Scan relay fail-closed: " + str(exc))

    def _status(self):
        msg = String()
        msg.data = json.dumps({
            "mode": self._plan.mode.value,
            "enabled": bool(self.get_parameter("allow_fault_injection").value),
            "published": self._published,
            "dropped": self._dropped,
            "errors": self._errors,
            "certified_estop": False,
        })
        self._status_pub.publish(msg)


def main(args=None):
    # rclpy context may already be stopped by the ROS launch signal handler.
    # External shutdown is normal; genuine node/programming exceptions surface.
    from rclpy.executors import ExternalShutdownException
    rclpy.init(args=args)
    node = None
    try:
        node = FaultInjectorNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except Exception as exc:
        # rclpy may raise RCLError during a launch-initiated context shutdown.
        # Never suppress other runtime failures merely because ROS is stopping.
        if not rclpy.ok() and type(exc).__name__ == "RCLError":
            pass
        else:
            raise
    finally:
        try:
            if node is not None:
                node.destroy_node()
        finally:
            rclpy.try_shutdown()


if __name__ == "__main__":
    main()
