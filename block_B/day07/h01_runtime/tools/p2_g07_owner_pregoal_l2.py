#!/usr/bin/env python3
"""Actual Owner-matched PRE-GOAL static Gazebo obstacle/LaserScan L2, no Goal.

One isolated existing Harmonic server (not a synthetic fixture). Moves the
preloaded world cylinder once, before any Goal. Validates two independent,
strictly newer LiDAR samples and stationary odom; no /cmd_vel or Fault.
"""
import argparse
from collections import deque
import json
import math
import os
from pathlib import Path
import subprocess
import time

from p2_g07_relocated_no_goal_probe import DEMO_WORLD_POSE, sector_min
from p2_g07_owner_prepositioned import pregoal_side_obstacle_ready
from p2_l3_gz_fixture import admit_preloaded as admit_preloaded_fixture


def build_pregoal_baseline(*, front_m, side_m, scan_topic,
                           publisher_identity, scan_frame_id,
                           scan_header_stamp, scan_host_receive_time,
                           gazebo_robot_world_pose=None,
                           initial_obstacle_world_pose=None):
    """Pure ROS-free record. Never infer world pose from AMCL/odom or set_pose.

    This record is written BEFORE the first physical clearance exception.
    Unknown Gazebo entity poses remain null until independently measured.
    """
    known = (type(front_m) in (int, float) and math.isfinite(front_m)
             and type(side_m) in (int, float) and math.isfinite(side_m))
    clear = known and front_m > .75 and side_m > 1.20
    failure = ("NONE" if clear else
               "OWNER_PREGOAL_NOT_CLEAR_BEFORE_FIXTURE" if known else
               "OWNER_PREGOAL_BASELINE_SCAN_ODOM_ABSENT")
    return {
        "schema": "axia_g07_owner_pregoal_baseline_v1",
        "status": "CLEAR" if clear else "BLOCKED",
        "first_failure": failure,
        "scan_topic": scan_topic,
        "publisher_identity": publisher_identity,
        "scan_frame_id": scan_frame_id,
        "scan_header_stamp": scan_header_stamp,
        "scan_host_receive_time": scan_host_receive_time,
        "front_m": front_m,
        "side_m": side_m,
        "required_front_m": .75,
        "required_side_m": 1.20,
        "gazebo_robot_world_pose": gazebo_robot_world_pose,
        "initial_obstacle_world_pose": initial_obstacle_world_pose,
        "goal_sent": False,
        "certified_estop": False,
    }


def save_pregoal_baseline(outdir, report):
    """Persist source evidence before any clearance exception is raised."""
    (outdir / "pregoal_baseline.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")


def parse_gz_model_pose(output):
    """Parse documented 'gz model -m NAME --pose' XYZ+RPY. Never infer poses."""
    if not isinstance(output, str):
        return None
    marker = "- Pose [ XYZ (m) ] [ RPY (rad) ]:"
    if output.count(marker) != 1:
        return None
    rows = output.split(marker, 1)[1].strip().splitlines()
    if len(rows) < 2:
        return None
    values = []
    for line in rows[:2]:
        line = line.strip()
        if not (line.startswith("[") and line.endswith("]")):
            return None
        # Gazebo Harmonic CLI uses whitespace; retain pipe-form support.\n        parts = line[1:-1].replace("|", " ").split()
        if len(parts) != 3:
            return None
        try:
            numbers = [float(x) for x in parts]
        except ValueError:
            return None
        if not all(math.isfinite(x) for x in numbers):
            return None
        values.extend(numbers)
    return dict(zip(("x", "y", "z", "roll", "pitch", "yaw"), values))


