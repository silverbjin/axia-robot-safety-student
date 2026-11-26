"""Read-only, exact-process P2 pre-Goal admission for isolated Jazzy simulator.

Fail closed on any absent/ambiguous role, wrong ROS session/domain/partition,
source SHA mismatch or process identity reuse. Never sends Goal, Twist or signal.
"""
from pathlib import Path
import re
import time

from axia_fault_injector.p2_process_fault_policy import eligible, matches_role
from p2_owned_process_fault import read_process

ROLES = ("p2_supervisor_node", "collision_monitor", "p2_base_guard_node")
_SHA = re.compile(r"^[0-9a-f]{40}$")


def _discover(role, session, required_env, *, proc_root=Path("/proc"), reader=read_process):
    role_seen = session_seen = 0
    matched = []
    for entry in proc_root.iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            proc = reader(int(entry.name))
            if not matches_role(proc, role):
                continue
            role_seen += 1
            if proc.session != session:
                continue
            session_seen += 1
            if all(proc.environ.get(k) == v for k, v in required_env.items()):
                matched.append(proc)
        except (OSError, ProcessLookupError, ValueError):
            continue
    if len(matched) != 1:
        raise ValueError(
            f"PID_{role}_COUNT_{len(matched)}_ROLE_{role_seen}_SESSION_{session_seen}"
        )
    return matched[0]


def inspect(launch_pid, expected_sha, actual_sha, env, *,
            proc_root=Path("/proc"), reader=read_process):
    """Return a candidate with *actual* /proc identity; never grant movement.

    A failed preflight returns diagnostic status instead of silently
    approving an unowned process. Only role, PID, session and two non-secret
    isolated transport markers are recorded.
    """
    report = {
        "status": "P2_PRE_GOAL_PID_BLOCKED",
        "gate_accepted": False, "goal_sent": False,
        "fault_injected": False, "certified_estop": False,
        "checked_host_monotonic": time.monotonic(),
    }
    try:
        if not isinstance(expected_sha, str) or not _SHA.fullmatch(expected_sha):
            raise ValueError("SOURCE_SHA_INVALID")
        if actual_sha != expected_sha:
            raise ValueError("SOURCE_SHA_MISMATCH")
        domain = env.get("ROS_DOMAIN_ID")
        partition = env.get("GZ_PARTITION")
        if (not isinstance(domain, str) or not domain.isdecimal()
                or not isinstance(partition, str)
                or not partition.startswith("axia_p2_")):
            raise ValueError("ISOLATED_ROS_ENVIRONMENT_REQUIRED")
        if type(launch_pid) is not int or launch_pid <= 1:
            raise ValueError("LAUNCH_PID_INVALID")
        launch = reader(launch_pid)
        if launch.pid != launch_pid or launch.session != launch_pid:
            raise ValueError("LAUNCH_SESSION_NOT_ISOLATED")
        required = {"ROS_DOMAIN_ID": domain, "GZ_PARTITION": partition}
        if any(launch.environ.get(k) != v for k, v in required.items()):
            raise ValueError("LAUNCH_ENV_MISMATCH")
        procs = {
            role: _discover(role, launch_pid, required,
                            proc_root=proc_root, reader=reader)
            for role in ROLES
        }
        if len({launch_pid, *(p.pid for p in procs.values())}) != 4:
            raise ValueError("PID_COLLISION")
        for case, target in (("G05", "p2_supervisor_node"),
                             ("G06", "collision_monitor")):
            ok, reason = eligible(
                case=case, target=procs[target],
                guard=procs["p2_base_guard_node"], launch=launch,
                source_sha=expected_sha, actual_source_sha=actual_sha,
                ros_domain_id=domain, gz_partition=partition,
            )
            if not ok:
                raise ValueError(case + "_POLICY_" + reason)
        # Detect PID recycling / different argv+session+environment across scan.
        for role, first in procs.items():
            if reader(first.pid) != first:
                raise ValueError("PROCESS_CHANGED_" + role)
        if reader(launch.pid) != launch:
            raise ValueError("LAUNCH_CHANGED")
        report.update(
            status="P2_PRE_GOAL_PID_CANDIDATE",
            reason="THREE_EXACT_OWNED_PROCESSES",
            session=launch_pid,
            pid_by_role={role: procs[role].pid for role in ROLES},
            ros_domain_id=domain, gz_partition=partition,
            source_sha=expected_sha,
        )
    except (OSError, ProcessLookupError, ValueError) as exc:
        report["reason"] = str(exc)[:160]
    return report
