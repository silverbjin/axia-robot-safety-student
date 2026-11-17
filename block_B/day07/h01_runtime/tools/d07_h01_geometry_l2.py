#!/usr/bin/env python3
"""D07-H01 REAL ROS/Gazebo pre-Goal geometry admission; never publishes a Goal.

Use the official P1/P2/P3 Waffle and Nav2 from existing G07 setup.
Temporarily relocate the existing cylinder with Gazebo native set_pose while
the Waffle is STATIONARY; query official ComputePathToPose before/after;
require real new LaserScan stamps and global Costmap obstacle marking.
Restore obstacle away and verify clearing BEFORE any teaching motion attempt.
No Controller commands or direct cmd_vel publisher. Simulation only.
"""
from __future__ import annotations
import argparse
from collections import deque
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from d07_h01_oracle import (GOAL, route_evidence, path_distance, select_route_intrusion,
                            costmap_roundtrip_evidence, baseline_path_restoration,
                            costmap_spatial_diff)
from d07_h01_costmap_drift import (assess_spatial_drift, assess_roi_clearing,
                                     select_fresh_baselines,
                                     trace_post_restore_lethal_history,
                                     classify_readonly_roi_path_probe)
from d07_h01_path_cost_correlation import correlate_official_path_cost
from d07_h01_nav2_clear_config import (NAMES as NAV2_OBSTACLE_NAMES,
                                        assess_live_obstacle_clear_config)
from d07_h01_native_costmap_layers import (audit_native_layer_costs,
                                            compare_native_layer_roundtrip,
                                            prioritize_native_layer_suspects)
from d07_h01_amcl_pre_goal import retry_actual_amcl_map_pose
from d07_h01_free_planner_repeat import (
    classify_two_free_official_paths, choose_bounded_free_official_pair)
from d07_h01_nav2_scan_source import assess_real_nav2_scan_delivery
from d07_h01_free_grid_timing_probe import assess_preintrusion_timing
from d07_h01_native_corridor_return import audit_native_master_path_corridor
from d07_h01_native_master_full_evidence import (
    compare_full_native_master,assess_full_published_native_barrier)
from d07_h01_native_topic_catchup import assess_native_topic_catchup
from d07_h01_preintrusion_baseline import (
    assess_two_real_free_grid_baselines,choose_bounded_stable_free_baselines)
from d07_h01_post_free_plan_epoch import assess_post_free_path_epoch
from p2_g07_demo_corridor import DEMO_START
from p2_g07_relocated_no_goal_probe import DEMO_WORLD_POSE, sector_min
from p2_g07_spawn_contract import official_tb3_spawn
from p2_l3_coordinate_frames import make_frame_anchor
from p2_l3_gz_fixture import RADIUS, move
from d07_h01_contact_probe import NATIVE_CONTACT_TOPIC, discover_contact_advertisement
from p2_l3_live_session import Observer, _map_robot_pose
from d07_h01_path_visual import (admit_gui_simulation, publish_official_path)



def _native_gz_contact_advertisement(output_dir):
    """Harmonic native source metadata ONLY; never claim calibrated zero contact.

    Real stationary calibration L2 #43585633188 observed Gazebo publishing
    gz.msgs.Contacts at the fully qualified sensor path, NOT its SDF-requested
    /axia_p2_g07/contacts alias. Use exactly the verified source here.
    """
    def gz_probe(args, logname):
        cmd=["gz",*args]
        result=subprocess.run(cmd,text=True,capture_output=True,timeout=8,
                              check=False)
        data=result.stdout+"\n"+result.stderr
        (output_dir/logname).write_text(data,encoding="utf-8")
        if result.returncode!=0:
            raise RuntimeError("NATIVE_CONTACT_METADATA_GZ_CLI_NONZERO")
        return data
    listing=gz_probe(["topic","-l"],"native_contact_topic_list.log")
    metadata=gz_probe(["topic","-i","-t",NATIVE_CONTACT_TOPIC],
                      "native_contact_topic_info.log")
    result=discover_contact_advertisement(listing,metadata)
    (output_dir/"g07_contact_topic_probe.json").write_text(
        json.dumps({**result,"contact_topic":NATIVE_CONTACT_TOPIC,
                    "other_contact_topics":[t for t in listing.splitlines()
                                            if "contact" in t.lower()],
                    "contact_ground_truth_ready":False,
                    "positive_control_proven":False,
                    "goal_sent":False},sort_keys=True,indent=2)+"\n",
        encoding="utf-8")
    return result


def _live_nav2_obstacle_config(node):
    """Single bounded ROS read from the actual running official Nav2 node.

    ROS Jazzy may return an empty value array when ANY requested parameter
    is absent. List first, verify names, then Get only that exact complete
    list; unknown is HOLD. No parameter writes and NO nav Goal.
    """
    from rcl_interfaces.srv import ListParameters,GetParameters
    from rcl_interfaces.msg import ParameterType
    hold={"status":"OBSTACLE_LAYER_PARAMETER_PROVENANCE_HOLD",
          "reason":"LIVE_NAV2_PARAMETER_SERVICES_NOT_VERIFIED",
          "motion_admitted":False,"goal_sent":False,
          "obstacle_cell_clearing_proven":False}
    list_service="/global_costmap/global_costmap/list_parameters"
    get_service="/global_costmap/global_costmap/get_parameters"
    lc=node.create_client(ListParameters,list_service)
    gc=node.create_client(GetParameters,get_service)
    def response(client,req):
        if not client.wait_for_service(timeout_sec=4.):
            return None
        future=client.call_async(req)
        until=time.monotonic()+5.
        while not future.done() and time.monotonic()<until:
            time.sleep(.05)
        if not future.done() or future.exception() is not None:
            return None
        return future.result()
    try:
        listing=ListParameters.Request()
        listing.prefixes=["obstacle_layer"]
        listing.depth=0
        lr=response(lc,listing)
        if lr is None or not set(NAV2_OBSTACLE_NAMES).issubset(
                set(lr.result.names)):
            return {**hold,"reason":"EXACT_OBSTACLE_LAYER_PARAMETER_NAMES_MISSING",
                    "advertised_obstacle_parameter_names":(
                        sorted(lr.result.names)[:24] if lr is not None else [])}
        req=GetParameters.Request()
        req.names=list(NAV2_OBSTACLE_NAMES)
        gr=response(gc,req)
        if gr is None or len(gr.values)!=len(req.names):
            return {**hold,"reason":"JAZZY_GET_PARAMETERS_EMPTY_OR_INCOMPLETE"}
        decoded={}
        for name,value in zip(req.names,gr.values):
            if value.type==ParameterType.PARAMETER_BOOL:
                data=bool(value.bool_value)
            elif value.type==ParameterType.PARAMETER_DOUBLE:
                data=float(value.double_value)
            elif value.type==ParameterType.PARAMETER_STRING:
                data=str(value.string_value)
            else:
                return {**hold,"reason":"UNEXPECTED_EFFECTIVE_PARAMETER_TYPE",
                        "first_invalid_parameter":name}
            decoded[name]=data
        result=assess_live_obstacle_clear_config(decoded)
        return {**result,"source":"/global_costmap/global_costmap",
                "runtime_values":decoded}
    finally:
        node.destroy_client(lc)
        node.destroy_client(gc)


def _native_costmap_layer_maps(node):
    """Read exact OFFICIAL Jazzy layer services once; never mutate any layer.

    Costmap2DROS creates GetCostmap services for CostmapLayer plugins.
    Calls are sequential, not atomic; timestamp/skew is preserved.
    The Costmap2DPublisher translates native raw 0..255 to 0..100 topics.
    """
    from nav2_msgs.srv import GetCostmap
    names={
        "obstacle_layer":"/global_costmap/get_obstacle_layer",
        "static_layer":"/global_costmap/get_static_layer",
        # Jazzy's InflationLayer isn't a CostmapLayer with a separate
        # get_inflation_layer service. Read its effects in the master.
        "costmap":"/global_costmap/get_costmap",
    }
    hold={"status":"NATIVE_LAYER_PROVENANCE_HOLD_NO_GOAL",
          "reason":"OFFICIAL_GET_COSTMAP_LAYER_SERVICE_UNAVAILABLE",
          "source_causality_proven":False,
          "obstacle_layer_clearing_proven":False,
          "motion_admitted":False,"goal_sent":False}
    raw={}
    for name,service in names.items():
        cli=node.create_client(GetCostmap,service)
        try:
            if not cli.wait_for_service(timeout_sec=3.):
                return {**hold,"missing_service":service}
            future=cli.call_async(GetCostmap.Request())
            deadline=time.monotonic()+5.
            while not future.done() and time.monotonic()<deadline:
                time.sleep(.05)
            if not future.done() or future.exception() is not None:
                return {**hold,"reason":"NATIVE_LAYER_CALL_NO_RESPONSE",
                        "missing_service":service}
            msg=future.result().map
            stamp=(float(msg.header.stamp.sec)+
                   float(msg.header.stamp.nanosec)*1e-9)
            raw[name]={
                "service":service,"frame":msg.header.frame_id,
                "width":int(msg.metadata.size_x),
                "height":int(msg.metadata.size_y),
                "resolution":float(msg.metadata.resolution),
                "origin":[float(msg.metadata.origin.position.x),
                          float(msg.metadata.origin.position.y)],
                "stamp":stamp,
                "received_monotonic":time.monotonic(),
                "cells":[int(c) for c in msg.data],
            }
        except (RuntimeError,ValueError,TypeError,AttributeError) as ex:
            return {**hold,"reason":type(ex).__name__+":"+str(ex),
                    "missing_service":service}
        finally:
            node.destroy_client(cli)
    return raw



def _observe_native_published_catchup(old_topic,native_data,costmaps,lock):
    """Evidence-only <=10s source-stamped actual Grid join after native Master.

    Shared by both first failure paths: inner .36m count timeout AND outer
    .75m ROI-positive despite count match. NEVER changes safety TTL,
    G07 state, Costmap parameters, or the original failure verdict.
    """
    observed_done=time.monotonic()
    stamp=native_data.get("service_stamps",{}).get("costmap")
    rows=[]
    if (type(stamp) in (int,float) and math.isfinite(stamp)
            and native_data.get("status")==(
                "NATIVE_LAYER_SUSPECT_COSTS_OBSERVED_NO_GOAL")):
        # Real L2 #43672582071 produced four post-native Grid stamps by
        # ~7s, last mismatches [5,0]. One further fresh Grid publication
        # is required to test two consecutive matching snapshots. This
        # increases a read-only observational budget, NOT CM/Guard/sensor
        # TTL, Costmap clearing duration, or any motion admission limit.
        deadline=time.monotonic()+10.0
        last_evaluated_receipt=None
        while time.monotonic()<deadline:
            with lock:
                fresh=[(t,g) for t,g in costmaps
                       if t>observed_done and
                       float(g.header.stamp.sec)+
                       float(g.header.stamp.nanosec)*1e-9>stamp]
            fresh.sort(key=lambda v:v[0])
            rows=fresh[-12:]
            # A genuine publication [12 mismatch, 0 mismatch] is only
            # a FIRST match. Continue within the existing seven-second
            # observation budget to inspect the NEXT source-stamped Grid.
            # Avoid repeating expensive large-grid conversion on each
            # 100-ms poll when no new callback has arrived.
            if len(rows)>=2 and rows[-1][0]!=last_evaluated_receipt:
                last_evaluated_receipt=rows[-1][0]
                candidate=assess_native_topic_catchup(
                    old_topic,native_data,
                    [_drift_payload(t,g) for t,g in rows])
                if candidate.get("two_consecutive_native_matches_verified") is True:
                    break
            time.sleep(.1)
    return assess_native_topic_catchup(
        old_topic,native_data,
        [_drift_payload(t,g) for t,g in rows])


