#!/usr/bin/env python3
"""Owner-only G05/G06 SIGKILL tool. No implicit YES; default is dry-run.

This is a *simulation* fault helper, not a safety certification. It validates
isolation, source SHA, running independent command guard, PID identity, and
requires per-case approval directly via /dev/tty before ANY SIGKILL.
"""
import argparse
from dataclasses import dataclass
import json
import math
import os
import select
import re
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'ros2_ws/src/axia_fault_injector'))
from axia_fault_injector.p2_process_fault_policy import Process, eligible, ROLES
from p2_l3_acceptance_contract import before_moving_fault
from p2_live_fault_gate import capture as live_fault_admission


def read_process(pid):
    if type(pid) is not int or pid < 2:
        raise ValueError('INVALID_PID')
    p = Path('/proc') / str(pid)
    argv = tuple(x.decode('utf-8','replace') for x in
                 (part for part in (p/'cmdline').read_bytes().split(b'\0') if part))
    env = {}
    for item in (p/'environ').read_bytes().split(b'\0'):
        if b'=' in item:
            k, v = item.split(b'=',1)
            k = k.decode('utf-8','replace')
            if k in ('ROS_DOMAIN_ID','GZ_PARTITION'):
                env[k] = v.decode('utf-8','replace')
    return Process(pid, os.getsid(pid), argv, env)


@dataclass(frozen=True)
class OwnerCrashConsent:
    """Per-case physical TTY consent, collected before Goal, never auto-YES."""
    case: str
    source_sha: str
    granted_mono: float


# The acceptance worker is a fresh Python *process*, not a ROS executor thread.
# Deliberately no environment override: only this pinned, repository-owned script.
_CONSENT_WORKER = Path(__file__).with_name('p2_tty_crash_consent_worker.py')