def _read_only_gazebo_world_poses(outdir):
    """On physical clearance BLOCKED only; bounded low-priority model state.

    Every query retains short stdout/stderr; an unresponsive Gazebo remains
    UNKNOWN. Does not change world, fixture, sensors, or Goal authority.
    """
    result = {}
    for model, field in (("turtlebot3_waffle", "gazebo_robot_world_pose"),
                         ("axia_p2_g07_obstacle", "initial_obstacle_world_pose")):
        raw = "GAZEBO_MODEL_POSE_NOT_VERIFIED"
        try:
            proc = subprocess.run(
                ["nice", "-n", "19", "gz", "model", "-m", model, "--pose"],
                text=True, capture_output=True, timeout=5, check=False)
            raw = ("exit=" + str(proc.returncode) + "\n" +
                   (proc.stdout + proc.stderr)[:6000])
            pose = (parse_gz_model_pose(proc.stdout)
                    if proc.returncode == 0 and "- Name: " + model in proc.stdout
                    else None)
        except (OSError, subprocess.TimeoutExpired) as exc:
            pose = None
            raw = type(exc).__name__ + ":GAZEBO_MODEL_POSE_NOT_VERIFIED"
        (outdir / ("gz_pose_" + model + ".log")).write_text(
            raw + "\n", encoding="utf-8")
        result[field] = pose
    return result