def _native_costmap_layer_probe(node, topic, suspect_idxs, *,
                                baseline_native=None, raw_native=None):
    """Read-only native restored raw layers vs optional genuine free baseline."""
    raw=raw_native if raw_native is not None else _native_costmap_layer_maps(node)
    if not isinstance(raw,dict) or "status" in raw:
        return raw
    verdict=audit_native_layer_costs(raw,topic,list(suspect_idxs)[:12])
    if baseline_native is not None:
        roundtrip=compare_native_layer_roundtrip(
            baseline_native,raw,topic,list(suspect_idxs)[:12])
        verdict["native_roundtrip"]=roundtrip
        print("AXIA_D07_H01_NATIVE_BASELINE_RESTORE_DELTA_ONLY "+
              json.dumps(roundtrip,sort_keys=True),flush=True)
    return verdict


def _roi_native_layer_indices(topic,roi,xy,lethal_history=None):
    """First actual persistent lethal must win over lower-index cost gradient.

    Last L2 #43600093293 saw persistent lethal 77738 but first 12 suspect
    ROIs excluded it. Inspect that native ObstacleLayer cell FIRST.
    """
    indices=prioritize_native_layer_suspects(
        roi,lethal_history,max_count=12)
    if indices:
        return indices
    origin=topic["origin"]
    res=topic["resolution"]
    width=topic["width"]
    col=math.floor((xy[0]-origin[0])/res)
    row=math.floor((xy[1]-origin[1])/res)
    if not (0<=col<width and 0<=row<topic["height"]):
        return []
    return [row*width+col]

def _admit(args,pre):
    req={"GITHUB_ACTIONS":"true","AXIA_P0_SIM_ONLY":"1",
         "AXIA_D07_H01_CI_ALLOWED":"1",
         "AXIA_G07_CI_SIM_GOAL_ALLOWED":"1","ROS_DISTRO":"jazzy",
         "AXIA_G07_OWNER_STARTUP_PARITY":"1"}
    if getattr(args,"gui",False):
        if not admit_gui_simulation(os.environ):
            raise RuntimeError("D07_H01_GUI_SIMULATION_NO_MOVING_GOAL_DENIED")
    elif any(os.environ.get(k)!=v for k,v in req.items()):
        raise RuntimeError("D07_H01_GEOMETRY_PUBLIC_SIM_ONLY")
    if not os.environ.get("GZ_PARTITION","").startswith("axia_p2_"):
        raise RuntimeError("D07_H01_NONISOLATED_GAZEBO")
    actual=subprocess.check_output(["git","-c","safe.directory="+str(Path(__file__).resolve().parents[1]),
              "-C",str(Path(__file__).resolve().parents[1]),"rev-parse","HEAD"],
              text=True,timeout=5).strip()
    if len(args.source_sha)!=40 or actual!=args.source_sha:
        raise RuntimeError("D07_H01_PRIVATE_SOURCE_PIN_MISMATCH")
    start=json.loads(args.startup.read_text())
    if not (start.get("status")=="SMOKE_READY"
            and start.get("goal_sent") is False
            and start.get("fault_injected") is False):
        raise RuntimeError("D07_H01_STARTUP_NOT_SAFE_NO_GOAL")
    if not (pre.get("status")=="P2_G07_OWNER_PREGOAL_L2_READY_NO_GOAL"
            and pre.get("goal_sent") is False and pre.get("native_set_pose_ack") is True
            and pre.get("post_ack_distinct_ros_scan_count",0)>=2):
        raise RuntimeError("D07_H01_REAL_PREGOAL_NOT_READY")


def _lethal_near(grid,xy,radius=.36):
    if grid is None or grid.info.resolution<=0 or len(grid.data)!=grid.info.width*grid.info.height:
        return None
    info=grid.info
    x,y=xy; res=info.resolution
    ox,oy=info.origin.position.x,info.origin.position.y
    cells=0
    for i in range(info.height):
        cy=oy+(i+.5)*res
        if abs(cy-y)>radius:
            continue
        for j in range(info.width):
            cx=ox+(j+.5)*res
            if (cx-x)**2+(cy-y)**2<=radius*radius:
                if int(grid.data[i*info.width+j])>=95:
                    cells+=1
    return cells


def _grid_payload(grid):
    """Read-only native OccupancyGrid metadata and cells, never a cmd."""
    return {"frame":grid.header.frame_id,
            "width":int(grid.info.width),"height":int(grid.info.height),
            "resolution":float(grid.info.resolution),
            "origin":[float(grid.info.origin.position.x),
                      float(grid.info.origin.position.y)],
            "cells":[int(v) for v in grid.data]}


def _drift_payload(received_monotonic, grid):
    """Actual official Grid header and monotonic callback receipt, immutable evidence."""
    data=_grid_payload(grid)
    data.update({
        "source":"official_nav2_global_costmap",
        "session_id":os.environ["GZ_PARTITION"],
        "stamp":float(grid.header.stamp.sec)+float(grid.header.stamp.nanosec)*1e-9,
        "received_monotonic":float(received_monotonic),
    })
    return data


def _pose(node,xy):
    from geometry_msgs.msg import PoseStamped
    p=PoseStamped();p.header.frame_id="map"
    p.header.stamp=node.get_clock().now().to_msg()
    p.pose.position.x,p.pose.position.y=map(float,xy)
    p.pose.orientation.w=1.
    return p


def _compute(node,client,start,raw_path_store=None):
    from nav2_msgs.action import ComputePathToPose
    from action_msgs.msg import GoalStatus
    if not client.wait_for_server(timeout_sec=8.):
        raise RuntimeError("D07_H01_OFFICIAL_PLANNER_ACTION_UNAVAILABLE")
    goal=ComputePathToPose.Goal()
    goal.start=_pose(node,start)
    goal.goal=_pose(node,GOAL)
    goal.use_start=True
    goal.planner_id="GridBased"
    sent=client.send_goal_async(goal)
    until=time.monotonic()+15
    while not sent.done() and time.monotonic()<until:time.sleep(.05)
    if not sent.done() or sent.result() is None or not sent.result().accepted:
        raise RuntimeError("D07_H01_PLANNER_GOAL_REQUEST_NOT_ACCEPTED")
    future=sent.result().get_result_async()
    until=time.monotonic()+15
    while not future.done() and time.monotonic()<until:time.sleep(.05)
    if not future.done() or future.result() is None:
        raise RuntimeError("D07_H01_PLANNER_RESULT_TIMEOUT")
    result=future.result()
    if result.status!=GoalStatus.STATUS_SUCCEEDED:
        raise RuntimeError("D07_H01_OFFICIAL_PLANNER_RESULT_NOT_SUCCEEDED")
    path=result.result.path
    if path.header.frame_id!="map" or len(path.poses)<3:
        raise RuntimeError("D07_H01_OFFICIAL_PATH_FRAME_OR_POSES_INVALID")
    report={"frame_id":"map","source":"official_nav2",
            "source_header_stamp":(
                float(path.header.stamp.sec)+
                float(path.header.stamp.nanosec)*1e-9),
            "poses":[[float(p.pose.position.x),float(p.pose.position.y)] for p in path.poses],
            "start":list(start),"goal":list(GOAL),"received_at":time.monotonic()}
    # Only store raw native ROS Path OUTSIDE serializable evidence, keyed by
    # the exact report identity. Do not synthesize path coordinates/stamps.
    if raw_path_store is not None:
        raw_path_store[id(report)]=path
    return report