def consent_before_goal(case, source_sha, *, wait_seconds=30.0):
    """Fail closed with an independently enforced wall-clock Owner consent timeout.

    /dev/tty may leave a Python thread inside os.read even when O_NONBLOCK
    was requested. Running that read in an isolated subprocess lets the ROS
    observer's main thread enforce a separate timeout and preserve evidence.
    No approval is inferred from a child exit code alone.
    """
    if case not in ROLES or not isinstance(source_sha, str) or not re.fullmatch(r'[a-f0-9]{40}', source_sha):
        raise ValueError('INVALID_CASE_OR_SOURCE_FOR_CRASH_CONSENT')
    if (not isinstance(wait_seconds, (float, int)) or
            not (0.0 < wait_seconds <= 60.0) or
            not math.isfinite(wait_seconds)):
        raise ValueError('OWNER_CRASH_APPROVAL_DEADLINE_INVALID')
    if not (sys.stdin.isatty() and os.path.exists('/dev/tty')):
        raise ValueError('OWNER_CONTROLLING_TTY_REQUIRED')
    phrase = 'YES-P2-' + case + '-CRASH'
    print('P2_L3_'+case+'_CRASH_APPROVAL_WAITING: BEFORE_GOAL timeout_sec='+str(wait_seconds),
          flush=True)
    print('P2_L3_'+case+'_CRASH_APPROVAL_WORKER_START',flush=True)
    try:
        result = subprocess.run(
            [sys.executable, str(_CONSENT_WORKER), case, source_sha,
             str(wait_seconds)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
            timeout=wait_seconds+1.0, check=False)
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError('OWNER_CRASH_APPROVAL_CHILD_TIMEOUT_NO_GOAL_NO_FAULT') from exc
    except OSError as exc:
        raise ValueError('OWNER_CRASH_APPROVAL_WORKER_UNAVAILABLE') from exc
    accepted = 'OWNER_CONSENT_APPROVED '+case+' '+source_sha
    if result.returncode != 0:
        allowed = (
            'OWNER_CRASH_APPROVAL_TIMEOUT_NO_GOAL_NO_FAULT',
            'OWNER_CRASH_APPROVAL_TOO_LONG',
            'OWNER_CRASH_APPROVAL_TTY_EOF',
            'OWNER_CRASH_APPROVAL_REFUSED_OR_MISTYPED',
            'OWNER_CONTROLLING_TTY_REQUIRED',
        )
        reason = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else ''
        if reason not in allowed:
            reason = 'OWNER_CRASH_APPROVAL_WORKER_FAILED'
        if reason == 'OWNER_CRASH_APPROVAL_TIMEOUT_NO_GOAL_NO_FAULT':
            raise TimeoutError(reason)
        raise ValueError(reason)
    if result.stdout.strip() != accepted:
        raise ValueError('OWNER_CRASH_APPROVAL_INVALID_WORKER_ACK')
    print('P2_L3_'+case+'_CRASH_APPROVED_BEFORE_GOAL',flush=True)
    return OwnerCrashConsent(case, source_sha, time.monotonic())


def signal_with_pre_goal_consent(*, consent, case, pid, guard_pid, launch_pid,
                                  source_sha, ros_domain_id, gz_partition,
                                  evidence_dir, live_snapshot):
    """One-shot fault from the existing live ROS observer, no second ROS init.

    The trusted Owner runner calls this only after its separate Goal/Crash
    physical TTY prompts. Revalidate live same-session topics, Goal and
    exact PID identities *immediately* before signaling. Fail closed.
    """
    now = time.monotonic()
    if (not isinstance(consent, OwnerCrashConsent) or consent.case != case
            or consent.source_sha != source_sha
            or not (0 <= now - consent.granted_mono <= 60.0)):
        raise ValueError('CRASH_CONSENT_MISSING_EXPIRED_OR_WRONG_CASE')
    if type(pid) is not int or type(guard_pid) is not int or type(launch_pid) is not int:
        raise ValueError('INVALID_OWNED_PROCESS_ID')
    approved, why = before_moving_fault(live_snapshot)
    if not approved:
        raise ValueError('LIVE_FAULT_GATE_BLOCKED:' + why)
    expected = {
        'supervisor_publishers': [('axia_safety_supervisor', 'geometry_msgs/msg/Twist')],
        'cm_publishers': [('collision_monitor', 'geometry_msgs/msg/Twist')],
    }
    if any(live_snapshot.get(key) != value for key, value in expected.items()):
        raise ValueError('UPSTREAM_PUBLISHER_GRAPH_UNVERIFIED')
    actual = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True, timeout=5).strip()
    first = (read_process(pid), read_process(guard_pid), read_process(launch_pid))
    ok, reason = eligible(
        case=case, target=first[0], guard=first[1], launch=first[2],
        source_sha=source_sha, actual_source_sha=actual,
        ros_domain_id=ros_domain_id, gz_partition=gz_partition)
    if not ok:
        raise ValueError('OWNED_PROCESS_PREFLIGHT:' + reason)
    root = Path(evidence_dir).resolve(strict=True)
    if (Path(evidence_dir).is_symlink() or root.stat().st_mode & 0o077
            or root == ROOT or ROOT in root.parents):
        raise ValueError('EVIDENCE_DIR_NOT_PRIVATE')
    if (read_process(pid), read_process(guard_pid), read_process(launch_pid)) != first:
        raise ValueError('OWNED_PROCESS_CHANGED_BEFORE_SIGNAL')
    # The short Goal may complete during PID/SHA checks. Never signal on
    # a replayed or stale snapshot, even after valid pre-Goal consent.
    age = time.monotonic() - live_snapshot['mono']
    if not (0.0 <= age <= 0.25):
        raise ValueError('LIVE_MOTION_SNAPSHOT_EXPIRED_BEFORE_SIGNAL')
    audit = root / ('p2_' + case.lower() + '_fault_event.json')
    event = {
        'case': case, 'pid': pid, 'guard_pid': guard_pid,
        'session': first[2].session, 'source_sha': actual,
        'ros_domain_id': ros_domain_id, 'gz_partition': gz_partition,
        'operator_tty_approved': True, 'approved_before_goal': True,
        'verified_goal_uuid': live_snapshot['goal_uuid'],
        'live_gate_result': why, 'signal': 'SIGKILL',
        'at_host_monotonic_sec': time.monotonic(),
        'gate_accepted': False, 'certified_estop': False,
    }
    with audit.open('x', encoding='utf-8') as output:
        json.dump(event, output, indent=2, sort_keys=True)
        output.write('\n')
        output.flush()
        os.fsync(output.fileno())
    # Only the exact role-owned PID; no process-group termination.
    os.kill(pid, signal.SIGKILL)
    return event




