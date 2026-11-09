#!/usr/bin/env python3
"""Actual ROS 2 Jazzy + Gazebo Harmonic P1/D3 headless smoke.

Only runs in an isolated virtual Waffle simulation. No Start, Goal, Fault,
Reset, Rearm, /cmd_vel or certified E-Stop is attempted. Failure is nonzero and
every gate is written to results/d03-v3-ros-gazebo/summary.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "ros2_ws/src"
LAUNCH = SOURCE / "axia_safety_bringup/launch/axia_tb3_p1.launch.py"
MODEL = SOURCE / "axia_d3_demo/models/pedestrian_proxy.sdf"
SAFE_WORLD = re.compile(r"^/world/([A-Za-z][A-Za-z0-9_]{0,39})/set_pose$")
REQUIRED_TOPICS = {
    "/clock": "rosgraph_msgs/msg/Clock",
    "/scan": "sensor_msgs/msg/LaserScan",
    "/odom": "nav_msgs/msg/Odometry",
    "/axia/safety/state": "std_msgs/msg/String",
    "/axia/fault/status": "std_msgs/msg/String",
}


def subprocess_run(args, *, env, timeout=15):
    return subprocess.run(args, env=env, text=True, capture_output=True,
                          timeout=timeout, check=False)


def wait_topic(name, expected_type, env, seconds):
    until = time.monotonic() + seconds
    attempts = 0
    error = ""
    while time.monotonic() < until:
        attempts += 1
        remain = until - time.monotonic()
        # --once proves an actual ROS message was transported through DDS;
        # sensor streams must match best_effort Gazebo publisher QoS.
        args = ["ros2", "topic", "echo", name, "--once", "--field", "header"]
        if name in ("/clock", "/axia/safety/state", "/axia/fault/status"):
            args = ["ros2", "topic", "echo", name, "--once"]
        if name == "/scan":
            args += ["--qos-reliability", "best_effort"]
        try:
            r = subprocess_run(args, env=env, timeout=max(1, min(12, remain)))
            if r.returncode == 0 and r.stdout.strip():
                typ = subprocess_run(["ros2", "topic", "type", name], env=env, timeout=8)
                if typ.returncode == 0 and typ.stdout.strip() == expected_type:
                    return {"status": "MESSAGE_OBSERVED", "type": typ.stdout.strip(),
                            "attempts": attempts, "excerpt": r.stdout[:1600],
                            "uncertified": ("stop_is_certified_estop" in r.stdout
                                            and "stop_is_certified_estop\": false" in r.stdout)}
                error = "UNEXPECTED_TOPIC_TYPE:" + typ.stdout.strip() + typ.stderr[-150:]
            else:
                error = (r.stderr or r.stdout)[-350:] or "NO_TOPIC_DATA"
        except subprocess.TimeoutExpired:
            error = "READ_TIMEOUT"
        time.sleep(.5)
    return {"status": "BLOCKED", "attempts": attempts, "error": error}


def wait_world(env, seconds):
    deadline = time.monotonic() + seconds
    err = "NO_GAZEBO_SERVICES"
    while time.monotonic() < deadline:
        try:
            r = subprocess_run(["gz", "service", "-l"], env=env, timeout=10)
            if r.returncode == 0:
                services = set(r.stdout.splitlines())
                worlds = sorted({m.group(1) for service in services
                                 if (m := SAFE_WORLD.fullmatch(service))})
                worlds = [w for w in worlds if "/world/" + w + "/create" in services]
                if len(worlds) == 1:
                    return worlds[0]
                err = "UNEXPECTED_WORLD_MATCHES:" + repr(worlds)
            else:
                err = "GZ_SERVICE_DISCOVERY:" + (r.stderr or "")[-200:]
        except subprocess.TimeoutExpired:
            err = "GZ_SERVICE_TIMEOUT"
        time.sleep(1)
    raise RuntimeError(err)


def preview_proxy(world, env, output):
    if not MODEL.is_file():
        raise RuntimeError("P1_D3_SDF_MODEL_NOT_FOUND")
    spawn = subprocess_run(["ros2", "run", "ros_gz_sim", "create",
                           "-world", world, "-file", str(MODEL),
                           "-name", "d3_pedestrian_proxy", "-x", "0",
                           "-y", "0", "-z", "0"], env=env, timeout=55)
    (output / "spawn.log").write_text(spawn.stdout + "\n" + spawn.stderr)
    if spawn.returncode:
        raise RuntimeError("D3_GAZEBO_SPAWN_FAILED:" + (spawn.stderr or spawn.stdout)[-400:])
    poses = []
    for x in (0.3, 0.6, 0.9):
        req = ('name: "d3_pedestrian_proxy" position: { x: ' + str(x) +
               ' y: 0 z: 0 } orientation: { w: 1 }')
        command = ["gz", "service", "-s", "/world/" + world + "/set_pose",
                   "--reqtype", "gz.msgs.Pose", "--reptype", "gz.msgs.Boolean",
                   "--timeout", "5000", "--req", req]
        result = subprocess_run(command, env=env, timeout=12)
        (output / ("set_pose_" + str(x) + ".log")).write_text(
            result.stdout + "\n" + result.stderr)
        ok = result.returncode == 0 and re.search(
            r"(?mi)\bdata\s*:\s*true\b|^\s*true\s*$", result.stdout) is not None
        poses.append({"x": x, "gazebo_service_true": ok, "returncode": result.returncode})
        if not ok:
            raise RuntimeError("D3_GAZEBO_SET_POSE_REJECTED:" +
                               (result.stdout + result.stderr)[-400:])
    return {"status": "GAZEBO_CREATE_AND_SET_POSE_3X_ACCEPTED", "world": world,
            "poses": poses, "gui_render_verified": False, "moving_human_verified": False}


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shutdown(process):
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGINT)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=25)
    except subprocess.TimeoutExpired:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)
    return process.returncode


def execute(output, timeout_sec):
    assert os.getenv("AXIA_D03_V3_CI_SIM_ONLY") == "YES", "CI isolated sim approval required"
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({
        "ROS_DOMAIN_ID": "178", "ROS_AUTOMATIC_DISCOVERY_RANGE": "LOCALHOST",
        "GZ_PARTITION": "axia_d3_ci_" + env.get("GITHUB_RUN_ID", "local"),
        "TURTLEBOT3_MODEL": "waffle",
        "LIBGL_ALWAYS_SOFTWARE": "1", "AXIA_P0_SIM_ONLY": "1",
    })
    result = {
        "scope": "REAL_ROS2_GAZEBO_P1_D3_HEADLESS_NO_GOAL_NO_FAULT",
        "source_commit": env.get("GITHUB_SHA", "LOCAL_UNVERIFIED"),
        "target_model": "TurtleBot3 Waffle", "ros": "Jazzy", "gazebo": "Harmonic",
        "simulation_only": True, "nav2_goal_sent": False,
        "fault_injection_sent": False, "software_stop_verified": False,
        "certified_estop": False, "gui_verified": False,
        "result": "BLOCKED", "checks": {},
    }
    command = ["ros2", "launch", str(LAUNCH), "headless:=True",
               "use_rviz:=False", "autostart:=false",
               "use_composition:=False", "use_respawn:=False",
               "allow_fault_injection:=true"]
    result["launch_command"] = command
    p = None
    log = output / "p1_gazebo_launch.log"
    deadline = time.monotonic() + timeout_sec
    with log.open("w", encoding="utf-8") as stream:
        p = subprocess.Popen(command, cwd=ROOT, env=env, text=True,
                             stdout=stream, stderr=subprocess.STDOUT,
                             start_new_session=True)
        try:
            for topic, typ in REQUIRED_TOPICS.items():
                if p.poll() is not None:
                    raise RuntimeError("P1_LAUNCH_EARLY_EXIT:" + str(p.returncode))
                remaining = deadline - time.monotonic()
                if remaining < 10:
                    raise RuntimeError("P1_STARTUP_DEADLINE")
                entry = wait_topic(topic, typ, env, min(75, remaining))
                result["checks"][topic] = entry
                if entry["status"] != "MESSAGE_OBSERVED":
                    raise RuntimeError("P1_TOPIC_MISSING:" + topic + ":" + entry.get("error", ""))
            if not result["checks"]["/axia/safety/state"]["uncertified"]:
                raise RuntimeError("P1_STATE_CERTIFICATION_FLAG_MISSING")
            if deadline - time.monotonic() < 15:
                raise RuntimeError("GAZEBO_DEADLINE_BEFORE_MODEL")
            world = wait_world(env, min(65, deadline - time.monotonic()))
            result["checks"]["world"] = world
            result["checks"]["proxy"] = preview_proxy(world, env, output)
            result["result"] = "REAL_ROS_GAZEBO_HEADLESS_SMOKE_PASS"
        except (OSError, RuntimeError, subprocess.TimeoutExpired, AssertionError) as e:
            result["error"] = type(e).__name__ + ":" + str(e)[:650]
        finally:
            result["launch_exit_code"] = shutdown(p)
            result["shutdown_clean_requested"] = True
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    files = sorted(p for p in output.iterdir() if p.is_file())
    (output / "SHA256SUMS").write_text("".join(
        f"{sha256_file(f)}  {f.name}\n" for f in files
    ))
    print(json.dumps({k: v for k, v in result.items() if k not in ("checks", "launch_command")},
                     ensure_ascii=False), flush=True)
    return 0 if result["result"] == "REAL_ROS_GAZEBO_HEADLESS_SMOKE_PASS" else 2


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default="results/d03-v3-ros-gazebo")
    p.add_argument("--timeout", type=int, default=300)
    args = p.parse_args()
    return execute(Path(args.out), args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
