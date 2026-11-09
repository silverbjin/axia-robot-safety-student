"""AXIA ROS 2 software supervisor — T04 adapter, NOT a certified E-Stop.

P1-T05 must wire official Nav2 -> smoother -> supervisor -> CollisionMonitor.
P1-T06 must validate sensor/TF/lifecycle faults on real ROS/Gazebo.
"""
import json
import time

import rclpy
from geometry_msgs.msg import PoseStamped, Twist
from lifecycle_msgs.msg import State
from lifecycle_msgs.srv import GetState
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from std_srvs.srv import Trigger

from .command_gate import GatePolicy, TwistCommand, gate_command
from .fsm import (
    SafetySnapshot, SafetyState, can_move, transition,
    health_loss_requires_goal_stop,
)
from .ros_nav2_client import RosNav2GoalOwner
from .watchdog import (ScanPacket, ScanPolicy, ScanCallbackTiming,
                       observe_scan_callback_interval, scan_callback_deadline_breached,
                       check_scan, scan_timed_out)


def _from_ros_twist(msg):
    return TwistCommand(
        linear_x=msg.linear.x, linear_y=msg.linear.y, linear_z=msg.linear.z,
        angular_x=msg.angular.x, angular_y=msg.angular.y, angular_z=msg.angular.z,
    )


def _to_ros_twist(command):
    msg = Twist()
    msg.linear.x = float(command.linear_x)
    msg.angular.z = float(command.angular_z)
    return msg