def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case',choices=['G05','G06'],required=True)
    ap.add_argument('--pid',type=int,required=True)
    ap.add_argument('--guard-pid',type=int,required=True)
    ap.add_argument('--launch-pid',type=int,required=True)
    ap.add_argument('--source-sha',required=True)
    ap.add_argument('--ros-domain-id',required=True)
    ap.add_argument('--gz-partition',required=True)
    ap.add_argument('--evidence-dir',type=Path,required=True)
    ap.add_argument('--execute',action='store_true')
    args=ap.parse_args(argv)
    try:
        actual=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
        ok,reason=eligible(case=args.case,target=read_process(args.pid),
            guard=read_process(args.guard_pid),launch=read_process(args.launch_pid),
            source_sha=args.source_sha,actual_source_sha=actual,
            ros_domain_id=args.ros_domain_id,gz_partition=args.gz_partition)
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:
        ok,reason=False,'PREFLIGHT_INVALID:'+type(exc).__name__
    if not ok:
        print('P2_FAULT_BLOCKED '+reason,file=sys.stderr)
        return 2
    if not args.execute:
        print('P2_FAULT_DRY_RUN_ONLY pid='+str(args.pid)+' case='+args.case)
        return 0
    if not (sys.stdin.isatty() and sys.stdout.isatty() and os.path.exists('/dev/tty')):
        print('P2_FAULT_BLOCKED CONTROLLING_TTY_REQUIRED',file=sys.stderr)
        return 2
    phrase='YES-P2-'+args.case+'-CRASH'
    try:
        with open('/dev/tty','r',encoding='utf-8') as tty_in, \
                open('/dev/tty','w',encoding='utf-8') as tty_out:
            tty_out.write('SIMULATOR ONLY, targeted '+args.case+' process SIGKILL. Type '+phrase+': ')
            tty_out.flush()
            answer=tty_in.readline().strip()
    except OSError:
        answer=''
    if answer != phrase:
        print('P2_FAULT_BLOCKED NO_CASE_SPECIFIC_OWNER_APPROVAL',file=sys.stderr)
        return 2
    # Repeat admission AFTER human I/O, because PID reuse or exit can occur.
    try:
        live=read_process(args.pid)
        guard=read_process(args.guard_pid)
        launch=read_process(args.launch_pid)
        ok,reason=eligible(case=args.case,target=live,guard=guard,launch=launch,
            source_sha=args.source_sha,actual_source_sha=actual,
            ros_domain_id=args.ros_domain_id,gz_partition=args.gz_partition)
        if not ok:
            raise ValueError(reason)
        # The executable name, owning session, and TTY consent alone DO NOT
        # establish that the robot is currently protected and moving. Sample
        # the actual isolated ROS graph/Guard/Action/odom before *any* kill.
        try:
            live_ok, live_reason, live_sample = live_fault_admission(seconds=5.0)
        except Exception as exc:
            raise ValueError('LIVE_FAULT_GATE_UNAVAILABLE:'+type(exc).__name__) from exc
        if not live_ok:
            raise ValueError('LIVE_FAULT_GATE_BLOCKED:'+live_reason)
        # The observation window may have ended a moment ago. Re-check owner
        # identity after observing; abort if a process was recycled or died.
        if read_process(args.pid) != live or read_process(args.guard_pid) != guard or read_process(args.launch_pid) != launch:
            raise ValueError('PROCESS_REPLACED_DURING_LIVE_PROBE')
        root=args.evidence_dir.resolve(strict=True)
        if args.evidence_dir.is_symlink() or (root.stat().st_mode & 0o077):
            raise ValueError('EVIDENCE_DIR_NOT_PRIVATE_0700')
        # No implicit creation under the git repository / GitHub Artifacts.
        if root == ROOT or ROOT in root.parents:
            raise ValueError('EVIDENCE_MUST_BE_OUTSIDE_REPOSITORY')
        event={'case':args.case,'pid':args.pid,'guard_pid':args.guard_pid,
               'session':launch.session,'source_sha':actual,
               'ros_domain_id':args.ros_domain_id,'gz_partition':args.gz_partition,
               'operator_tty_approved':True,'signal':'SIGKILL',
               'live_gate_result':live_reason,
               'verified_goal_uuid':live_sample.get('action_goal_uuid'),
               'at_host_monotonic_sec':time.monotonic(),
               'gate_accepted':False,'certified_estop':False}
        audit=root/('p2_'+args.case.lower()+'_fault_event.json')
        with audit.open('x',encoding='utf-8') as fp:
            json.dump(event,fp,indent=2,sort_keys=True)
            fp.write('\n')
        os.kill(args.pid,signal.SIGKILL)  # only the owned exact process
        print('P2_FAULT_SIGNAL_SENT case='+args.case+' pid='+str(args.pid)
              +' audit='+str(audit)+' G05_G06_NOT_ACCEPTED')
        return 0
    except (OSError,ValueError) as exc:
        print('P2_FAULT_BLOCKED '+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
