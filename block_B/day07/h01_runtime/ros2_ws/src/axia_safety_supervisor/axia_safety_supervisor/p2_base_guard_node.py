"""P2 sim-only final delivery guard. Live ROS/Gazebo behavior NOT verified here.

Single ROS /cmd_vel publisher; if Supervisor or Collision Monitor stops while
moving, host-monotonic timeout latches ZERO. Guard's own death is NOT covered.
"""
import json
import os
import time

import rclpy
from action_msgs.srv import CancelGoal
from geometry_msgs.msg import Twist
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from rclpy.executors import ExternalShutdownException
from .p2_shutdown_context import is_context_waitset_shutdown, is_context_publish_shutdown
from rclpy.node import Node
from std_msgs.msg import String

from .p2_base_guard_policy import Motion, State, ZERO
from .p2_guard_evidence_mode import internal_timing_evidence_enabled


def _motion(msg):
    return Motion(msg.linear.x, msg.angular.z, msg.linear.y, msg.linear.z,
                  msg.angular.x, msg.angular.y)


def _twist(motion):
    msg = Twist()
    msg.linear.x = motion.linear_x
    msg.angular.z = motion.angular_z
    return msg


class P2BaseCommandGuard(Node):
    def __init__(self):
        super().__init__('axia_base_command_guard')
        if not self.has_parameter('use_sim_time'):
            self.declare_parameter('use_sim_time', True)
        self._policy = State()
        # Immutable evidence of the earliest Guard latch; kept in every
        # subsequent status for rosbag custody even if first frame is missed.
        self._first_latch_trace = None
        # One Nav2 action owner in the isolated educational simulator. Zero
        # GoalInfo requests cancellation of *all* current NavigateToPose goals.
        # This is an emergency request, NOT evidence of terminal CANCELED.
        self._cancel_client = self.create_client(
            CancelGoal, '/navigate_to_pose/_action/cancel_goal')
        self._cancel_future = None
        self._cancel_acknowledged = False
        self._last_cancel_attempt = None
        self._final = self.create_publisher(Twist, '/cmd_vel', 10)
        self._status = self.create_publisher(String, '/axia/p2/base_guard', 10)
        # Critical CM input first: real CI #43042721872 observed independent
        # CM delivery 55ms ahead of this Guard's last callback near the 150ms
        # watchdog. Prefer accepting genuine CM callbacks before source/FSM
        # audit traffic when the single-threaded executor has several ready.
        # Registration order is only a scheduling hint, NOT a safety waiver.
        # Original reliable QoS depth 10 and all CM/Supervisor TTLs stay fixed.
        self.create_subscription(Twist, '/cmd_vel_pre_guard',
                                 lambda msg: self._accept('collision_monitor', msg), 10)
        self.create_subscription(Twist, '/cmd_vel_supervised',
                                 lambda msg: self._accept('supervisor', msg), 10)
        # Existing Supervisor audit topic provides the distinction that a
        # bare geometry_msgs/Twist cannot encode: healthy authorized NORMAL
        # controller ZERO vs actual protective/manual software STOP.
        self.create_subscription(String, '/axia/safety/state',
                                 self._accept_supervisor_state, 10)
        self._steady = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(0.05, self._tick, clock=self._steady)
        self.get_logger().warning(
            'P2 simulation-only TTL guard active: zero-on-missing /cmd_vel sources; '
            'NOT a certified E-Stop, NOT resilient to guard/bridge/Gazebo death'
        )

    def _accept(self, source, msg):
        self._policy.receive(source, _motion(msg), time.monotonic())

    def _accept_supervisor_state(self, msg):
        try:
            data = json.loads(msg.data)
            if not isinstance(data, dict):
                data = {}
        except (TypeError, ValueError):
            data = {}
        diagnostics = data.get("health_diagnostics")
        diagnostics = diagnostics if isinstance(diagnostics, dict) else {}
        healthy = all(diagnostics.get(key) is True for key in (
            "clock_ok", "scan_ok", "graph_ok",
            "cm_lifecycle_ok", "nav2_action_ready",
        ))
        self._policy.receive_supervisor_state(
            data.get("state"), time.monotonic(),
            goal_id=data.get("goal_id"), healthy=healthy,
            stop_reason=data.get("stop_reason", "INVALID"),
        )

    def _cancel_result(self, future):
        try:
            response = future.result()
            self._cancel_acknowledged = (
                response.return_code == 0 and bool(response.goals_canceling))
        except Exception as exc:
            self._cancel_acknowledged = False
            self.get_logger().warning('P2 cancel response failed: '+type(exc).__name__)
        finally:
            self._cancel_future = None

    def _request_cancel(self):
        if self._cancel_acknowledged or self._cancel_future is not None:
            return
        now = time.monotonic()
        if self._last_cancel_attempt is not None and now - self._last_cancel_attempt < 0.5:
            return
        self._last_cancel_attempt = now
        if not self._cancel_client.service_is_ready():
            return
        try:
            # ROS 2 CancelGoal default GoalInfo UUID=0, stamp=0 selects all.
            self._cancel_future = self._cancel_client.call_async(CancelGoal.Request())
            self._cancel_future.add_done_callback(self._cancel_result)
        except Exception as exc:
            self._cancel_future = None
            self.get_logger().warning('P2 cancel request failed: '+type(exc).__name__)

    def _tick(self):
        tick_mono = time.monotonic()
        out = self._policy.step(tick_mono)
        if self._policy.latched and self._first_latch_trace is None:
            self._first_latch_trace = self._policy.diagnostic_snapshot(tick_mono)
        if self._policy.latched:
            self._request_cancel()
        self._final.publish(_twist(out))
        status = String()
        status_fields = {
            'latched': self._policy.latched,
            'cancel_acknowledged': self._cancel_acknowledged,
            'goal_terminal_verified': False,
            'reason': self._policy.reason,
            'first_latch_trace': self._first_latch_trace,
            'sim_only': True,
            'certified_estop': False,
        }
        # G07 CI and true Owner SIM only: expose Guard's own steady
        # monotonic receive ages on the EXISTING 20Hz status topic.
        # This is read-only evidence. Never change CM/Guard TTL or ZERO.
        if internal_timing_evidence_enabled(os.environ):
            snapshot = self._policy.diagnostic_snapshot(tick_mono)
            status_fields['cm_age_sec'] = snapshot['cm_age_sec']
            status_fields['supervisor_age_sec'] = snapshot['supervisor_age_sec']
            # This monotonic latch becomes True ONLY when this exact Guard
            # has forwarded a real nonzero CM command. NO_FRESH_PAIR before
            # first motion is fail-closed ZERO but not a postmotion stale fault.
            # Read-only provenance; State.step and CM_TTL_SEC=.15 unchanged.
            status_fields['guard_ever_moved'] = self._policy.ever_moved
        status.data = json.dumps(status_fields, sort_keys=True)
        self._status.publish(status)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = P2BaseCommandGuard()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except Exception as exc:
        # Native #44881017415: SIGINT invalidated the ROS context while
        # a 20Hz Guard _tick was in self._status.publish(status). Reuse the
        # P2 Supervisor's existing EXACT shutdown-only classifier.
        # A live-context publisher failure is never suppressed.
        context_ok=rclpy.ok()
        if not (is_context_waitset_shutdown(exc,context_ok=context_ok)
                or is_context_publish_shutdown(exc,context_ok=context_ok)):
            raise
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
