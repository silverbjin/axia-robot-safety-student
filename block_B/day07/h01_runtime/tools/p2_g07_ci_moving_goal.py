#!/usr/bin/env python3
"""Shared simulation-only Jazzy/Gazebo moving G07 Goal for CI and Owner.

CI requires GitHub Actions authority. Owner requires controlling TTY, exact
source SHA and three run-owned processes before any Goal. Neither mode grants
final Owner L3 acceptance or certified hardware E-Stop.
"""
import argparse
from collections import deque
import faulthandler
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from p2_g07_events_executor_policy import select_events_executor
from p2_g07_health_first_boundary import HealthFirstBoundary
from p2_l3_live_session import Observer, _call_start, _publish_goal, _map_robot_pose
from p2_l3_coordinate_frames import make_frame_anchor, obstacle_world_pose
from p2_g07_spawn_contract import official_tb3_spawn
from p2_l3_gz_fixture import move_ci_verified
from p2_g07_ci_stop_stage import plan_stop_fixture
from p2_l3_acceptance_contract import zone_phase_sample
from p2_g07_ci_moving_goal_oracle import assess, first_delivery_breach, first_pre_latch_delivery_timing, guard_cm_receive_skew, post_stop_odom_zero_dwell

# G07 classroom only: improve visible cruise before moving the same fixture.
CLEAR_MIN_TRAVEL_M = 0.12

def _require_ci_only(expected_sha):
    assert os.environ.get("GITHUB_ACTIONS")=="true", "NOT_PUBLIC_GITHUB_ACTIONS"
    assert os.environ.get("AXIA_G07_CI_SIM_GOAL_ALLOWED")=="1", "NO_SCOPED_SIM_GOAL_OPT_IN"
    assert os.environ.get("AXIA_P0_SIM_ONLY")=="1", "NOT_SIM_ONLY"
    assert os.environ.get("ROS_DISTRO")=="jazzy", "ROS_JAZZY_REQUIRED"
    assert os.environ.get("GZ_PARTITION","").startswith("axia_p2_"), "NO_ISOLATED_GZ_PARTITION"
    assert os.environ.get("AXIA_P2_G07_PHYSICAL_PREFLIGHT")=="1", "NO_REAL_HARMONIC_PHYSICAL_OVERLAY"
    current=subprocess.check_output(["git","rev-parse","HEAD"],text=True,timeout=5).strip()
    assert current==expected_sha, "CI_SOURCE_SHA_MISMATCH"

def _task03_exact_goal_terminal(node, obs, goal_uuid):
    """One exact Nav2 action CancelGoal AFTER physical STOP and 1s odom ZERO.

    This cancels only the UUID already issued by the Supervisor. A successful
    service return alone is NOT terminal proof; require real ROS ActionStatus=5.
    Does not rearm, inject faults or change any command publisher.
    """
    import re
    from action_msgs.srv import CancelGoal
    from p2_g07_task03_contract import audit_goal_terminal
    if not re.fullmatch(r"[0-9a-f]{32}", goal_uuid):
        raise RuntimeError("TASK03_GOAL_UUID_MALFORMED")
    if obs.data()["goals"].get(goal_uuid)!=2:
        raise RuntimeError("TASK03_GOAL_NOT_EXECUTING_AT_CANCEL")
    client=node.create_client(CancelGoal,"/navigate_to_pose/_action/cancel_goal")
    if not client.wait_for_service(timeout_sec=3):
        raise RuntimeError("TASK03_CANCEL_SERVICE_MISSING")
    req=CancelGoal.Request()
    req.goal_info.goal_id.uuid=list(bytes.fromhex(goal_uuid))
    future=client.call_async(req)
    deadline=time.monotonic()+10.0
    while not future.done() and time.monotonic()<deadline:
        time.sleep(.05)
    if not future.done():
        raise RuntimeError("TASK03_EXACT_CANCEL_ACK_TIMEOUT")
    ans=future.result()
    if ans is None:
        raise RuntimeError("TASK03_EXACT_CANCEL_EMPTY_ACK")
    canceled=["".join(format(v,"02x") for v in row.goal_id.uuid)
              for row in ans.goals_canceling]
    # Goal state is reported by the existing real Nav2 action status topic.
    while time.monotonic()<deadline:
        snap=obs.data()
        if snap["goals"].get(goal_uuid)==5: break
        if snap["goals"].get(goal_uuid) in (4,6): break
        time.sleep(.05)
    snap=obs.data()
    verdict=audit_goal_terminal(goal_uuid, int(ans.return_code),canceled,
                                snap["goals"].get(goal_uuid),
                                snap["guard"].get("latched"))
    if verdict["status"]!="EXACT_GOAL_UUID_TERMINAL_CANCELED_PASS":
        raise RuntimeError("TASK03_EXACT_GOAL_TERMINAL_UNVERIFIED")
    print("AXIA_G07_TASK03_EXACT_GOAL_UUID_CANCELED_NATIVE_ACTION_PASS "+goal_uuid,
          flush=True)
    return verdict


def _stop_supervisor_active(vin):
    """STOP checks motion authority by magnitude: Nav2 can legitimately
    reverse to avoid the physical obstacle. The *final* CM/Guard must still
    be ZERO; no reverse-motion allowance bypasses the fresh physical scan,
    Goal EXECUTING, native Gazebo ACK, or one-second odom stop dwell.
    """
    return (type(vin) in (int,float) and math.isfinite(vin)
            and .005 < abs(vin) <= .22)

def _fresh(snap,keys,limit=.3):
    now=snap.get("mono")
    if not isinstance(now,(int,float)):return None
    ages=[]
    for k in keys:
        t=snap.get(k+"_at")
        if not isinstance(t,(float,int)) or not 0<=now-t<=limit:
            return None
        ages.append(now-t)
    return max(ages)

def _period(values,t0,t1):
    v=[z["t"] for z in values if t0<=z["t"]<=t1]
    return max((b-a for a,b in zip(v,v[1:])),default=None)

