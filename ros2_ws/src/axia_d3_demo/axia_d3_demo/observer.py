"""D3 read-only observation of existing P1 /diagnostics, FSM, fault status and odom.

A unit-test pass or DEMO_OBSERVED does not prove physical safety or E-Stop.
"""
import argparse
import json
import math
from pathlib import Path
import time

from .contract import append_event


def main(argv=None):
    ap = argparse.ArgumentParser(description='D3 read-only ROS observer')
    ap.add_argument('--evidence', required=True, help='shared JSONL log (outside public student repo)')
    parsed, ros_args = ap.parse_known_args(argv)
    out = Path(parsed.evidence).expanduser()
    if out.exists() and out.is_symlink():
        raise SystemExit('Refuse symlinked D3 evidence path')
    if out.is_dir():
        raise SystemExit('D3 evidence path must be a JSONL file')
    try:
        import rclpy
        from rclpy.node import Node
        from std_msgs.msg import String
        from diagnostic_msgs.msg import DiagnosticArray
        from nav_msgs.msg import Odometry
    except ImportError as ex:
        raise SystemExit('ROS 2 Jazzy rclpy/std_msgs/nav_msgs/diagnostic_msgs required') from ex

    class D3Observer(Node):
        def __init__(self):
            super().__init__('axia_d3_observer')
            self._path = out
            self._prior_state = None
            self._prior_fault = None
            self._last_state_at = 0.0
            self._last_odom_at = 0.0
            self._last_diag_at = 0.0
            self._last_fault_at = 0.0
            # Subscription only; deliberately no cmd velocity/Goal/Fault authority.
            self.create_subscription(String, '/axia/safety/state', self._on_state, 10)
            self.create_subscription(String, '/axia/fault/status', self._on_fault, 10)
            self.create_subscription(DiagnosticArray, '/diagnostics', self._on_diagnostics, 10)
            self.create_subscription(Odometry, '/odom', self._on_odom, 10)
            self.get_logger().info('D3 observation only; waiting for NORMAL+moving, intrusion and DROP_SCAN')

        def _on_state(self, message):
            try:
                payload = json.loads(message.data)
                state = payload.get('state')
                if not isinstance(payload, dict) or state not in (
                    'BOOT_SAFE', 'NORMAL', 'LIMITED', 'PROTECTIVE_STOP',
                    'SW_STOP_LATCHED', 'RECOVERY_REQUIRED'
                ):
                    return
                now = time.monotonic()
                if state != self._prior_state or now-self._last_state_at >= .5:
                    append_event(self._path, 'p1_state', state=state,
                                 scan_fault_code=payload.get('scan_fault_code'))
                    self._prior_state, self._last_state_at = state, now
                    if state == 'PROTECTIVE_STOP':
                        self.get_logger().warning('Observed P1 PROTECTIVE_STOP (not an E-Stop certificate)')
            except (ValueError, TypeError, AttributeError):
                self.get_logger().warning('Ignored invalid P1 JSON')

        def _on_fault(self, message):
            try:
                payload = json.loads(message.data)
                if not isinstance(payload, dict):
                    return
                mode, enabled = payload.get('mode'), payload.get('enabled')
                if mode not in ('NORMAL', 'DROP_SCAN', 'STALE_STAMP', 'FUTURE_STAMP') or type(enabled) is not bool:
                    return
                now = time.monotonic()
                if mode != self._prior_fault or now-self._last_fault_at >= 1.0:
                    append_event(self._path, 'fault_status', mode=mode, enabled=enabled)
                    self._prior_fault, self._last_fault_at = mode, now
            except (ValueError, TypeError, AttributeError):
                self.get_logger().warning('Ignored invalid Fault Injector status JSON')

        def _on_diagnostics(self, message):
            now = time.monotonic()
            if now-self._last_diag_at < .25:
                return
            for st in message.status:
                if st.name != 'AXIA/P1/SafetySupervisor' or int(st.level) not in (0, 1, 2, 3):
                    continue
                append_event(self._path, 'diagnostic', name=st.name, level=int(st.level))
                self._last_diag_at = now
                return

        def _on_odom(self, message):
            now = time.monotonic()
            if now-self._last_odom_at < .18:
                return
            v = float(message.twist.twist.linear.x)
            w = float(message.twist.twist.angular.z)
            if not (math.isfinite(v) and math.isfinite(w)):
                return
            append_event(self._path, 'odom', v=round(v, 5), w=round(w, 5))
            self._last_odom_at = now

    rclpy.init(args=ros_args)
    node = D3Observer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
