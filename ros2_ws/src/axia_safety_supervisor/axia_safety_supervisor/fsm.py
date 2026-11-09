"""Deterministic ROS-free P1 state machine. Software stop is NOT an E-Stop.

Integration must implement goal ownership, action cancellation, timer and Twist
publication separately. Only trusted goal-client events may authorize a goal.
"""
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Optional, FrozenSet
from uuid import uuid4


class SafetyState(str, Enum):
    BOOT_SAFE = "BOOT_SAFE"
    NORMAL = "NORMAL"
    LIMITED = "LIMITED"
    PROTECTIVE_STOP = "PROTECTIVE_STOP"
    SW_STOP_LATCHED = "SW_STOP_LATCHED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class CancelResolution(str, Enum):
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"
    CANCELED = "CANCELED"
    NO_GOAL_VERIFIED = "NO_GOAL_VERIFIED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class SafetySnapshot:
    state: SafetyState = SafetyState.BOOT_SAFE
    healthy: bool = False
    cancel_resolution: CancelResolution = CancelResolution.UNKNOWN
    expected_cancel_goal_id: Optional[str] = None
    generation: int = 0
    startup_epoch: str = field(default_factory=lambda: uuid4().hex)
    used_goal_ids: FrozenSet[str] = frozenset()
    authorized_goal_id: Optional[str] = None
    last_goal_id: Optional[str] = None
    audit_seq: int = 0
    reason: str = "BOOT_SAFE"
    stop_reason: str = ""  # Persistent hazard cause, not last audit event.

    @property
    def cancel_confirmed(self) -> bool:
        """Read-only compatibility: ACK alone is never terminal."""
        return self.cancel_resolution in {
            CancelResolution.CANCELED, CancelResolution.NO_GOAL_VERIFIED
        }


def health_loss_requires_goal_stop(state: SafetyState) -> bool:
    """A live/Started owner must cancel on health loss; BOOT_SAFE has no Goal.

    Never call RosNav2GoalOwner.stop() on a *transient pre-Start* scan/DDS
    warning: its trusted GoalTracker persists stop_requested=True and would
    subsequently reject every first Goal even after BOOT_SAFE health recovers.
    SW_STOP_LATCHED/PROTECTIVE_STOP already requested stop at first transition.
    """
    return state in (SafetyState.NORMAL, SafetyState.LIMITED)


def can_move(s: SafetySnapshot) -> bool:
    """Command authorization only, NOT proof of robot movement/safety."""
    return (
        s.state in (SafetyState.NORMAL, SafetyState.LIMITED)
        and s.healthy is True
        and isinstance(s.authorized_goal_id, str)
        and bool(s.authorized_goal_id)
    )


def _record(s: SafetySnapshot, reason: str, **changes) -> SafetySnapshot:
    return replace(s, audit_seq=s.audit_seq + 1, reason=reason, **changes)


def _stop(s: SafetySnapshot, reason: str, *, manual: bool = False) -> SafetySnapshot:
    if s.state == SafetyState.SW_STOP_LATCHED and not manual:
        return _record(s, reason, healthy=False if reason == "HEALTH_BAD" else s.healthy)
    tracked = s.authorized_goal_id if s.authorized_goal_id is not None else s.expected_cancel_goal_id
    return _record(
        s, reason,
        state=SafetyState.SW_STOP_LATCHED if manual else SafetyState.PROTECTIVE_STOP,
        authorized_goal_id=None,
        expected_cancel_goal_id=tracked,
        cancel_resolution=CancelResolution.PENDING if tracked else CancelResolution.UNKNOWN,
        stop_reason=reason,
    )


