"""ROS-independent owned Nav2 goal lifecycle.

A CancelGoal ACK is never terminal cancellation. Goal ownership is scoped to
this trusted client only; it cannot detect foreign action clients.
"""
from enum import Enum
from typing import Optional


class GoalPhase(str, Enum):
    UNKNOWN = "UNKNOWN"
    IDLE = "IDLE"
    SENDING = "SENDING"
    ACTIVE = "ACTIVE"
    STOP_WAIT_ACCEPT = "STOP_WAIT_ACCEPT"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCEL_ACK = "CANCEL_ACK"
    CANCELED = "CANCELED"
    TERMINAL_OTHER = "TERMINAL_OTHER"
    FAILED = "FAILED"


class GoalTracker:
    """Single in-flight goal; fail closed on unexpected result or cancel reply."""

    def __init__(self) -> None:
        self.phase = GoalPhase.UNKNOWN
        self.goal_id: Optional[str] = None
        self.stop_requested = False
        self.cancel_acknowledged = False
        self._server_known = False

    @property
    def no_goal_verified(self) -> bool:
        # Only within the topology assumption of one exclusive trusted owner.
        return self._server_known and self.phase == GoalPhase.IDLE and self.goal_id is None

    @property
    def cancel_needed(self) -> bool:
        return self.phase == GoalPhase.CANCEL_PENDING and bool(self.goal_id)

    @property
    def cancel_confirmed(self) -> bool:
        return self.phase == GoalPhase.CANCELED

    def server_ready(self) -> None:
        self._server_known = True
        if self.phase == GoalPhase.UNKNOWN:
            self.phase = GoalPhase.IDLE

    def begin_send(self) -> bool:
        if not self.no_goal_verified or self.stop_requested:
            return False
        self.phase = GoalPhase.SENDING
        return True

    def accept_goal(self, goal_id: str) -> bool:
        if (self.phase not in (GoalPhase.SENDING, GoalPhase.STOP_WAIT_ACCEPT)
                or not isinstance(goal_id, str) or not goal_id.strip()):
            self.phase = GoalPhase.FAILED
            return False
        stopped = self.phase == GoalPhase.STOP_WAIT_ACCEPT
        self.goal_id = goal_id
        self.phase = GoalPhase.CANCEL_PENDING if stopped else GoalPhase.ACTIVE
        return True

    def reject_goal(self) -> bool:
        if self.phase not in (GoalPhase.SENDING, GoalPhase.STOP_WAIT_ACCEPT):
            self.phase = GoalPhase.FAILED
            return False
        self.phase = GoalPhase.IDLE
        self.goal_id = None
        return True

    def request_stop(self) -> bool:
        self.stop_requested = True
        if self.phase == GoalPhase.SENDING:
            self.phase = GoalPhase.STOP_WAIT_ACCEPT
            return True
        if self.phase == GoalPhase.ACTIVE:
            self.phase = GoalPhase.CANCEL_PENDING
            return True
        return self.phase in {
            GoalPhase.IDLE, GoalPhase.STOP_WAIT_ACCEPT, GoalPhase.CANCEL_PENDING,
            GoalPhase.CANCEL_ACK, GoalPhase.CANCELED, GoalPhase.TERMINAL_OTHER,
        }

    def cancel_response(self, *, return_code: int, goals_canceling: list[str]) -> bool:
        if (self.phase != GoalPhase.CANCEL_PENDING or type(return_code) is not int
                or return_code != 0 or not isinstance(goals_canceling, list)
                or self.goal_id not in goals_canceling):
            self.phase = GoalPhase.FAILED
            return False
        self.cancel_acknowledged = True
        self.phase = GoalPhase.CANCEL_ACK
        return True

    def terminal(self, *, goal_id: str, goal_status: int) -> bool:
        if goal_id != self.goal_id and self.stop_requested and self.phase in (
                GoalPhase.CANCEL_PENDING, GoalPhase.CANCEL_ACK):
            # Ignore an unrelated terminal event while retaining the expected
            # cancellation target; never authorize recovery for this mismatch.
            return False
        if (not isinstance(goal_id, str) or goal_id != self.goal_id or
                type(goal_status) is not int or goal_status not in (4, 5, 6) or
                self.phase not in (GoalPhase.ACTIVE, GoalPhase.CANCEL_PENDING,
                                   GoalPhase.CANCEL_ACK)):
            self.phase = GoalPhase.FAILED
            return False
        if self.stop_requested:
            self.phase = GoalPhase.CANCELED if goal_status == 5 else GoalPhase.TERMINAL_OTHER
        else:
            self.phase = GoalPhase.IDLE
            self.goal_id = None
        return True

    def cancel_timeout(self) -> None:
        self.phase = GoalPhase.FAILED

    def rearm(self) -> bool:
        if self.phase not in (GoalPhase.CANCELED, GoalPhase.IDLE):
            return False
        self.phase = GoalPhase.IDLE
        self.goal_id = None
        self.stop_requested = False
        self.cancel_acknowledged = False
        return True
