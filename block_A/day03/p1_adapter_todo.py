"""D03 student TODO: P1 JSON -> diagnostic_msgs/DiagnosticStatus data.

Pure Python contract: NO ROS dependency, no command publisher, no motion authority.
The ROS bridge supplies the actual diagnostic_msgs types after this mapping.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DiagnosticRecord:
    level: int                 # 0 OK / 1 WARN / 2 ERROR / 3 STALE
    name: str                  # AXIA/P1/SafetySupervisor
    message: str               # conservative, fixed message code
    hardware_id: str           # simulated robot only
    values: tuple[tuple[str, str], ...]  # sanitized key/value pairs


def diagnose_p1_state(raw_json: str | None, *, received_mono: float | None,
                      now_mono: float, timeout_s: float = 1.0) -> DiagnosticRecord:
    """Return diagnostic data, NEVER authorize robot motion.

    TODO-1: Reject non-finite/negative time and invalid timeout; fail closed.
    TODO-2: None raw_json / no receipt / old receipt -> level STALE (3).
    TODO-3: Decode JSON object, require state and stop_is_certified_estop=false.
    TODO-4: PROTECTIVE_STOP -> ERROR; BOOT_SAFE/LIMITED/RECOVERY_REQUIRED/
            SW_STOP_LATCHED -> WARN; NORMAL -> OK only with healthy flags.
    TODO-5: Return sanitized values. Never emit goal_id or raw JSON.
    """
    return DiagnosticRecord(2, "AXIA/P1/SafetySupervisor", "TODO_NOT_IMPLEMENTED",
                            "tb3_waffle_sim", ())