def run(outdir):
    if (os.environ.get("ROS_DISTRO")!="jazzy" or
        os.environ.get("AXIA_P0_SIM_ONLY")!="1" or
        not os.environ.get("GZ_PARTITION","").startswith("axia_p2_")):
        raise RuntimeError("OWNER_PREGOAL_SIMULATION_ENV_INVALID")
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan
    from nav_msgs.msg import Odometry
    outdir.mkdir(parents=True,exist_ok=False,mode=0o700)
    os.chmod(outdir,0o700)
    rclpy.init()
    node=rclpy.create_node("axia_g07_owner_pregoal_l2_observer")
    scans=deque(maxlen=80)
    raw_scans=deque(maxlen=80)
    speeds=deque(maxlen=80)
    def on_scan(msg):
        side=sector_min(msg)
        values=[v for i,v in enumerate(msg.ranges)
                if abs(msg.angle_min+i*msg.angle_increment)<=.18
                and type(v) in (int,float) and math.isfinite(v)
                and msg.range_min<=v<=msg.range_max]
        if side is None or not values:return
        stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
        if math.isfinite(stamp):
            scans.append((time.monotonic(),stamp,min(values),side,
                          msg.header.frame_id,time.time(),
                          msg.angle_min,msg.angle_max,msg.angle_increment))
    def on_raw_scan(msg):
        side=sector_min(msg)
        values=[v for i,v in enumerate(msg.ranges)
                if abs(msg.angle_min+i*msg.angle_increment)<=.18
                and type(v) in (int,float) and math.isfinite(v)
                and msg.range_min<=v<=msg.range_max]
        if side is not None and values:
            raw_scans.append({
                "scan_topic":"/scan", "frame_id":msg.header.frame_id,
                "stamp":msg.header.stamp.sec + msg.header.stamp.nanosec*1e-9,
                "host_receive_time":time.time(),
                "front_m":min(values), "side_m":side,
                "angle_min":msg.angle_min, "angle_max":msg.angle_max,
                "angle_increment":msg.angle_increment})
    def on_odom(msg):
        speeds.append((time.monotonic(),msg.twist.twist.linear.x,
                       msg.twist.twist.angular.z))
    subs=[
        node.create_subscription(LaserScan,"/safety/scan",on_scan,qos_profile_sensor_data),
        node.create_subscription(LaserScan,"/scan",on_raw_scan,qos_profile_sensor_data),
        node.create_subscription(Odometry,"/odom",on_odom,qos_profile_sensor_data),
    ]
    try:
        # Fail-closed custody: even missing initial Scan/Odom is preserved.
        save_pregoal_baseline(outdir, build_pregoal_baseline(
            front_m=None, side_m=None, scan_topic="/safety/scan",
            publisher_identity=None, scan_frame_id=None,
            scan_header_stamp=None, scan_host_receive_time=None))
        deadline=time.monotonic()+8
        while time.monotonic()<deadline and (len(scans)<3 or len(speeds)<3):
            rclpy.spin_once(node,timeout_sec=.15)
        if len(scans)<3 or len(speeds)<3:
            raise RuntimeError("OWNER_PREGOAL_BASELINE_SCAN_ODOM_ABSENT")
        before=scans[-1]
        endpoints=node.get_publishers_info_by_topic("/safety/scan")
        publishers=[{
            "node_name":info.node_name,
            "node_namespace":info.node_namespace,
            "endpoint_gid":bytes(info.endpoint_gid).hex(),
            "qos_reliability":str(info.qos_profile.reliability),
            "qos_durability":str(info.qos_profile.durability)
        } for info in endpoints]
        baseline=build_pregoal_baseline(
            front_m=before[2], side_m=before[3],
            scan_topic="/safety/scan",
            publisher_identity=publishers if publishers else None,
            scan_frame_id=before[4],
            scan_header_stamp=before[1],
            scan_host_receive_time=before[5],
            gazebo_robot_world_pose=None,
            initial_obstacle_world_pose=None)
        baseline.update({
            "scan_angle_min":before[6], "scan_angle_max":before[7],
            "scan_angle_increment":before[8],
            "raw_scan":raw_scans[-1] if raw_scans else None,
            "raw_scan_publishers":[{
                "node_name":p.node_name,
                "node_namespace":p.node_namespace,
                "endpoint_gid":bytes(p.endpoint_gid).hex(),
                "qos_reliability":str(p.qos_profile.reliability),
                "qos_durability":str(p.qos_profile.durability)}
                for p in node.get_publishers_info_by_topic("/scan")] or None,
            "ros_domain_id":os.environ.get("ROS_DOMAIN_ID"),
            "gz_partition":os.environ.get("GZ_PARTITION"),
        })
        save_pregoal_baseline(outdir, baseline)
        if baseline["status"] != "CLEAR":
            baseline.update(_read_only_gazebo_world_poses(outdir))
            save_pregoal_baseline(outdir, baseline)
            raise RuntimeError("OWNER_PREGOAL_NOT_CLEAR_BEFORE_FIXTURE")
        # Exact same Owner function and coordinates; Gazebo native set_pose ACK
        # occurs BEFORE any Nav2 Goal. No second Gazebo move after this.
        fixture=admit_preloaded_fixture(*DEMO_WORLD_POSE,outdir,require_contact=False)
        ack_at=time.monotonic()
        qualified=[]
        deadline=ack_at+9
        last_stamp=before[1]
        while time.monotonic()<deadline:
            rclpy.spin_once(node,timeout_sec=.1)
            if not scans or not speeds:continue
            t,stamp,front,side,*_=scans[-1]
            _,vx,wz=speeds[-1]
            valid=(
                stamp>last_stamp and
                pregoal_side_obstacle_ready(
                    side_m=side,front_m=front,laser_at=t,
                    pose_ack_at=ack_at,now=time.monotonic(),
                    odom_vx=vx,odom_wz=wz,goal_sent=False)
            )
            if valid and (not qualified or stamp>qualified[-1][1]):
                qualified.append((t,stamp,front,side,vx,wz))
            elif not valid:
                qualified.clear()
            if len(qualified)>=2:break
        report={
            "schema":"axia_g07_owner_pregoal_physical_l2_v1",
            "status":"P2_G07_OWNER_PREGOAL_L2_READY_NO_GOAL" if len(qualified)>=2 else "BLOCKED",
            "world_xy":list(DEMO_WORLD_POSE),
            "native_set_pose_ack":bool(fixture.get("set_pose_ack")),
            "post_ack_distinct_ros_scan_count":len(qualified),
            "front_m":qualified[-1][2] if qualified else None,
            "side_m":qualified[-1][3] if qualified else None,
            "stationary_odom_checked":bool(qualified),
            "goal_sent":False,"fault_injected":False,"gate_accepted":False,
            "certified_estop":False,"physical_moving_stop_verified":False,
            "collision_ground_truth":False,
        }
        (outdir/"owner_pregoal_l2.json").write_text(
            json.dumps(report,sort_keys=True,indent=2)+"\n")
        if len(qualified)<2:
            raise RuntimeError("OWNER_PREGOAL_TWO_FRESH_PHYSICAL_LASERSCAN_REQUIRED")
        print("AXIA_G07_OWNER_PREGOAL_PHYSICAL_L2_PASS_NO_GOAL "+
              f"front_m={report['front_m']:.3f} side_m={report['side_m']:.3f}",flush=True)
        return report
    finally:
        for sub in subs:node.destroy_subscription(sub)
        node.destroy_node()
        rclpy.shutdown()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        run(args.output)
        return 0
    except (OSError,ValueError,RuntimeError) as exc:
        print("AXIA_G07_OWNER_PREGOAL_PHYSICAL_L2_BLOCKED "+
              type(exc).__name__+":"+str(exc),flush=True)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