def _pre_goal_odom_pose(snap, data):
    """Confirm actual fresh Observer odom before any start/Goal operation.

    A ready ROS graph is not a receipt from this recently attached node.
    Keep existing after-Goal 300ms sensor TTL; this is PRE-GOAL readiness
    only, never simulated odom or a watchdog relaxation.
    """
    if not isinstance(snap, dict) or not isinstance(data, dict):
        return None
    now, last = snap.get("mono"), snap.get("odom_at")
    samples, pose = data.get("odom"), data.get("pose")
    if (not isinstance(now, (int,float))
            or not isinstance(last, (int,float))
            or not all(math.isfinite(x) for x in (now,last))
            or not 0 <= now-last <= .30
            or not isinstance(samples, (list,tuple)) or len(samples)<2
            or not isinstance(pose,(list,tuple)) or len(pose)!=3
            or not all(type(x) in (int,float) and math.isfinite(x) for x in pose)):
        return None
    before, recent = samples[-2].get("t"), samples[-1].get("t")
    if (not isinstance(before,(int,float))
            or not isinstance(recent,(int,float))
            or not all(math.isfinite(x) for x in (before,recent))
            or not 0 < recent-before <= .30
            or abs(recent-last)>0.03):
        return None
    return tuple(pose)


def run(args):
    # Same exact Gazebo/ROS phase and stop oracle for public CI and WSL2.
    # Only PRE-GOAL authority differs; the Owner cannot set CI credentials.
    owner_launch_pid=getattr(args,"owner_launch_pid",None)
    owner_mode=owner_launch_pid is not None
    if owner_mode:
        from p2_g07_shared_admission import admit_owner
        from p2_pre_goal_process_gate import inspect as inspect_owned_processes
        actual=subprocess.check_output(
            ["git","-C",str(Path(__file__).resolve().parents[1]),
             "rev-parse","HEAD"],text=True,timeout=5).strip()
        owner_scope=admit_owner(
            expected_sha=args.source_sha,actual_sha=actual,
            launch_pid=owner_launch_pid,env=os.environ,
            has_tty=(os.isatty(0) and os.path.exists("/dev/tty")),
            inspect=inspect_owned_processes)
        print("AXIA_G07_OWNER_COMMON_PREGOAL_PID_TTY_AUTHORITY_PASS "
              "same_real_gazebo_goal_runner=true",flush=True)
    else:
        _require_ci_only(args.source_sha)
        owner_scope=None
    startup=json.loads(args.startup.read_text())
    pregoal=json.loads(args.pregoal.read_text())
    assert startup.get("status")=="SMOKE_READY" and startup.get("goal_sent") is False
    assert startup.get("fault_injected") is False
    assert pregoal.get("status")=="P2_G07_OWNER_PREGOAL_L2_READY_NO_GOAL"
    assert pregoal.get("native_set_pose_ack") is True
    assert pregoal.get("post_ack_distinct_ros_scan_count",0)>=2
    assert pregoal.get("front_m",0)>.75 and .55<=pregoal.get("side_m",0)<=.95
    args.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    report={"schema":"axia_g07_public_ci_moving_goal_v1","status":"BLOCKED",
            "reason":"NOT_STARTED","sim_only":True,"ci_specific":not owner_mode,
            "source_sha":args.source_sha,"goal_sent":False,
            "fault_injected":False,"certified_estop":False,
            "collision_ground_truth_available":False,"gate_accepted":False,
            "owner_l3_accepted":False,
            "owner_authority_verified":(owner_scope is not None),
            "shared_execution_mode":("owner" if owner_mode else "ci")}
    def save():
        (args.output/"ci_moving_goal_result.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n")
    save()
    import rclpy
    from rclpy.node import Node
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.parameter import Parameter
    from std_msgs.msg import String
    rclpy.init()
    node=Node("axia_g07_public_ci_sim_only_moving_goal",
              parameter_overrides=[Parameter("use_sim_time",value=True)],
              automatically_declare_parameters_from_overrides=True)
    # Reproduce the WSL2 Owner's original observation scheduling and I/O:
    # 2 executor workers plus line-buffered evidence. Only an explicitly
    # admitted CI-only simulation may select the parity profile.
    owner_observer_parity = (
        owner_mode or os.environ.get("AXIA_G07_CI_OWNER_OBSERVER_PARITY") == "1")
    if owner_observer_parity and not owner_mode:
        assert os.environ.get("GITHUB_ACTIONS")=="true"
        assert os.environ.get("AXIA_G07_CI_SIM_GOAL_ALLOWED")=="1"
        print("AXIA_G07_CI_OWNER_OBSERVER_PARITY_ADMITTED "
              "workers=2 buffered=true bounded_flush_sec=0.75 "
              "periodic_watchdog=false",flush=True)
    requested_probe=os.environ.get("AXIA_G07_OBSERVER_IO_PROBE","0")
    if requested_probe not in ("0","1"):
        raise ValueError("G07_OBSERVER_IO_PROBE_INVALID_SETTING")
    io_probe=(requested_probe=="1")
    if io_probe:
        if not (not owner_mode and
                os.environ.get("GITHUB_ACTIONS")=="true" and
                os.environ.get("AXIA_G07_CI_SIM_GOAL_ALLOWED")=="1" and
                os.environ.get("AXIA_P0_SIM_ONLY")=="1" and
                owner_observer_parity):
            raise ValueError("G07_OBSERVER_IO_PROBE_REQUIRES_PUBLIC_SIM_ONLY")
        print("AXIA_G07_OBSERVER_IO_PROBE=CI_ONLY_READ_ONLY "
              "NO_CALLBACK_IO_ADDED ORIGINAL_FLUSH_RETAINED",flush=True)
    silence_probe=None
    if io_probe:
        from p2_g07_observer_io_probe import FirstExecutorSilenceSnapshot
        silence_probe=FirstExecutorSilenceSnapshot(threshold_ms=160)
    spin_status={"started_at":None}
    heartbeat_ticks=deque(maxlen=14000)
    heartbeat_stop=threading.Event()
    probe_thread=None
    if io_probe:
        def observer_probe_heartbeat():
            while not heartbeat_stop.is_set():
                now=time.monotonic()
                heartbeat_ticks.append(now)
                # Same existing CI-only heartbeat; no new ROS entities.
                # Inspect the last callback timestamp without callback I/O.
                # Record ONE stack of the original executor at 160ms silence.
                if (report.get("goal_sent") is True and
                        silence_probe is not None and worker.ident is not None):
                    rows=obs._g07_io_probe.rows
                    if rows:
                        spin_started_at=(spin_status["started_at"]
                                         if bounded_wait_candidate else None)
                        silence_probe.capture(
                            now=now,last_callback_at=rows[-1][1],
                            goal_active=True,spin_thread_ident=worker.ident,
                            spin_started_at=spin_started_at,
                            spin_timeout_ms=20 if bounded_wait_candidate else None)
                heartbeat_stop.wait(.020)
        probe_thread=threading.Thread(
            target=observer_probe_heartbeat,
            name="g07_readonly_io_probe_heartbeat",daemon=True)
        probe_thread.start()
    events_candidate=select_events_executor(
        os.environ,owner_mode=owner_mode)
    # CI-only A/B candidate: the original two-worker Multi executor, with
    # bounded wait-set wake horizon. Owner/default is unchanged.
    from p2_g07_observer_io_probe import select_bounded_executor_wait_candidate
    bounded_wait_candidate=select_bounded_executor_wait_candidate(
        os.environ,owner_mode=owner_mode)
    if bounded_wait_candidate:
        assert not events_candidate and owner_observer_parity
        print("AXIA_G07_CI_MULTI2_WAITSET_20MS_AB "
              "OWNER_UNCHANGED STRICT_TTL_120_150_300_HOLD_IF_FAILED",
              flush=True)
    if events_candidate:
        print("AXIA_G07_MOVING_EVENTS_EXECUTOR_AB=CI_ONLY "
              "OFFICIAL_JAZZY_QOS_GOAL_CM_GUARD_TTL_UNCHANGED",flush=True)
    observer_started_at=time.monotonic()
    obs=(Observer(node,args.output,buffered_evidence=True,
                  periodic_flush_sec=.75,io_probe=io_probe)
         if owner_observer_parity
         else Observer(node,args.output,buffered_evidence=True,
                       io_probe=io_probe))
    parity_trace=(args.output/"owner_parity_fatal_trace.log").open("x",buffering=1) if owner_observer_parity else None
    if parity_trace is not None:
        faulthandler.enable(file=parity_trace, all_threads=True)
    guard_ticks=[]
    def on_guard(m):
        guard_ticks.append(time.monotonic())
        if len(guard_ticks)>3000:del guard_ticks[:1500]
    extra=node.create_subscription(String,"/axia/p2/base_guard",on_guard,10)
    if events_candidate:
        from rclpy.experimental import EventsExecutor
        executor=EventsExecutor()
    else:
        executor=MultiThreadedExecutor(num_threads=2 if owner_observer_parity else 3)
    executor.add_node(node)
    spin_stop=threading.Event()
    def spin_multi_with_bounded_wait():
        while not spin_stop.is_set() and rclpy.ok():
            spin_status["started_at"]=time.monotonic()
            try:
                executor.spin_once(timeout_sec=.02)
            except Exception:
                # The only suppressed exception is an expected shutdown
                # AFTER stop was signaled; earlier spin errors still crash.
                if not spin_stop.is_set():
                    raise
                break
            finally:
                spin_status["started_at"]=None
    worker=threading.Thread(
        target=(spin_multi_with_bounded_wait if bounded_wait_candidate
                else executor.spin),
        name="g07_observer_executor_spin",daemon=True)
    worker.start()
    published=None
    stop_ack_at=None
    stop_pre_move_front=None
    distinct_stop_scans=[]
    try:
        graph_checks=True
        health_boundary=HealthFirstBoundary(max_samples=48)
        def wait(check,secs,label):
            until=time.monotonic()+secs
            samples=[]
            last_sample=0.
            last_health_sample=0.
            while time.monotonic()<until:
                snap=obs.snapshot(include_graph=graph_checks)
                data=obs.data()
                if label=="HEALTH":
                    # Strictly a bounded in-memory observation in the existing
                    # same callback/poll loop. No extra ROS subscriptions,
                    # discovery requests, Goal or safety decision changes.
                    boundary_at=time.monotonic()
                    if boundary_at-last_health_sample>=.25:
                        health_boundary.record(boundary_at,snap,data)
                        last_health_sample=boundary_at
                g=snap.get("guard",{})
                if g.get("latched") is True:
                    report["first_guard_latch"]=g.get("first_latch_trace")
                    raise RuntimeError("GUARD_LATCH_DURING_"+label+":"+str(g.get("reason")))
                goal_status=snap.get("action_status")
                if report["goal_sent"] and goal_status in (3,4,5,6):
                    raise RuntimeError("GOAL_TERMINATED_DURING_"+label+":"+str(goal_status))
                result=check(snap,data)
                if result is not None:return result
                now=time.monotonic()
                if label in ("SLOW","STOP") and now-last_sample>=.35:
                    last_sample=now
                    front=data.get("scan")
                    pose=data.get("pose")
                    samples.append({
                        "t":round(now,3),
                        "front_m":round(front,4) if isinstance(front,(float,int)) else None,
                        "side_m":round(data["side_scan"],4) if isinstance(data.get("side_scan"),(float,int)) else None,
                        "odom_pose": [round(z,4) for z in pose] if pose else None,
                        "odom_vx":snap.get("odom_speed"),
                        "supervised_vx":snap.get("supervised_speed"),
                        "cm_vx":snap.get("pre_guard_speed"),
                        "final_vx":snap.get("final_speed"),
                        "goal_status":goal_status,
                        "guard_reason":g.get("reason"),
                    })
                time.sleep(.025)
            if samples:
                scan=[x["front_m"] for x in samples if x["front_m"] is not None]
                active=[x for x in samples if x["front_m"] is not None
                        and .4<x["front_m"]<.75]
                summary={"phase":label,"observations":len(samples),
                         "min_front_m":min(scan) if scan else None,
                         "max_supervised_in_slow_zone":max(
                             (x["supervised_vx"] for x in active if isinstance(
                                 x["supervised_vx"],(int,float))),default=None),
                         "first":samples[:3],"last":samples[-8:]}
                (args.output/(label.lower()+"_timeout_trace.json")).write_text(
                    json.dumps(summary,sort_keys=True,indent=2)+"\n")
                print("AXIA_G07_CI_MOVING_"+label+"_TIMEOUT_DIAGNOSTICS "
                      +json.dumps(summary,sort_keys=True),flush=True)
            if label=="HEALTH":
                diag=health_boundary.result()
                report["health_first_boundary"]=diag
                (args.output/"first_health_boundary.json").write_text(
                    json.dumps(diag,sort_keys=True,indent=2)+"\n")
                print("AXIA_G07_FIRST_HEALTH_UNVERIFIED_HOLD "+
                      json.dumps({k:diag.get(k) for k in (
                          "status","first_readiness_blockers","first_sample",
                          "first_state_transition","last_sample",
                          "samples","release")},sort_keys=True),flush=True)
            raise RuntimeError("CI_MOVING_GOAL_TIMEOUT_"+label)
        wait(lambda snap,data: True if
             data["supervisor"].get("health_diagnostics",{}).get("cm_lifecycle_ok") is True
             and snap.get("clock_advancing") and data.get("scan") is not None
             else None,12,"HEALTH")
        # Discovery is asynchronous in the full Harmonic/Nav2 overlay.
        # Do not mistake an early empty graph for a safety defect, and never
        # issue a Goal before all three exact actual publishers are present.
        expected=[("axia_base_command_guard","geometry_msgs/msg/Twist")]
        def real_graph_ready(s,d):
            return s if (s["final_publishers"]==expected
                and s["cm_publishers"]==[("collision_monitor","geometry_msgs/msg/Twist")]
                and s["supervisor_publishers"]==[("axia_safety_supervisor","geometry_msgs/msg/Twist")]) else None
        try:
            s=wait(real_graph_ready,12,"EXCLUSIVE_SUPERVISOR_CM_GUARD_GRAPH")
        except RuntimeError:
            snap=obs.snapshot()
            print("AXIA_G07_CI_PRE_GOAL_GRAPH_DIAGNOSTIC "+
                  json.dumps({k:snap.get(k) for k in (
                     "final_publishers","cm_publishers","supervisor_publishers")},
                     sort_keys=True),flush=True)
            raise
        # Exclusive graph proved pre-Goal; avoid DDS introspection at 40Hz
        # during safety-critical Supervisor -> CM -> Guard delivery.
        graph_checks=False
        # Run #44250223189: graphical /scan and graph were ready, but
        # this new Observer had not yet delivered TWO fresh /odom callbacks.
        # Do not turn a benign asynchronous discovery boundary into an
        # unnamed assertion or send an unanchored Goal.
        start_pose=wait(_pre_goal_odom_pose,4,"PRE_GOAL_ODOM")
        print("AXIA_G07_TASK04_REAL_OBSERVER_ODOM_READY_BEFORE_GOAL "
              "two_fresh_callbacks=true max_gap_sec=0.3",flush=True)
        # An actual TF-derived map/odom anchor and verified official world
        # spawn are required before the Goal, not inferred from raw /odom.
        world_anchor=make_frame_anchor(
            _map_robot_pose(node,obs),start_pose,official_tb3_spawn(),
            map_pose_source=getattr(obs,'map_pose_source',
                                    'amcl_pose_map_transient_local'))
        _call_start(node,obs)
        wait(lambda s,d: True if d["supervisor"].get("state")=="NORMAL" else None,
             5,"SUPERVISOR_START")
        published=_publish_goal(node,obs,demo_corridor=True)
        goal_sent_at=time.monotonic()
        report["goal_sent"]=True
        save()
        print("AXIA_G07_PUBLIC_CI_SIMULATION_ONLY_ONE_SUPERVISOR_GOAL_SENT",flush=True)
        # The Owner WSL2 action status arrived ~2s after real cruise began.
        # Observe the real CLEAR motion before the delayed status callback.
        def phase(name):
            def check(s,d):
                action_status=s.get("action_status")
                if name=="clear":
                    # One already-issued Goal; no prior command publisher.
                    # Terminal statuses never admit a CLEAR observation.
                    if action_status not in (None,1,2):return None
                elif action_status!=2:return None
                age=_fresh(s,("scan","supervised","pre_guard","final","odom","guard","clock"))
                if age is None:return None
                vin=s.get("supervised_speed")
                cm=s.get("pre_guard_speed")
                final=s.get("final_speed")
                front=d.get("scan")
                if not all(isinstance(x,(float,int)) and math.isfinite(x)
                           for x in (vin,cm,final,front)):return None
                # CLEAR needs observable cruise; the real Nav2 SLOW/STOP
                # path can legitimately command 0.020m/s while rotating.
                # Still require positive motion authority; never accept
                # numerical noise, a synthetic scan or a stale command.
                if name=="stop":
                    if not _stop_supervisor_active(vin):return None
                    if stop_ack_at is None or stop_pre_move_front is None:
                        return None
                    scan_at=s.get("scan_at")
                    if not isinstance(scan_at,(int,float)) or scan_at<=stop_ack_at:
                        return None
                    if (not (.14<=front<.4)
                        or stop_pre_move_front-front<.10):
                        return None
                    if (not distinct_stop_scans
                        or scan_at>distinct_stop_scans[-1]):
                        distinct_stop_scans.append(scan_at)
                    if len(distinct_stop_scans)<2:
                        return None
                elif vin <= (.03 if name=="clear" else .005):
                    # CLEAR and SLOW still require forward proof.
                    return None
                if name=="clear":
                    condition=front>.75 and cm>.03 and final>.03
                elif name=="slow":
                    condition=(.4<front<.75 and 0<cm<=.30*vin+.01
                               and 0<final<=.30*vin+.01)
                else:
                    condition=(.14<=front<.4 and abs(cm)<.01 and abs(final)<.01)
                if not condition:return None
                return {"front_m":front,"supervised_vx":vin,"cm_vx":cm,
                        "final_vx":final,"age_sec":age}
            return check
        rows={}
        rows["clear"]=wait(phase("clear"),8,"CLEAR")
        report["clear"]=rows["clear"]
        report["goal_status_at_clear"]=obs.snapshot(include_graph=False).get("action_status")
        report["clear_before_action_ack"]=(report["goal_status_at_clear"]!=2)
        print("AXIA_G07_PUBLIC_CI_MOVING_CLEAR_REAL_GAZEBO_LIDAR_CM_PASS "+
              json.dumps(rows["clear"],sort_keys=True),flush=True)
        save()
        # Validate the SAME Goal as EXECUTING before any moving obstacle stage.
        # Delayed status receipt cannot erase previously observed real cruise.
        wait(lambda s,d: s.get("goal_uuid") if
             s.get("action_status")==2 and s.get("goal_uuid") is not None else None,
             15,"ACTION_EXECUTING")
        goal_uuid=obs.snapshot(include_graph=False)["goal_uuid"]
        report["goal_uuid"]=goal_uuid
        report["same_goal_executing_after_clear"]=True
        print("AXIA_G07_PUBLIC_CI_ACTUAL_NAV2_GOAL_EXECUTING "+goal_uuid,flush=True)
        # Real odom displacement, not elapsed sleep or a fabricated /scan.
        # The same authorized Goal stays EXECUTING and all safety streams
        # must still be fresh while showing a longer CLEAR cruise.
        def clear_motion_ready(s,d):
            pose=d.get("pose")
            if (s.get("action_status")!=2
                    or not isinstance(pose,(tuple,list)) or len(pose)!=3
                    or any(type(v) not in (int,float) or not math.isfinite(v)
                           for v in pose)
                    or s.get("guard",{}).get("latched") is not False
                    or _fresh(s,("scan","odom","guard","clock",
                                 "supervised","pre_guard","final")) is None
                    or not isinstance(d.get("scan"),(float,int))
                    or d["scan"]<=.75):
                return None
            distance=math.hypot(pose[0]-start_pose[0],pose[1]-start_pose[1])
            return distance if distance>=CLEAR_MIN_TRAVEL_M else None
        clear_travel=wait(clear_motion_ready,8,"CLEAR_DISTANCE")
        report["clear_odom_travel_m"]=round(clear_travel,6)
        print("AXIA_G07_MVP_VISIBLE_CLEAR_ODOM_CONFIRMED "+
              json.dumps({"distance_m":clear_travel,
                          "required_m":CLEAR_MIN_TRAVEL_M}),flush=True)
        save()
        # Keep the original pre-Goal side/LiDAR proof, then move that same
        # physical cylinder into the visible SLOW sector. No synthetic Scan.
        slow_target=obstacle_world_pose(
            world_anchor,obs.data().get("pose"),.62,.07,demo_corridor=True)
        slow_request_started=time.monotonic()
        report["slow_native_request_started_monotonic"]=slow_request_started
        slow_ack=move_ci_verified(*slow_target,sim_env=os.environ,
            pregoal_native_verified=(pregoal.get("native_set_pose_ack") is True),
            owner_admitted=(owner_scope is not None))
        slow_ack_at=time.monotonic()
        (args.output/"ci_slow_native_gazebo_set_pose_ack.log").write_text(slow_ack)
        report.update(slow_native_set_pose_ack=True,slow_world_xy=list(slow_target),
                      slow_native_ack_at_monotonic=slow_ack_at,
                      slow_native_service_duration_sec=round(
                          slow_ack_at-slow_request_started,6))
        print("AXIA_G07_MVP_SLOW_PHYSICAL_FIXTURE_ACK "+
              json.dumps({"world_xy":slow_target,"surface_m":.62,
                          "request_started_monotonic":slow_request_started,
                          "ack_at_monotonic":slow_ack_at},sort_keys=True),flush=True)
        save()
        rows["slow"]=wait(phase("slow"),35,"SLOW")
        report["slow"]=rows["slow"]
        report["goal_status_at_slow"]=2
        print("AXIA_G07_PUBLIC_CI_MOVING_SLOW_REAL_GAZEBO_LIDAR_CM_PASS "+
              json.dumps(rows["slow"],sort_keys=True),flush=True)
        save()
        # Reuse the existing single STOP fixture planner and real Gazebo ACK.
        snap=obs.snapshot(include_graph=False)
        stop_pre_move_front=obs.data().get("scan")
        if not isinstance(stop_pre_move_front,(float,int)):
            raise RuntimeError("STOP_PREPOSITION_REAL_SCAN_MISSING")
        target=plan_stop_fixture(
            world_anchor,obs.data().get("pose"),
            goal_status=snap.get("action_status"),
            guard_latched=snap.get("guard",{}).get("latched"),
            real_slow_observed=True)
        native_request_started=time.monotonic()
        ack=move_ci_verified(*target,sim_env=os.environ,
            pregoal_native_verified=(pregoal.get("native_set_pose_ack") is True),
            owner_admitted=(owner_scope is not None))
        stop_ack_at=time.monotonic()
        report["stop_native_service_duration_sec"]=round(
            stop_ack_at-native_request_started,6)
        (args.output/"ci_stop_native_gazebo_set_pose_ack.log").write_text(ack)
        report.update(
            stop_native_set_pose_ack=True,
            stop_world_xy=list(target),
            stop_pre_move_front_m=stop_pre_move_front)
        save()
        print("AXIA_G07_CI_MOVING_REAL_GAZEBO_STOP_INTRUSION_ACK "
              +json.dumps({"world_xy":target,
                          "pre_front_m":stop_pre_move_front,
                          "native_service_duration_sec":
                              report["stop_native_service_duration_sec"]},
                         sort_keys=True),flush=True)
        rows["stop"]=wait(phase("stop"),40,"STOP")
        report["stop"]=rows["stop"]
        report["goal_status_at_stop"]=2
        print("AXIA_G07_PUBLIC_CI_MOVING_STOP_REAL_GAZEBO_LIDAR_CM_PASS "+
              json.dumps(rows["stop"],sort_keys=True),flush=True)
        report["stop_post_ack_distinct_ros_scan_count"]=len(distinct_stop_scans)
        save()
        def dwell(s,d):
            if _fresh(s,("odom","guard","clock")) is None:return None
            # Only real consecutive /odom callbacks after the physical
            # native STOP ACK can prove a one-second stopped robot.
            value=post_stop_odom_zero_dwell(d["odom"],stop_ack_at)
            return value if value>=1.0 else None
        stop_dwell=wait(dwell,3.5,"ODOM_STOP_DWELL")
        final=obs.data()
        displacement=math.hypot(final["pose"][0]-start_pose[0],
                                final["pose"][1]-start_pose[1])
        latest=obs.snapshot(include_graph=False)
        t1=time.monotonic()
        if owner_mode or os.environ.get("AXIA_G07_TASK03_FORMAL_CI")=="1":
            if not owner_mode and os.environ.get("AXIA_G07_TASK02_SIMPLE_TF_CANDIDATE")!="1":
                raise RuntimeError("TASK03_PUBLIC_SIM_ONLY_CANDIDATE_REQUIRED")
            obs._write("task03_motion_window_end",at=t1)
            # The exact active Goal UUID is canceled immediately AFTER real
            # STOP and >=1s odom ZERO, BEFORE a diagnostic TTL oracle can
            # raise and skip cleanup. Retain the original strict TTL gate.
            report["goal_cancel_attempted"]=True
            save()
            task03_goal=_task03_exact_goal_terminal(node,obs,goal_uuid)
            report.update(goal_cancel_ack=True,goal_cancel_uuid=goal_uuid,
                          goal_cancel_status=5,
                          task03_exact_goal_terminal=task03_goal)
            save()
        # Complete read-only host-monotonic callback evidence through t1
        # before assessing required delivery intervals. Owner mode still
        # line-flushes every event; CI buffered evidence flushes once here.
        obs.flush_events()
        speed_data=obs.data()
        periods={}
        for key,entries in (("source",speed_data["vin"]),
                            ("cm",speed_data["pre"])):
            periods[key]=_period(entries,goal_sent_at,t1)
        gt=[x for x in guard_ticks if goal_sent_at<=x<=t1]
        periods["guard"]=max((b-a for a,b in zip(gt,gt[1:])),default=None)
        # Independently include actual LaserScan, odom and FSM message
        # interarrival, not just whether each single signal is live.
        # All timestamps come from the actual ROS Observer callback ledger.
        event_ticks={"scan":[],"odom":[],"supervisor":[],"clock":[]}
        for line in (args.output/"actual_ros_events.jsonl").read_text().splitlines():
            event=json.loads(line)
            kind=event.get("kind")
            t=event.get("t")
            if (kind in event_ticks and isinstance(t,(int,float))
                    and goal_sent_at<=t<=t1):
                event_ticks[kind].append(t)
        for kind,ts in event_ticks.items():
            periods[kind]=max((b-a for a,b in zip(ts,ts[1:])),default=None)
        if any(x is None for x in periods.values()):
            raise RuntimeError("REAL_CI_PUBLISHING_PERIODS_NOT_MEASURED")
        # Required acceptance intervals are unchanged. Persist the earliest
        # raw host-monotonic delivery gap for EACH safety channel, and the
        # FIRST system-wide boundary violation (not the last exception).
        timestamps={
            "source":[x["t"] for x in speed_data["vin"]],
            "cm":[x["t"] for x in speed_data["pre"]],
            "guard":gt,
            **event_ticks,
        }
        bounds={"source":.15,"cm":.15,"guard":.15,"supervisor":.15,
                "scan":.30,"odom":.30,"clock":.30}
        timing={kind:first_delivery_breach(
            ts,start=goal_sent_at,end=t1,limit=bounds[kind],
            stop_ack=stop_ack_at)
            for kind,ts in timestamps.items()}
        report["delivery_interval_diagnostics"]=timing
        violations=sorted(
            ({"channel":kind,"limit_sec":bounds[kind],**value}
             for kind,value in timing.items()
             if value["first_violation_sec"] is not None),
            key=lambda value:value["first_violation_at"])
        report["first_timing_violation"]=violations[0] if violations else None
        report["odom_stop_dwell_sec_observed_before_oracle"]=stop_dwell
        print("AXIA_G07_CI_ODOM_DWELL_PRE_ORACLE "
              +"seconds="+str(round(stop_dwell,6)),flush=True)
        print("AXIA_G07_CI_MEASURED_MESSAGE_PERIODS "+
              json.dumps(periods,sort_keys=True),flush=True)
        if violations:
            print("AXIA_G07_CI_FIRST_TIMING_VIOLATION "+
                  json.dumps(violations[0],sort_keys=True),flush=True)
        report.update(
            max_scan_interval_sec=periods["scan"],
            max_odom_interval_sec=periods["odom"],
            max_supervisor_fsm_interval_sec=periods["supervisor"],
            max_clock_interval_sec=periods["clock"])
        report.update(goal_status_executing=True,
                      guard_latched=latest["guard"].get("latched"),
                      real_gazebo_world=True,actual_physical_scan=True,
                      native_obstacle_set_pose_ack=True,
                      observed_odom_moved_m=displacement,
                      odom_stopped_dwell_sec=stop_dwell,
                      max_source_interval_sec=periods["source"],
                      max_cm_interval_sec=periods["cm"],
                      max_guard_interval_sec=periods["guard"])
        verdict=assess(report,owner_authorized=(owner_scope is not None))
        report["status"]=verdict["status"]
        report["reason"]=verdict["reason"]
        save()
        if verdict["status"]!="CI_GAZEBO_MOVING_GOAL_CANDIDATE":
            raise RuntimeError("ACTUAL_MOVING_GOAL_CI_ORACLE_"+verdict["reason"])
        # The educational MVP already proved physical CLEAR/SLOW/STOP and
        # >1s real odom ZERO. Cancel the one live Nav2 Goal now; the legacy
        # 15s post-STOP soak held it open until the Guard's real TTL latched.
        # Never change the Guard timeout or force-rearm its safe latch.
        if owner_observer_parity and report.get("slow_native_set_pose_ack") is True:
            print("AXIA_G07_MVP_POST_STOP_SOAK_SKIPPED_GOAL_CANCEL_FIRST",flush=True)
        if owner_observer_parity and report.get("slow_native_set_pose_ack") is not True:
            # The original Owner died 14.997s after startup, with 15s dump.
            # Keep this exact observer alive through the same boundary
            # AFTER validating real CLEAR/SLOW/STOP and the strict TTLs.
            until=observer_started_at+15.25
            while time.monotonic()<until:
                if not worker.is_alive():
                    raise RuntimeError("CI_OWNER_EXECUTOR_DEAD_BEFORE_15S")
                snap=obs.snapshot(include_graph=False)
                now=time.monotonic()
                if (not isinstance(snap.get("clock_at"),(float,int))
                    or now-snap["clock_at"]>.30
                    or not isinstance(snap.get("guard_at"),(float,int))
                    or now-snap["guard_at"]>.15):
                    raise RuntimeError("CI_OWNER_OBSERVER_STALE_BEFORE_15S")
                time.sleep(.05)
            report["owner_observer_parity_survived_15s"]=True
            print("AXIA_G07_CI_OWNER_OBSERVER_SURVIVED_15S "
                  "workers=2 buffered=true bounded_flush_sec=0.75 native_crash=false",
                  flush=True)
            save()
        if owner_mode:
            # CI safety verdict is reused verbatim, but never claim an
            # accepted Owner L3 or hardware E-Stop from one demo run.
            report["common_g07_ci_oracle_status"]=verdict["status"]
            report["status"]="NUMERICAL_CANDIDATE"
            report["reason"]="OWNER_G07_COMMON_SCENARIO_RAW_REVIEW_REQUIRED"
            report["shared_execution_mode"]="owner"
            save()
            print("P2_L3_G07_NUMERICAL_CANDIDATE "
                  "G07_COMMON_REAL_GAZEBO_CLEAR_SLOW_STOP_ODOM_PASS "
                  +"displacement_m="+str(round(displacement,4))
                  +" stopped_dwell_s="+str(round(stop_dwell,3))
                  +" max_interarrival="+json.dumps(periods,sort_keys=True)
                  +" OWNER_L3_RAW_REVIEW_REQUIRED CERTIFIED_ESTOP=false",
                  flush=True)
        else:
            print("AXIA_G07_PUBLIC_CI_MOVING_GOAL_CLEAR_SLOW_STOP_ODOM_PASS "
                  +"displacement_m="+str(round(displacement,4))
                  +" stopped_dwell_s="+str(round(stop_dwell,3))
                  +" max_interarrival="+json.dumps(periods,sort_keys=True)
                  +" OWNER_L3_NOT_RUN CERTIFIED_ESTOP=false",flush=True)
        return 0
    except Exception as exc:
        # Do not conceal the original failure with cleanup diagnostics.
        report["first_failure_preserved"]=type(exc).__name__+":"+str(exc)[:220]
        report["best_effort_cancel_attempted"]=False
        # If an authorized single Goal remains active, try its EXACT UUID
        # once. No synthetic ACK, new Goal, cmd_vel or safety rearm.
        if (report.get("goal_sent") is True
                and report.get("goal_cancel_attempted") is not True
                and report.get("goal_cancel_ack") is not True):
            live=obs.data()
            identifier=report.get("goal_uuid")
            status=(live.get("goals") or {}).get(identifier)
            guard_latched=(live.get("guard") or {}).get("latched")
            if (isinstance(identifier,str) and len(identifier)==32
                    and status==2 and guard_latched is False):
                report["best_effort_cancel_attempted"]=True
                report["goal_cancel_attempted"]=True
                save()
                try:
                    audit=_task03_exact_goal_terminal(node,obs,identifier)
                    report.update(goal_cancel_ack=True,goal_cancel_uuid=identifier,
                                  goal_cancel_status=5,
                                  best_effort_cancel_verified=True,
                                  task03_exact_goal_terminal=audit)
                    print("AXIA_G07_MVP_EXCEPTION_EXACT_UUID_CANCEL_VERIFIED",
                          flush=True)
                except Exception as cancel_exc:
                    report["best_effort_cancel_failure"]=(
                        type(cancel_exc).__name__+":"+str(cancel_exc)[:120])
                    print("AXIA_G07_MVP_EXCEPTION_EXACT_UUID_CANCEL_HOLD "+
                          type(cancel_exc).__name__,flush=True)
            else:
                report["best_effort_cancel_failure"]="NOT_ACTIVE_OR_SAFE_TO_CANCEL"
        # Preserve all callback records before classifying earliest real
        # Guard/CM/FSM timing failure; do not imply a buffered PASS.
        obs.flush_events()
        raw=obs.data()
        first=raw["guard"].get("first_latch_trace")
        report.update(status="BLOCKED",reason=type(exc).__name__+":"+str(exc)[:220],
                      first_guard_latch=first)
        # The full STOP oracle is never reached after an early Guard latch.
        # Preserve the FIRST real post-Goal sensor/CM-observer delivery
        # violation nonetheless; absence of STOP ACK remains explicit.
        # This is diagnostics only: it neither overrides a Guard latch nor
        # equates external /cmd_vel_pre_guard observation with Guard CM rx.
        if report.get("goal_sent") is True:
            try:
                until=(first.get("tick_monotonic")
                       if isinstance(first,dict) and
                       isinstance(first.get("tick_monotonic"),(float,int))
                       else time.monotonic())
                rows=[json.loads(line) for line in
                      (args.output/"actual_ros_events.jsonl").read_text().splitlines()]
                early=first_pre_latch_delivery_timing(
                    rows,goal_start=goal_sent_at,end=until)
                report["pre_latch_delivery_diagnostics"]=early
                if early["first_timing_violation"] is not None:
                    print("AXIA_G07_FIRST_POST_GOAL_TIMING_VIOLATION_BEFORE_LATCH "+
                          json.dumps(early["first_timing_violation"],
                                     sort_keys=True),flush=True)
                else:
                    print("AXIA_G07_EARLY_LATCH_TIMING_DIAGNOSTIC_NO_BREACH_IN_OBSERVER "+
                          "NOT_A_SAFETY_PASS",flush=True)
            except (OSError,ValueError,TypeError) as diag_exc:
                report["pre_latch_delivery_diagnostic_error"]=type(diag_exc).__name__
                print("AXIA_G07_PRE_LATCH_TIMING_DIAGNOSTIC_UNVERIFIED "+
                      type(diag_exc).__name__,flush=True)
        # Minimal privacy-safe first-latch telemetry; do not publish raw bags,
        # private source, complete process environment, or Goal authority.
        if isinstance(first,dict):
            # Independent Observer received a newer CM packet in the same
            # monotonic clock while Guard had no corresponding callback.
            # Report only timing metadata; never treat this as proof of a
            # healthy CM or override the 150ms fail-closed safety latch.
            skew=guard_cm_receive_skew(raw.get("pre",[]),first)
            report["cm_guard_receive_skew"]=skew
            print("AXIA_G07_PUBLIC_CI_FIRST_CM_GUARD_RECEIPT_SKEW "
                  +json.dumps(skew,sort_keys=True),flush=True)
            print("AXIA_G07_PUBLIC_CI_FIRST_GUARD_LATCH_INTERNAL "
                  +json.dumps(first,sort_keys=True),flush=True)
        # Supervisor publishes safety FSM state in the same 50ms tick as
        # /cmd_vel_supervised. Inspect actual OBSERVED FSM and Action events
        # relative to the first Guard latch; do not infer STOP cause from
        # the Twist ZERO value alone. Only safe fields enter public logs.
        try:
            latch_at=first.get("tick_monotonic") if isinstance(first,dict) else None
            entries=[]
            for line in (args.output/"actual_ros_events.jsonl").read_text().splitlines():
                item=json.loads(line)
                if item.get("kind") not in ("supervisor","action","guard"):
                    continue
                t=item.get("t")
                if not isinstance(t,(float,int)):
                    continue
                if latch_at is not None and not (latch_at-.40 <= t <= latch_at+.18):
                    continue
                row={"kind":item["kind"],"t":round(t,6)}
                if item["kind"]=="supervisor":
                    state=item.get("data",{})
                    row.update(state=state.get("state"),
                               reason=state.get("reason"),
                               stop_reason=state.get("stop_reason"),
                               healthy=all(state.get("health_diagnostics",{}).get(k)
                                   for k in ("clock_ok","scan_ok","graph_ok",
                                             "cm_lifecycle_ok","nav2_action_ready")))
                elif item["kind"]=="action":
                    row["status"]=item.get("status")
                elif item["kind"]=="guard":
                    row.update(reason=item.get("data",{}).get("reason"),
                               latched=item.get("data",{}).get("latched"))
                entries.append(row)
            print("AXIA_G07_PUBLIC_CI_PRE_LATCH_FSM_ACTION_TIMELINE "+
                  json.dumps(entries[-30:],sort_keys=True),flush=True)
        except (OSError,ValueError,TypeError) as diag_exc:
            print("AXIA_G07_PUBLIC_CI_FSM_TIMELINE_NOT_AVAILABLE "+
                  type(diag_exc).__name__,flush=True)
        for kind,rows in (("SUPERVISOR",raw.get("vin",[])),
                          ("ACTUAL_CM",raw.get("pre",[])),
                          ("FINAL",raw.get("cmd",[]))):
            compact=[{k:round(z[k],6) for k in ("t","vx","wz")}
                     for z in rows[-5:]]
            print("AXIA_G07_PUBLIC_CI_PRE_LATCH_"+kind+" "
                  +json.dumps(compact,sort_keys=True),flush=True)
        print(("P2_L3_G07_OWNER_COMMON_BLOCKED " if owner_mode
               else "AXIA_G07_PUBLIC_CI_MOVING_GOAL_BLOCKED ")+report["reason"],
              flush=True)
        return 2
    finally:
        save()
        spin_stop.set()
        executor.shutdown(timeout_sec=2)
        worker.join(timeout=2)
        heartbeat_stop.set()
        if probe_thread is not None:
            probe_thread.join(timeout=1.)
        node.destroy_subscription(extra)
        if io_probe:
            try:
                diag=obs.io_probe_summary(heartbeats=list(heartbeat_ticks))
                diag["first_executor_silence_snapshot"]=silence_probe.result()
                (args.output/"g07_observer_io_probe_summary.json").write_text(
                    json.dumps(diag,sort_keys=True,indent=2)+"\n")
                print("AXIA_G07_OBSERVER_IO_FIRST_BOUNDARY "+
                      json.dumps({k:diag.get(k) for k in (
                          "status","first_violation","correlated_channels",
                          "max_lock_wait_ms","max_json_ms","max_write_ms",
                          "max_flush_ms","heartbeat_max_gap_ms",
                          "root_cause_proven","release")},sort_keys=True),
                      flush=True)
            except (OSError,ValueError,TypeError) as probe_exc:
                print("AXIA_G07_OBSERVER_IO_CAPTURE_UNVERIFIED_HOLD "+
                      type(probe_exc).__name__,flush=True)
        obs.close()
        node.destroy_node()
        if parity_trace is not None:
            faulthandler.disable()
            parity_trace.close()
        rclpy.shutdown()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--startup",type=Path,required=True)
    p.add_argument("--pregoal",type=Path,required=True)
    p.add_argument("--source-sha",required=True)
    # Optional Owner CLI path; all PID/TTY/SHA admission stays in run().
    # Never turn on CI Goal authority to obtain this path in WSL2.
    p.add_argument("--owner-launch-pid",type=int)
    a=p.parse_args()
    try:return run(a)
    except Exception as exc:
        print("AXIA_G07_PUBLIC_CI_MOVING_GOAL_PRECHECK_BLOCKED "
              +type(exc).__name__+":"+str(exc),flush=True)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