class SafetySupervisorNode(Node):
    def __init__(self):
        super().__init__("axia_safety_supervisor")
        if not self.has_parameter("use_sim_time"):
            self.declare_parameter("use_sim_time", True)
        self.declare_parameter("command_timeout_sec", 0.5)
        self.declare_parameter("scan_timeout_sec", 0.5)
        self.declare_parameter("cancel_terminal_timeout_sec", 3.0)
        self.declare_parameter("max_linear_mps", 0.22)
        self.declare_parameter("max_angular_rps", 2.0)
        self.declare_parameter("limited_ratio", 0.3)
        self.declare_parameter("laser_frame", "base_scan")
        self.declare_parameter("front_sector_min_rad", -0.35)
        self.declare_parameter("front_sector_max_rad", 0.35)
        self.declare_parameter("front_min_finite_fraction", 0.6)
        self.declare_parameter("front_max_missing_run", 3)
        self._policy = GatePolicy(
            self.get_parameter("max_linear_mps").value,
            self.get_parameter("max_angular_rps").value,
            self.get_parameter("limited_ratio").value,
            self.get_parameter("command_timeout_sec").value,
        )
        self._scan_policy = ScanPolicy(
            frame_id=self.get_parameter("laser_frame").value,
            timeout_sec=self.get_parameter("scan_timeout_sec").value,
            future_tolerance_ns=100_000_000,
            sector_min_rad=self.get_parameter("front_sector_min_rad").value,
            sector_max_rad=self.get_parameter("front_sector_max_rad").value,
            min_finite_fraction=self.get_parameter("front_min_finite_fraction").value,
            max_missing_run=self.get_parameter("front_max_missing_run").value,
        )
        self._state = SafetySnapshot()  # BOOT_SAFE; no persisted authority.
        self._cmd = None
        self._cmd_rx_mono = None
        self._cmd_epoch = None
        self._cmd_generation = None
        self._authorized_at_mono = None
        self._last_scan_mono = None
        self._scan_callback_timing = ScanCallbackTiming()
        self._scan_good = False
        self._scan_fault_code = None
        self._prior_scan_stamp = None
        self._last_ros_ns = None
        self._last_ros_progress_mono = time.monotonic()
        self._last_reason = "BOOT_SAFE"
        self._health_diagnostics = {
            "clock_ok": False, "scan_ok": False, "graph_ok": None,
            "cm_lifecycle_ok": None, "nav2_action_ready": None,
            "scan_fault_code": None,
        }
        # The Collision Monitor endpoint must be lifecycle ACTIVE, not
        # merely advertising a publisher. Check via nonblocking GetState.
        self._cm_state_client = self.create_client(
            GetState, "/collision_monitor/get_state"
        )
        self._cm_active = False
        self._cm_last_success_mono = None
        self._cm_last_query_mono = 0.0
        self._cm_future = None
        self._cmd_pub = self.create_publisher(Twist, "/cmd_vel_supervised", 10)
        self._state_pub = self.create_publisher(String, "/axia/safety/state", 10)
        self.create_subscription(Twist, "/cmd_vel_smoothed", self._on_cmd, 10)
        self.create_subscription(LaserScan, "/safety/scan", self._on_scan,
                                 qos_profile_sensor_data)
        self.create_subscription(PoseStamped, "/axia/safety/goal_pose",
                                 self._on_goal_request, 10)
        self.create_service(Trigger, "/axia/safety/start", self._start)
        self.create_service(Trigger, "/axia/safety/request_sw_stop", self._sw_stop)
        self.create_service(Trigger, "/axia/safety/reset", self._reset)
        self.create_service(Trigger, "/axia/safety/rearm", self._rearm)
        # Explicit operator-controlled recovery from in-operation
        # PROTECTIVE_STOP. Does not clear SW_STOP_LATCHED, does not
        # rearm, cannot authorize a Goal and cannot override missing
        # Nav2 terminal Cancel / no-goal ownership proof.
        self.create_service(Trigger, "/axia/safety/fault_cleared", self._fault_cleared)
        self._owner = RosNav2GoalOwner(
            self, on_accepted=self._on_accepted, on_terminal=self._on_terminal,
            on_cancel_ack=self._on_cancel_ack, on_failure=self._on_action_failure,
            on_no_goal=self._on_no_goal,
            cancel_timeout_sec=self.get_parameter("cancel_terminal_timeout_sec").value,
        )
        # Explicit steady clock: simulated /clock must not suspend timeout/zero output.
        self._steady = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(0.05, self._tick, clock=self._steady)
        self.get_logger().warning(
            "P1-T04 educational SW stop only; launch graph and physical odom unverified"
        )

    def _clear_cmd(self):
        self._cmd = None
        self._cmd_rx_mono = None
        self._cmd_epoch = None
        self._cmd_generation = None

    def _on_cmd(self, msg):
        if not can_move(self._state):
            return
        self._cmd = _from_ros_twist(msg)
        self._cmd_rx_mono = time.monotonic()
        self._cmd_epoch = self._state.startup_epoch
        self._cmd_generation = self._state.generation

    def _on_scan(self, msg):
        now = time.monotonic()
        before_timing = self._scan_callback_timing
        self._scan_callback_timing = observe_scan_callback_interval(
            before_timing,
            prior_mono=self._last_scan_mono,
            now_mono=now, timeout_sec=self._scan_policy.timeout_sec,
        )
        if scan_callback_deadline_breached(before_timing, self._scan_callback_timing):
            # A fresh message after a long callback stall must not erase the
            # missed steady-clock watchdog deadline. _trip is a no-op in
            # BOOT_SAFE but cancels and zeros immediately in NORMAL/LIMITED.
            self._trip("scan_stale")
        stamp_ns = int(msg.header.stamp.sec) * 1_000_000_000 + int(msg.header.stamp.nanosec)
        packet = ScanPacket(
            stamp_ns=stamp_ns, frame_id=msg.header.frame_id, ranges=msg.ranges,
            range_min=msg.range_min, range_max=msg.range_max,
            angle_min=msg.angle_min, angle_max=msg.angle_max,
            angle_increment=msg.angle_increment,
        )
        ros_ns = self.get_clock().now().nanoseconds
        result = check_scan(packet, now_ros_ns=ros_ns,
                            prior_stamp_ns=self._prior_scan_stamp,
                            policy=self._scan_policy)
        self._last_scan_mono = now
        self._scan_good = result.ok
        self._scan_fault_code = None if result.ok else result.reason
        if result.ok:
            self._prior_scan_stamp = stamp_ns
        else:
            self._trip("scan_invalid")  # Fault source, not generic health_bad.

    def _graph_ready(self):
        # A graph oracle, not access control and not CM lifecycle validation.
        publishers = self.get_publishers_info_by_topic("/cmd_vel")
        subscribers = self.get_subscriptions_info_by_topic("/cmd_vel_supervised")
        return (
            len(publishers) == 1
            and publishers[0].node_name == "collision_monitor"
            and publishers[0].topic_type == "geometry_msgs/msg/Twist"
            and any(e.node_name == "collision_monitor" for e in subscribers)
        )

    def _clock_ready(self, now):
        ros_ns = self.get_clock().now().nanoseconds
        if ros_ns <= 0:
            return False
        if self._last_ros_ns is not None and ros_ns < self._last_ros_ns:
            self._trip("clock_regression")
            return False
        if self._last_ros_ns is None or ros_ns > self._last_ros_ns:
            self._last_ros_progress_mono = now
        self._last_ros_ns = ros_ns
        if now - self._last_ros_progress_mono > 0.5:
            self._trip("clock_stalled")
            return False
        return True

    def _on_cm_state(self, future):
        try:
            state = future.result().current_state
            self._cm_active = state.id == State.PRIMARY_STATE_ACTIVE
            self._cm_last_success_mono = (
                time.monotonic() if self._cm_active else None
            )
        except Exception as exc:
            self._cm_active = False
            self._cm_last_success_mono = None
            self.get_logger().warning(
                "Collision Monitor GetState failed: " + type(exc).__name__
            )
        finally:
            self._cm_future = None

    def _cm_lifecycle_ready(self, now):
        if not self._cm_state_client.service_is_ready():
            self._cm_active = False
            self._cm_last_success_mono = None
            return False
        if self._cm_future is None and now - self._cm_last_query_mono >= 0.3:
            self._cm_last_query_mono = now
            try:
                self._cm_future = self._cm_state_client.call_async(GetState.Request())
                self._cm_future.add_done_callback(self._on_cm_state)
            except Exception as exc:
                self._cm_active = False
                self._cm_last_success_mono = None
                self.get_logger().warning(
                    "Collision Monitor state request failed: " + type(exc).__name__
                )
                self._cm_future = None
                return False
        return (
            self._cm_active and self._cm_last_success_mono is not None
            and 0 <= now - self._cm_last_success_mono <= 1.0
        )

    def _health(self, now):
        clock_ok = self._clock_ready(now)
        lost_scan = scan_timed_out(
            now_mono=now, last_rx_mono=self._last_scan_mono,
            timeout_sec=self._scan_policy.timeout_sec,
        )
        if lost_scan:
            self._scan_fault_code = "SCAN_TIMEOUT"
            self._trip("scan_stale")
        scan_ok = self._scan_good and not lost_scan
        # Preserve original short-circuit behavior; None means NOT EVALUATED.
        # This is diagnostic-only. Never accept a goal because a predicate
        # has not been observed, and never relax a watchdog.
        graph_ok = self._graph_ready() if clock_ok and scan_ok else None
        cm_ok = self._cm_lifecycle_ready(now) if graph_ok else None
        action_ok = self._owner.ready() if cm_ok else None
        self._health_diagnostics = {
            "clock_ok": bool(clock_ok),
            "scan_ok": bool(scan_ok),
            "graph_ok": graph_ok,
            "cm_lifecycle_ok": cm_ok,
            "nav2_action_ready": action_ok,
            "nav2_action_diagnostics": (
                self._owner.readiness_snapshot() if action_ok is False else None
            ),
            "scan_fault_code": self._scan_fault_code,
            "scan_callback_intervals": self._scan_callback_timing.intervals,
            "scan_callback_gaps_over_timeout": self._scan_callback_timing.over_timeout,
            "scan_callback_invalid_intervals": self._scan_callback_timing.invalid_intervals,
            "scan_callback_max_gap_sec": round(
                self._scan_callback_timing.max_gap_sec, 6),
            "scan_age_sec": (
                round(now - self._last_scan_mono, 4)
                if self._last_scan_mono is not None else None
            ),
            "cm_last_success_age_sec": (
                round(now - self._cm_last_success_mono, 4)
                if self._cm_last_success_mono is not None else None
            ),
            "cm_active": self._cm_active,
        }
        return bool(clock_ok and scan_ok and graph_ok and cm_ok and action_ok)

    def _trip(self, reason):
        if self._state.state == SafetyState.SW_STOP_LATCHED:
            return
        if self._state.state not in (SafetyState.NORMAL, SafetyState.LIMITED):
            return
        self._state = transition(self._state, reason)
        self._clear_cmd()
        self._cmd_pub.publish(Twist())
        self._owner.stop()

    def _tick(self):
        now = time.monotonic()
        self._owner.check_timeout()
        healthy = self._health(now)
        if healthy and not self._state.healthy:
            self._state = transition(self._state, "health_ok")
        elif not healthy and self._state.healthy:
            self.get_logger().warning(
                "HEALTH_BAD_DIAGNOSTIC " + json.dumps(self._health_diagnostics,
                                                      sort_keys=True)
            )
            # A transient BOOT_SAFE health drop must not poison the
            # exclusively owned Nav2 GoalTracker. Its stop_requested flag
            # persists until explicit rearm, which BOOT_SAFE does not use.
            # NORMAL/LIMITED still cancel their Goal fail-closed.
            should_cancel_owner = health_loss_requires_goal_stop(self._state.state)
            self._state = transition(self._state, "health_bad")
            self._clear_cmd()
            if should_cancel_owner:
                self._owner.stop()
        if can_move(self._state) and self._authorized_at_mono is not None:
            # Track absence AND expiry of a previously received command.
            # Zero-only output without a protective state would auto-resume
            # when stale upstream commands reappear.
            last_command_or_goal = (
                self._cmd_rx_mono if self._cmd_rx_mono is not None
                else self._authorized_at_mono
            )
            if (now < last_command_or_goal or
                    now - last_command_or_goal > self._policy.cmd_timeout_sec):
                self._trip("cmd_stale")
        decision = gate_command(
            self._state, self._cmd, self._policy,
            now_mono=now, received_mono=self._cmd_rx_mono,
            authorized_at_mono=self._authorized_at_mono if self._authorized_at_mono is not None else now,
            input_generation=self._cmd_generation,
            input_epoch=self._cmd_epoch,
        )
        if can_move(self._state) and decision.reason in (
            "NONFINITE_COMMAND", "NONPLANAR_COMMAND", "INVALID_COMMAND_TYPE",
            "STALE_OR_REPLAYED_COMMAND", "INVALID_POLICY"
        ) and self._cmd is not None:
            self._trip("fault")
            decision = gate_command(
                self._state, None, self._policy, now_mono=now,
                received_mono=None, authorized_at_mono=now,
                input_generation=None, input_epoch=None,
            )
        self._cmd_pub.publish(_to_ros_twist(decision.command))
        message = String()
        message.data = json.dumps({
            "state": self._state.state.value, "reason": self._state.reason,
            "stop_reason": self._state.stop_reason,
            "scan_fault_code": self._scan_fault_code,
            "health_diagnostics": self._health_diagnostics,
            "seq": self._state.audit_seq,
            "cancel_resolution": self._state.cancel_resolution.value,
            "generation": self._state.generation,
            "goal_id": self._state.authorized_goal_id,
            "stop_is_certified_estop": False,
        })
        self._state_pub.publish(message)

    def _service_reply(self, response, before):
        response.success = self._state.state != before
        response.message = self._state.reason
        return response

    def _start(self, _request, response):
        previous = self._state.state
        if self._health(time.monotonic()):
            self._state = transition(self._state, "health_ok")
            self._state = transition(self._state, "start")
        else:
            self._state = transition(self._state, "start")
        return self._service_reply(response, previous)

    def _sw_stop(self, _request, response):
        self._state = transition(self._state, "sw_stop")
        self._clear_cmd()
        self._cmd_pub.publish(Twist())
        self._owner.stop()
        response.success = self._state.state == SafetyState.SW_STOP_LATCHED
        response.message = self._state.reason
        return response

    def _reset(self, _request, response):
        previous = self._state.state
        self._state = transition(self._state, "reset")
        return self._service_reply(response, previous)

    def _fault_cleared(self, _request, response):
        previous = self._state.state
        # A held protective stop is never silently released when the
        # watchdog recovers. Re-sample the complete live guard and require
        # a trusted Nav2 terminal cancel (or verified absence of any Goal).
        if (previous != SafetyState.PROTECTIVE_STOP
                or not self._health(time.monotonic())
                or not self._state.cancel_confirmed):
            response.success = False
            response.message = "FAULT_CLEAR_REJECTED"
            return response
        self._state = transition(self._state, "health_ok")
        self._state = transition(self._state, "fault_cleared")
        self._clear_cmd()
        self._authorized_at_mono = None
        self._cmd_pub.publish(Twist())
        return self._service_reply(response, previous)

    def _rearm(self, _request, response):
        previous = self._state.state
        if (previous == SafetyState.RECOVERY_REQUIRED and self._state.healthy
                and self._owner.rearm()):
            self._state = transition(self._state, "rearm")
            self._clear_cmd()
            self._authorized_at_mono = None
        response.success = self._state.state != previous
        response.message = self._state.reason
        return response

    def _on_goal_request(self, pose):
        if not can_move(self._state) and self._state.state == SafetyState.NORMAL:
            # NORMAL is disarmed; a fresh goal may authorize motion.
            if self._state.healthy and self._owner.ready():
                self._owner.send_pose(pose)

    def _on_accepted(self, goal_id, stopped):
        if stopped or self._state.state not in (SafetyState.NORMAL, SafetyState.LIMITED):
            self._state = transition(self._state, "track_cancel_goal", goal_id=goal_id)
            self._clear_cmd()
            return
        self._state = transition(
            self._state, "authorize_goal", goal_id=goal_id,
            generation=self._state.generation, startup_epoch=self._state.startup_epoch,
        )
        if can_move(self._state):
            self._authorized_at_mono = time.monotonic()
            self._clear_cmd()
        else:
            self._owner.stop()

    def _on_no_goal(self):
        if self._state.state in (SafetyState.SW_STOP_LATCHED, SafetyState.PROTECTIVE_STOP):
            self._state = transition(
                self._state, "no_goal_verified", verified_by_goal_manager=True
            )

    def _on_cancel_ack(self, _goal_id):
        self._state = transition(self._state, "cancel_ack")

    def _on_terminal(self, goal_id, status, canceled):
        if self._state.state in (SafetyState.SW_STOP_LATCHED, SafetyState.PROTECTIVE_STOP):
            if canceled and status == 5:
                self._state = transition(
                    self._state, "cancel_terminal", goal_id=goal_id,
                    goal_status="CANCELED",
                )
            return
        names = {4: "SUCCEEDED", 5: "CANCELED", 6: "ABORTED"}
        self._state = transition(
            self._state, "goal_finished", goal_id=goal_id,
            goal_status=names.get(status, "UNKNOWN"),
        )
        self._clear_cmd()

    def _on_action_failure(self, reason):
        self.get_logger().error("Nav2 action failed closed: " + reason)
        self._state = transition(self._state, "cancel_failed")
        if self._state.state in (SafetyState.NORMAL, SafetyState.LIMITED):
            self._trip("fault")
        self._clear_cmd()
        self._cmd_pub.publish(Twist())

def main(args=None):
    # rclpy context may already be stopped by the ROS launch signal handler.
    # External shutdown is normal; genuine node/programming exceptions surface.
    from rclpy.executors import ExternalShutdownException
    rclpy.init(args=args)
    node = None
    try:
        node = SafetySupervisorNode()
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
