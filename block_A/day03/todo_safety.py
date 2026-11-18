"""AXIA Block A D03: educational pure-Python TODO, NO ROS publisher/actuator.

Mapping uses ROS diagnostic_msgs/DiagnosticStatus integer levels 0/1/2/3,
but does NOT assert that a live ROS DiagnosticArray or physical safety loop exists.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DiagnosticSample:
    level: int
    name: str
    observed_mono: float
    message: str = ""


@dataclass(frozen=True)
class Verdict:
    mode: str
    reason: str
    requires_manual_recovery: bool


def assess_diagnostic(sample: DiagnosticSample, *, now_mono: float, timeout_s: float,
                      sw_stop_latched: bool = False,
                      prior_protective_stop: bool = False) -> Verdict:
    """Student task: implement fail-closed diagnostic -> candidate safe-mode mapping.

    Must NOT publish `/cmd_vel`, call Nav2 or claim E-Stop certification.
    NORMAL_CANDIDATE does not authorize motion or automatically rearm a robot.
    """
    # TODO-1: manual SW stop takes highest precedence.
    # TODO-2: validate type/finite time/positive timeout/name and ROS level 0..3.
    # TODO-3: age > timeout means transport STALE; age == timeout remains current.
    # TODO-4: level ERROR/STALE => PROTECTIVE_STOP, WARN => LIMITED_CANDIDATE.
    # TODO-5: after prior protective stop, healthy OK does not auto-restart.
    return Verdict("PROTECTIVE_STOP", "TODO_NOT_IMPLEMENTED", True)