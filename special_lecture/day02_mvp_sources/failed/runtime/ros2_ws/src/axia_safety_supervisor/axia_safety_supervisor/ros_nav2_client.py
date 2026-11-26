"""ROS 2 Jazzy Nav2 NavigateToPose owned-action adapter.

One trusted client only. No claim to block foreign ROS 2 action clients.
"""
import time
import json

from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient

from .nav2_cancel_client import GoalPhase, GoalTracker
from .action_diagnostics import action_graph_snapshot


def _goal_hex(goal_id):
    return bytes(goal_id.uuid).hex()


class RosNav2GoalOwner:
    def __init__(self, node, *, on_accepted, on_terminal, on_cancel_ack,
                 on_failure, on_no_goal, action_name="/navigate_to_pose",
                 cancel_timeout_sec=3.0):
        self._node = node
        self._action_name = action_name
        self._last_ready = None
        self._last_diagnostic = {"observed_ready": None, "action_name": action_name}
        self._client = ActionClient(node, NavigateToPose, action_name)
        self.tracker = GoalTracker()
        self._on_accepted = on_accepted
        self._on_terminal = on_terminal
        self._on_cancel_ack = on_cancel_ack
        self._on_failure = on_failure
        self._on_no_goal = on_no_goal
        self._handle = None
        self._cancel_sent = False
        self._deadline = None
        self._timeout = float(cancel_timeout_sec)

    def readiness_snapshot(self):
        """Last observed readiness and exact action-endpoint graph at loss."""
        return dict(self._last_diagnostic)

    def ready(self):
        # Fail-closed: never reuse an old ready=True to authorize a goal.
        ready = bool(self._client.server_is_ready())
        if ready:
            self.tracker.server_ready()
        if ready is False and self._last_ready is not False:
            snapshot = action_graph_snapshot(self._node, self._action_name)
            snapshot.update(
                observed_ready=False,
                goal_phase=self.tracker.phase.value,
                goal_id=self.tracker.goal_id,
            )
            self._last_diagnostic = snapshot
            if self._last_ready is True:
                self._node.get_logger().warning(
                    "ACTION_SERVER_READINESS_LOST " +
                    json.dumps(snapshot, sort_keys=True)
                )
        elif ready and self._last_ready is not True:
            self._last_diagnostic = {
                "observed_ready": True,
                "action_name": self._action_name,
                "goal_phase": self.tracker.phase.value,
                "goal_id": self.tracker.goal_id,
            }
        self._last_ready = ready
        return ready

    def send_pose(self, pose):
        if not self.ready() or not self.tracker.begin_send():
            return False
        goal = NavigateToPose.Goal()
        goal.pose = pose
        try:
            future = self._client.send_goal_async(goal)
            future.add_done_callback(self._goal_response)
        except Exception as exc:
            self.tracker.cancel_timeout()
            self._on_failure("SEND_FAILED:" + type(exc).__name__)
            return False
        return True

    def _goal_response(self, future):
        try:
            handle = future.result()
            if handle is None or not handle.accepted:
                if not self.tracker.reject_goal():
                    self._on_failure("GOAL_REJECT_STATE_INVALID")
                elif self.tracker.stop_requested and self.tracker.no_goal_verified:
                    self._on_no_goal()
                return
            self._handle = handle
            goal_id = _goal_hex(handle.goal_id)
            if not self.tracker.accept_goal(goal_id):
                self._on_failure("GOAL_ACCEPT_STATE_INVALID")
                return
            result_future = handle.get_result_async()
            result_future.add_done_callback(self._result)
            self._on_accepted(goal_id, self.tracker.stop_requested)
            if self.tracker.cancel_needed:
                self._cancel()
        except Exception as exc:
            self.tracker.cancel_timeout()
            self._on_failure("GOAL_RESPONSE_ERROR:" + type(exc).__name__)

    def stop(self):
        if not self.tracker.request_stop():
            self._on_failure("STOP_OWNERSHIP_UNKNOWN")
            return
        if self.tracker.no_goal_verified and self.ready():
            self._on_no_goal()
        if self.tracker.cancel_needed:
            self._cancel()
        elif self.tracker.phase == GoalPhase.STOP_WAIT_ACCEPT:
            self._deadline = time.monotonic() + self._timeout

    def _cancel(self):
        if self._cancel_sent or self._handle is None or not self.tracker.cancel_needed:
            return
        self._cancel_sent = True
        self._deadline = time.monotonic() + self._timeout
        try:
            future = self._handle.cancel_goal_async()
            future.add_done_callback(self._cancel_response)
        except Exception as exc:
            self.tracker.cancel_timeout()
            self._on_failure("CANCEL_SEND_FAILED:" + type(exc).__name__)

    def _cancel_response(self, future):
        if self.tracker.phase == GoalPhase.CANCELED:
            return  # Terminal result can race ahead of the ACK callback.
        try:
            response = future.result()
            goals = [_goal_hex(info.goal_id) for info in response.goals_canceling]
            if not self.tracker.cancel_response(
                return_code=int(response.return_code), goals_canceling=goals
            ):
                self._on_failure("CANCEL_ACK_REJECTED_OR_WRONG_UUID")
                return
            self._on_cancel_ack(self.tracker.goal_id)
        except Exception as exc:
            self.tracker.cancel_timeout()
            self._on_failure("CANCEL_ACK_ERROR:" + type(exc).__name__)

    def _result(self, future):
        try:
            status = int(future.result().status)
            goal_id = self.tracker.goal_id
            if not self.tracker.terminal(goal_id=goal_id, goal_status=status):
                self._on_failure("GOAL_TERMINAL_UNKNOWN")
                return
            self._deadline = None
            self._on_terminal(goal_id, status, self.tracker.cancel_confirmed)
        except Exception as exc:
            self.tracker.cancel_timeout()
            self._on_failure("RESULT_ERROR:" + type(exc).__name__)

    def check_timeout(self):
        if self._deadline is not None and time.monotonic() > self._deadline:
            if self.tracker.phase in (
                GoalPhase.STOP_WAIT_ACCEPT, GoalPhase.CANCEL_PENDING,
                GoalPhase.CANCEL_ACK
            ):
                self.tracker.cancel_timeout()
                self._deadline = None
                self._on_failure("CANCEL_TERMINAL_TIMEOUT")

    def rearm(self):
        if not self.tracker.rearm():
            return False
        self._handle = None
        self._cancel_sent = False
        self._deadline = None
        return True
