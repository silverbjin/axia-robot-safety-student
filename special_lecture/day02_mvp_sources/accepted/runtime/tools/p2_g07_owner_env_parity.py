#!/usr/bin/env python3
"""AXIA P2 G07 Owner/CI exact core parity, driven by private Owner profile lock.

Read-only. Verifies 25 exact Debian packages, five official Nav2/Map/World
SHA256 digests, Ubuntu/Jazzy/Gazebo, and runtime ROS isolation. It cannot
reproduce WSL2 scheduler, WSLg GPU or moving-Goal performance in a Linux CI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "configs" / "p2_g07_owner_ci_runtime_lock_20261111.json"
NAME_RE = re.compile(r"^[a-z0-9+.-]+$")
VERSION_RE = re.compile(r"^[a-zA-Z0-9.+:~_+-]{1,120}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
OFFICIAL_RE = re.compile(
    r"^(?:nav2_bringup|nav2_minimal_tb3_sim)/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+$"
)
MINIMUM_NAMES = frozenset({
    "ros-jazzy-nav2-bringup", "ros-jazzy-navigation2",
    "ros-jazzy-nav2-minimal-tb3-sim", "ros-jazzy-nav2-collision-monitor",
    "ros-jazzy-ros-gz", "ros-jazzy-ros-gz-bridge", "ros-jazzy-rclpy",
    "gz-sim8-cli", "libgz-sim8", "libsdformat14",
})
REQUIRED_OFFICIAL = frozenset({
    "nav2_bringup/launch/tb3_simulation_launch.py",
    "nav2_bringup/params/nav2_params.yaml",
    "nav2_bringup/maps/tb3_sandbox.pgm",
    "nav2_bringup/maps/tb3_sandbox.yaml",
    "nav2_minimal_tb3_sim/worlds/tb3_sandbox.sdf.xacro",
})


def validate_lock(lock: dict) -> dict:
    if not isinstance(lock, dict) or lock.get("schema") != "axia_p2_g07_owner_ci_runtime_lock_v1":
        raise ValueError("OWNER_LOCK_SCHEMA_INVALID")
    if (lock.get("owner_profile_sha256")
            != "2e3cede57587e57b262b2f73b28dc1fe1346fcb682faf271e294116b1bdbf3b6"
            or lock.get("owner_profile_package_count") != 639):
        raise ValueError("UNREVIEWED_OWNER_PROFILE_SOURCE")
    packages = lock.get("packages")
    files = lock.get("official_file_sha256")
    if not isinstance(packages, dict) or len(packages) != 25 or not MINIMUM_NAMES <= packages.keys():
        raise ValueError("OWNER_LOCK_PACKAGE_SCOPE_INVALID")
    if not isinstance(files, dict) or files.keys() != REQUIRED_OFFICIAL:
        raise ValueError("OWNER_LOCK_OFFICIAL_SCOPE_INVALID")
    if any(not isinstance(key, str) or not NAME_RE.fullmatch(key)
           or not isinstance(version, str) or not VERSION_RE.fullmatch(version)
           for key, version in packages.items()):
        raise ValueError("OWNER_LOCK_PACKAGE_VALUE_INVALID")
    if any(not isinstance(key, str) or not OFFICIAL_RE.fullmatch(key)
           or ".." in key.split("/") or not isinstance(digest, str)
           or not SHA_RE.fullmatch(digest)
           for key, digest in files.items()):
        raise ValueError("OWNER_LOCK_OFFICIAL_SHA_INVALID")
    if (lock.get("os", {}).get("id") != "ubuntu"
            or lock["os"].get("version_id") != "24.04"
            or lock["os"].get("architecture") != "x86_64"
            or lock["os"].get("python_major_minor") != "3.12"
            or lock["os"].get("ros_distro") != "jazzy"
            or lock["os"].get("gazebo_sim_version") != "8.15.0"):
        raise ValueError("OWNER_LOCK_RUNTIME_PROFILE_INVALID")
    return lock


def read_lock(path: Path = LOCK_PATH) -> dict:
    if not path.is_file() or path.stat().st_size > 20_000:
        raise ValueError("OWNER_LOCK_ABSENT_OR_OVERSIZED")
    return validate_lock(json.loads(path.read_text(encoding="utf-8")))


def _dpkg(name: str) -> str:
    try:
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${Version}", name],
            capture_output=True, text=True, timeout=6, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return "UNAVAILABLE"
    return result.stdout.strip() if result.returncode == 0 else "NOT_INSTALLED"


def _os_info() -> dict:
    document = Path("/etc/os-release").read_text(encoding="utf-8")
    os_id = os_version = ""
    for row in document.splitlines():
        if row.startswith("ID="):
            os_id = row.split("=", 1)[1].strip().strip('"')
        elif row.startswith("VERSION_ID="):
            os_version = row.split("=", 1)[1].strip().strip('"')
    return {
        "id": os_id, "version_id": os_version,
        "architecture": platform.machine(),
        "python_major_minor": f"{sys.version_info.major}.{sys.version_info.minor}",
    }


def _gazebo_version() -> str:
    try:
        result = subprocess.run(
            ["gz", "sim", "--version"], capture_output=True, text=True,
            timeout=12, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "UNAVAILABLE"
    if result.returncode != 0:
        return "UNAVAILABLE"
    match = re.search(r"(?<![0-9])8\.\d+\.\d+(?![0-9])", result.stdout)
    return match.group(0) if match else "UNAVAILABLE"


def _installed_hashes(lock: dict) -> dict:
    base = Path("/opt/ros/jazzy/share")
    result = {}
    for file_key in lock["official_file_sha256"]:
        pkg, rel = file_key.split("/", 1)
        path = base / pkg / rel
        try:
            result[file_key] = hashlib.sha256(path.read_bytes()).hexdigest() if (
                path.is_file() and path.stat().st_size <= 8_000_000
            ) else "MISSING"
        except OSError:
            result[file_key] = "UNAVAILABLE"
    return result


def assess_snapshot(lock: dict, *, installed_debs: dict, installed_hashes: dict,
                    env: dict, mode: str, os_info: dict, wsl_detected: bool,
                    kernel_release: str, gazebo_version: str = "8.15.0") -> dict:
    lock = validate_lock(lock)
    if mode not in ("owner", "ci"):
        raise ValueError("INVALID_PARITY_MODE")
    mismatch = {}
    package_checks = {}
    for name, expected in lock["packages"].items():
        actual = installed_debs.get(name, "NOT_INSTALLED")
        package_checks[name] = {"expected": expected, "actual": actual, "matches": actual == expected}
        if actual != expected:
            mismatch["packages." + name] = {"expected": expected, "actual": actual}
    official_checks = {}
    for name, expected in lock["official_file_sha256"].items():
        actual = installed_hashes.get(name, "MISSING")
        official_checks[name] = {"expected": expected, "actual": actual, "matches": actual == expected}
        if actual != expected:
            mismatch["official_files." + name] = {"expected": expected, "actual": actual}
    for name in ("id", "version_id", "architecture", "python_major_minor"):
        expected = lock["os"][name]
        if os_info.get(name) != expected:
            mismatch["os." + name] = {"expected": expected, "actual": os_info.get(name)}
    if gazebo_version != lock["os"]["gazebo_sim_version"]:
        mismatch["gazebo_sim_version"] = {"expected": lock["os"]["gazebo_sim_version"],
                                           "actual": gazebo_version}
    if env.get("ROS_DISTRO") != "jazzy":
        mismatch["ROS_DISTRO"] = "EXPECTED_JAZZY"
    if env.get("ROS_AUTOMATIC_DISCOVERY_RANGE") != "LOCALHOST":
        mismatch["ROS_AUTOMATIC_DISCOVERY_RANGE"] = "EXPECTED_ISOLATED_LOCALHOST"
    if env.get("RMW_IMPLEMENTATION", "") not in ("", "rmw_fastrtps_cpp"):
        mismatch["RMW_IMPLEMENTATION"] = "EXPECTED_DEFAULT_FASTRTPS"
    domain = env.get("ROS_DOMAIN_ID", "")
    if not isinstance(domain, str) or not domain.isascii() or not domain.isdecimal() or not 0 <= int(domain) <= 232:
        mismatch["ROS_DOMAIN_ID"] = "INVALID_ISOLATED_DOMAIN"
    if not env.get("GZ_PARTITION", "").startswith("axia_p2_"):
        mismatch["GZ_PARTITION"] = "NOT_ISOLATED_P2_SESSION"
    if env.get("AXIA_P0_SIM_ONLY") != "1":
        mismatch["AXIA_P0_SIM_ONLY"] = "SIMULATION_ONLY_MARKER_REQUIRED"
    if mode == "owner" and not wsl_detected:
        mismatch["owner_kernel"] = "WSL2_REQUIRED"
    if mode == "ci" and wsl_detected:
        mismatch["ci_kernel"] = "CI_NOT_WSL2_REQUIRED"
    return {
        "schema": "axia_p2_g07_env_userspace_parity_v2",
        "mode": mode,
        "status": "CORE_PARITY_PASS" if not mismatch else "PARITY_BLOCKED",
        "checked_packages": len(package_checks),
        "checked_official_files": len(official_checks),
        "checks": package_checks,
        "official_files": official_checks,
        "gazebo_sim_version": gazebo_version,
        "wsl_detected": bool(wsl_detected),
        "kernel_release": kernel_release[:120],
        "wsl_kernel_equal_ci": False,
        "gazebo_scheduler_equal_ci": False,
        "rmw_effective_class": "rmw_fastrtps_cpp",
        "discovery_range": env.get("ROS_AUTOMATIC_DISCOVERY_RANGE"),
        "domain_id_valid": "ROS_DOMAIN_ID" not in mismatch,
        "gz_partition_present": bool(env.get("GZ_PARTITION")),
        "mismatch": mismatch,
        "goal_sent": False, "fault_injected": False,
        "certified_estop": False, "gate_accepted": False,
    }


def collect(mode: str, lock_path: Path = LOCK_PATH) -> dict:
    lock = read_lock(lock_path)
    kernel = platform.release()
    wsl = "microsoft" in kernel.lower() or "wsl" in kernel.lower()
    return assess_snapshot(
        lock, mode=mode,
        installed_debs={name: _dpkg(name) for name in lock["packages"]},
        installed_hashes=_installed_hashes(lock),
        env=os.environ, os_info=_os_info(),
        gazebo_version=_gazebo_version(),
        wsl_detected=wsl, kernel_release=kernel,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("owner", "ci"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = collect(args.mode)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("AXIA_G07_ENV_PARITY_BLOCKED " + type(exc).__name__ + ":" + str(exc), flush=True)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    if report["status"] != "CORE_PARITY_PASS":
        print("AXIA_G07_ENV_PARITY_BLOCKED mismatches=" +
              ",".join(sorted(report["mismatch"])), flush=True)
        return 2
    print("AXIA_G07_ENV_CORE_PARITY_PASS mode=" + args.mode +
          " packages=25 files=5 WSL2_KERNEL_SCHEDULER_NOT_EQUIVALENT", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
