"""Simulation-only exact-PID process fault admission, two P2 cases only.

Never processes unknown PIDs, kills process groups, or authorizes a Goal.
Only the standalone Owner CLI can send the signal with explicit TTY consent.
"""
from dataclasses import dataclass
import os
import re
from pathlib import PurePosixPath

ROLES = {'G05': 'p2_supervisor_node', 'G06': 'collision_monitor'}
SHA = re.compile(r'[a-f0-9]{40}\Z')


@dataclass(frozen=True)
class Process:
    pid: int
    session: int
    command: tuple[str, ...]
    environ: dict[str, str]


def matches_role(process: Process, role: str) -> bool:
    """Recognize direct executable or exact ROS Python console-script entrypoint.

    Jazzy Python console scripts can appear in /proc/PID/cmdline as
    /usr/bin/python3 + <install>/lib/axia_safety_supervisor/<entrypoint>.
    Never use substring matching; session, env, SHA and TTY gates still apply.
    """
    if role not in ('p2_supervisor_node', 'p2_base_guard_node', 'collision_monitor'):
        return False
    if not isinstance(process, Process) or not process.command:
        return False
    program = os.path.basename(process.command[0])
    if program == role:
        return True  # pre-existing direct executable behavior
    if role == 'collision_monitor' or not re.fullmatch(r'python(?:3(?:\.\d+)?)?', program):
        return False
    if len(process.command) < 2:
        return False
    script = PurePosixPath(process.command[1])
    return (script.is_absolute() and '..' not in script.parts
            and script.parts[-3:] == ('lib', 'axia_safety_supervisor', role))

def eligible(*, case, target, guard, launch, source_sha, actual_source_sha,
             ros_domain_id, gz_partition) -> tuple[bool, str]:
    if case not in ROLES:
        return False, 'UNSUPPORTED_CASE'
    if (not isinstance(source_sha, str) or not SHA.fullmatch(source_sha)
            or source_sha != actual_source_sha):
        return False, 'SOURCE_SHA_MISMATCH'
    if not all(isinstance(p, Process) and type(p.pid) is int and p.pid > 1
               for p in (target, guard, launch)):
        return False, 'PROCESS_METADATA_INVALID'
    if len({target.pid, guard.pid, launch.pid}) != 3:
        return False, 'PID_COLLISION'
    if launch.session != launch.pid or any(p.session != launch.session
                                            for p in (target, guard)):
        return False, 'PROCESS_NOT_OWNED_BY_ISOLATED_LAUNCH'
    if not all(isinstance(p.command, tuple) and p.command
               for p in (target, guard, launch)):
        return False, 'EMPTY_PROCESS_COMMAND'
    if not matches_role(target, ROLES[case]):
        return False, 'WRONG_FAULT_TARGET'
    if not matches_role(guard, 'p2_base_guard_node'):
        return False, 'INDEPENDENT_GUARD_PROCESS_MISSING'
    if not isinstance(ros_domain_id, str) or not ros_domain_id.isdecimal():
        return False, 'ROS_DOMAIN_INVALID'
    if not isinstance(gz_partition, str) or not gz_partition.startswith('axia_p2_'):
        return False, 'GZ_PARTITION_NOT_ISOLATED'
    for p in (target, guard, launch):
        if p.environ.get('ROS_DOMAIN_ID') != ros_domain_id or (
            p.environ.get('GZ_PARTITION') != gz_partition
        ):
            return False, 'RUN_ENVIRONMENT_MISMATCH'
    return True, 'CANDIDATE_OWNED_REQUIRES_TTY_CONSENT'
