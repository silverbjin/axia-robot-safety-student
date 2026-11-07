"""Read-only ROS 2 Jazzy wrapper around the D03 student's pure mapper.

Subscribes only /axia/safety/state, publishes only /diagnostics.
Never publishes velocity, sends a Nav2 goal, or invokes safety services.
Run only after the pure Python mapper's public tests are GREEN.
"""
import time

from p1_adapter_todo import diagnose_p1_state


def main() -> None:
    try:
        import rclpy
        from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
        from rclpy.node import Node
        from std_msgs.msg import String
    except ImportError as exc:
        raise SystemExit("ROS 2 Jazzy + diagnostic_msgs required for ROS bridge") from exc

    class D03DiagnosticsBridge(Node):
        def __init__(self):
            super().__init__("axia_d03_diagnostics_bridge")
            self._raw_state = None
            self._received_mono = None
            self._status_pub = self.create_publisher(DiagnosticArray, "/diagnostics", 10)
            self.create_subscription(String, "/axia/safety/state", self._on_state, 10)
            self.create_timer(0.5, self._publish_status)

        def _on_state(self, msg: String):
            self._raw_state = msg.data
            self._received_mono = time.monotonic()

        def _publish_status(self):
            record = diagnose_p1_state(
                self._raw_state, received_mono=self._received_mono,
                now_mono=time.monotonic(), timeout_s=1.0,
            )
            status = DiagnosticStatus()
            status.level = record.level
            status.name = record.name
            status.message = record.message
            status.hardware_id = record.hardware_id
            status.values = [KeyValue(key=k, value=v) for k, v in record.values]
            array = DiagnosticArray()
            array.header.stamp = self.get_clock().now().to_msg()
            array.status = [status]
            self._status_pub.publish(array)

    rclpy.init()
    node = D03DiagnosticsBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