def transition(
    s: SafetySnapshot, event: str, *, goal_id: Optional[str] = None,
    goal_status: Optional[str] = None, generation: Optional[int] = None,
    verified_by_goal_manager: bool = False,
    startup_epoch: Optional[str] = None,
) -> SafetySnapshot:
    """Fail closed on invalid state/event; record every attempted transition.

    A prior goal may only be canceled by a trusted confirmed terminal result.
    """
    if not isinstance(s.state, SafetyState):
        return _stop(s, "INVALID_STATE")
    if event == "sw_stop":
        return _stop(s, "SW_STOP_REQUESTED", manual=True)
    if event in {"scan_stale", "scan_invalid", "cmd_stale", "clock_regression",
                 "clock_stalled", "tf_invalid", "fault"}:
        return _stop(s, "FAULT:" + event)
    if event == "health_bad":
        # The robot has never been Started and owns no movement authority.
        # A momentary sensor/CM/DDS delay during BOOT_SAFE must withhold
        # Start without converting an unarmed boot into a *latched* stop
        # whose recovery service is not yet available. Never auto-Start.
        if s.state == SafetyState.BOOT_SAFE:
            return _record(s, "BOOT_HEALTH_BAD", healthy=False)
        if s.state in (
            SafetyState.RECOVERY_REQUIRED, SafetyState.PROTECTIVE_STOP,
            SafetyState.SW_STOP_LATCHED
        ):
            # Preserve original stop cause, pending cancel and Goal UUID.
            return _record(s, "HEALTH_BAD", healthy=False)
        x = _stop(s, "HEALTH_BAD")
        return replace(x, healthy=False)
    if event == "health_ok":
        return _record(s, "HEALTH_OK", healthy=True)
    if event == "start":
        if s.state == SafetyState.BOOT_SAFE and s.healthy:
            return _record(s, "START_APPROVED", state=SafetyState.NORMAL,
                           generation=s.generation + 1, authorized_goal_id=None,
                           stop_reason="")
        return _record(s, "START_REJECTED")
    if event in {"limit_on", "limit_off"}:
        if s.healthy and s.state in (SafetyState.NORMAL, SafetyState.LIMITED):
            return _record(s, "LIMIT_ON" if event == "limit_on" else "LIMIT_OFF",
                           state=SafetyState.LIMITED if event == "limit_on" else SafetyState.NORMAL)
        return _record(s, "LIMIT_REJECTED")
    if event == "cancel_ack":
        return _record(s, "CANCEL_ACCEPTED_NOT_TERMINAL")
    if event == "track_cancel_goal":
        if (s.state in (SafetyState.SW_STOP_LATCHED, SafetyState.PROTECTIVE_STOP)
                and s.expected_cancel_goal_id is None and not s.cancel_confirmed
                and isinstance(goal_id, str) and bool(goal_id.strip())):
            return _record(s, "LATE_GOAL_TRACKED_FOR_CANCEL",
                           expected_cancel_goal_id=goal_id,
                           cancel_resolution=CancelResolution.PENDING)
        return _record(s, "LATE_GOAL_REJECTED")
    if event == "cancel_failed":
        if s.state in (SafetyState.SW_STOP_LATCHED, SafetyState.PROTECTIVE_STOP):
            return _record(s, "CANCEL_FAILED",
                           cancel_resolution=CancelResolution.FAILED)
        return _record(s, "CANCEL_FAILURE_IGNORED")
    if event == "cancel_terminal":
        if (s.state in {SafetyState.SW_STOP_LATCHED, SafetyState.PROTECTIVE_STOP}
                and goal_status == "CANCELED" and isinstance(goal_id, str)
                and bool(goal_id) and goal_id == s.expected_cancel_goal_id):
            return _record(s, "CANCEL_CONFIRMED",
                           cancel_resolution=CancelResolution.CANCELED)
        return _record(s, "CANCEL_NOT_CONFIRMED")
    if event == "no_goal_verified":
        if (verified_by_goal_manager is True
                and s.state in {SafetyState.SW_STOP_LATCHED, SafetyState.PROTECTIVE_STOP}
                and s.expected_cancel_goal_id is None):
            return _record(s, "NO_ACTIVE_GOAL_VERIFIED",
                           cancel_resolution=CancelResolution.NO_GOAL_VERIFIED)
        return _record(s, "NO_GOAL_PROOF_REJECTED")
    if event == "reset":
        if s.state == SafetyState.SW_STOP_LATCHED and s.healthy and s.cancel_confirmed:
            return _record(s, "RESET_TO_RECOVERY", state=SafetyState.RECOVERY_REQUIRED)
        return _record(s, "RESET_REJECTED")
    if event == "fault_cleared":
        if s.state == SafetyState.PROTECTIVE_STOP and s.healthy and s.cancel_confirmed:
            return _record(s, "FAULT_TO_RECOVERY", state=SafetyState.RECOVERY_REQUIRED)
        return _record(s, "FAULT_CLEAR_REJECTED")
    if event == "rearm":
        if s.state == SafetyState.RECOVERY_REQUIRED and s.healthy and s.cancel_confirmed:
            return _record(s, "REARMED_DISARMED", state=SafetyState.NORMAL,
                           generation=s.generation + 1, authorized_goal_id=None,
                           stop_reason="")
        return _record(s, "REARM_REJECTED")
    if event == "authorize_goal":
        if (s.state in {SafetyState.NORMAL, SafetyState.LIMITED} and s.healthy
                and isinstance(goal_id, str) and bool(goal_id.strip())
                and goal_id.strip() == goal_id
                and goal_id not in s.used_goal_ids
                and s.authorized_goal_id is None
                and type(generation) is int and generation == s.generation
                and isinstance(startup_epoch, str)
                and startup_epoch == s.startup_epoch):
            return _record(s, "GOAL_AUTHORIZED", last_goal_id=goal_id,
                           authorized_goal_id=goal_id,
                           used_goal_ids=s.used_goal_ids | frozenset((goal_id,)))
        return _stop(s, "GOAL_AUTHORIZATION_INVALID")
    if event == "goal_finished":
        if (isinstance(goal_id, str) and goal_id == s.authorized_goal_id
                and goal_status in {"SUCCEEDED", "ABORTED", "CANCELED"}):
            return _record(s, "GOAL_TERMINAL:" + goal_status, authorized_goal_id=None)
        return _stop(s, "GOAL_RESULT_INVALID")
    return _stop(s, "INVALID_EVENT")
