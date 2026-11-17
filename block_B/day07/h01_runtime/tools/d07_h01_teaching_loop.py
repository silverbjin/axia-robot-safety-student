#!/usr/bin/env python3
"""D07-H01 classroom-only infinite physical obstacle/official Planner loop.

Run *after* the original three-phase H01 real-L2 proof, with the SAME live
Gazebo/Nav2/RViz processes. No NavigateToPose, no cmd_vel, no real E-Stop.
Never converts an educational planner result into motion authorization.
Ctrl+C (SIGINT) or SIGTERM restores the simulator obstacle and stops this node.
A single bounded cycle is permissible only in public GitHub Actions.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import signal
import sys
import threading
import time


def shutdown_rclpy_once(rclpy):
    """Avoid SIGINT double-shutdown after ROS signal handlers close context.

    Owner WSL2 L3 2026-11-17: ROS context was already invalid at teardown.
    This only protects the final lifecycle call; the executor must still
    quiesce first and any active-context shutdown error must still surface.
    """
    if not rclpy.ok():
        return False
    rclpy.shutdown()
    return True


def teaching_positions(intrusion, away):
    """Four positions; only the original approved G07 physical corridor."""
    from p2_l3_gz_fixture import _valid_xy
    if len(intrusion) != 2 or len(away) != 2:
        raise ValueError("H01_TEACHING_XY_SHAPE_INVALID")
    x,y=map(float,intrusion)
    a,b=map(float,away)
    _valid_xy(x,y,demo_corridor=True)
    _valid_xy(a,b,demo_corridor=False)
    lateral_y=y+.12 if y+.12<=1.55 else y-.12
    _valid_xy(x,lateral_y,demo_corridor=True)
    return [("free",a,b),("intrusion",x,y),
            ("lateral",x,lateral_y),("restored",a,b)]


def admit(evidence, source_sha, max_cycles, environment):
    """Fail-closed pure admission; no unverified safety or Goal escalation."""
    if (evidence.get("source_sha")!=source_sha
            or evidence.get("goal_sent") is not False
            or evidence.get("real_nav2") is not True
            or evidence.get("real_laser_scan") is not True
            or evidence.get("actual_costmap_obstacle_observed") is not True
            or evidence.get("obstacle_restored_away") is not True
            or evidence.get("path_changed") is not True
            or evidence.get("certified_estop") is not False):
        raise ValueError("H01_TEACHING_ORIGINAL_PHYSICAL_BASELINE_NOT_PROVEN")
    if environment.get("AXIA_G07_CI_SIM_GOAL_ALLOWED")!="0":
        raise ValueError("H01_TEACHING_MOVING_GOAL_DENIED")
    if environment.get("AXIA_D07_H01_TEACHING_LOOP")!="1":
        raise ValueError("H01_TEACHING_SCOPE_ABSENT")
    if max_cycles!=0 and (max_cycles!=1 or environment.get("GITHUB_ACTIONS")!="true"):
        raise ValueError("H01_TEACHING_BOUNDED_CYCLE_CI_ONLY")
    return True


def _stamp(header):
    return float(header.stamp.sec)+float(header.stamp.nanosec)*1e-9


def run(args):
    from p2_l3_gz_fixture import move, RADIUS
    from p2_g07_demo_corridor import DEMO_START
    from d07_h01_geometry_l2 import _compute
    import rclpy
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.qos import (qos_profile_sensor_data,QoSProfile,
                            ReliabilityPolicy,DurabilityPolicy)
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.action import ActionClient
    from sensor_msgs.msg import LaserScan
    from nav_msgs.msg import OccupancyGrid,Path as NavPath,Odometry
    from nav2_msgs.action import ComputePathToPose

    raw=json.loads((args.evidence/"d07_h01_geometry.json").read_text())
    original=json.loads((args.evidence/"d07_h01_before_after_actual_nav2_paths.json").read_text())
    if not admit(raw,args.source_sha,args.max_cycles,os.environ):
        raise RuntimeError("H01_TEACHING_ADMISSION_FAILED")
    p=raw.get("intrusion_candidate",{})
    before=original.get("before",{})
    start=before.get("start")
    if (not isinstance(start,list) or len(start)!=2
            or any(type(v) not in (int,float) or not math.isfinite(v) for v in start)):
        raise RuntimeError("H01_TEACHING_REAL_MAP_START_NOT_VERIFIED")
    away=(round(DEMO_START[0]+1.35+RADIUS,2),DEMO_START[1])
    positions=teaching_positions(p["world_xy"],away)
    stop=threading.Event()
    def on_signal(_signum,_frame):
        stop.set()
        print("D07_H01_TEACHING_CTRL_C_STOP REQUESTED",flush=True)
    signal.signal(signal.SIGINT,on_signal)
    signal.signal(signal.SIGTERM,on_signal)
    rows=args.evidence/"teaching_cycle_evidence.jsonl"

    rclpy.init()
    node=Node("axia_d07_h01_rqt_teaching_planner_no_goal",
              parameter_overrides=[Parameter("use_sim_time",value=True)],
              automatically_declare_parameters_from_overrides=True)
    lock=threading.Lock()
    latest={"scan":(0.,0.),"map":(0.,0.),"odom":(0.,None)}
    def scan_cb(msg):
        st=_stamp(msg.header)
        with lock: latest["scan"]=(time.monotonic(),st)
    def map_cb(msg):
        st=_stamp(msg.header)
        with lock: latest["map"]=(time.monotonic(),st)
    def odom_cb(msg):
        with lock: latest["odom"]=(time.monotonic(),float(msg.twist.twist.linear.x))
    subs=[
        node.create_subscription(LaserScan,"/scan",scan_cb,qos_profile_sensor_data),
        node.create_subscription(OccupancyGrid,"/global_costmap/costmap",map_cb,
            QoSProfile(depth=4,reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL)),
        node.create_subscription(Odometry,"/odom",odom_cb,qos_profile_sensor_data),
    ]
    pub=node.create_publisher(
        NavPath,"/axia/d07/h01/path_visual",
        QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,
                   durability=DurabilityPolicy.TRANSIENT_LOCAL))
    client=ActionClient(node,ComputePathToPose,"/compute_path_to_pose")
    executor=MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    th=threading.Thread(target=executor.spin,daemon=True)
    th.start()
    cycle=0
    print("D07_H01_TEACHING_LIVE_REPEAT_STARTED NO_GOAL CTRL_C_TO_STOP "
          "RQT_GRAPH_REFRESH_AFTER_START",flush=True)
    try:
        while not stop.is_set():
            cycle+=1
            for stage,x,y in positions:
                if stop.is_set():break
                # Native Gazebo ACK is REQUIRED. Do not publish synthetic scans.
                move(x,y,demo_corridor=(stage not in ("free","restored")))
                moved=time.monotonic()
                deadline=moved+18.
                fresh=None
                while time.monotonic()<deadline and not stop.is_set():
                    with lock: snap=dict(latest)
                    if (snap["scan"][0]>moved and snap["map"][0]>moved
                            and snap["scan"][1]>0 and snap["map"][1]>0
                            and snap["odom"][0]>0 and snap["odom"][1] is not None):
                        fresh=snap;break
                    time.sleep(.12)
                if stop.is_set():break
                if fresh is None:
                    raise RuntimeError("H01_TEACHING_FRESH_PHYSICAL_SCAN_COSTMAP_TIMEOUT")
                if abs(fresh["odom"][1])>.01:
                    raise RuntimeError("H01_TEACHING_ODOM_STATIONARY_CONTRACT_VIOLATION")
                originals={}
                path=_compute(node,client,start,originals)
                ros_path=originals[id(path)]
                if ros_path.header.frame_id!="map" or len(ros_path.poses)<3:
                    raise RuntimeError("H01_TEACHING_OFFICIAL_MAP_PATH_INVALID")
                deadline=time.monotonic()+12
                while pub.get_subscription_count()<1 and time.monotonic()<deadline:
                    if stop.is_set():break
                    time.sleep(.15)
                if stop.is_set():break
                if pub.get_subscription_count()<1:
                    raise RuntimeError("H01_TEACHING_RVIZ_PATH_SUBSCRIBER_MISSING")
                pub.publish(ros_path)
                data={
                    "schema":"d07_h01_classroom_repeated_official_nav2_v1",
                    "cycle":cycle,"stage":stage,
                    "world_xy":[x,y],"real_native_gazebo_pose_ack":True,
                    "real_scan_stamp":fresh["scan"][1],
                    "real_costmap_stamp":fresh["map"][1],
                    "path_pose_count":len(ros_path.poses),
                    "path_header_stamp":_stamp(ros_path.header),
                    "path_frame":ros_path.header.frame_id,
                    "official_action":"ComputePathToPose",
                    "rviz_path_subscribers":pub.get_subscription_count(),
                    "goal_sent":False,"cmd_vel_sent":False,
                    "robot_moved":False,"certified_estop":False,
                    "formal_axia_mvp_accepted":False}
                with rows.open("a",encoding="utf-8") as fp:
                    fp.write(json.dumps(data,sort_keys=True)+"\n")
                print("D07_H01_TEACHING_CYCLE "+json.dumps(data,sort_keys=True),
                      flush=True)
                # Explanation time for rqt_graph filters and RViz Path.
                deadline=time.monotonic()+args.hold_s
                while time.monotonic()<deadline and not stop.is_set():
                    time.sleep(.15)
            if args.max_cycles==1 and cycle>=1:break
        print("D07_H01_TEACHING_CTRL_C_STOP "+
              ("OPERATOR" if stop.is_set() else "PUBLIC_CI_BOUNDED_CYCLE"),
              flush=True)
        return 0
    finally:
        # Restore physical cylinder first; only this session's own ROS
        # executor is joined before any rclpy object is destroyed.
        try:
            move(*away)
            print("D07_H01_TEACHING_OBSTACLE_RESTORED_AWAY",flush=True)
        except Exception as exc:
            print("D07_H01_TEACHING_RESTORE_FAILED "+str(exc),flush=True)
            raise
        stopped=executor.shutdown(timeout_sec=8.)
        th.join(timeout=8.)
        if not stopped or th.is_alive():
            raise RuntimeError("D07_H01_TEACHING_EXECUTOR_NOT_QUIESCENT")
        for sub in subs:node.destroy_subscription(sub)
        node.destroy_publisher(pub)
        node.destroy_node()
        shutdown_rclpy_once(rclpy)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",required=True,type=Path)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--hold-s",type=int,default=8)
    p.add_argument("--max-cycles",type=int,default=0)
    a=p.parse_args()
    if not (5<=a.hold_s<=15 and a.max_cycles in (0,1)):
        raise SystemExit("D07_H01_TEACHING_BOUNDED_PARAMS_INVALID")
    try:return run(a)
    except Exception as exc:
        print("D07_H01_TEACHING_BLOCKED_FIRST_BOUNDARY "+
              type(exc).__name__+":"+str(exc),flush=True)
        return 2


if __name__=="__main__":
    sys.exit(main())
