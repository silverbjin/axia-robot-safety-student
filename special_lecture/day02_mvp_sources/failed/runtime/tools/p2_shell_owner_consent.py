#!/usr/bin/env python3
"""P2 MVP: one-shot Owner Crash consent receipt from proven Shell TTY gate.

This is SIMULATION ONLY. The caller shell checks the exact second YES phrase
directly on its controlling TTY *before* creating this receipt. This helper
never sends a Goal, ROS command, fault signal or process termination.
"""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import time

from p2_owned_process_fault import OwnerCrashConsent


def _validate(case, source_sha, launch_pid, domain, partition):
    if case not in ("G05", "G06"):
        raise ValueError("SHELL_CRASH_CASE_INVALID")
    if not isinstance(source_sha, str) or not re.fullmatch(r"[a-f0-9]{40}", source_sha):
        raise ValueError("SHELL_CRASH_SHA_INVALID")
    if type(launch_pid) is not int or launch_pid < 2:
        raise ValueError("SHELL_CRASH_LAUNCH_PID_INVALID")
    if not isinstance(domain, str) or not domain.isdecimal():
        raise ValueError("SHELL_CRASH_DOMAIN_INVALID")
    if not isinstance(partition, str) or not partition.startswith("axia_p2_"):
        raise ValueError("SHELL_CRASH_PARTITION_INVALID")


def _require_private_parent(path):
    parent = path.parent
    if not parent.is_dir() or parent.is_symlink():
        raise ValueError("SHELL_CRASH_EVIDENCE_DIR_INVALID")
    metadata = parent.stat()
    if metadata.st_uid != os.getuid() or (stat.S_IMODE(metadata.st_mode) & 0o077):
        raise ValueError("SHELL_CRASH_EVIDENCE_DIR_NOT_PRIVATE")


def write_receipt(path, case, source_sha, launch_pid, domain, partition):
    path = Path(path)
    _validate(case, source_sha, launch_pid, domain, partition)
    _require_private_parent(path)
    payload = {
        "case": case, "source_sha": source_sha, "launch_pid": launch_pid,
        "ros_domain_id": domain, "gz_partition": partition,
        "approved_by": "OWNER_SHELL_TTY_EXACT_CASE_CRASH_PHRASE",
        "granted_mono": time.monotonic(),
        "gate_accepted": False, "certified_estop": False,
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return payload


def consume_receipt(path, case, source_sha, launch_pid, domain, partition):
    path = Path(path)
    _validate(case, source_sha, launch_pid, domain, partition)
    _require_private_parent(path)
    meta = path.lstat()
    if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.getuid()
            or (stat.S_IMODE(meta.st_mode) & 0o077)):
        raise ValueError("SHELL_CRASH_RECEIPT_NOT_PRIVATE_REGULAR")
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    expected = {
        "case": case, "source_sha": source_sha, "launch_pid": launch_pid,
        "ros_domain_id": domain, "gz_partition": partition,
        "approved_by": "OWNER_SHELL_TTY_EXACT_CASE_CRASH_PHRASE",
        "gate_accepted": False, "certified_estop": False,
    }
    if any(payload.get(k) != v for k, v in expected.items()):
        raise ValueError("SHELL_CRASH_RECEIPT_CONTEXT_MISMATCH")
    granted = payload.get("granted_mono")
    age = time.monotonic() - granted if type(granted) in (int, float) else -1
    if not 0 <= age <= 60:
        raise ValueError("SHELL_CRASH_RECEIPT_EXPIRED")
    consumed = path.with_name(path.name + ".consumed")
    if consumed.exists():
        raise ValueError("SHELL_CRASH_RECEIPT_REPLAY")
    path.rename(consumed)  # one-shot; consumed record preserved as raw evidence
    return OwnerCrashConsent(case, source_sha, granted)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=Path, required=True)
    parser.add_argument("--case", choices=("G05", "G06"), required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--launch-pid", type=int, required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--partition", required=True)
    args = parser.parse_args(argv)
    if not os.isatty(0) or not Path("/dev/tty").exists():
        parser.error("OWNER_CONTROLLING_TTY_REQUIRED")
    write_receipt(args.write, args.case, args.sha, args.launch_pid,
                  args.domain, args.partition)
    print("P2_SHELL_CRASH_CONSENT_RECORDED_NO_GOAL_NO_FAULT", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
