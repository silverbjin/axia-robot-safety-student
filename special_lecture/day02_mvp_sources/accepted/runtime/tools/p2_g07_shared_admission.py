"""G07 simulation-only Owner admission for the exact CI/Owner shared scenario.

A GitHub CI runner is authorized independently by _require_ci_only().
This helper never approves Goal by itself: it verifies that the existing
Owner Shell has already completed a real controlling-TTY consent and that
the protected Supervisor/CM/Guard process group matches the pinned SHA.
"""
import re

_ROLES=frozenset(("p2_supervisor_node","collision_monitor","p2_base_guard_node"))
_SHA=re.compile(r"^[a-f0-9]{40}$")

def admit_owner(*,expected_sha,actual_sha,launch_pid,env,has_tty,inspect):
    if (not isinstance(expected_sha,str) or not _SHA.fullmatch(expected_sha)
            or actual_sha!=expected_sha or type(launch_pid) is not int
            or launch_pid<=1):
        raise ValueError("OWNER_EXACT_SOURCE_OR_SESSION_INVALID")
    if (env.get("GITHUB_ACTIONS")=="true"
            or env.get("AXIA_G07_CI_SIM_GOAL_ALLOWED")=="1"):
        raise ValueError("OWNER_AND_CI_AUTHORITY_CANNOT_OVERLAP")
    if (env.get("AXIA_G07_OWNER_COMMON_RUNNER_AUTHORIZED")!="1"
            or env.get("AXIA_P2_OWNER_PINNED_SHA")!=expected_sha
            or not has_tty):
        raise ValueError("OWNER_MANUAL_TTY_GOAL_NOT_AUTHORIZED")
    if (env.get("ROS_DISTRO")!="jazzy"
            or env.get("AXIA_P0_SIM_ONLY")!="1"
            or not env.get("GZ_PARTITION","").startswith("axia_p2_")
            or not str(env.get("ROS_DOMAIN_ID","")).isdecimal()):
        raise ValueError("OWNER_SIMULATION_ISOLATION_INVALID")
    admission=inspect(launch_pid,expected_sha,actual_sha,env)
    if (admission.get("status")!="P2_PRE_GOAL_PID_CANDIDATE"
            or set(admission.get("pid_by_role",{}))!=_ROLES
            or len(set(admission["pid_by_role"].values()))!=3
            or launch_pid in admission["pid_by_role"].values()):
        raise ValueError("OWNER_THREE_ROLE_PID_BLOCKED:"+str(
            admission.get("reason","ROLE_OR_PID_MISMATCH")))
    return {"mode":"owner","goal_sent":False,"gate_accepted":False,
            "certified_estop":False,
            "launch_pid":launch_pid,
            "owned_pids":admission["pid_by_role"]}
