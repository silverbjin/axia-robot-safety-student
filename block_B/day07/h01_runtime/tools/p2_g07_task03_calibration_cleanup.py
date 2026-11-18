"""Disposable NO-GOAL native ECM positive-control cleanup contract.

This is **not** an exception to the moving Goal's original Nav2 lifecycle
ACK/CM-clean-exit acceptance. The disposable NO_GOAL calibration can be
independent of a localization shutdown timeout only when the *actual*
positive witness is proven, all launched ROS/GZ processes have stopped, the
shutdown was graceful (no forced kill), and a NEW ROS_DOMAIN/GZ_PARTITION
will be used for motion. Fail closed for other errors.
"""
import os
from pathlib import Path

def actual_calibration_process_leaks(old_partition):
    if not isinstance(old_partition,str) or not old_partition.startswith("axia_p2_t03_positive_"):
        raise ValueError("TASK03_PARTITION_NOT_POSITIVE_DISPOSABLE")
    key=("GZ_PARTITION="+old_partition).encode()+b"\x00"
    seen=[]
    for p in Path("/proc").iterdir():
        if not p.name.isdecimal() or int(p.name)==os.getpid():
            continue
        try:
            if key not in p.joinpath("environ").read_bytes():
                continue
            cmd=p.joinpath("cmdline").read_bytes().replace(b"\x00",b" ").decode(errors="replace").lower()
            if any(k in cmd for k in ("gz sim","gzserver","ros2 launch",
                                       "collision_monitor","lifecycle_manager",
                                       "axia_base_command_guard","nav2_",
                                       "robot_state_publisher")):
                seen.append(int(p.name))
        except (OSError,PermissionError,ProcessLookupError):
            continue
    return seen


def assess_calibration_teardown(witness,startup,shutdown,teardown,runner_rc,leaked_pids):
    fail={"schema":"axia.g07.task03.no_goal_calibration_exception_v1",
          "status":"CONTACT_CALIBRATION_CLEANUP_UNVERIFIED_HOLD",
          "world_isolation_required":True,
          "native_nav2_l2_pass":False,
          "moving_goal_accepted":False,
          "certified_estop":False}
    if not isinstance(witness,dict) or not isinstance(startup,dict) or not isinstance(shutdown,dict):
        return fail
    if not (witness.get("sensor_found") is True
            and witness.get("report_complete") is True
            and type(witness.get("positive_contacts")) is int
            and witness["positive_contacts"]>0
            and type(witness.get("observed_iterations")) is int
            and witness["observed_iterations"]>=20
            and witness.get("missing_iterations")==0
            and type(witness.get("source_sha")) is str
            and len(witness["source_sha"])==64
            and all(c in "0123456789abcdef" for c in witness["source_sha"])
            and startup.get("status")=="SMOKE_READY"
            and startup.get("goal_sent") is False
            and startup.get("fault_injected") is False
            and type(runner_rc) is int
            and type(leaked_pids) is list
            and len(leaked_pids)==0
            and type(teardown) is str
            and "P2_L2_GRACEFUL_TEARDOWN" in teardown
            and "P2_L2_FORCED_SIGKILL" not in teardown):
        return fail
    if runner_rc==0:
        if not (shutdown.get("status")=="NAV2_LIFECYCLE_SHUTDOWN_ACK"
                and shutdown.get("navigation_ack") is True
                and shutdown.get("localization_ack") is True):
            return fail
        return {**fail,"status":"CONTACT_CALIBRATION_PROVEN_DISPOSABLE_ONLY",
                "cleanup_stage":"NATIVE_NAV_LOCALIZATION_ACK_BOTH"}
    if (runner_rc==3 and
            shutdown.get("status")=="BLOCKED_LIFECYCLE_LOCALIZATION_SERVICE_TIMEOUT"
            and shutdown.get("navigation_ack") is True
            and shutdown.get("localization_ack") is False):
        return {**fail,"status":"CONTACT_CALIBRATION_PROVEN_DISPOSABLE_ONLY",
                "cleanup_stage":"NO_GOAL_LOCALIZATION_TIMEOUT_BUT_NO_LEAK_OR_FORCED_KILL"}
    return fail
