"""G07 Owner shutdown truth audit (SIM ONLY, never E-Stop certification).

Runs only AFTER the original Owner process group has terminated. It does
not alter navigation or ROS lifecycles and cannot turn a numerical candidate
into final Owner L3 acceptance. Log-file paths remain private Owner evidence.
"""
import argparse
import json
import re
from pathlib import Path

_CM_NONZERO = re.compile(
    r"\[(?:ERROR|WARN)\]\s+\[collision_monitor(?:-\d+)?\]:"
    r"\s*process has died\b[^\n]*?exit code\s+(-?\d+)\b"
)
_CM_CLEAN = re.compile(
    r"\[INFO\]\s+\[collision_monitor(?:-\d+)?\]:"
    r"\s*process has finished cleanly\b"
)


def audit(launch_log: str, live_log: str) -> dict:
    if not isinstance(launch_log, str) or not isinstance(live_log, str):
        raise TypeError("INVALID_SHUTDOWN_EVIDENCE")
    abnormal = _CM_NONZERO.search(launch_log)
    clean = bool(_CM_CLEAN.search(launch_log))
    if abnormal is not None:
        status = "BLOCKED_CM_ABNORMAL_EXIT"
        exit_code = int(abnormal.group(1))
    elif clean:
        status = "SHUTDOWN_CLEAN_CANDIDATE"
        exit_code = 0
    else:
        status = "BLOCKED_CM_SHUTDOWN_UNVERIFIED"
        exit_code = None
    return {
        "schema": "axia_g07_owner_shutdown_audit_v1",
        "status": status,
        "cm_exit_code": exit_code,
        "rclpy_destroyable_warning_observed": (
            "cannot use Destroyable because destruction was requested" in live_log
        ),
        "raw_motion_evidence_unchanged": True,
        "owner_l3_accepted": False,
        "certified_estop": False,
        "collision_ground_truth": False,
        "sim_only": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--launch-log", type=Path, required=True)
    ap.add_argument("--live-log", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    verdict = audit(
        args.launch_log.read_text(encoding="utf-8", errors="replace"),
        args.live_log.read_text(encoding="utf-8", errors="replace"),
    )
    args.output.write_text(json.dumps(verdict, sort_keys=True, indent=2)+"\n")
    print("AXIA_G07_OWNER_SHUTDOWN_AUDIT " + json.dumps(verdict, sort_keys=True),
          flush=True)
    return 0 if verdict["status"]=="SHUTDOWN_CLEAN_CANDIDATE" else 2


if __name__=="__main__":
    raise SystemExit(main())
