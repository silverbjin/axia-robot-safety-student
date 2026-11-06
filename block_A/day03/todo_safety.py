"""D03 순수 Python 교육용 TODO. No ROS publishers or robot commands."""
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
    """DiagnosticStatus 0/1/2/3 → mode candidate. NOT movement authority."""
    # TODO-1: SW_STOP_LATCHED has highest priority.
    # TODO-2: reject bad level, timestamp, name, timeout and non-finite inputs.
    # TODO-3: if age > timeout, return PROTECTIVE_STOP/DIAGNOSTIC_STALE.
    # TODO-4: ERROR or STALE => PROTECTIVE_STOP; WARN => LIMITED_CANDIDATE.
    # TODO-5: previous protective stop + healthy input => RECOVERY_REQUIRED.
    return Verdict("PROTECTIVE_STOP", "TODO_NOT_IMPLEMENTED", True)
