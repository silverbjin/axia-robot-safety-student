#!/usr/bin/env python3
"""D07 H01 classroom-only repeated *physical* obstacle -> official Nav2 Path.

Run ONLY after d07_h01_geometry_l2.py proved the initial real Waffle scan,
Gazebo set_pose, native Costmap, official ComputePathToPose, and RViz subscriber.
Keep the SAME Gazebo/official Nav2/RViz session alive. The robot NEVER drives.
No new navigation Controller implementation, no fake path or safety verdict.
A student Ctrl+C restores the cylinder and closes just the owned session.
"""
from __future__ import annotations
import argparse
from collections import deque
import json
import math
import os
from pathlib import Path
import signal
import threading
import time


def parse_cycle_limit(text):
    """0 = until Ctrl+C; 1..12 bounded for public real Gazebo CI only."""
    if type(text) is not str or not text or not text.isascii() or not text.isdecimal():
        raise ValueError("H01_CLASSROOM_CYCLE_LIMIT_INVALID")
    value=int(text)
    if value>12:
        raise ValueError("H01_CLASSROOM_CYCLE_LIMIT_INVALID")
    return value


def load_verified_h01(geometry, paths, phases, source_sha):
    """Fail-closed: a static or synthetic fixture cannot open the live loop."""
    if not (isinstance(geometry,dict) and geometry.get("source_sha")==source_sha
            and geometry.get("real_nav2") is True
            and geometry.get("real_laser_scan") is True
            and geometry.get("actual_costmap_obstacle_observed") is True
            and geometry.get("obstacle_restored_away") is True
            and geometry.get("goal_sent") is False
            and geometry.get("path_changed") is True
            and geometry.get("status") in (
                "D07_H01_REAL_NAV2_GEOMETRY_READY_NO_GOAL",
                "D07_H01_REAL_NAV2_GEOMETRY_CONTACT_HOLD_NO_GOAL")):
        raise ValueError("H01_CLASSROOM_REAL_GEOMETRY_PROVENANCE_REQUIRED")
    if not (isinstance(paths,dict)
            and paths.get("source_sha")==source_sha
            and isinstance(paths.get("before"),dict)
            and len(paths["before"].get("poses",[]))>=3
            and isinstance(paths["before"].get("start"),list)):
        raise ValueError("H01_CLASSROOM_ORIGINAL_OFFICIAL_ROUTE_REQUIRED")
    stage_set={x.get("stage") for x in phases if isinstance(x,dict)
               and x.get("source")=="official_compute_path_to_pose"
               and x.get("rviz_subscription_count",0)>=1}
    if not {"before","intrusion","restored"}<=stage_set:
        raise ValueError("H01_CLASSROOM_ACTUAL_RVIZ_THREE_PHASES_REQUIRED")
    candidate=geometry.get("intrusion_candidate")
    if not isinstance(candidate,dict):
        raise ValueError("H01_CLASSROOM_NATIVE_WORLD_CANDIDATE_REQUIRED")
    for field in ("world_xy","map_xy"):
        xy=candidate.get(field)
        if not (isinstance(xy,list) and len(xy)==2
                and all(type(v) in (int,float) and math.isfinite(v) for v in xy)):
            raise ValueError("H01_CLASSROOM_NATIVE_WORLD_CANDIDATE_INVALID")
    if not (type(candidate.get("bearing_rad")) in (int,float)
            and math.isfinite(candidate["bearing_rad"])):
        raise ValueError("H01_CLASSROOM_BEARING_NOT_VERIFIED")
    return candidate


class UserStop(Exception):
    pass


