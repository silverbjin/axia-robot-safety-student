#!/usr/bin/env python3
"""P2-only official Nav2 staged startup; no Goal, no fault, no /cmd_vel.

Reuses the P1 proven localization-before-navigation sequencer and initial-pose
acknowledgement. Replaces only P1-specific /cmd_vel graph with P2 guard graph.
A READY result is a simulation preflight, not G05/G06/G07 acceptance.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from d07_h01_cm_startup_boundary import classify_first_cm_startup_failure

from p1_gazebo_startup import Sequencer, StartupBlocked, REQUIRED_NAV_NODES
from p1_ros_readiness_probe import initial_clock_wait_budget


def g07_ci_initial_clock_budget(env):
    """CI-only 90s discovery, no Goal and no operating watchdog change."""
    return initial_clock_wait_budget("clock", 90, env=env)


def manage_g07_or_legacy(sequencer: Sequencer, name: str, gate: str):
    """G07 exact CI/Owner native Lifecycle request; other P2 cases unchanged."""
    if os.environ.get("AXIA_G07_OWNER_STARTUP_PARITY") != "1":
        sequencer.manage(name, gate)
        return
    native_file=(sequencer.output.parent /
                 (sequencer.output.stem + "." + gate.lower() + ".native.json"))
    # D07 stationary GUI: do not spin 90s on a lost service response.
    # The regular G07/Moving Goal and Navigation startup budgets are unchanged.
    d07_localization = (
        name == "localization"
        and os.environ.get("AXIA_D07_H01_GUI_NO_GOAL") == "1"
        and os.environ.get("AXIA_G07_CI_SIM_GOAL_ALLOWED", "0") == "0"
        and os.environ.get("AXIA_P0_SIM_ONLY") == "1")
    native_budget = "24" if d07_localization else "90"
    rc, _ = sequencer.command(
        gate, [sys.executable, "tools/p2_g07_lifecycle_service.py",
               "--manager", name, "--command", "startup",
               "--timeout-sec", native_budget, "--output", str(native_file)],
        timeout=38 if d07_localization else 103)
    try:
        v=json.loads(native_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        v={}
    acknowledged=(rc == 0 and v.get("status")=="ACK"
                  and v.get("success") is True and v.get("manager")==name
                  and v.get("command")=="startup" and v.get("goal_sent") is False)
    # A lost reply is NOT a lifecycle ACK. D07 only: independent official
    # manager/is_active plus BOTH /get_state services, twice; no STARTUP retry.
    # No other G07 case, especially any moving-Goal route, may use this gate.
    read_only_reconciled = False
    if (not acknowledged and d07_localization
            and v.get("status") == "SERVICE_TIMEOUT"
            and v.get("request_sent") is True):
        recovery_file = (sequencer.output.parent /
                         (sequencer.output.stem + "." + gate.lower()
                          + ".readonly_reconcile.json"))
        try:
            recovery_rc, _ = sequencer.command(
                gate + "_READONLY_RECONCILE",
                [sys.executable, "tools/d07_h01_lifecycle_reconcile.py",
                 "--native", str(native_file),
                 "--output", str(recovery_file),
                 "--timeout-sec", "14"], timeout=19)
            candidate = json.loads(recovery_file.read_text(encoding="utf-8"))
            read_only_reconciled = (
                recovery_rc == 0
                and candidate.get("status") == "READONLY_ACTIVE_RECONCILED_NO_ACK"
                and candidate.get("admitted_for_d07_no_goal") is True
                and candidate.get("lifecycle_ack_received") is False
                and candidate.get("startup_resent") is False
                and candidate.get("goal_sent") is False)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            read_only_reconciled = False
        if read_only_reconciled:
            print("D07_H01_LOCALIZATION_READONLY_ACTIVE_NO_ACK"
                  " ORIGINAL_SERVICE_RESPONSE_LOST"
                  " MOVING_GOAL_NOT_AUTHORIZED", flush=True)
    if (not acknowledged and name=="navigation"
        and (os.environ.get("AXIA_D07_H01_GEOMETRY_ONLY")=="1"
             or os.environ.get("AXIA_D07_H01_GUI_NO_GOAL")=="1")):
        # Real no-goal #43668837849: the CM preflight GetState returned,
        # then original official manager STARTUP REJECTED GetState request.
        # Diagnose AFTER that first irreversible manager error with ONE
        # read-only CM GetState call; do NOT retry partial Nav2 STARTUP.
        folder=sequencer.output.parent
        prepath=folder/"d07_h01_cm_lifecycle_prestart.json"
        postpath=folder/"d07_h01_cm_after_failed_manager.json"
        output=folder/"d07_h01_first_cm_manager_startup_failure.json"
        try:
            pre=json.loads(prepath.read_text(encoding="utf-8"))
        except (OSError,ValueError):
            pre={}
        post={}
        try:
            proc=subprocess.run(
                [sys.executable,"tools/d07_h01_cm_lifecycle_ready.py",
                 "--timeout-sec","12","--after-failed-manager",
                 "--output",str(postpath)],
                capture_output=True,text=True,timeout=18,check=False)
            if postpath.is_file():
                post=json.loads(postpath.read_text(encoding="utf-8"))
            post.setdefault("post_probe_returncode",proc.returncode)
        except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
            post={"status":"CM_AFTER_FAILED_MANAGER_PROVENANCE_HOLD_NO_GOAL",
                  "reason":type(exc).__name__,"goal_sent":False}
        try:
            # Latest startup log only. Keep the FIRST relevant manager error,
            # not the final staged-runner exception or late shutdown SIGINT.
            native_log=(folder/"launch.log").read_text(
                encoding="utf-8",errors="replace")[-750000:]
        except OSError:
            native_log=""
        diag=classify_first_cm_startup_failure(v,pre,post,native_log)
        output.write_text(json.dumps(diag,sort_keys=True,indent=2)+"\n",
                          encoding="utf-8")
        print("AXIA_D07_H01_FIRST_CM_MANAGER_STARTUP_FAILURE "+
              json.dumps(diag,sort_keys=True),flush=True)
    sequencer.require(
        acknowledged or read_only_reconciled,
        gate, "G07_NATIVE_LIFECYCLE_STARTUP_" +
        str(v.get("status","NO_RESPONSE")) +
        ":request_sent=" + str(v.get("request_sent",False)))
    if read_only_reconciled:
        sequencer.record(gate, "PASS",
                         "D07_ONLY_READONLY_ACTIVE_NO_ACK_NOT_LIFECYCLE_ACK")
    else:
        sequencer.record(gate,"PASS","G07_SHARED_NATIVE_"+name.upper()+"_ACK")


def run(sequencer: Sequencer, initialpose_output: Path):
    folder = sequencer.output.parent
    sequencer.probe("clock", folder/"clock_diagnostics.json", timeout=g07_ci_initial_clock_budget(os.environ))
    rc, log = sequencer.command("pre_navigation_state",
                               ["ros2", "lifecycle", "get", "/planner_server"], timeout=10)
    sequencer.require(not (rc == 0 and re.search(r"\bactive\s*\[3\]", log, re.I)),
                      "NAVIGATION_NOT_ACTIVE", "planner cannot be active before localization")
    manage_g07_or_legacy(sequencer,"localization","LOCALIZATION_START")
    sequencer.require(sequencer.lifecycle_active("map_server", 45)
                      and sequencer.lifecycle_active("amcl", 45),
                      "MAP_AMCL_ACTIVE", "official localization ACTIVE")
    rc, _ = sequencer.command("initialpose", [
        sys.executable, "tools/p0_initialpose_ros.py", "--x", "-2.0",
        "--y", "-0.5", "--yaw", "0", "--radius", "0.35",
        "--ack-initial-pose", "--amcl-service-ack",
        "--output", str(initialpose_output)], timeout=50)
    try:
        pose=json.loads(initialpose_output.read_text())
    except (OSError, ValueError):
        pose={}
    sequencer.require(rc == 0 and pose.get('result') == 'POSE_DELIVERY_ACKNOWLEDGED'
                      and pose.get('delivery',{}).get('acknowledged') is True
                      and pose.get('delivery',{}).get('service') == '/set_initial_pose',
                      "INITIALPOSE_MAP_CHECKED", "official AMCL initial-pose delivery ACK")
    sequencer.probe("localization", folder/"localization_diagnostics.json", timeout=50)
    # H01 read-only regression of real L2 #43661330404 first failure:
    # the official manager could not send collision_monitor/get_state.
    # Require genuine pre-STARTUP CM GetState reply; never retry a partially
    # executed manager STARTUP or claim safety graph/TTL from this probe.
    if ((os.environ.get("AXIA_D07_H01_GEOMETRY_ONLY")=="1"
         or os.environ.get("AXIA_D07_H01_GUI_NO_GOAL")=="1")
            and os.environ.get("AXIA_G07_OWNER_STARTUP_PARITY")=="1"):
        cm_path=folder/"d07_h01_cm_lifecycle_prestart.json"
        cm_rc,_=sequencer.command(
            "cm_lifecycle_prestart",
            [sys.executable,"tools/d07_h01_cm_lifecycle_ready.py",
             "--timeout-sec","12","--output",str(cm_path)],timeout=23)
        try:
            cm=json.loads(cm_path.read_text(encoding="utf-8"))
        except (OSError,ValueError):
            cm={}
        sequencer.require(
            cm_rc==0 and cm.get("status")=="CM_GET_STATE_ACK_NO_GOAL"
            and cm.get("native_get_state_responded") is True
            and cm.get("goal_sent") is False
            and cm.get("navigation_startup_proven") is False,
            "CM_LIFECYCLE_PRESTART",
            "ACTUAL_CM_GET_STATE_"+str(cm.get("status","NO_RESPONSE"))+
            ":"+str(cm.get("reason","NO_DIAGNOSTIC")))
    manage_g07_or_legacy(sequencer,"navigation","NAVIGATION_START")
    sequencer.require(all(sequencer.lifecycle_active(name, deadline_sec=30)
                          for name in REQUIRED_NAV_NODES),
                      "CM_ACTIVE", "official navigation and Collision Monitor ACTIVE")
    graph_path=folder/"p2_graph_diagnostics.json"
    rc,_=sequencer.command("p2_graph", [sys.executable,
                    "tools/p2_readonly_graph_probe.py", "--timeout-sec", "45",
                    "--output", str(graph_path)], timeout=60)
    try:
        graph=json.loads(graph_path.read_text())
    except (OSError, ValueError):
        graph={}
    sequencer.require(rc==0 and graph.get('status')=='P2_NO_GOAL_READONLY_READY'
                      and graph.get('goal_sent') is False
                      and graph.get('fault_injected') is False
                      and graph.get('gate_accepted') is False,
                      "P2_GRAPH_READY", str(graph.get('graph_reasons', ['P2_GRAPH_UNVERIFIED'])))
    sequencer.probe("navigation", folder/"navigation_diagnostics.json", timeout=50)
    sequencer.evidence.update(status="SMOKE_READY", goal_sent=False,
                              fault_injected=False, gate_accepted=False,
                              scope="P2_OFFICIAL_WAFFLE_NO_GOAL_ONLY")
    sequencer.persist()
    return 0


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--initialpose-output', required=True, type=Path)
    p.add_argument('--allow-sim-initialpose', action='store_true')
    args=p.parse_args(argv)
    sequencer=Sequencer(args.output)
    sequencer.persist()
    try:
        if os.environ.get('ROS_DISTRO') != 'jazzy' or os.environ.get('AXIA_P0_SIM_ONLY') != '1':
            raise StartupBlocked('ROS_JAZZY_SIMULATION_ONLY_REQUIRED')
        if not os.environ.get('GZ_PARTITION', '').startswith('axia_p2_'):
            raise StartupBlocked('ISOLATED_GZ_PARTITION_REQUIRED')
        if not args.allow_sim_initialpose:
            raise StartupBlocked('EXPLICIT_SIM_INITIALPOSE_OPT_IN_REQUIRED')
        status=run(sequencer, args.initialpose_output)
        print('P2_STAGED_NO_GOAL_READY G05_G06_G07_ACCEPTED=false',flush=True)
        return status
    except StartupBlocked as exc:
        sequencer.evidence.update(status='BLOCKED', failed_gate=str(exc),
                                  gate_accepted=False, goal_sent=False, fault_injected=False)
        sequencer.persist()
        print('P2_STAGED_NO_GOAL_BLOCKED: '+str(exc), file=sys.stderr,flush=True)
        return 2
    except Exception as exc:
        sequencer.evidence.update(status='ERROR', error=type(exc).__name__,
                                  gate_accepted=False, goal_sent=False, fault_injected=False)
        sequencer.persist()
        print('P2_STAGED_NO_GOAL_ERROR: '+type(exc).__name__, file=sys.stderr,flush=True)
        return 4


if __name__=='__main__':
    raise SystemExit(main())