def run(args):
    pre=json.loads(args.pregoal.read_text())
    _admit(args,pre)
    args.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    result={"status":"BLOCKED","source_sha":args.source_sha,"goal_sent":False,
            "real_nav2":False,"real_laser_scan":False,"path_viable":False,
            "obstacle_pose_native_ack":False,
            "post_ack_scan_stamp_progressed":False,
            "actual_costmap_obstacle_observed":False,
            "path_changed":False,"contact_topic_proven":False,
            "map_frame":"map","certified_estop":False,
            "formal_accepted":False,"owner_l3_accepted":False,
            "reason":"START"}
    outfile=args.output/"d07_h01_geometry.json"
    def save():
        outfile.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    save()
    import rclpy
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.qos import qos_profile_sensor_data,QoSProfile,DurabilityPolicy,ReliabilityPolicy
    from sensor_msgs.msg import LaserScan
    from nav_msgs.msg import OccupancyGrid, Path as NavPath
    from nav2_msgs.action import ComputePathToPose
    from rclpy.action import ActionClient
    rclpy.init()
    node=Node("axia_d07_h01_real_geometry_no_goal",
              parameter_overrides=[Parameter("use_sim_time",value=True)],
              automatically_declare_parameters_from_overrides=True)
    observer=Observer(node,args.output,buffered_evidence=True,periodic_flush_sec=.75)
    lock=threading.Lock()
    scans=deque(maxlen=100)
    raw_nav2_scans=deque(maxlen=160)
    costmaps=deque(maxlen=20)
    active_bearing={"rad":None}
    def on_scan(msg):
        side=sector_min(msg)
        with lock:
            bearing=active_bearing["rad"]
        chosen=sector_min(msg,bearing=bearing) if bearing is not None else None
        stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
        if side is not None and math.isfinite(stamp):
            with lock: scans.append((time.monotonic(),stamp,side,chosen))
    def on_raw_nav2_scan(msg):
        # The ACTUAL official global ObstacleLayer is configured for /scan,
        # not /safety/scan (real effective Jazzy parameter L2 #43595015264).
        # Preserve raw callback stamp and corridor finite ray independently.
        with lock:
            bearing=active_bearing["rad"]
        chosen=sector_min(msg,bearing=bearing) if bearing is not None else None
        stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
        if math.isfinite(stamp) and stamp>0:
            with lock:
                raw_nav2_scans.append((time.monotonic(),stamp,chosen))
    def on_costmap(msg):
        with lock: costmaps.append((time.monotonic(),msg))
    raw_scan_sub=node.create_subscription(LaserScan,"/scan",on_raw_nav2_scan,qos_profile_sensor_data)
    scan_sub=node.create_subscription(LaserScan,"/safety/scan",on_scan,qos_profile_sensor_data)
    map_sub=node.create_subscription(OccupancyGrid,"/global_costmap/costmap",on_costmap,
        QoSProfile(depth=4,reliability=ReliabilityPolicy.RELIABLE,
                   durability=DurabilityPolicy.TRANSIENT_LOCAL))
    client=ActionClient(node,ComputePathToPose,"/compute_path_to_pose")
    raw_official_paths={} if getattr(args,"gui",False) else None
    visual_publisher=(node.create_publisher(
        NavPath,"/axia/d07/h01/path_visual",
        QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,
                   durability=DurabilityPolicy.TRANSIENT_LOCAL))
        if getattr(args,"gui",False) else None)
    phase_ledger=args.output/"phase_evidence.jsonl"
    def publish_phase(phase,report,scan_stamp,costmap_stamp):
        if visual_publisher is None:
            return
        original=raw_official_paths.get(id(report))
        if original is None:
            raise RuntimeError("D07_H01_OFFICIAL_PATH_RAW_SOURCE_MISSING")
        # A real GUI client is started after the strict free Costmap baseline.
        # Wait for a REAL DDS RViz Path subscriber BEFORE publishing the
        # original official Action Path, never synthesize or replay a fake.
        deadline=time.monotonic()+35.0
        while (visual_publisher.get_subscription_count()<1
               and time.monotonic()<deadline):
            time.sleep(.25)
        if visual_publisher.get_subscription_count()<1:
            raise RuntimeError("D07_H01_GUI_RVIZ_PATH_SUBSCRIPTION_ABSENT")
        data=publish_official_path(
            visual_publisher,original,phase=phase,
            scan_stamp=scan_stamp,costmap_stamp=costmap_stamp,
            current_clock=node.get_clock().now().nanoseconds*1e-9)
        time.sleep(args.gui_hold_s)
        data["rviz_subscription_count"]=int(
            visual_publisher.get_subscription_count())
        with phase_ledger.open("a",encoding="utf-8") as fp:
            fp.write(json.dumps(data,sort_keys=True)+"\n")
        result.setdefault("gui_path_phases",[]).append(data)
        save()
        print("D07_H01_GUI_OFFICIAL_PATH_PHASE "+
              json.dumps(data,sort_keys=True),flush=True)
        if data["rviz_subscription_count"]<1:
            raise RuntimeError("D07_H01_GUI_RVIZ_PATH_SUBSCRIPTION_ABSENT")
    executor=MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    th=threading.Thread(target=executor.spin,daemon=True);th.start()
    original_world=(round(DEMO_START[0]+1.35+RADIUS,2),DEMO_START[1])
    moved=False
    try:
        def until(fn,label,seconds=10.):
            limit=time.monotonic()+seconds
            while time.monotonic()<limit:
                out=fn()
                if out:return out
                time.sleep(.065)
            raise RuntimeError("D07_H01_NO_GOAL_"+label+"_TIMEOUT")
        until(lambda: observer.snapshot(include_graph=False).get("clock_advancing"),"CLOCK")
        try:
            # Existing _map_robot_pose() waits up to 3 seconds per call for
            # genuine AMCL /amcl_pose map coordinates. Public actual L2
            # #43597565919 failed on its FIRST 3s window even though pregoal
            # P2 was READY. Retry only exact transient-local AMCL absence,
            # max three reads; never synthesize map from /odom or Gazebo.
            map_pose=retry_actual_amcl_map_pose(
                lambda:_map_robot_pose(node,observer))
        except RuntimeError as amcl_error:
            first_amcl_boundary={
                "status":"REAL_AMCL_MAP_POSE_HOLD_NO_GOAL",
                "first_invalid_boundary":"AMCL_MAP_POSE_NOT_OBSERVED",
                "reason":str(amcl_error),
                "genuine_amcl_pose_proven":False,
                "attempted_bounded_real_reads":3,
                "goal_sent":False,"motion_admitted":False}
            result["first_amcl_map_pose_boundary"]=first_amcl_boundary
            save()
            print("AXIA_D07_H01_FIRST_AMCL_MAP_POSE_BOUNDARY "+
                  json.dumps(first_amcl_boundary,sort_keys=True),flush=True)
            raise
        odom_pose=until(lambda:observer.data().get("pose"),"REAL_ODOM")
        anchor=make_frame_anchor(map_pose,odom_pose,official_tb3_spawn(),
                  map_pose_source="amcl_pose_map_transient_local")
        map0,world0=anchor["map_pose"],anchor["world_pose"]
        # Do not guess obstacle map placement from a straight start→goal line:
        # use the REAL official Nav2 baseline Path after the cylinder is away.
        # The topic was absent in real public L2 #43562819849. Keep motor
        # authority BLOCKED, but allow read-only actual route geometry evidence
        # to proceed. This is NOT a collision-free or actual-driving result.
        # Source/type advertisement is NOT a calibration and never validates
        # a continuous no-collision window. Keep full motion still BLOCKED.
        try:
            contact_native_metadata=_native_gz_contact_advertisement(args.output)
        except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as err:
            contact_native_metadata={
                "status":"NATIVE_CONTACT_METADATA_HOLD_NO_GOAL",
                "reason":type(err).__name__+":"+str(err),
                "topic_type_proven":False,
                "source_verified":False,
                "contact_ground_truth_ready":False,
                "motion_admitted":False,"goal_sent":False}
        result["contact_native_metadata"]=contact_native_metadata
        result["contact_topic_proven"]=contact_native_metadata.get(
            "topic_type_proven") is True
        result["contact_ground_truth_ready"]=False
        result["motion_admitted"]=False
        result["contact_topic_probe"]={
            "native_topic":NATIVE_CONTACT_TOPIC,
            "topic_type_proven":result["contact_topic_proven"],
            "positive_control_proven":False,
            "other_contact_topics":[]}
        save()
        print("AXIA_D07_H01_REAL_NATIVE_CONTACT_ADVERTISEMENT_ONLY "+
              json.dumps(contact_native_metadata,sort_keys=True),flush=True)
        if not result["contact_topic_proven"]:
            print("AXIA_D07_H01_CONTACT_TOPIC_MISSING_MOTION_GOAL_DENIED",flush=True)
        # Read the EXACT effective global Costmap ObstacleLayer scan settings
        # before moving the physical obstacle. Purely diagnostic and bounded;
        # do not change params or claim Nav2 internal scan consumption.
        actual_nav2_config=_live_nav2_obstacle_config(node)
        result["live_nav2_obstacle_parameters"]=actual_nav2_config
        save()
        print("AXIA_D07_H01_ACTUAL_NAV2_CLEARING_PARAMS_ONLY "+
              json.dumps(actual_nav2_config,sort_keys=True),flush=True)
        away_ack=move(*original_world)
        moved=True
        base_at=time.monotonic()
        def recent_side(minstamp=0):
            with lock:
                v=[x for x in scans if x[0]>base_at and x[1]>minstamp]
            return v[-1] if len(v)>=2 else None
        away=until(lambda:recent_side() if recent_side() and recent_side()[2]>1.2 else None,
                   "REAL_BASELINE_SIDE_SCAN")
        before=_compute(node,client,map_pose[:2],raw_official_paths)
        # Query independent official ComputePathToPose again while the SAME
        # physical obstacle is still parked AWAY and Waffle is stationary.
        # This tests whether "return to ONE original baseline path" is
        # meaningful even before physical intrusion. The second plan is
        # diagnostics ONLY; no G07 Goal, cmd_vel or motion authority.
        free_repeat_path=_compute(node,client,map_pose[:2],raw_official_paths)
        result["first_two_real_free_official_paths"]=classify_two_free_official_paths(
            before,free_repeat_path)
        print("AXIA_D07_H01_TWO_NATIVE_FREE_OFFICIAL_PATHS "+
              json.dumps(result["first_two_real_free_official_paths"],sort_keys=True),
              flush=True)
        # H01 actual Gazebo #43670282482: two freely computed paths may
        # diverge 0.4277m before the cylinder is ever introduced. Only
        # choose a path from the LAST two consecutive stable official reads.
        # At most TWO extra ComputePathToPose calls, physically NO motion.
        free_paths=[before,free_repeat_path]
        free_stable=choose_bounded_free_official_pair(free_paths)
        while (free_stable["status"]==(
                "AWAITING_CONSECUTIVE_FREE_PATH_STABILITY_NO_GOAL")
                and len(free_paths)<4):
            free_paths.append(_compute(node,client,map_pose[:2],raw_official_paths))
            free_stable=choose_bounded_free_official_pair(free_paths)
        result["preintrusion_free_planner_stabilization"]=free_stable
        save()
        print("AXIA_D07_H01_PREINTRUSION_FREE_PLANNER_STABILITY "+
              json.dumps(free_stable,sort_keys=True),flush=True)
        if free_stable["status"]!=(
                "CONSECUTIVE_FREE_OFFICIAL_PATHS_STABLE_NO_GOAL"):
            raise RuntimeError("D07_H01_PREINTRUSION_PLANNER_PATH_UNSTABLE_NO_GOAL")
        i,j=free_stable["pair_indices"]
        before=free_paths[i]
        free_repeat_path=free_paths[j]
        result["two_real_free_official_paths"]=classify_two_free_official_paths(
            before,free_repeat_path)
        if result["two_real_free_official_paths"]["status"]!=(
                "FREE_OFFICIAL_PATH_REPEAT_STABLE_NO_GOAL"):
            raise RuntimeError("D07_H01_TWO_FREE_OFFICIAL_PATHS_PROVENANCE_HOLD")
        try:
            candidate=select_route_intrusion(
                before["poses"],map_pose=map0,world_pose=world0,
                second_free_path=free_repeat_path["poses"])
        except ValueError as mismatch:
            result["first_free_route_boundary"]={
                "reason":str(mismatch),
                "free_paths":result["two_real_free_official_paths"],
                "goal_sent":False,"motion_admitted":False}
            save()
            print("AXIA_D07_H01_FIRST_COMMON_FREE_ROUTE_BOUNDARY "+
                  json.dumps(result["first_free_route_boundary"],sort_keys=True),
                  flush=True)
            raise
        obstacle_map=tuple(candidate["map_xy"])
        result["obstacle_map_xy"]=list(obstacle_map)
        result["intrusion_candidate"]=candidate
        result["first_intrusion_candidate_map_xy"]=list(obstacle_map)
        # Query a FREE baseline scan along the chosen measured Nav2 path.
        with lock:
            active_bearing["rad"]=candidate["bearing_rad"]
        candidate_at=time.monotonic()
        expect_surface=candidate["robot_distance_m"]-RADIUS
        def candidate_free():
            with lock:
                rows=[v for v in scans if v[0]>candidate_at and v[1]>away[1]
                      and v[3] is not None]
            if len(rows)<2 or rows[-1][1]<=rows[-2][1]:
                return None
            return rows[-1] if rows[-1][3]>expect_surface+.15 else None
        candidate_baseline=until(candidate_free,"CANDIDATE_BASELINE_SCAN_CLEAR")
        def baseline_costmap():
            with lock: rows=[(t,g) for t,g in costmaps if t>candidate_at]
            for t,g in reversed(rows):
                n=_lethal_near(g,obstacle_map)
                if n is not None:return (t,n,g)
            return None
        # Two physically observed *pre-intrusion* Costmap updates must
        # have distinct native ROS header stamps and callback receipts.
        def baseline_snapshots():
            with lock:
                rows=[(t,float(g.header.stamp.sec)+
                       float(g.header.stamp.nanosec)*1e-9,g)
                      for t,g in costmaps if t>candidate_baseline[0]]
            return select_fresh_baselines(
                rows,earliest_received=candidate_baseline[0])
        baseline_pairs=until(baseline_snapshots,"TWO_REAL_COSTMAP_BASELINES")
        initial_free_baselines=assess_two_real_free_grid_baselines(
            _drift_payload(baseline_pairs[0][0],baseline_pairs[0][2]),
            _drift_payload(baseline_pairs[1][0],baseline_pairs[1][2]),
            obstacle_map_xy=obstacle_map)
        result["first_two_free_costmap_baselines"]=initial_free_baselines
        # Actual Gazebo #43602758109: first free 179->181 lethals
        # (4 new, 2 removed) even before physical obstacle intrusion.
        # Avoid declaring this a clearing failure; allow at most 6 genuine
        # FREE native Costmap updates to find 2 consecutive matching lethal
        # index sets, never change safety TTL or synthesize any map/scan.
        stable_pair_diagnostic=None
        if initial_free_baselines["status"]!=(
                "TWO_FREE_BASELINE_LETHAL_CELLS_STABLE_NO_GOAL"):
            if initial_free_baselines["status"]==(
                    "FREE_BASELINE_PROVENANCE_HOLD_NO_GOAL"):
                result["two_real_free_costmap_baselines"]=initial_free_baselines
                # First failure before physical Gazebo intrusion, distinguish
                # UNKNOWN physical ROI from frame/stamp/session mismatches.
                # Do NOT move the cylinder or mark this a clearing failure.
                result["first_free_grid_provenance_boundary"]={
                    "status":initial_free_baselines["status"],
                    "reason":initial_free_baselines["reason"],
                    "first_invalid_boundary":
                        initial_free_baselines.get("first_invalid_boundary"),
                    "unknown_cell_count":
                        initial_free_baselines.get("unknown_cell_count"),
                    "first_unknown_cell_index":
                        initial_free_baselines.get("first_unknown_cell_index"),
                    "source_grid_stamps":
                        initial_free_baselines.get("source_grid_stamps"),
                    "goal_sent":False,"motion_admitted":False}
                save()
                print("AXIA_D07_H01_FIRST_FREE_GRID_PROVENANCE_BOUNDARY "+
                      json.dumps(result["first_free_grid_provenance_boundary"],
                                 sort_keys=True),flush=True)
                raise RuntimeError("D07_H01_FREE_COSTMAP_BASELINE_UNSTABLE_NO_GOAL")
            stabilization_state={"signatures":None,"last":None}
            # Freeze the FIRST actually failed pair; future evaluation may
            # only use up to FOUR later Grid callbacks. Older buffered maps
            # cannot be selected as a stale "stable" baseline.
            initial_failed_pair=tuple(baseline_pairs)
            def physically_free_stable_pair():
                with lock:
                    observed=[(t,float(g.header.stamp.sec)+
                               float(g.header.stamp.nanosec)*1e-9,g)
                              for t,g in costmaps
                              if t>initial_failed_pair[-1][0]]
                bounded=[*initial_failed_pair,*observed[:4]]
                stamp_signature=tuple((t,stamp) for t,stamp,_ in bounded)
                if stabilization_state["signatures"]==stamp_signature:
                    return None
                stabilization_state["signatures"]=stamp_signature
                audit=choose_bounded_stable_free_baselines(
                    [_drift_payload(t,g) for t,_,g in bounded],
                    obstacle_map_xy=obstacle_map)
                stabilization_state["last"]=audit
                if audit["status"]=="STABLE_FREE_GRID_PAIR_SELECTED_NO_GOAL":
                    x,y=audit["pair_indices"]
                    return ([bounded[x],bounded[y]],audit)
                if audit["status"] in (
                    "UNSTABLE_FREE_GRID_BASELINE_HOLD_NO_GOAL",
                    "FREE_BASELINE_PROVENANCE_HOLD_NO_GOAL"):
                    raise RuntimeError("D07_H01_FREE_COSTMAP_BASELINE_UNSTABLE_NO_GOAL")
                return None
            try:
                stable_result=until(physically_free_stable_pair,
                                    "FREE_COSTMAP_STABILIZATION",seconds=13.)
                baseline_pairs,stable_pair_diagnostic=stable_result
            except RuntimeError:
                result["free_costmap_stabilization"]=stabilization_state["last"]
                result["two_real_free_costmap_baselines"]=initial_free_baselines
                # A physical obstacle has NOT yet been inserted. Preserve
                # the earliest actual lethal indices, then read official
                # Obstacle/Static/Master native layers at latest Grid receipt.
                # These non-atomic services cannot prove per-ray causality.
                first_variation=(stabilization_state["last"] or {}).get(
                    "first_observed_variation") or {}
                suspects=list(dict.fromkeys(
                    first_variation.get("first_new_lethal_indices",[]) +
                    first_variation.get("first_removed_lethal_indices",[])))[:12]
                with lock:
                    last_native_grid=costmaps[-1] if costmaps else None
                    latest_raw_scans=list(raw_nav2_scans)[-2:]
                    latest_safety_scans=list(scans)[-2:]
                    # Only genuine callbacks belonging to the *current*
                    # physical-free candidate; never mix other sessions.
                    timing_grid_rows=[{
                        "received_monotonic":t,
                        "ros_stamp":float(g.header.stamp.sec)+
                            float(g.header.stamp.nanosec)*1e-9}
                        for t,g in costmaps if t>=initial_failed_pair[0][0]]
                    timing_scan_rows=[{
                        "received_monotonic":t,"ros_stamp":stamp,
                        "corridor_range_m":distance}
                        for t,stamp,distance in raw_nav2_scans]
                # Observer already owns the actual /odom event ledger.
                # Read it only once on failure; the non-atomic join does NOT
                # change sensor QoS, Costmap, TTL or any acceptance predicate.
                try:
                    observer.event_file.flush()
                    with open(observer.event_file.name,encoding="utf-8") as fd:
                        actual_odom_events=[
                            json.loads(line) for line in fd
                            if '"kind": "odom"' in line]
                    timing_probe=assess_preintrusion_timing(
                        actual_odom_events,timing_grid_rows,timing_scan_rows,
                        first_changed_indices=suspects)
                except (OSError,ValueError,TypeError) as diagnostic_error:
                    timing_probe={
                        "status":"FREE_GRID_TIMING_PROVENANCE_HOLD",
                        "reason":type(diagnostic_error).__name__,
                        "source_causality_proven":False,
                        "cross_node_ttl_proven":False,
                        "motion_admitted":False,"goal_sent":False}
                result["preintrusion_source_timing"]=timing_probe
                print("AXIA_D07_H01_FREE_GRID_SOURCE_TIMING_ONLY "+
                      json.dumps(timing_probe,sort_keys=True),flush=True)
                native_first={
                    "status":"PREINTRUSION_NATIVE_LAYER_PROVENANCE_HOLD_NO_GOAL",
                    "first_invalid_boundary":"PRE_INTRUSION_BASELINE_LETHAL_VARIATION",
                    "source_causality_proven":False,
                    "goal_sent":False,"motion_admitted":False,
                    "actual_first_indices":suspects,
                    "raw_nav2_scan_last_two":[
                        {"received_monotonic":row[0],"ros_stamp":row[1],
                         "corridor_range_m":row[2]}
                        for row in latest_raw_scans],
                    "safety_scan_last_two":[
                        {"received_monotonic":row[0],"ros_stamp":row[1],
                         "corridor_range_m":row[3]}
                        for row in latest_safety_scans],
                }
                if last_native_grid and suspects:
                    try:
                        native_first["native_layers"]=_native_costmap_layer_probe(
                            node,_drift_payload(*last_native_grid),suspects)
                    except Exception as native_error:
                        native_first["native_probe_error"]=(
                            type(native_error).__name__+":"+str(native_error))
                result["preintrusion_native_free_variation"]=native_first
                save()
                print("AXIA_D07_H01_PREINTRUSION_NATIVE_FIRST_VARIATION_NO_GOAL "+
                      json.dumps(native_first,sort_keys=True),flush=True)
                print("AXIA_D07_H01_TWO_REAL_FREE_COSTMAP_BASELINES "+
                      json.dumps(result["free_costmap_stabilization"],
                                 sort_keys=True),flush=True)
                raise RuntimeError("D07_H01_FREE_COSTMAP_BASELINE_UNSTABLE_NO_GOAL")
        else:
            stable_pair_diagnostic=choose_bounded_stable_free_baselines(
                [_drift_payload(t,g) for t,_,g in baseline_pairs],
                obstacle_map_xy=obstacle_map)
        base_t,base_stamp,base_grid=baseline_pairs[-1]
        original_grid=(base_t,_lethal_near(base_grid,obstacle_map),base_grid)
        if original_grid[1] is None or base_stamp<=0:
            raise RuntimeError("D07_H01_INVALID_BASELINE_COSTMAP")
        result["baseline_costmap_lethal_cells"]=original_grid[1]
        result["baseline_grid_stamps"]=[row[1] for row in baseline_pairs]
        free_baselines=assess_two_real_free_grid_baselines(
            _drift_payload(baseline_pairs[0][0],baseline_pairs[0][2]),
            _drift_payload(baseline_pairs[1][0],baseline_pairs[1][2]),
            obstacle_map_xy=obstacle_map)
        result["free_costmap_stabilization"]=stable_pair_diagnostic
        result["two_real_free_costmap_baselines"]=free_baselines
        save()
        print("AXIA_D07_H01_TWO_REAL_FREE_COSTMAP_BASELINES "+
              json.dumps({"selected":free_baselines,
                          "initial":initial_free_baselines,
                          "stabilization":stable_pair_diagnostic},
                         sort_keys=True),flush=True)
        if (free_baselines["status"]!=(
                "TWO_FREE_BASELINE_LETHAL_CELLS_STABLE_NO_GOAL")
            or stable_pair_diagnostic["status"]!=(
                "STABLE_FREE_GRID_PAIR_SELECTED_NO_GOAL")):
            raise RuntimeError("D07_H01_FREE_COSTMAP_BASELINE_UNSTABLE_NO_GOAL")
        # Bounded read-only actual native baseline BEFORE Gazebo intrusion.
        # Keep full raw only in memory; public log gets source stamps, never
        # confidential frames or a fabricated Costmap-cleared PASS.
        native_baseline_layers=_native_costmap_layer_maps(node)
        result["native_baseline_layers_captured"]=(
            isinstance(native_baseline_layers,dict)
            and "status" not in native_baseline_layers)
        result["native_baseline_source_stamps"]=(
            {n:v["stamp"] for n,v in native_baseline_layers.items()}
            if result["native_baseline_layers_captured"] else {})
        save()
        if getattr(args,"gui",False):
            # Actual L2 #43792298836: the old official Before Path ROS
            # stamp 56.256 PRECEDED the final Free Grid pair 56.706/58.704.
            # Such an early Planner path cannot be the authoritative
            # restoration reference even with identical native Costmap.
            # Obtain TWO REAL OFFICIAL paths only AFTER the verified Free
            # Grid and native master, while physical obstacle remains AWAY.
            if not result["native_baseline_layers_captured"]:
                raise RuntimeError("D07_H01_POST_FREE_NATIVE_MASTER_NOT_READY")
            before=_compute(node,client,map_pose[:2],raw_official_paths)
            free_repeat_path=_compute(node,client,map_pose[:2],raw_official_paths)
            post_free_paths=[before,free_repeat_path]
            post_free_pair=choose_bounded_free_official_pair(post_free_paths)
            while (post_free_pair["status"]==(
                    "AWAITING_CONSECUTIVE_FREE_PATH_STABILITY_NO_GOAL")
                    and len(post_free_paths)<4):
                post_free_paths.append(
                    _compute(node,client,map_pose[:2],raw_official_paths))
                post_free_pair=choose_bounded_free_official_pair(post_free_paths)
            if post_free_pair["status"]!=(
                    "CONSECUTIVE_FREE_OFFICIAL_PATHS_STABLE_NO_GOAL"):
                raise RuntimeError(
                    "D07_H01_POST_FREE_OFFICIAL_PLANNER_UNSTABLE_NO_GOAL")
            pi,pj=post_free_pair["pair_indices"]
            before,free_repeat_path=post_free_paths[pi],post_free_paths[pj]
            plan_epoch=assess_post_free_path_epoch(
                [before,free_repeat_path],
                grid_stamp=base_stamp,
                native_stamp=native_baseline_layers["costmap"]["stamp"])
            result["post_free_official_path_epoch"]=plan_epoch
            print("AXIA_D07_H01_POST_FREE_OFFICIAL_PATH_SOURCE_EPOCH "+
                  json.dumps(plan_epoch,sort_keys=True),flush=True)
            if plan_epoch["source_epoch_ready"] is not True:
                raise RuntimeError("D07_H01_POST_FREE_PATH_SOURCE_EPOCH_HOLD")
            result["preintrusion_free_planner_stabilization"]=post_free_pair
            result["two_real_free_official_paths"]=classify_two_free_official_paths(
                before,free_repeat_path)
            if result["two_real_free_official_paths"]["status"]!=(
                    "FREE_OFFICIAL_PATH_REPEAT_STABLE_NO_GOAL"):
                raise RuntimeError("D07_H01_POST_FREE_TWO_PATHS_NOT_STABLE")
            # Never keep an earlier physical intrusion candidate if the
            # genuinely later official path has moved. Recompute using ONLY
            # existing shared-path route selection; no custom planner.
            try:
                new_candidate=select_route_intrusion(
                    before["poses"],map_pose=map0,world_pose=world0,
                    second_free_path=free_repeat_path["poses"])
            except ValueError as ex:
                result["post_free_common_path_failure"]={
                    "reason":str(ex),"source_epoch":plan_epoch,
                    "goal_sent":False,"motion_admitted":False}
                save()
                raise RuntimeError("D07_H01_POST_FREE_COMMON_ROUTE_HOLD") from ex
            new_xy=tuple(new_candidate["map_xy"])
            free_baselines=assess_two_real_free_grid_baselines(
                _drift_payload(baseline_pairs[0][0],baseline_pairs[0][2]),
                _drift_payload(baseline_pairs[1][0],baseline_pairs[1][2]),
                obstacle_map_xy=new_xy)
            stable_pair_diagnostic=choose_bounded_stable_free_baselines(
                [_drift_payload(t,g) for t,_,g in baseline_pairs],
                obstacle_map_xy=new_xy)
            if (free_baselines["status"]!=(
                    "TWO_FREE_BASELINE_LETHAL_CELLS_STABLE_NO_GOAL")
                or stable_pair_diagnostic["status"]!=(
                    "STABLE_FREE_GRID_PAIR_SELECTED_NO_GOAL")):
                result["post_free_route_roi_failure"]={
                    "free_roi":free_baselines,
                    "stabilization":stable_pair_diagnostic,
                    "goal_sent":False,"motion_admitted":False}
                save()
                raise RuntimeError("D07_H01_POST_FREE_ROUTE_ROI_NOT_STABLE")
            # Revalidate a fresh genuine /safety/scan for the NEW route
            # bearing and expected physical cylinder surface before any
            # native Gazebo set_pose or official displayed Path.
            candidate=new_candidate
            obstacle_map=new_xy
            result["obstacle_map_xy"]=list(obstacle_map)
            result["intrusion_candidate"]=candidate
            with lock:
                active_bearing["rad"]=candidate["bearing_rad"]
            candidate_at=time.monotonic()
            expect_surface=candidate["robot_distance_m"]-RADIUS
            candidate_baseline=until(
                candidate_free,"POST_STABLE_CANDIDATE_BASELINE_SCAN_CLEAR")
            original_grid=(
                base_t,_lethal_near(base_grid,obstacle_map),base_grid)
            if original_grid[1] is None:
                raise RuntimeError("D07_H01_POST_FREE_INVALID_ROI_GRID")
            result["baseline_costmap_lethal_cells"]=original_grid[1]
            result["two_real_free_costmap_baselines"]=free_baselines
            result["free_costmap_stabilization"]=stable_pair_diagnostic
            result["post_free_baseline_reselected"]={
                "old_candidate_map_xy":list(
                    result["first_intrusion_candidate_map_xy"]),
                "official_candidate_map_xy":list(obstacle_map),
                "source_header_stamp":before["source_header_stamp"],
                "native_master_stamp":native_baseline_layers["costmap"]["stamp"],
                "free_grid_stamps":[row[1] for row in baseline_pairs],
                "selected_roi_stable":True,"goal_sent":False,
                "motion_admitted":False}
            save()
            print("AXIA_D07_H01_POST_FREE_BASELINE_RESELECTED "+
                  json.dumps(result["post_free_baseline_reselected"],
                             sort_keys=True),flush=True)
        # D07_H01_GUI_AFTER_FREE_BASELINE_MARKER: only NOW may the display
        # watcher start Gazebo -g / RViz2. Marker lives in a fresh exclusive
        # output directory and is SHA-matched; it is NOT a safety PASS.
        if getattr(args,"gui",False):
            (args.output/"gui_after_free_baseline.ready").write_text(
                args.source_sha+"\n",encoding="utf-8")
            print("D07_H01_GUI_AFTER_FREE_BASELINE_MARKER SOURCE_SHA="+
                  args.source_sha+" NO_GOAL",flush=True)
        publish_phase("before",before,candidate_baseline[1],base_stamp)
        # Record the actual baseline occupancy. In physical L2 #43566626745
        # there were already 42 lethal cells BEFORE the cylinder intrusion.
        # Restoration must prove exactly the original map, not "zero cells".
        # This NO-GOAL evidence never certifies motor or collision safety.
        # Native Harmonic one physical obstacle intrusion only while STATIONARY.
        ack=move(*candidate["world_xy"],demo_corridor=True)
        intrude_at=time.monotonic()
        result["obstacle_pose_native_ack"]=bool(ack)
        def new_physical_scan():
            with lock:
                rows=[v for v in scans if v[0]>intrude_at and v[1]>candidate_baseline[1]
                      and v[3] is not None
                      and abs(v[3]-expect_surface)<=.16]
            if (len(rows)<2 or rows[-1][1]<=rows[-2][1]
                    or candidate_baseline[3]-rows[-1][3]<=.15):
                return None
            return rows[-1]
        actual=until(new_physical_scan,"REAL_NEW_PHYSICAL_LIDAR")
        result["real_laser_scan"]=True
        result["post_ack_scan_stamp_progressed"]=True
        def marked():
            with lock: rows=list(costmaps)
            for t,g in reversed(rows):
                if t>intrude_at:
                    n=_lethal_near(g,obstacle_map)
                    if n is not None and n>=original_grid[1]+3:return (t,n,g)
            return None
        grid=until(marked,"REAL_COSTMAP_MARKING")
        result["actual_costmap_obstacle_observed"]=True
        after=_compute(node,client,map_pose[:2],raw_official_paths)
        measured=route_evidence(before,after,obstacle_map_xy=obstacle_map,
             scan_stamp_advanced=True,costmap_observed=True,
             contact_topic_proven=result["contact_topic_proven"],frame_anchor_attested=True)
        result["route_oracle"]=measured
        (args.output/"d07_h01_before_after_actual_nav2_paths.json").write_text(
          json.dumps({"before":before,"after":after,"obstacle_map_xy":list(obstacle_map),
                      "costmap_lethal_near":grid[1],
                      "scan_after_gazebo_ack_stamp":actual[1],
                      "source_sha":args.source_sha},indent=2)+"\n")
        if measured["geometry_ready"] is not True:
            first={
                "reason":measured.get("reason"),
                "before_min_m":measured.get("before_min_m"),
                "after_min_m":measured.get("after_min_m"),
                "path_delta_m":measured.get("path_delta_m"),
                "before_path_points":len(before["poses"]),
                "after_path_points":len(after["poses"]),
                "costmap_lethal_cells":grid[1],
                "contact_topic_proven":result["contact_topic_proven"],
                "contact_other_topics":result.get("contact_topic_probe",{}).get("other_contact_topics",[]),
                "goal_sent":False,
            }
            result["first_route_boundary"]=first
            save()
            print("AXIA_D07_H01_FIRST_ROUTE_BOUNDARY "+json.dumps(first,sort_keys=True),flush=True)
            raise RuntimeError("D07_H01_NO_FEASIBLE_OFFICIAL_NAV2_DETOUR")
        result["path_changed"]=True
        result["path_viable"]=True
        result["real_nav2"]=True
        publish_phase("intrusion",after,actual[1],
                      float(grid[2].header.stamp.sec)+
                      float(grid[2].header.stamp.nanosec)*1e-9)
        # This marker is not accepted until the original physical model is
        # restored away and the native clearing is observed.
        result["reason"]="ROUTE_CANDIDATE_RESTORING_CLEAR_BASELINE"
        result["route_candidate_metrics"]={
            "before_min_m":measured.get("before_min_m"),
            "after_min_m":measured.get("after_min_m"),
            "path_delta_m":measured.get("path_delta_m"),
            "baseline_costmap_lethal_cells":original_grid[1],
            "intrusion_costmap_lethal_cells":grid[1],
            "contact_topic_proven":result["contact_topic_proven"],
            "goal_sent":False,
        }
        save()
        print("AXIA_D07_H01_ROUTE_CANDIDATE_NOT_MOTION "+
              json.dumps(result["route_candidate_metrics"],sort_keys=True),flush=True)
        restore_ack=move(*original_world);moved=False
        restore_at=time.monotonic()
        def clear_scan():
            with lock:
                rows=[x for x in scans if x[0]>restore_at and x[1]>actual[1]
                      and x[3] is not None and x[3]>expect_surface+.15]
            return rows[-1] if len(rows)>=2 and rows[-1][1]>rows[-2][1] else None
        restored=until(clear_scan,"REAL_BASELINE_RESTORATION")
        # Compare first physical-clear evidence at the ACTUAL raw sensor
        # consumed by Nav2 (/scan) vs the Supervisor safety scan. The two
        # subscriber callbacks do NOT prove ObstacleLayer consumed a ray.
        with lock:
            actual_raw_rows=[tuple(v) for v in raw_nav2_scans
                             if v[0]>restore_at]
            actual_safety_rows=[tuple(v) for v in scans
                                if v[0]>restore_at]
        def packet(topic,row,chosen):
            return {"topic":topic,"received_monotonic":row[0],
                    "ros_stamp":row[1],"corridor_range_m":chosen}
        raw_obs=[packet("/scan",x,x[2]) for x in actual_raw_rows]
        safety_obs=[packet("/safety/scan",x,x[3])
                    for x in actual_safety_rows]
        result["nav2_raw_scan_source_join"]=assess_real_nav2_scan_delivery(
            raw_obs,safety_obs,
            restore_received_monotonic=restore_at,
            intrusion_ros_stamp=actual[1],
            minimum_clear_range_m=expect_surface+.15)
        save()
        print("AXIA_D07_H01_RAW_NAV2_SCAN_VS_SAFETY_SCAN_ONLY "+
              json.dumps(result["nav2_raw_scan_source_join"],sort_keys=True),
              flush=True)
        def post_restore_costmap_samples():
            # Only grids after the SECOND fresh /safety/scan of the restored
            # physical world; the old pre-restore snapshots are not evidence.
            with lock:
                rows=[(t,_lethal_near(g,obstacle_map),g)
                      for t,g in costmaps if t>restored[0]]
            return [(t,n,g) for t,n,g in rows if n is not None]
        restored_grid_holder={"grid":None}
        def cleared_grid():
            rows=post_restore_costmap_samples()
            if len(rows)<2:
                return None
            if rows[-1][1]!=original_grid[1] or rows[-2][1]!=original_grid[1]:
                return None
            verdict=costmap_roundtrip_evidence(
                original_grid[1],grid[1],rows[-1][1],
                native_restore_ack=bool(restore_ack),
                post_restore_scan_advanced=(restored[1]>actual[1]),
                post_restore_costmap_samples=len(rows))
            if verdict["status"]!="LETHAL_COUNT_RETURNED_NO_GOAL":
                return None
            restored_grid_holder["grid"]=rows[-1][2]
            restored_grid_holder["row"]=rows[-1]
            return verdict
        try:
            roundtrip=until(cleared_grid,"ACTUAL_COSTMAP_CLEARING")
        except RuntimeError:
            with lock:
                after_restoration=[(t,g) for t,g in costmaps if t>restore_at]
            restored_costmap_lethal_cells=(
                _lethal_near(after_restoration[-1][1],obstacle_map)
                if after_restoration else None)
            first={
                "reason":"ACTUAL_COSTMAP_CLEARING_TIMEOUT",
                "baseline_costmap_lethal_cells":original_grid[1],
                "intrusion_costmap_lethal_cells":grid[1],
                "restored_costmap_lethal_cells":restored_costmap_lethal_cells,
                "post_restore_scan_stamp":restored[1],
                "post_restore_scan_range_m":restored[3],
                "post_restore_costmap_samples":len(after_restoration),
                "obstacle_model_restore_ack":bool(restore_ack),
                "goal_sent":False,
            }
            # Real L2 #43575697256: 41 -> 121 -> 46 at timeout.
            # Preserve the ACTUAL first costmap cell differences even when
            # the count-only clearing predicate never becomes true.
            recent_rows=post_restore_costmap_samples()
            if len(recent_rows)>=2:
                newest=recent_rows[-1]
                # The previous public L2 reported ONE residual lethal cell,
                # but only its count: no physical coordinate or persistence
                # across the six fresh published costmaps. Observe exact
                # native cells and Grid header stamps after the clear scan.
                # This remains diagnostic-only, not an ObstacleLayer fix or
                # permission to send a NavigateToPose / final cmd_vel.
                post_restore_lethal_history=trace_post_restore_lethal_history(
                    _drift_payload(baseline_pairs[0][0],baseline_pairs[0][2]),
                    _drift_payload(baseline_pairs[1][0],baseline_pairs[1][2]),
                    _drift_payload(grid[0],grid[2]),
                    [_drift_payload(t,g) for t,_,g in recent_rows[-12:]],
                    obstacle_map_xy=obstacle_map,
                    clear_scan_received_monotonic=restored[0],
                    clear_scan_stamp=restored[1])
                result["post_restore_lethal_history"]=post_restore_lethal_history
                print("AXIA_D07_H01_FIRST_NEW_LETHAL_CELL_HISTORY "+
                      json.dumps(post_restore_lethal_history,sort_keys=True),
                      flush=True)
                spatial=costmap_spatial_diff(
                    _grid_payload(original_grid[2]),
                    _grid_payload(newest[2]),
                    obstacle_map_xy=obstacle_map)
                result["costmap_spatial"]=spatial
                drift=assess_spatial_drift(
                    _drift_payload(baseline_pairs[0][0],baseline_pairs[0][2]),
                    _drift_payload(baseline_pairs[1][0],baseline_pairs[1][2]),
                    _drift_payload(grid[0],grid[2]),
                    _drift_payload(newest[0],newest[2]),
                    obstacle_map_xy=obstacle_map)
                result["costmap_natural_drift"]=drift
                roi=assess_roi_clearing(
                    _drift_payload(baseline_pairs[0][0],baseline_pairs[0][2]),
                    _drift_payload(baseline_pairs[1][0],baseline_pairs[1][2]),
                    _drift_payload(grid[0],grid[2]),
                    _drift_payload(newest[0],newest[2]),
                    obstacle_map_xy=obstacle_map)
                result["costmap_roi_clearing"]=roi
                _raw_topic=_drift_payload(newest[0],newest[2])
                result["native_layer_attribution"]=_native_costmap_layer_probe(
                    node,_raw_topic,
                    _roi_native_layer_indices(_raw_topic,roi,obstacle_map,
                    lethal_history=result.get("post_restore_lethal_history")),
                    baseline_native=native_baseline_layers)
                # Reuse exactly the same bounded diagnostic on BOTH
                # actual Costmap failure paths; original first timeout wins.
                result["post_native_costmap_catchup"]=_observe_native_published_catchup(
                    _raw_topic,result["native_layer_attribution"],costmaps,lock)
                save()
                print("AXIA_D07_H01_POST_NATIVE_COSTMAP_PUBLISH_CATCHUP "+
                      json.dumps(result["post_native_costmap_catchup"],sort_keys=True),
                      flush=True)
                print("AXIA_D07_H01_NATIVE_LAYER_FIRST_RESIDUE_BOUNDARY "+
                      json.dumps(result["native_layer_attribution"],sort_keys=True),
                      flush=True)
                print("AXIA_D07_H01_REAL_ROI_CLEARING_DIAGNOSTIC "+
                      json.dumps(roi,sort_keys=True),flush=True)
                # CI wipes private evidence after the job. Print only
                # bounded factual cell coordinates/costs before fail-closed
                # timeout so the FIRST spatial boundary is reviewable.
                print("AXIA_D07_H01_REAL_COSTMAP_DRIFT_DIAGNOSTIC "+
                      json.dumps(drift,sort_keys=True),flush=True)
                first_drift_boundary={
                    "status":drift["status"],
                    "reason":drift["reason"],
                    "first_invalid_boundary":drift["first_invalid_boundary"],
                    "natural_drift_cells":drift.get("natural_drift_cells"),
                    "unexplained_cell_count":drift.get("unexplained_cell_count"),
                    "residual_lethal_near_obstacle":
                        drift.get("residual_lethal_near_obstacle"),
                    "unexplained_near_obstacle_count":
                        drift.get("unexplained_near_obstacle_count"),
                    "unexplained_outside_obstacle_count":
                        drift.get("unexplained_outside_obstacle_count"),
                    "first_unexplained_details":
                        drift.get("first_unexplained_details",[]),
                    "different_cell_count":spatial.get("different_cell_count"),
                    "changed_inside_0p75m_obstacle":
                        spatial.get("changed_inside_0p75m_obstacle"),
                    "baseline_costmap_lethal_cells":original_grid[1],
                    "restored_costmap_lethal_cells":restored_costmap_lethal_cells,
                    "goal_sent":False,
                }
                result["first_drift_boundary"]=first_drift_boundary
                print("AXIA_D07_H01_FIRST_DRIFT_BOUNDARY "+
                      json.dumps(first_drift_boundary,sort_keys=True),
                      flush=True)
            else:
                first["spatial_evidence"]="INSUFFICIENT_FRESH_POST_RESTORE_GRIDS"
            result["first_clearing_boundary"]=first
            save()
            print("AXIA_D07_H01_FIRST_CLEARING_BOUNDARY "+
                  json.dumps(first,sort_keys=True),flush=True)
            raise
        result["costmap_roundtrip"]=roundtrip
        result["restored_costmap_lethal_cells"]=original_grid[1]
        # The .36m lethal COUNT may return to baseline while physical .75m
        # ROI has NEW lethal cells (real L2 #43591323956: count 0 but 3
        # new ROI lethal). Always preserve exact per-cell history, including
        # on the count-success branch, before evaluating the strict ROI.
        # No clearing command, simulated data, Goal or safety TTL changes.
        _post_restore_rows=post_restore_costmap_samples()
        result["post_restore_lethal_history"]=trace_post_restore_lethal_history(
            _drift_payload(baseline_pairs[0][0],baseline_pairs[0][2]),
            _drift_payload(baseline_pairs[1][0],baseline_pairs[1][2]),
            _drift_payload(grid[0],grid[2]),
            [_drift_payload(t,g) for t,_,g in _post_restore_rows[-12:]],
            obstacle_map_xy=obstacle_map,
            clear_scan_received_monotonic=restored[0],
            clear_scan_stamp=restored[1])
        save()
        print("AXIA_D07_H01_FIRST_NEW_LETHAL_CELL_HISTORY "+
              json.dumps(result["post_restore_lethal_history"],sort_keys=True),
              flush=True)
        if result["post_restore_lethal_history"]["status"] != (
                "POST_RESTORE_ROI_RESIDUE_DIAGNOSTIC_ONLY"):
            raise RuntimeError("D07_H01_POST_CLEAR_CELL_HISTORY_PROVENANCE_HOLD")
        # Equal lethal-cell counts do NOT prove equal occupied coordinates or
        # inflation costs. Compare entire actual global Costmap cell array
        # before intrusion and after restoration; record SHA256 and first diff.
        spatial=costmap_spatial_diff(
            _grid_payload(original_grid[2]),
            _grid_payload(restored_grid_holder["grid"]),
            obstacle_map_xy=obstacle_map)
        result["costmap_spatial"]=spatial
        result["costmap_intrusion_spatial"]=costmap_spatial_diff(
            _grid_payload(original_grid[2]),_grid_payload(grid[2]),
            obstacle_map_xy=obstacle_map)
        save()
        print("AXIA_D07_H01_LETHAL_COUNT_ONLY_NO_GOAL "+
              json.dumps(roundtrip,sort_keys=True),flush=True)
        print("AXIA_D07_H01_COSTMAP_SPATIAL_DIAGNOSTIC "+
              json.dumps(spatial,sort_keys=True),flush=True)
        if spatial["status"]=="BLOCKED":
            raise RuntimeError("D07_H01_COSTMAP_SPATIAL_EVIDENCE_INVALID")
        # Compare both real untouched baselines, physical marking and
        # post-restoration Grid. Never infer natural drift from just the
        # lone baseline used in the historic 306-cell mismatch.
        drift=assess_spatial_drift(
            _drift_payload(baseline_pairs[0][0],baseline_pairs[0][2]),
            _drift_payload(baseline_pairs[1][0],baseline_pairs[1][2]),
            _drift_payload(grid[0],grid[2]),
            _drift_payload(restored_grid_holder["row"][0],
                           restored_grid_holder["row"][2]),
            obstacle_map_xy=obstacle_map)
        result["costmap_natural_drift"]=drift
        roi=assess_roi_clearing(
            _drift_payload(baseline_pairs[0][0],baseline_pairs[0][2]),
            _drift_payload(baseline_pairs[1][0],baseline_pairs[1][2]),
            _drift_payload(grid[0],grid[2]),
            _drift_payload(restored_grid_holder["row"][0],
                           restored_grid_holder["row"][2]),
            obstacle_map_xy=obstacle_map)
        result["costmap_roi_clearing"]=roi
        print("AXIA_D07_H01_REAL_ROI_CLEARING_DIAGNOSTIC "+
              json.dumps(roi,sort_keys=True),flush=True)
        save()
        print("AXIA_D07_H01_REAL_COSTMAP_DRIFT_DIAGNOSTIC "+
              json.dumps(drift,sort_keys=True),flush=True)
        roi_path_probe_gate=classify_readonly_roi_path_probe(
            roi,drift,roundtrip,
            native_restore_ack=bool(restore_ack),
            post_restore_scan_advanced=(restored[1]>actual[1]))
        result["roi_path_probe_gate"]=roi_path_probe_gate
        save()
        if (drift["spatial_restoration_proven"] is not True
                and roi_path_probe_gate["path_probe_allowed"] is not True):
            # Preserve the FIRST map violation; a later Planner result is
            # useful correlation but must not mask the initial failure.
            first_drift_boundary={
                "reason":drift["reason"],
                "status":drift["status"],
                "first_invalid_boundary":drift["first_invalid_boundary"],
                "natural_drift_cells":drift.get("natural_drift_cells"),
                "unexplained_cell_count":drift.get("unexplained_cell_count"),
                "residual_lethal_near_obstacle":
                    drift.get("residual_lethal_near_obstacle"),
                "goal_sent":False,
            }
            result["first_drift_boundary"]=first_drift_boundary
            save()
            print("AXIA_D07_H01_FIRST_DRIFT_BOUNDARY "+
                  json.dumps(first_drift_boundary,sort_keys=True),flush=True)
            try:
                last_probe=_compute(node,client,map_pose[:2],raw_official_paths)
                result["drift_correlated_planner"] = baseline_path_restoration(
                    before,last_probe,obstacle_map_xy=obstacle_map,
                    costmap_roundtrip_ready=True,
                    scan_stamp_advanced=(restored[1]>actual[1]))
                print("AXIA_D07_H01_DRIFT_CORRELATED_OFFICIAL_PATH "+
                      json.dumps(result["drift_correlated_planner"],sort_keys=True),
                      flush=True)
            except Exception as probe_error:
                result["drift_planner_probe_error"] = (
                    type(probe_error).__name__+":"+str(probe_error))
            _raw_topic=_drift_payload(
                restored_grid_holder["row"][0],restored_grid_holder["row"][2])
            result["native_layer_attribution"]=_native_costmap_layer_probe(
                node,_raw_topic,
                _roi_native_layer_indices(_raw_topic,roi,obstacle_map,
                    lethal_history=result.get("post_restore_lethal_history")),
                    baseline_native=native_baseline_layers)
            result["post_native_costmap_catchup"]=_observe_native_published_catchup(
                _raw_topic,result["native_layer_attribution"],costmaps,lock)
            print("AXIA_D07_H01_POST_NATIVE_COSTMAP_PUBLISH_CATCHUP "+
                  json.dumps(result["post_native_costmap_catchup"],sort_keys=True),
                  flush=True)
            print("AXIA_D07_H01_NATIVE_LAYER_FIRST_RESIDUE_BOUNDARY "+
                  json.dumps(result["native_layer_attribution"],sort_keys=True),
                  flush=True)
            save()
            raise RuntimeError("D07_H01_UNCLASSIFIED_COSTMAP_RESTORE_NO_GOAL")
        if roi_path_probe_gate["path_probe_allowed"] is not True:
            # A globally exact grid is NOT enough if native ROI clearing
            # provenance or fresh physical LaserScan is absent.
            result["first_roi_path_probe_boundary"]={
                "reason":roi_path_probe_gate["reason"],
                "status":roi_path_probe_gate["status"],
                "goal_sent":False}
            save()
            raise RuntimeError("D07_H01_ROI_CLEARING_PROVENANCE_HOLD_NO_GOAL")
        if drift["spatial_restoration_proven"] is not True:
            # Real public L2 #43590584866 had ZERO new lethal/excess ROI
            # but 312 unexplained global cells. The NEXT safety-relevant
            # boundary is actual official Planner Path restoration.
            # Do not claim clearing PASS, nor waive the Plan return check.
            result["global_drift_path_probe_only"]={
                "status":drift["status"],
                "unexplained_global_grid_cells":drift.get("unexplained_cell_count"),
                "roi_positive_excess":roi.get("positive_excess_near_obstacle"),
                "roi_new_lethal":roi.get("persistent_new_lethal_near_obstacle"),
                "goal_sent":False}
            save()
            print("AXIA_D07_H01_ROI_CLEAN_GLOBAL_DRIFT_PATH_PROBE_ONLY "+
                  json.dumps(result["global_drift_path_probe_only"],sort_keys=True),
                  flush=True)
        # Independent official PlannerServer may observe Costmap clearing
        # after the OccupancyGrid subscriber. Perform at most FOUR planning-
        # only ComputePathToPose requests; NEVER NavigateToPose or cmd_vel.
        path_restore_attempts=[]
        planner_cost_correlations=[]
        recovered=None
        for attempt in range(4):
            final_path=_compute(node,client,map_pose[:2],raw_official_paths)
            # Native /global_costmap/costmap source vs returned official Path.
            # Source callback time alone is NOT PlannerServer internal map
            # synchronization. Print bounded path-corridor cell costs before
            # interpreting the terminal path restoration error.
            with lock:
                costmap_before_result=[
                    (t,g) for t,g in costmaps
                    if restored[0]<t<final_path["received_at"]]
            if costmap_before_result:
                t,g=costmap_before_result[-1]
                correlation=correlate_official_path_cost(
                    _drift_payload(baseline_pairs[0][0],baseline_pairs[0][2]),
                    _drift_payload(baseline_pairs[1][0],baseline_pairs[1][2]),
                    _drift_payload(t,g),before,final_path,
                    obstacle_map_xy=obstacle_map)
            else:
                correlation={
                    "status":"COSTMAP_PLANNER_PROVENANCE_HOLD",
                    "reason":"NO_NEW_PUBLISHED_COSTMAP_BEFORE_PLANNER_RESULT",
                    "goal_sent":False,"motion_admitted":False,
                    "planner_internal_costmap_proven":False}
            planner_cost_correlations.append(correlation)
            result["planner_cost_correlations"]=planner_cost_correlations
            save()
            print("AXIA_D07_H01_REAL_PLANNER_COST_CORRELATION "+
                  json.dumps({"attempt":attempt+1,**correlation},
                             sort_keys=True),flush=True)
            path_check=baseline_path_restoration(
                before,final_path,obstacle_map_xy=obstacle_map,
                costmap_roundtrip_ready=(roundtrip["status"]=="LETHAL_COUNT_RETURNED_NO_GOAL"),
                scan_stamp_advanced=(restored[1]>actual[1]))
            path_restore_attempts.append({
                "attempt":attempt+1,
                "planner_result_at":final_path["received_at"],
                "status":path_check["status"],
                "reason":path_check["reason"],
                "baseline_path_min_m":path_check.get("baseline_path_min_m"),
                "restored_path_min_m":path_check.get("restored_path_min_m"),
                "path_return_delta_m":path_check.get("path_return_delta_m"),
                "restored_path_points":len(final_path["poses"]),
                "goal_sent":False,
            })
            if path_check["status"]=="RESTORED_OFFICIAL_NAV2_BASELINE_NO_GOAL":
                recovered=path_check
                break
            if attempt<3:
                time.sleep(.6)
        result["path_restore_attempts"]=path_restore_attempts
        # GUI ONLY: the previous actual public L2 had a fully restored
        # published and native master but FOUR official plans still detoured.
        # The native master read was AFTER those Planner actions. Wait for
        # two genuinely newer ROS Grid publications that equal EVERY raw
        # translated native master cell before exactly ONE extra official
        # ComputePathToPose. This is a read-only synchronization barrier,
        # NOT a change to the original Gate1 path/Costmap oracle or a TTL.
        if recovered is None and getattr(args,"gui",False):
            barrier_raw=_native_costmap_layer_maps(node)
            native_barrier=(
                barrier_raw.get("costmap")
                if isinstance(barrier_raw,dict) and "status" not in barrier_raw
                else None)
            source_received=(
                native_barrier.get("received_monotonic")
                if isinstance(native_barrier,dict) else None)
            source_stamp=(
                native_barrier.get("stamp")
                if isinstance(native_barrier,dict) else None)
            barrier={
                "status":"POST_NATIVE_FULL_GRID_BARRIER_HOLD",
                "reason":"NO_VALID_NATIVE_MASTER_BEFORE_PLANNER_REPROBE",
                "eligible_for_readonly_replan":False,
                "goal_sent":False,"motion_admitted":False,
                "planner_internal_costmap_proven":False}
            if (type(source_received) in (int,float)
                    and type(source_stamp) in (int,float)):
                last_evaluated=None
                barrier_deadline=time.monotonic()+9.0
                while time.monotonic()<barrier_deadline:
                    with lock:
                        fresh=[
                            (t,g) for t,g in costmaps
                            if t>source_received and
                            float(g.header.stamp.sec)+
                            float(g.header.stamp.nanosec)*1e-9>source_stamp]
                    fresh.sort(key=lambda x:x[0])
                    if len(fresh)>=2 and fresh[-1][0]!=last_evaluated:
                        last_evaluated=fresh[-1][0]
                        barrier=assess_full_published_native_barrier(
                            native_barrier,
                            [_drift_payload(t,g) for t,g in fresh[-2:]])
                        if barrier["eligible_for_readonly_replan"] is True:
                            break
                    time.sleep(.1)
            result["planner_native_full_barrier"]=barrier
            print("AXIA_D07_H01_POST_NATIVE_FULL_GRID_PLANNER_BARRIER "+
                  json.dumps(barrier,sort_keys=True),flush=True)
            if barrier["eligible_for_readonly_replan"] is True:
                final_path=_compute(node,client,map_pose[:2],
                                    raw_official_paths)
                last_check=baseline_path_restoration(
                    before,final_path,obstacle_map_xy=obstacle_map,
                    costmap_roundtrip_ready=(
                        roundtrip["status"]=="LETHAL_COUNT_RETURNED_NO_GOAL"),
                    scan_stamp_advanced=(restored[1]>actual[1]))
                path_restore_attempts.append({
                    "attempt":5,"phase":"AFTER_FULL_NATIVE_GRID_BARRIER",
                    "planner_result_at":final_path["received_at"],
                    "status":last_check["status"],
                    "reason":last_check["reason"],
                    "restored_path_points":len(final_path["poses"]),
                    "path_return_delta_m":last_check.get("path_return_delta_m"),
                    "goal_sent":False})
                print("AXIA_D07_H01_POST_BARRIER_OFFICIAL_PATH_ONLY "+
                      json.dumps(path_restore_attempts[-1],sort_keys=True),
                      flush=True)
                if last_check["status"]=="RESTORED_OFFICIAL_NAV2_BASELINE_NO_GOAL":
                    recovered=last_check
                    result["late_readonly_planner_restoration"]=(
                        "FULL_NATIVE_SOURCE_TOPIC_BARRIER_BEFORE_REPLAN")
            result["path_restore_attempts"]=path_restore_attempts
            save()
        if recovered is None:
            first={
                "reason":"OFFICIAL_NAV2_PATH_NOT_RESTORED_AFTER_COSTMAP",
                "first_attempt":path_restore_attempts[0],
                "last_attempt":path_restore_attempts[-1],
                "attempt_count":len(path_restore_attempts),
                "costmap_roundtrip":roundtrip["status"],
                "obstacle_model_restore_ack":bool(restore_ack),
                "goal_sent":False,
            }
            result["first_path_restoration_boundary"]=first
            _raw_topic=_drift_payload(
                restored_grid_holder["row"][0],restored_grid_holder["row"][2])
            # ONE read of the official native master at the first terminal
            # restore failure; share it with the existing bounded ROI audit.
            # GetCostmap is AFTER the last Planner reply and is not an atomic
            # internal PlannerServer snapshot. No ROS mutation or Goal.
            _post_planner_native=_native_costmap_layer_maps(node)
            result["native_layer_attribution"]=_native_costmap_layer_probe(
                node,_raw_topic,
                _roi_native_layer_indices(_raw_topic,roi,obstacle_map,
                    lethal_history=result.get("post_restore_lethal_history")),
                baseline_native=native_baseline_layers,
                raw_native=_post_planner_native)
            result["native_master_path_corridor"]=audit_native_master_path_corridor(
                native_baseline_layers.get("costmap")
                    if isinstance(native_baseline_layers,dict) else None,
                _post_planner_native.get("costmap")
                    if isinstance(_post_planner_native,dict) else None,
                before,final_path)
            result["full_native_master_restore"] = compare_full_native_master(
                native_baseline_layers.get("costmap")
                    if isinstance(native_baseline_layers,dict) else None,
                _post_planner_native.get("costmap")
                    if isinstance(_post_planner_native,dict) else None)
            print("AXIA_D07_H01_FULL_NATIVE_MASTER_RESTORE_ONLY "+
                  json.dumps(result["full_native_master_restore"],sort_keys=True),
                  flush=True)
            print("AXIA_D07_H01_NATIVE_ORIGINAL_PATH_CORRIDOR_AFTER_PLANNER "+
                  json.dumps(result["native_master_path_corridor"],sort_keys=True),
                  flush=True)
            print("AXIA_D07_H01_NATIVE_LAYER_FIRST_RESIDUE_BOUNDARY "+
                  json.dumps(result["native_layer_attribution"],sort_keys=True),
                  flush=True)
            save()
            print("AXIA_D07_H01_FIRST_PATH_RESTORE_BOUNDARY "+
                  json.dumps(first,sort_keys=True),flush=True)
            raise RuntimeError("D07_H01_BASELINE_PATH_NOT_RESTORED")
        result["baseline_path_restoration"]=recovered
        publish_phase("restored",final_path,restored[1],
                      float(restored_grid_holder["grid"].header.stamp.sec)+
                      float(restored_grid_holder["grid"].header.stamp.nanosec)*1e-9)
        save()
        print("AXIA_D07_H01_OFFICIAL_NAV2_BASELINE_PATH_RESTORED_NO_GOAL "+
              json.dumps(recovered,sort_keys=True),flush=True)
        if observer.snapshot(include_graph=False).get("odom_speed",0.) and abs(observer.snapshot(include_graph=False)["odom_speed"])>.01:
            raise RuntimeError("D07_H01_PREGOAL_ROBOT_MOVED")
        result.update(status=("D07_H01_REAL_NAV2_GEOMETRY_READY_NO_GOAL"
                              if result["contact_topic_proven"]
                              else "D07_H01_REAL_NAV2_GEOMETRY_CONTACT_HOLD_NO_GOAL"),
                      reason=("PHYSICAL_SCAN_COSTMAP_AND_OFFICIAL_NAV2_DETOUR_PROVEN"
                              if result["contact_topic_proven"]
                              else "CONTACT_TOPIC_UNAVAILABLE_GEOMETRY_ONLY_NO_GOAL"),
                      goal_sent=False,obstacle_restored_away=True,
                      restore_scan_stamp=restored[1],
                      before_path_points=len(before["poses"]),after_path_points=len(after["poses"]))
        save()
        print("AXIA_D07_H01_REAL_NAV2_GEOMETRY_NO_GOAL "+
              f"status={result['status']} before={len(before['poses'])} "+
              f"detour={len(after['poses'])} "+
              f"clearance={measured['after_min_m']:.3f} "+
              f"contact_ready={result['contact_topic_proven']}",flush=True)
        return result
    except Exception as exc:
        result.update(status="BLOCKED",reason=type(exc).__name__+":"+str(exc))
        save()
        print("AXIA_D07_H01_GEOMETRY_FAIL_CLOSED_NO_GOAL "+result["reason"],flush=True)
        raise
    finally:
        if moved:
            try:
                move(*original_world)
                print("AXIA_D07_H01_EMERGENCY_NO_GOAL_MODEL_RESTORED",flush=True)
            except Exception as err:
                print("AXIA_D07_H01_MODEL_RESTORE_NOT_PROVEN "+str(err),flush=True)
        # C36: genuine public student H01 L2 #44040942877 completed
        # real before/intrusion/restored then intermittently SIGABRT-ed while
        # destroying rclpy objects with the separate executor.spin daemon
        # still active. Quiesce it BEFORE ROS entity teardown; never treat
        # an unjoined worker as a successful live session.
        print("D07_H01_GEOMETRY_EXECUTOR_SHUTDOWN_BEGIN", flush=True)
        stopped=executor.shutdown(timeout_sec=8.0)
        th.join(timeout=8.0)
        if not stopped or th.is_alive():
            print("D07_H01_GEOMETRY_EXECUTOR_QUIESCENCE_BLOCKED",flush=True)
            raise RuntimeError("D07_H01_GEOMETRY_EXECUTOR_NOT_QUIESCENT")
        print("D07_H01_GEOMETRY_EXECUTOR_QUIESCENT",flush=True)
        observer.flush_events()
        node.destroy_subscription(scan_sub)
        node.destroy_subscription(map_sub)
        if visual_publisher is not None:
            node.destroy_publisher(visual_publisher)
        observer.close()
        node.destroy_node()
        rclpy.shutdown()
        print("D07_H01_GEOMETRY_ROS_CONTEXT_CLEAN_EXIT",flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--startup",required=True,type=Path)
    p.add_argument("--pregoal",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--gui",action="store_true",help="real classroom Path display, never moving Goal")
    p.add_argument("--gui-hold-s",type=int,default=int(os.environ.get("AXIA_D07_GUI_HOLD_S","10")))
    a=p.parse_args()
    if a.gui and not 5<=a.gui_hold_s<=15:
        raise SystemExit("D07_H01_GUI_HOLD_INVALID")
    try:
        run(a);return 0
    except Exception:return 2


if __name__=="__main__":
    sys.exit(main())
