"""G10 synthetic combined-fault / manual reset oracle: L0 educational only.

No real ROS/Gazebo/Owner Goal or Fault is started or authenticated here.
A synthetic event sequence MUST NOT be represented as formal G10 acceptance.
"""
from __future__ import annotations

import math
import re

_UUID = re.compile(r"^[0-9a-f]{32}$")
_REQUIRED = (
    "GOAL_EXECUTING", "ODOM_MOVING", "SCAN_FAULT", "CM_LOST",
    "GUARD_LATCH", "FINAL_CMD", "ODOM_STOP_DWELL", "NAV2_GOAL_CANCELED",
    "RESET_REJECTED_ACTIVE_FAULT", "HEALTH_RESTORED",
    "OWNER_RESET_APPROVED", "RESET_OK", "OWNER_REARM_APPROVED",
    "REARM_OK", "NO_AUTO_RESUME",
)


def assess_g10_compound(events) -> dict:
    result = {
        "status": "BLOCKED",
        "reason": "MISSING_OR_INVALID_EVIDENCE",
        "stop_latency_sec": None,
        "verification_level": "SYNTHETIC_L0_ONLY",
        "formal_accepted": False,
        "goal_sent": False,
        "fault_injected": False,
        "certified_estop": False,
    }
    if not isinstance(events, list) or not 15 <= len(events) <= 256:
        return result
    last = -math.inf
    names = []
    for e in events:
        if not isinstance(e, dict) or type(e.get("event")) is not str:
            return result
        at = e.get("t_sec")
        if type(at) not in (int, float) or not math.isfinite(at) or at < 0 or at <= last:
            return result
        last = at
        names.append(e["event"])
    if any(name in names for name in
           ("AUTO_RESUME", "UNAPPROVED_GOAL", "NAV2_GOAL_SUCCEEDED",
            "NEW_GOAL_WITHOUT_OWNER_APPROVAL")):
        result["reason"] = "UNAUTHORIZED_MOTION_OR_UNSAFE_GOAL_TERMINAL"
        return result
    if any(names.count(name) != 1 for name in _REQUIRED):
        return result
    positions = [names.index(key) for key in _REQUIRED]
    if positions != sorted(positions):
        result["reason"] = "FIRST_SAFETY_OR_RECOVERY_TRANSITION_ORDER_VIOLATED"
        return result
    observations = {e["event"]: e for e in events}
    goal = observations["GOAL_EXECUTING"].get("goal_uuid")
    terminal = observations["NAV2_GOAL_CANCELED"].get("goal_uuid")
    if (type(goal) is not str or not _UUID.fullmatch(goal)
            or terminal != goal):
        result["reason"] = "GOAL_UUID_PROVENANCE_MISMATCH"
        return result
    moving = observations["ODOM_MOVING"].get("speed_mps")
    if type(moving) not in (int, float) or not math.isfinite(moving) or moving <= .03:
        result["reason"] = "ACTUAL_MOTION_NOT_PROVEN"
        return result
    first_fault = observations["SCAN_FAULT"]["t_sec"]
    if observations["CM_LOST"]["t_sec"] - first_fault > .5:
        result["reason"] = "FAULTS_NOT_COMPOUND"
        return result
    stop = observations["ODOM_STOP_DWELL"]
    stop_t, dwell = stop.get("stop_t"), stop.get("dwell_sec")
    if (type(stop_t) not in (float, int) or type(dwell) not in (float, int)
            or not math.isfinite(stop_t) or not math.isfinite(dwell)
            or not 0 <= stop_t - first_fault <= 1.5
            or dwell < 1.0
            or stop_t + dwell > stop["t_sec"] + 1e-8):
        result["reason"] = "STOP_LATENCY_OR_ODOM_DWELL_NOT_PROVEN"
        return result
    latch_t = observations["GUARD_LATCH"]["t_sec"]
    if not first_fault < latch_t <= stop_t:
        result["reason"] = "GUARD_LATCH_AFTER_STOP_OR_BEFORE_FAULT"
        return result
    for e in events:
        if e["event"] in ("FINAL_CMD", "NO_AUTO_RESUME") and e["t_sec"] >= latch_t:
            vx, wz = e.get("vx"), e.get("wz")
            if (type(vx) not in (float, int) or type(wz) not in (float, int)
                    or not math.isfinite(vx) or not math.isfinite(wz)
                    or abs(vx) >= 0.01 or abs(wz) >= .02):
                result["reason"] = "POST_LATCH_NONZERO_OR_MISSING_CMD"
                return result
    result.update(
        status="L0_SYNTHETIC_SEQUENCE_CANDIDATE",
        reason="RAW_ROS_GAZEBO_GOAL_AUTHORITY_NOT_ATTESTED",
        stop_latency_sec=round(stop_t - first_fault, 6),
    )
    return result
