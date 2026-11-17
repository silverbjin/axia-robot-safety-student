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
import time

from p2_g07_relocated_no_goal_probe import DEMO_WORLD_POSE, sector_min
from p2_g07_owner_prepositioned import pregoal_side_obstacle_ready
from p2_l3_gz_fixture import admit_preloaded as admit_preloaded_fixture


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
            scans.append((time.monotonic(),stamp,min(values),side))
    def on_odom(msg):
        speeds.append((time.monotonic(),msg.twist.twist.linear.x,
                       msg.twist.twist.angular.z))
    subs=[
        node.create_subscription(LaserScan,"/safety/scan",on_scan,qos_profile_sensor_data),
        node.create_subscription(Odometry,"/odom",on_odom,qos_profile_sensor_data),
    ]
    try:
        deadline=time.monotonic()+8
        while time.monotonic()<deadline and (len(scans)<3 or len(speeds)<3):
            rclpy.spin_once(node,timeout_sec=.15)
        if len(scans)<3 or len(speeds)<3:
            raise RuntimeError("OWNER_PREGOAL_BASELINE_SCAN_ODOM_ABSENT")
        before=scans[-1]
        if before[2] <= .75 or before[3] <= 1.2:
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
            t,stamp,front,side=scans[-1]
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
