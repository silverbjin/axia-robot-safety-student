#!/usr/bin/env python3
"""Capture-time, same-process provenance for read-only P1-T08 observables.

Only records what a producer observed while invoked within a pinned checkout.
A receipt is NOT proof of ROS origin, Start ACK, Goal authorization or
Gazebo acceptance. Call at the final evidence write, not as posthoc relabeling.
"""
from __future__ import annotations

import os
import math
from pathlib import Path
import re
import subprocess
import time
from typing import Mapping

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{7,79}\Z")
_SHA = re.compile(r"[a-f0-9]{40}\Z")
_KEYS = ("AXIA_T08_RUN_ID", "AXIA_T08_SESSION_ID", "AXIA_T08_SOURCE_SHA")


class ProvenanceError(ValueError):
    """Runtime capture context cannot be tied to a pinned isolated session."""


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True,
            timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProvenanceError("SOURCE_GIT_UNAVAILABLE") from exc
    if result.returncode != 0:
        raise ProvenanceError("SOURCE_GIT_UNAVAILABLE")
    return result.stdout.strip()


def live_provenance(*, source_root: Path, environ: Mapping[str, str] | None = None,
                    now_ns: int | None = None) -> dict:
    """Fail closed if checkout, ROS isolation, session or clock is unverified."""
    env = os.environ if environ is None else environ
    if not isinstance(env, Mapping):
        raise ProvenanceError("ENVIRONMENT_INVALID")
    run_id = env.get("AXIA_T08_RUN_ID")
    session_id = env.get("AXIA_T08_SESSION_ID")
    source_sha = env.get("AXIA_T08_SOURCE_SHA")
    if not isinstance(run_id, str) or not _ID.fullmatch(run_id) or not isinstance(
            session_id, str) or not _ID.fullmatch(session_id):
        raise ProvenanceError("RUN_SESSION_INVALID")
    if not isinstance(source_sha, str) or not _SHA.fullmatch(source_sha):
        raise ProvenanceError("SOURCE_SHA_INVALID")
    domain = env.get("ROS_DOMAIN_ID")
    partition = env.get("GZ_PARTITION")
    if not (env.get("ROS_DISTRO") == "jazzy"
            and env.get("AXIA_P0_SIM_ONLY") == "1"
            and env.get("AXIA_T08_FAULT_APPROVED", "NO") == "NO"
            and isinstance(domain, str) and domain.isascii() and domain.isdecimal()
            and 1 <= int(domain) <= 232
            and isinstance(partition, str) and 0 < len(partition) <= 128):
        raise ProvenanceError("SIM_ISOLATION_INVALID")
    root = Path(source_root).resolve(strict=True)
    if _git(root, "rev-parse", "--verify", "HEAD") != source_sha:
        raise ProvenanceError("SOURCE_SHA_MISMATCH")
    if _git(root, "status", "--porcelain", "--untracked-files=no"):
        raise ProvenanceError("SOURCE_DIRTY")
    now = time.monotonic_ns() if now_ns is None else now_ns
    if type(now) is not int or now <= 0:
        raise ProvenanceError("MONOTONIC_CLOCK_INVALID")
    return {"run_id": run_id, "session_id": session_id,
            "source_sha": source_sha, "ros_domain_id": domain,
            "gz_partition": partition, "captured_monotonic_ns": now}



def supervisor_observation_ns(last_state_received_mono: float,
                              *, now_mono: float | None = None) -> int:
    """Tie a ready Supervisor receipt to the actual ROS-message receive time.

    The caller must pass a value recorded inside its rclpy message callback.
    The accepted age is at most 0.5s, as required by the R01 binding gate.
    This does not authenticate the publisher or grant any Goal authority.
    """
    now = time.monotonic() if now_mono is None else now_mono
    if (type(last_state_received_mono) not in (int, float)
            or type(now) not in (int, float)
            or not math.isfinite(last_state_received_mono)
            or not math.isfinite(now)
            or last_state_received_mono <= 0 or now <= 0
            or last_state_received_mono > now):
        raise ProvenanceError("SUPERVISOR_RECEIPT_TIME_INVALID")
    if now - last_state_received_mono > 0.5:
        raise ProvenanceError("SUPERVISOR_RECEIPT_STALE")
    captured_ns = int(last_state_received_mono * 1_000_000_000)
    if captured_ns <= 0:
        raise ProvenanceError("SUPERVISOR_RECEIPT_TIME_INVALID")
    return captured_ns


def stamp_live_record(record: dict, *, source_root: Path,
                      environ: Mapping[str, str] | None = None,
                      now_ns: int | None = None) -> dict:
    """Opt-in capture-time injection; never retag existing provenance."""
    env = os.environ if environ is None else environ
    if not isinstance(record, dict) or not isinstance(env, Mapping):
        raise ProvenanceError("RECORD_OR_ENV_INVALID")
    if not any(env.get(name) for name in _KEYS):
        if env.get("AXIA_T08_R01_READ_ONLY_BINDING") == "YES":
            raise ProvenanceError("CAPTURE_CONTEXT_MISSING")
        return record
    if "provenance" in record:
        raise ProvenanceError("PROVENANCE_ALREADY_PRESENT")
    receipt = live_provenance(source_root=source_root, environ=env, now_ns=now_ns)
    return {**record, "provenance": receipt}
