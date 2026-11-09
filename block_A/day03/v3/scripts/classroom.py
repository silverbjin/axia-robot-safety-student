#!/usr/bin/env python3
"""AXIA D03 v3 student classroom launcher.

Retains existing P1 FSM / Action ownership. Only a pedagogical Gazebo proxy and
the existing simulation-only Fault Injector are actuated, after separate approvals.
Never triggers a Nav2 Goal, Start, Reset, Rearm, or cmd_vel.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import time

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[4]
LAB = ROOT / "block_A/day03"
SRC = ROOT / "ros2_ws/src"
WORK = Path.home() / "axia_d3_v3_classroom"
SESSION = WORK / "session.env"
ROUTE = WORK / "route.env"
P1_LAUNCH = SRC / "axia_safety_bringup/launch/axia_tb3_p1.launch.py"
ROS = Path("/opt/ros/jazzy/setup.bash")
INSTALL = ROOT / "install/setup.bash"
PACKAGES = ("axia_safety_supervisor", "axia_fault_injector",
            "axia_scenario_verifier", "axia_d3_demo")
MARKER = "AXIA_D3_V3_SIM_ONLY"
RUN_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,39}$")


class Blocked(RuntimeError):
    pass


def say(*args):
    print("[D03_V3]", *args, flush=True)


def refuse(message):
    raise Blocked(message)


def safe_file(p: Path) -> bool:
    return p.is_file() and not p.is_symlink()


def ensure_work():
    if WORK.is_symlink():
        refuse("classroom directory is symlinked")
    WORK.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not WORK.is_dir():
        refuse("classroom path is not a directory")
    for sub in ("evidence", "logs"):
        folder = WORK / sub
        if folder.is_symlink():
            refuse("classroom subdirectory is symlinked")
        folder.mkdir(mode=0o700, exist_ok=True)
        folder.chmod(0o700)


def make_name() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + secrets.token_hex(4)


def new_evidence_name() -> str:
    return str(WORK / "evidence" / ("d03_v3_" + make_name() + ".jsonl"))


def encode_env(mapping: dict[str, str]) -> str:
    return "".join("export " + name + "=" + shlex.quote(str(value)) + "\n"
                   for name, value in mapping.items())


def write_exclusive(p: Path, content: str):
    if p.is_symlink():
        refuse("refusing symlink output: " + p.name)
    try:
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        refuse("refusing overwrite: " + str(p))
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(content)


def parse_env(p: Path) -> dict[str, str]:
    if not safe_file(p):
        refuse("missing or unsafe env file: " + str(p))
    result = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"export ([A-Z][A-Z0-9_]*)=(.*)", line)
        if not match:
            refuse("invalid env file format")
        tokens = shlex.split(match.group(2), posix=True)
        if len(tokens) != 1:
            refuse("invalid env value")
        result[match.group(1)] = tokens[0]
    return result


def classroom_env() -> dict[str, str]:
    if WORK.is_symlink():
        refuse("classroom directory is symlinked")
    s = parse_env(SESSION)
    try:
        d = int(s["ROS_DOMAIN_ID"])
    except (KeyError, ValueError):
        refuse("invalid ROS_DOMAIN_ID")
    if not 0 <= d <= 232:
        refuse("ROS_DOMAIN_ID outside 0..232")
    if s.get("GZ_PARTITION", "").startswith("axia_d3_") is False:
        refuse("unexpected Gazebo partition")
    if s.get(MARKER) != "1" or s.get("AXIA_P0_SIM_ONLY") != "1":
        refuse("simulation-only marker absent")
    evidence = Path(s.get("D3_EVIDENCE", ""))
    if evidence.parent != WORK / "evidence" or evidence.suffix != ".jsonl" or evidence.is_symlink():
        refuse("unsafe evidence path")
    result = os.environ.copy()
    result.update(s)
    return result


def create_session():
    ensure_work()
    if SESSION.is_symlink():
        refuse("session symlink prohibited")
    if SESSION.exists():
        if not safe_file(SESSION):
            refuse("existing session is not a regular file")
        classroom_env()
        say("[SESSION_REUSED]", SESSION)
        return
    raw = os.environ.get("AXIA_D3_V3_DOMAIN_ID", "174")
    if not raw.isdecimal() or not 0 <= int(raw) <= 232:
        refuse("AXIA_D3_V3_DOMAIN_ID must be 0..232")
    s = {
        "ROS_DOMAIN_ID": raw,
        "ROS_AUTOMATIC_DISCOVERY_RANGE": "LOCALHOST",
        "GZ_PARTITION": "axia_d3_student_" + str(os.getuid()) + "_" + make_name(),
        "D3_EVIDENCE": new_evidence_name(),
        MARKER: "1",
        "AXIA_P0_SIM_ONLY": "1",
        "TURTLEBOT3_MODEL": "waffle",
    }
    write_exclusive(SESSION, encode_env(s))
    say("[SESSION_CREATED]", SESSION)
    say("[NEXT] source " + shlex.quote(str(SESSION)) + " in every ROS terminal")


def allocate_evidence():
    s = classroom_env()
    path = new_evidence_name()
    if Path(path).exists() or Path(path).is_symlink():
        refuse("fresh evidence already exists")
    mapping = {k: v for k, v in s.items() if k in (
        "ROS_DOMAIN_ID", "ROS_AUTOMATIC_DISCOVERY_RANGE", "GZ_PARTITION",
        "D3_EVIDENCE", MARKER, "AXIA_P0_SIM_ONLY", "TURTLEBOT3_MODEL")}
    mapping["D3_EVIDENCE"] = path
    temp = WORK / (".session_" + secrets.token_hex(8))
    write_exclusive(temp, encode_env(mapping))
    os.replace(temp, SESSION)
    say("[NEW_EVIDENCE]", path)
    say("[NOTE] The old P1 fault/Stop latch was NOT cleared")


def route_values(args: list[str]):
    if len(args) != 5:
        refuse("route requires WORLD START_X START_Y END_X END_Y")
    sys.path.insert(0, str(SRC / "axia_d3_demo"))
    from axia_d3_demo.scenario import validate_path
    try:
        return validate_path(args[0], (args[1], args[2]), (args[3], args[4]))
    except (ValueError, TypeError) as exc:
        refuse("unsafe route: " + str(exc))


def set_route(args: list[str]):
    classroom_env()
    if ROUTE.is_symlink():
        refuse("route symlink prohibited")
    world, (sx, sy), (ex, ey) = route_values(args)
    mapping = {"D3_WORLD": world, "D3_START_X": str(sx), "D3_START_Y": str(sy),
               "D3_END_X": str(ex), "D3_END_Y": str(ey)}
    # Preserve previous route rather than overwrite if a failed demo exists.
    if ROUTE.exists():
        old = parse_env(ROUTE)
        if old == mapping:
            say("[ROUTE_REUSED]", ROUTE)
            return
        refuse("existing route differs; preserve it and review Gazebo coordinates")
    write_exclusive(ROUTE, encode_env(mapping))
    say("[ROUTE_SAVED]", ROUTE)
    say("[CHECK] Confirm world, path, camera and clearance manually in Gazebo")


def with_route(env: dict[str, str]) -> dict[str, str]:
    route = parse_env(ROUTE)
    required = ("D3_WORLD", "D3_START_X", "D3_START_Y", "D3_END_X", "D3_END_Y")
    if not all(route.get(name) for name in required):
        refuse("route incomplete")
    route_values([route[k] for k in required])
    return {**env, **route}


def ros_call(args: list[str], *, env=None, cwd=None, capture=False, timeout=None):
    if not ROS.is_file():
        refuse("ROS 2 Jazzy is missing")
    # Fixed shell program, no user-provided shell code. Arguments are positional.
    cmd = ["bash", "-c",
           'source "$1"; if [[ -f "$2" ]]; then source "$2"; fi; shift 2; exec "$@"',
           "axia-d3", str(ROS), str(INSTALL), *args]
    return subprocess.run(cmd, cwd=cwd, env=env, text=True,
                          capture_output=capture, timeout=timeout, check=False)


def must_run(proc, label):
    if proc.returncode:
        refuse(label + " failed (rc=" + str(proc.returncode) + "): " +
               (proc.stderr or proc.stdout or "")[-500:])


def preflight():
    if sys.platform != "linux":
        refuse("Linux Ubuntu 24.04 required")
    if Path("/etc/os-release").is_file():
        text = Path("/etc/os-release").read_text()
        if "ID=ubuntu" not in text or 'VERSION_ID="24.04"' not in text:
            refuse("Ubuntu 24.04 required")
    if not P1_LAUNCH.is_file():
        refuse("P1 student launch missing")
    for name in PACKAGES:
        if not (SRC / name / "package.xml").is_file():
            refuse("missing P1 source package " + name)
    if not INSTALL.is_file():
        refuse("run prepare: install/setup.bash missing")
    if not shutil.which("gz") or not shutil.which("colcon"):
        refuse("Gazebo Harmonic gz CLI and colcon required")
    for name in ("nav2_bringup", "nav2_minimal_tb3_sim", "ros_gz_sim", *PACKAGES):
        p = ros_call(["ros2", "pkg", "prefix", name], capture=True, timeout=12)
        must_run(p, "ROS package " + name)
    say("[READY] P1_D03_V3_SOURCE_BUILD_PREFLIGHT (NO GOAL, GUI OR FAULT RUN)")


def prepare():
    if not P1_LAUNCH.is_file():
        refuse("P1 student runtime source missing")
    if not shutil.which("colcon"):
        refuse("colcon is missing")
    p = ros_call(["colcon", "build", "--base-paths", "ros2_ws/src",
                  "--symlink-install", "--packages-select", *PACKAGES],
                 cwd=ROOT)
    must_run(p, "colcon build")
    preflight()


def approve(word: str, question: str):
    try:
        with open("/dev/tty", "r", encoding="utf-8") as inp:
            print("[APPROVAL] " + question + " Type " + word + ": ", end="", flush=True)
            decision = inp.readline().strip()
    except OSError:
        refuse("interactive terminal required for " + word)
    if decision != word:
        refuse("operator declined " + word)


def gz_world(env):
    route = with_route(env)
    p = subprocess.run(["gz", "service", "-l"], env=route, capture_output=True,
                       text=True, timeout=10, check=False)
    must_run(p, "Gazebo service discovery")
    world = route["D3_WORLD"]
    services = set(p.stdout.splitlines())
    for name in ("/world/" + world + "/set_pose", "/world/" + world + "/create"):
        if name not in services:
            refuse("Gazebo world service missing: " + name)
    return route


def scene_args(env):
    return ["--world", env["D3_WORLD"],
            "--start-x", env["D3_START_X"], "--start-y", env["D3_START_Y"],
            "--end-x", env["D3_END_X"], "--end-y", env["D3_END_Y"]]


def student_green():
    # Both public TODOs must be completed before ROS fault-related lab.
    p = subprocess.run(["bash", str(LAB / "scripts/run_lab.sh"), "green"],
                       cwd=ROOT, text=True, check=False)
    must_run(p, "student D03 TODO tests not GREEN")


def launch(env):
    preflight()
    if not (env.get("DISPLAY") or env.get("WAYLAND_DISPLAY")):
        refuse("Gazebo WSLg GUI display not configured")
    approve("YES-D3-SIM", "Run isolated Waffle simulator (no Goal automatically)?")
    env.pop("QT_QPA_PLATFORM", None) if env.get("QT_QPA_PLATFORM") == "offscreen" else None
    cmd = ["ros2", "launch", str(P1_LAUNCH), "headless:=False",
           "use_rviz:=False", "autostart:=false", "use_composition:=False",
           "allow_fault_injection:=true"]
    must_run(ros_call(cmd, env=env, cwd=ROOT), "P1 Gazebo launch")


def preview(env):
    preflight()
    env = gz_world(env)
    approve("YES-D3-PREVIEW", "Show moving human-shaped pedagogical proxy only?")
    cmd = ["ros2", "run", "axia_d3_demo", "d3_scene", "--mode", "preview",
           *scene_args(env), "--ack-sim-only"]
    must_run(ros_call(cmd, env=env, cwd=ROOT), "Gazebo moving proxy preview")
    say("[NEXT] Remove this proxy before live run")


def remove_proxy(env):
    preflight()
    env = with_route(env)
    approve("YES-D3-REMOVE", "Remove ONLY d3_pedestrian_proxy?")
    cmd = ["ros2", "run", "ros_gz_sim", "remove", "--ros-args",
           "-p", "world:=" + env["D3_WORLD"], "-p", "entity_name:=d3_pedestrian_proxy"]
    must_run(ros_call(cmd, env=env, cwd=ROOT), "proxy remove")


def bridge(env):
    preflight()
    student_green()
    cmd = ["python3", str(LAB / "ros_diagnostics_bridge.py")]
    env["PYTHONPATH"] = str(LAB) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    must_run(ros_call(cmd, env=env, cwd=ROOT), "student Diagnostics bridge")


def live(env):
    preflight()
    env = gz_world(env)
    student_green()
    evidence = Path(env["D3_EVIDENCE"])
    if evidence.exists() or evidence.is_symlink():
        refuse("evidence already exists; run new-evidence")
    for topic, expected in (("/axia/safety/state", "std_msgs/msg/String"),
                            ("/odom", "nav_msgs/msg/Odometry")):
        r = ros_call(["ros2", "topic", "type", topic], env=env, capture=True, timeout=15)
        must_run(r, "topic " + topic)
        if r.stdout.strip() != expected:
            refuse("wrong topic type: " + topic)
    approve("YES-D3-SIM", "P1 owner-approved Goal already running in isolated sim?")
    approve("YES-D3-FAULT", "Authorize ONE scan_drop in this isolated simulator?")
    env["PYTHONPATH"] = str(LAB) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    logbase = WORK / "logs" / evidence.stem
    observers = []
    handles = []
    try:
        for suffix, args in (
            (".bridge.log", ["python3", str(LAB / "ros_diagnostics_bridge.py")]),
            (".observer.log", ["ros2", "run", "axia_d3_demo", "d3_observer",
                               "--evidence", str(evidence)])):
            handle = open(str(logbase) + suffix, "x", encoding="utf-8")
            handles.append(handle)
            cmd = ["bash", "-c",
                   'source "$1"; if [[ -f "$2" ]]; then source "$2"; fi; shift 2; exec "$@"',
                   "axia-d3", str(ROS), str(INSTALL), *args]
            observers.append(subprocess.Popen(cmd, stdout=handle, stderr=subprocess.STDOUT,
                                              env=env, cwd=ROOT, start_new_session=True))
        time.sleep(2)
        if any(p.poll() is not None for p in observers):
            refuse("bridge or observer exited early: inspect logs")
        cmd = ["ros2", "run", "axia_d3_demo", "d3_scene", "--mode", "live",
               *scene_args(env), "--evidence", str(evidence),
               "--ready-timeout-s", "60", "--ack-sim-only", "--ack-fault"]
        must_run(ros_call(cmd, env=env, cwd=ROOT), "D3 live scene")
    finally:
        for p in observers:
            if p.poll() is None:
                try:
                    os.killpg(p.pid, signal.SIGINT)
                    p.wait(timeout=4)
                except (OSError, subprocess.TimeoutExpired):
                    if p.poll() is None:
                        p.terminate()
            if p.poll() is None:
                p.kill()
        for h in handles:
            h.close()
        say("[EVIDENCE]", evidence)
        say("[LOGS]", str(logbase) + ".bridge.log", str(logbase) + ".observer.log")
        say("[SAFETY] P1 remains fail-closed; NO automatic Reset/Rearm/Goal")


def verify(env):
    cmd = ["-m", "axia_d3_demo.cli", "verify", "--evidence", env["D3_EVIDENCE"]]
    env["PYTHONPATH"] = str(SRC / "axia_d3_demo")
    p = subprocess.run([sys.executable, *cmd], env=env, text=True, check=False)
    must_run(p, "offline D3 evidence verification")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="D03 v3 P1-shared student lab. Never run on real robot.")
    ap.add_argument("command", nargs="?", default="help",
                    choices=("help", "session", "new-evidence", "status", "route",
                             "prepare", "preflight", "launch", "preview",
                             "remove-proxy", "bridge", "live", "verify"))
    ap.add_argument("args", nargs="*")
    parsed = ap.parse_args(argv)
    cmd = parsed.command
    if cmd == "help":
        ap.print_help()
        print("route WORLD SX SY EX EY | session | prepare | preflight | launch")
        print("preview | remove-proxy | bridge | live | new-evidence | verify")
        print("Approval codes: YES-D3-SIM, YES-D3-PREVIEW, YES-D3-REMOVE, YES-D3-FAULT")
        return 0
    if cmd == "session":
        create_session()
        return 0
    if cmd == "new-evidence":
        allocate_evidence()
        return 0
    if cmd == "route":
        set_route(parsed.args)
        return 0
    env = classroom_env()
    if cmd == "status":
        say("ROS_DOMAIN_ID=" + env["ROS_DOMAIN_ID"],
            "GZ_PARTITION=" + env["GZ_PARTITION"],
            "D3_EVIDENCE=" + env["D3_EVIDENCE"])
    elif cmd == "prepare":
        prepare()
    elif cmd == "preflight":
        preflight()
    elif cmd == "launch":
        launch(env)
    elif cmd == "preview":
        preview(env)
    elif cmd == "remove-proxy":
        remove_proxy(env)
    elif cmd == "bridge":
        bridge(env)
    elif cmd == "live":
        live(env)
    elif cmd == "verify":
        verify(env)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Blocked, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print("[D03_V3][BLOCKED]", str(error), file=sys.stderr)
        raise SystemExit(2)
