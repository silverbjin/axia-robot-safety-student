#!/usr/bin/env python3
"""FIX-05/06/08: sequence official Nav2 lifecycle managers, without a goal.

Caller MUST launch the official Waffle P1 launch with autostart:=false.
This command never publishes /cmd_vel, calls AXIA /start or sends a goal.
SIMULATION ONLY. A successful smoke is NOT a G00-G04 safety acceptance.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ORDERED_GATES = (
    "CLOCK_READY", "NAVIGATION_NOT_ACTIVE", "LOCALIZATION_START",
    "MAP_AMCL_ACTIVE", "INITIALPOSE_MAP_CHECKED", "AMCL_TF_READY",
    "NAVIGATION_START", "CM_ACTIVE", "GRAPH_READY", "NAV2_ACTION_READY",
)
REQUIRED_NAV_NODES = (
    "controller_server", "planner_server", "bt_navigator",
    "velocity_smoother", "collision_monitor",
)


def make_evidence():
    return {
        "status": "BLOCKED", "failed_gate": None, "stages": [],
        "gate_accepted": False, "certified_estop_verified": False,
        "gazebo_final_acceptance": "NOT_ACCEPTED",
        "scope": "OFFICIAL_GAZEBO_NAV2_NO_GOAL_SMOKE_ONLY",
    }


class StartupBlocked(RuntimeError):
    pass


class Sequencer:
    def __init__(self, output: Path):
        self.output = output
        self.evidence = make_evidence()
        self.output.parent.mkdir(parents=True, exist_ok=True)

    def record(self, gate, outcome, detail=None):
        self.evidence["stages"].append({
            "gate": gate, "status": outcome, "detail": detail,
            "wall_monotonic_s": round(time.monotonic(), 3),
        })
        self.persist()

    def persist(self):
        self.output.write_text(json.dumps(self.evidence, ensure_ascii=False, indent=2) + "\n")

    def require(self, condition, gate, reason):
        if not condition:
            self.evidence["failed_gate"] = gate
            self.record(gate, "BLOCKED", reason)
            raise StartupBlocked(gate + ": " + reason)
        self.record(gate, "PASS", reason)

    def command(self, gate, argv, timeout=35):
        started = time.monotonic()
        try:
            response = subprocess.run(
                argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=timeout, check=False
            )
            returncode, log = response.returncode, response.stdout or ""
        except subprocess.TimeoutExpired as exc:
            returncode = 124
            log = (exc.stdout or b"")
            if isinstance(log, bytes):
                log = log.decode(errors="replace")
            log += "\nTIMEOUT after " + str(timeout) + " seconds"
        logpath = self.output.parent / (self.output.stem + "." + gate.lower() + ".log")
        logpath.write_text("COMMAND: " + repr(argv) + "\nEXIT: " + str(returncode)
                           + "\nWALL_S: " + str(round(time.monotonic()-started, 3))
                           + "\n" + log)
        return returncode, log

    def lifecycle_active(self, name, deadline_sec=45):
        deadline = time.monotonic() + deadline_sec
        last = ""
        while time.monotonic() < deadline:
            rc, last = self.command("lifecycle_" + name,
                                    ["ros2", "lifecycle", "get", "/" + name], 6)
            if rc == 0 and re.search(r"\bactive\s*\[3\]", last, re.I):
                return True
            time.sleep(0.5)
        return False

    def manage(self, name, gate):
        target = "/lifecycle_manager_" + name + "/manage_nodes"
        cmd = ["ros2", "service", "call", target,
               "nav2_msgs/srv/ManageLifecycleNodes", "{command: 0}"]
        rc, text = self.command(gate, cmd, timeout=95)
        success = rc == 0 and bool(re.search(r"\bsuccess\s*[:=]\s*(true|True)\b", text))
        if not success:
            self.require(False, gate, "lifecycle manager " + name + " did not confirm startup success")
        self.record(gate, "PASS", name + " lifecycle startup confirmed")

    def probe(self, phase, output, timeout):
        cmd = [sys.executable, "tools/p1_ros_readiness_probe.py",
               "--phase", phase, "--timeout", str(timeout), "--output", str(output)]
        rc, _ = self.command("probe_" + phase, cmd, timeout=timeout+22)
        try:
            summary = json.loads(output.read_text())
        except (OSError, ValueError):
            summary = {}
        self.require(rc == 0 and summary.get("status") == "READY",
                     {"clock": "CLOCK_READY", "localization": "AMCL_TF_READY",
                      "navigation": "NAV2_ACTION_READY"}[phase],
                     summary.get("reason", "probe failed or missing evidence"))

    def run(self, initialpose_output: Path):
        self.probe("clock", self.output.parent / "clock_diagnostics.json", timeout=45)
        rc, output = self.command("pre_navigation_state",
                 ["ros2", "lifecycle", "get", "/planner_server"], timeout=10)
        self.require(not (rc == 0 and re.search(r"\bactive\s*\[3\]", output, re.I)),
                     "NAVIGATION_NOT_ACTIVE", "planner must not be active before localization")

        self.manage("localization", "LOCALIZATION_START")
        self.require(self.lifecycle_active("map_server", 45)
                     and self.lifecycle_active("amcl", 45),
                     "MAP_AMCL_ACTIVE", "map_server and amcl ACTIVE")

        pose_command = [
            sys.executable, "tools/p0_initialpose_ros.py",
            "--x", "-2.0", "--y", "-0.5", "--yaw", "0",
            "--radius", "0.35", "--ack-initial-pose", "--amcl-service-ack",
            "--output", str(initialpose_output),
        ]
        rc, _ = self.command("initialpose", pose_command, timeout=50)
        try:
            pose = json.loads(initialpose_output.read_text())
        except (OSError, ValueError):
            pose = {}
        self.require(
            rc == 0
            and pose.get("result") == "POSE_DELIVERY_ACKNOWLEDGED"
            and pose.get("delivery", {}).get("acknowledged") is True
            and pose.get("delivery", {}).get("service") == "/set_initial_pose",
                     "INITIALPOSE_MAP_CHECKED", pose.get("reason", "initialpose evidence missing"))

        self.probe("localization", self.output.parent / "localization_diagnostics.json",
                   timeout=50)
        self.manage("navigation", "NAVIGATION_START")
        self.require(all(self.lifecycle_active(name, deadline_sec=30)
                         for name in REQUIRED_NAV_NODES),
                     "CM_ACTIVE", "all Nav2 navigation nodes including Collision Monitor ACTIVE")

        graph_path = self.output.parent / "graph_diagnostics.json"
        rc, _ = self.command(
            "graph", [sys.executable, "tools/p1_t05_graph_oracle.py",
                      "--timeout", "22", "--output", str(graph_path)], timeout=35)
        try:
            graph = json.loads(graph_path.read_text())
        except (OSError, ValueError):
            graph = {}
        self.require(rc == 0 and graph.get("verdict", {}).get("passed") is True,
                     "GRAPH_READY", graph.get("verdict", {}).get("reasons", ["graph evidence missing"]))
        self.probe("navigation", self.output.parent / "navigation_diagnostics.json",
                   timeout=50)
        self.evidence["status"] = "SMOKE_READY"
        self.persist()
        return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--initialpose-output", required=True, type=Path)
    parser.add_argument("--allow-sim-initialpose", action="store_true")
    args = parser.parse_args()
    sequencer = Sequencer(args.output)
    sequencer.persist()
    try:
        if os.environ.get("AXIA_P0_SIM_ONLY") != "1" or not os.environ.get("GZ_PARTITION"):
            raise StartupBlocked("SIMULATION_MARKERS_MISSING")
        if os.environ.get("ROS_DISTRO") != "jazzy":
            raise StartupBlocked("ROS_JAZZY_REQUIRED")
        if not args.allow_sim_initialpose:
            raise StartupBlocked("EXPLICIT_SIM_INITIALPOSE_AUTHORIZATION_REQUIRED")
        rc = sequencer.run(args.initialpose_output)
        print("SMOKE_READY: real simulation readiness; G00-G04 NOT_ACCEPTED")
        return rc
    except StartupBlocked as exc:
        sequencer.evidence["status"] = "BLOCKED"
        if sequencer.evidence["failed_gate"] is None:
            sequencer.evidence["failed_gate"] = str(exc)
        sequencer.persist()
        print("SMOKE_BLOCKED:", exc, file=sys.stderr)
        return 2
    except Exception as exc:
        sequencer.evidence["status"] = "ERROR"
        sequencer.evidence["error"] = repr(exc)
        sequencer.persist()
        print("SMOKE_ERROR:", repr(exc), file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
