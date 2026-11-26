"""P1 software command gate pure policy. No certified E-stop or ROS output guarantee.

ROS Twist messages carry no goal UUID/epoch. The trusted ROS node must tag
receive-time commands, flush buffered commands on stop/rearm, and audit the
final Collision Monitor /cmd_vel path independently.
"""
from dataclasses import dataclass
import math
from typing import Optional

from .fsm import SafetySnapshot, SafetyState, can_move


@dataclass(frozen=True)
class TwistCommand:
    linear_x: float = 0.0
    linear_y: float = 0.0
    linear_z: float = 0.0
    angular_x: float = 0.0
    angular_y: float = 0.0
    angular_z: float = 0.0


@dataclass(frozen=True)
class GatePolicy:
    max_linear_mps: float
    max_angular_rps: float
    limited_ratio: float
    cmd_timeout_sec: float


@dataclass(frozen=True)
class GateDecision:
    command: TwistCommand
    allowed: bool
    reason: str


ZERO = TwistCommand()


def _finite(value) -> bool:
    return type(value) in (float, int) and math.isfinite(value)


def _deny(reason: str) -> GateDecision:
    return GateDecision(ZERO, False, reason)


def _clip(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))


def gate_command(
    snapshot: SafetySnapshot, incoming: Optional[TwistCommand], policy: GatePolicy,
    *, now_mono: float, received_mono: Optional[float], authorized_at_mono: float,
    input_generation: Optional[int], input_epoch: Optional[str],
) -> GateDecision:
    """Compute a conservative Twist output; runtime ROS node still pending."""
    if not isinstance(snapshot, SafetySnapshot) or not can_move(snapshot):
        return _deny("DISARMED_OR_STOP")
    if (not isinstance(policy, GatePolicy)
            or not all(_finite(v) for v in (policy.max_linear_mps, policy.max_angular_rps,
                                            policy.limited_ratio, policy.cmd_timeout_sec))
            or policy.max_linear_mps <= 0 or policy.max_angular_rps <= 0
            or not 0 < policy.limited_ratio <= 1 or policy.cmd_timeout_sec <= 0):
        return _deny("INVALID_POLICY")
    if (type(input_generation) is not int or input_generation != snapshot.generation
            or not isinstance(input_epoch, str) or input_epoch != snapshot.startup_epoch):
        return _deny("OLD_OR_UNTRUSTED_GENERATION")
    if (not _finite(now_mono) or not _finite(received_mono) or
            not _finite(authorized_at_mono) or
            received_mono > now_mono or received_mono < authorized_at_mono or
            now_mono - received_mono > policy.cmd_timeout_sec):
        return _deny("STALE_OR_REPLAYED_COMMAND")
    if not isinstance(incoming, TwistCommand):
        return _deny("INVALID_COMMAND_TYPE")
    if not all(_finite(getattr(incoming, field)) for field in (
            "linear_x", "linear_y", "linear_z", "angular_x", "angular_y", "angular_z")):
        return _deny("NONFINITE_COMMAND")
    if any(getattr(incoming, field) != 0 for field in (
            "linear_y", "linear_z", "angular_x", "angular_y")):
        return _deny("NONPLANAR_COMMAND")
    factor = policy.limited_ratio if snapshot.state == SafetyState.LIMITED else 1.0
    linear_limit = policy.max_linear_mps * factor
    angular_limit = policy.max_angular_rps * factor
    output = TwistCommand(
        linear_x=_clip(incoming.linear_x, linear_limit),
        angular_z=_clip(incoming.angular_z, angular_limit),
    )
    return GateDecision(output, True, "LIMITED" if factor != 1.0 else "AUTHORIZED")