def run(args):
    if os.environ.get("ROS_DISTRO")!="jazzy" or os.environ.get("AXIA_P0_SIM_ONLY")!="1":
        raise ValueError("H01_CLASSROOM_JAZZY_SIM_ONLY_REQUIRED")
    if os.environ.get("AXIA_D07_H01_GUI_NO_GOAL")!="1" or (
            os.environ.get("AXIA_G07_CI_SIM_GOAL_ALLOWED")!="0"):
        raise ValueError("H01_CLASSROOM_MOVING_GOAL_NOT_AUTHORIZED")
    if not os.environ.get("GZ_PARTITION","").startswith("axia_p2_"):
        raise ValueError("H01_CLASSROOM_GAZEBO_PARTITION_INVALID")
    if not 5<=args.hold_sec<=15:
        raise ValueError("H01_CLASSROOM_HOLD_INVALID")
    source_sha=args.source_sha
    if len(source_sha)!=40 or any(ch not in "0123456789abcdef" for ch in source_sha):
        raise ValueError("H01_CLASSROOM_SOURCE_SHA_INVALID")
    geometry=json.loads((args.output/"d07_h01_geometry.json").read_text())
    paths=json.loads((args.output/"d07_h01_before_after_actual_nav2_paths.json").read_text())
    phases=[json.loads(x) for x in (args.output/"phase_evidence.jsonl").read_text().splitlines() if x.strip()]
    candidate=load_verified_h01(geometry,paths,phases,source_sha)
    # Reuse only the already demonstrated exact physical route-world location.
    # The second location is the original verified parked-away world coordinate.
    from p2_l3_gz_fixture import move, _valid_xy, RADIUS
    from p2_g07_demo_corridor import DEMO_START
    from p2_g07_relocated_no_goal_probe import sector_min
    from d07_h01_oracle import path_distance
    from d07_h01_geometry_l2 import _lethal_near
    intrude_xy=tuple(candidate["world_xy"])
    away_xy=(round(DEMO_START[0]+1.35+RADIUS,2),DEMO_START[1])
    _valid_xy(*intrude_xy,demo_corridor=True)
    _valid_xy(*away_xy)
    origin=tuple(paths["before"]["start"])
    obstacle_map=tuple(candidate["map_xy"])
    bearing=float(candidate["bearing_rad"])
    expected=float(candidate["robot_distance_m"])-RADIUS
    if not .3<=expected<=2.5:
        raise ValueError("H01_CLASSROOM_PHYSICAL_DISTANCE_INVALID")

    import rclpy
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.action import ActionClient
    from rclpy.qos import qos_profile_sensor_data,QoSProfile,DurabilityPolicy,ReliabilityPolicy
    from sensor_msgs.msg import LaserScan
    from nav_msgs.msg import OccupancyGrid,Odometry,Path as NavPath
    from nav2_msgs.action import ComputePathToPose
    from action_msgs.msg import GoalStatus
    from geometry_msgs.msg import PoseStamped

    stopping=threading.Event()
    def sigint(signum, frame):
        stopping.set()
        print("D07_H01_CLASSROOM_CTRL_C_REQUESTED RESTORE_THEN_STOP NO_GOAL",
              flush=True)
    previous_sigint=signal.signal(signal.SIGINT,sigint)
    started=False
    intruded=False
    executor=None
    thread=None
    node=None
    ledger=args.output/"classroom_replan_cycles.jsonl"
    marker=args.output/"classroom_loop.ready"
    completed=0
    lock=threading.Lock()
    scans=deque(maxlen=100)
    grids=deque(maxlen=30)
    odom=deque(maxlen=30)

    def stamp(msg):
        return float(msg.header.stamp.sec)+float(msg.header.stamp.nanosec)*1e-9
    def on_scan(msg):
        value=sector_min(msg,bearing=bearing)
        with lock:
            scans.append((time.monotonic(),stamp(msg),value))
    def on_grid(msg):
        near=_lethal_near(msg,obstacle_map)
        with lock:
            grids.append((time.monotonic(),stamp(msg),near))
    def on_odom(msg):
        with lock:
            odom.append((time.monotonic(),
                         float(msg.twist.twist.linear.x),
                         float(msg.twist.twist.angular.z)))
    def snapshot():
        with lock:
            return list(scans),list(grids),list(odom)
    def require_live():
        if stopping.is_set():
            raise UserStop()
    def wait_for(predicate,code,seconds=18):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            require_live()
            found=predicate()
            if found is not None and found is not False:
                return found
            stopping.wait(.1)
        raise RuntimeError("H01_CLASSROOM_"+code+"_FIRST_REAL_BOUNDARY")
    def actual_odom_stopped():
        _,_,rows=snapshot()
        return bool(rows and time.monotonic()-rows[-1][0]<1.0
                    and abs(rows[-1][1])<=.01
                    and abs(rows[-1][2])<=.05)
    def compute():
        require_live()
        if not action.wait_for_server(timeout_sec=6.0):
            raise RuntimeError("H01_CLASSROOM_OFFICIAL_PLANNER_UNAVAILABLE")
        goal=ComputePathToPose.Goal()
        def pose(xy):
            p=PoseStamped()
            p.header.frame_id="map"
            p.header.stamp=node.get_clock().now().to_msg()
            p.pose.position.x=float(xy[0]);p.pose.position.y=float(xy[1])
            p.pose.orientation.w=1.0
            return p
        goal.start=pose(origin)
        goal.goal=pose(paths["before"]["goal"])
        goal.use_start=True
        goal.planner_id="GridBased"
        sent=action.send_goal_async(goal)
        wait_for(lambda:sent.done(),"ACTION_SEND_TIMEOUT",15)
        handle=sent.result()
        if handle is None or not handle.accepted:
            raise RuntimeError("H01_CLASSROOM_OFFICIAL_ACTION_REJECTED")
        done=handle.get_result_async()
        wait_for(lambda:done.done(),"ACTION_RESULT_TIMEOUT",15)
        reply=done.result()
        if reply is None or reply.status!=GoalStatus.STATUS_SUCCEEDED:
            raise RuntimeError("H01_CLASSROOM_OFFICIAL_ACTION_NOT_SUCCEEDED")
        path=reply.result.path
        if path.header.frame_id!="map" or len(path.poses)<3:
            raise RuntimeError("H01_CLASSROOM_OFFICIAL_PATH_INVALID")
        return path
    def poses(path):
        return [[float(p.pose.position.x),float(p.pose.position.y)]
                for p in path.poses]
    def publish(path,cycle,stage,laser,grid):
        require_live()
        wait_for(lambda:vis.get_subscription_count()>=1,
                 "RVIZ_REAL_PATH_SUBSCRIPTION_ABSENT",20)
        vis.publish(path)  # EXACT official Action result, not reconstructed Path.
        data={"cycle":cycle,"stage":stage,"source":"official_compute_path_to_pose",
              "source_sha":source_sha,"goal_sent":False,"robot_moved":False,
              "rviz_subscription_count":int(vis.get_subscription_count()),
              "pose_count":len(path.poses),"frame":path.header.frame_id,
              "real_scan_stamp":laser,"real_costmap_stamp":grid,
              "native_physical_world_xy":list(intrude_xy if stage=="intrusion" else away_xy),
              "genuine_gazebo_simulation":True,
              "certified_estop":False,"verification":"H01_CLASSROOM_NO_GOAL_ONLY"}
        with ledger.open("a",encoding="utf-8") as f:
            f.write(json.dumps(data,sort_keys=True)+"\n")
        print("D07_H01_CLASSROOM_REAL_PLAN "+
              json.dumps(data,sort_keys=True),flush=True)
        stopping.wait(args.hold_sec)
        return data

    try:
        rclpy.init()
        started=True
        node=Node("axia_d07_h01_classroom_planner_no_goal",
                  parameter_overrides=[Parameter("use_sim_time",value=True)],
                  automatically_declare_parameters_from_overrides=True)
        node.create_subscription(LaserScan,"/scan",on_scan,qos_profile_sensor_data)
        node.create_subscription(OccupancyGrid,"/global_costmap/costmap",on_grid,
             QoSProfile(depth=4,reliability=ReliabilityPolicy.RELIABLE,
                        durability=DurabilityPolicy.TRANSIENT_LOCAL))
        node.create_subscription(Odometry,"/odom",on_odom,qos_profile_sensor_data)
        action=ActionClient(node,ComputePathToPose,"/compute_path_to_pose")
        vis=node.create_publisher(NavPath,"/axia/d07/h01/path_visual",
            QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL))
        executor=MultiThreadedExecutor(num_threads=2)
        executor.add_node(node)
        thread=threading.Thread(target=executor.spin,daemon=True)
        thread.start()
        wait_for(lambda:len(snapshot()[0])>=2 and len(snapshot()[1])>=1,
                 "REAL_SENSOR_GRAPH_ABSENT",18)
        wait_for(lambda:actual_odom_stopped(),
                 "ACTUAL_WAFFLE_ODOM_NOT_STOPPED",12)
        wait_for(lambda:vis.get_subscription_count()>=1,
                 "RVIZ_REAL_PATH_SUBSCRIPTION_ABSENT",20)
        marker.write_text(source_sha+"\n")
        print("D07_H01_CLASSROOM_LOOP_READY SAME_GAZEBO_NAV2_RVIZ "+
              "CTRL_C_TO_STOP NO_GOAL",flush=True)

        cycle=0
        while args.max_cycles==0 or cycle<args.max_cycles:
            require_live()
            cycle+=1
            # The previous, fully verified H01 restored the cylinder AWAY.
            s0,g0,_=snapshot()
            if not g0 or g0[-1][2] is None:
                raise RuntimeError("H01_CLASSROOM_REAL_COSTMAP_BASELINE_UNKNOWN")
            baseline=g0[-1][2]
            before=compute()
            record_before=publish(before,cycle,"before",s0[-1][1],g0[-1][1])
            require_live()
            if not actual_odom_stopped():
                raise RuntimeError("H01_CLASSROOM_WAFFLE_MOVED_BEFORE_INTRUSION")
            move(*intrude_xy,demo_corridor=True)
            intruded=True
            t_in=time.monotonic()
            observed=wait_for(lambda:next(
                ((t,st,val) for t,st,val in reversed(snapshot()[0])
                 if t>t_in and val is not None and abs(val-expected)<=.16),
                None),"GAZEBO_NEW_RAW_SCAN_NOT_PROVEN",18)
            marked=wait_for(lambda:next(
                ((t,st,num) for t,st,num in reversed(snapshot()[1])
                 if t>t_in and num is not None and num>=baseline+3),
                None),"NAV2_COSTMAP_MARKING_NOT_PROVEN",20)
            detour=compute()
            detour_distance=round(
                path_distance(obstacle_map,poses(detour))-
                path_distance(obstacle_map,poses(before)),6)
            if detour_distance<.15:
                raise RuntimeError("H01_CLASSROOM_REAL_PATH_DETOUR_NOT_PROVEN")
            record_in=publish(detour,cycle,"intrusion",observed[1],marked[1])
            require_live()
            move(*away_xy)
            intruded=False
            t_away=time.monotonic()
            cleared_scan=wait_for(lambda:next(
                ((t,st,val) for t,st,val in reversed(snapshot()[0])
                 if t>t_away and st>observed[1]
                 and val is not None and val>expected+.15),
                None),"GAZEBO_REAL_SCAN_CLEAR_NOT_PROVEN",18)
            cleared_grid=wait_for(lambda:next(
                ((t,st,num) for t,st,num in reversed(snapshot()[1])
                 if t>t_away and num is not None and num<=baseline),
                None),"NAV2_COSTMAP_CLEAR_NOT_PROVEN",24)
            # Same real native planner may publish delayed updates after
            # Costmap topic; allow at most 5 bounded *read-only* queries.
            restored=None; restore_delta=None
            for attempt in range(5):
                require_live()
                candidate_clear=compute()
                restore_delta=round(abs(
                    path_distance(obstacle_map,poses(candidate_clear))-
                    path_distance(obstacle_map,poses(before))),6)
                if restore_delta<=.12:
                    restored=candidate_clear
                    break
                stopping.wait(.7)
            if restored is None:
                raise RuntimeError("H01_CLASSROOM_OFFICIAL_RETURN_PATH_NOT_RESTORED")
            record_out=publish(restored,cycle,"restored",
                               cleared_scan[1],cleared_grid[1])
            if not actual_odom_stopped():
                raise RuntimeError("H01_CLASSROOM_WAFFLE_MOVED_AFTER_REPLAN")
            completed+=1
            print("D07_H01_CLASSROOM_CYCLE_PASS "+
                  json.dumps({"cycle":cycle,"path_detour_m":detour_distance,
                              "path_restore_delta_m":restore_delta,
                              "rviz_subscribers":[record_before["rviz_subscription_count"],
                                                  record_in["rviz_subscription_count"],
                                                  record_out["rviz_subscription_count"]],
                              "goal_sent":False,"robot_moved":False,
                              "source_sha":source_sha},sort_keys=True),flush=True)
        print(f"D07_H01_CLASSROOM_BOUNDED_CI_CYCLES_PASS count={completed} NO_GOAL",
              flush=True)
    except UserStop:
        print(f"D07_H01_CLASSROOM_USER_CTRL_C_STOPPED count={completed} NO_GOAL",
              flush=True)
    finally:
        # Always restore the physical model before shutting down the ROS graph.
        # Retain original H01 Guard/Collision Monitor in the owned launch until
        # parent p2_no_goal_smoke_ci.sh performs the existing lifecycle cleanup.
        if intruded:
            try:
                move(*away_xy)
                print("D07_H01_CLASSROOM_INTERRUPT_MODEL_RESTORED_NO_GOAL",
                      flush=True)
            except Exception as e:
                print("D07_H01_CLASSROOM_RESTORE_NOT_PROVEN "+
                      type(e).__name__,flush=True)
                raise
        if executor is not None:
            stopped=executor.shutdown(timeout_sec=8.0)
            if thread is not None:
                thread.join(timeout=8.0)
            if not stopped or (thread is not None and thread.is_alive()):
                raise RuntimeError("H01_CLASSROOM_EXECUTOR_NOT_QUIESCENT")
        if node is not None:
            node.destroy_node()
        if started:
            rclpy.shutdown()
        signal.signal(signal.SIGINT,previous_sigint)
        print("D07_H01_CLASSROOM_ROS_CONTEXT_CLEAN_EXIT NO_GOAL",flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--source-sha",required=True)
    parser.add_argument("--max-cycles",type=parse_cycle_limit,default=0)
    parser.add_argument("--hold-sec",type=int,default=6)
    args=parser.parse_args()
    try:
        run(args)
        return 0
    except Exception as e:
        print("D07_H01_CLASSROOM_FIRST_FAILURE "+
              type(e).__name__+":"+str(e),flush=True)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
