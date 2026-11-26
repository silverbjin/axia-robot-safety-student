#!/usr/bin/env python3
"""Physical G07 preflight with Gazebo Harmonic, but NO Nav2 Goal or Fault.

Must run in the SAME shell partition and launched official Waffle as G07.
Proves preloaded world obstacle, actual set_pose ACK and changed ROS /safety/scan.
No synthetic scan, no assumed Gazebo service, no certified E-Stop claim.
"""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from p2_g07_spawn_contract import official_tb3_spawn
from p2_mvp_stop_geometry import STOP_DISPATCH_M, pregoal_stop_probe_acceptable
from p2_l3_gz_fixture import admit_preloaded as admit_preloaded_fixture, move as move_fixture, CONTACT_TOPIC, RADIUS


def scan_front(msg):
    if not isinstance(msg.angle_increment,(float,int)) or abs(msg.angle_increment)<1e-9:
        return None
    values=[v for i,v in enumerate(msg.ranges)
            if abs(msg.angle_min+i*msg.angle_increment)<=.18
            and math.isfinite(v) and msg.range_min<=v<=msg.range_max]
    return min(values) if values else None


def stop_observed(initial,measured,previous_front=None):
    # Require actual physical STOP <0.4m, not merely any changed scan.
    # Owner-matched CI 42786230200 observed 0.479m after 0.43m dispatch:
    # this is SLOWDOWN, and MUST NOT be mistaken for STOP. Also require
    # the new scan to be at least 5cm closer than the last position.
    if not (type(initial) in (int,float) and math.isfinite(initial)
            and type(measured) in (int,float) and math.isfinite(measured)
            and .14<=measured<.40 and initial-measured>=.10):
        return False
    if previous_front is not None:
        return (type(previous_front) in (int,float)
                and math.isfinite(previous_front)
                and previous_front-measured>=.05)
    return True


def gz_services(folder):
    try:
        process=subprocess.run(['gz','service','-l'],capture_output=True,text=True,timeout=12)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise RuntimeError('G07_GAZEBO_TRANSPORT_SERVICE_LIST_FAILED') from exc
    names=tuple(line.strip() for line in process.stdout.splitlines() if line.strip())
    diagnostics={'returncode':process.returncode,'gz_services':list(names),
                 'stdout':process.stdout[:6000],'stderr':process.stderr[:1200],
                 'gz_partition':os.environ.get('GZ_PARTITION','')}
    (folder/'gazebo_transport_services.json').write_text(
        json.dumps(diagnostics,sort_keys=True,indent=2)+'\n')
    if process.returncode != 0 or not all(
        name in names for name in ('/world/default/set_pose',)
    ):
        raise RuntimeError('G07_GAZEBO_SETPOSE_SERVICE_UNAVAILABLE:'
                           +'rc='+str(process.returncode)+' services='+str(len(names)))
    return names


def run(folder):
    if os.environ.get('ROS_DISTRO')!='jazzy' or os.environ.get('AXIA_P0_SIM_ONLY')!='1':
        raise RuntimeError('G07_REAL_JAZZY_SIM_ONLY_REQUIRED')
    if not os.environ.get('GZ_PARTITION','').startswith('axia_p2_'):
        raise RuntimeError('G07_ISOLATED_GAZEBO_PARTITION_REQUIRED')
    import rclpy
    from sensor_msgs.msg import LaserScan
    from rclpy.qos import qos_profile_sensor_data
    folder.mkdir(mode=0o700,exist_ok=False)
    os.chmod(folder,0o700)
    evidence=folder/'g07_physical_preflight.json'
    result={'status':'BLOCKED','goal_sent':False,'fault_injected':False,
            'gate_accepted':False,'certified_estop':False,
            'world_pose_source':'official_nav2_jazzy_tb3_simulation_launch',
            'native_contact_topic':CONTACT_TOPIC}
    rclpy.init()
    node=rclpy.create_node('axia_g07_physical_no_goal_probe')
    latest={'at':None,'value':None}
    def observed(message):
        value=scan_front(message)
        if value is not None:
            latest['at']=time.monotonic()
            latest['value']=value
    subscription=node.create_subscription(LaserScan,'/safety/scan',observed,qos_profile_sensor_data)
    def fresh_after(since,seconds,accept=lambda value: True):
        # A transport set_pose ACK precedes the next sensor scan. Ignore
        # fresh-but-not-yet-updated scans until the physical change is seen.
        limit=time.monotonic()+seconds
        while time.monotonic()<limit:
            rclpy.spin_once(node,timeout_sec=.1)
            if (latest['at'] is not None and latest['at']>since
                    and accept(latest['value'])):
                return latest['value']
        return None
    try:
        world_x,world_y,world_yaw=official_tb3_spawn()
        result['verified_official_world_spawn']=[world_x,world_y,world_yaw]
        services=gz_services(folder)
        result['gz_services']=list(services)
        print('G07_GAZEBO_SERVICE_DISCOVERY_PROVEN count='+str(len(services)),flush=True)
        initial=fresh_after(time.monotonic(),8.0,lambda v:v>.55)
        if initial is None or initial<=.55:
            raise RuntimeError('G07_BASELINE_FRONT_SCAN_NOT_CLEAR')
        result['baseline_front']=initial
        # Admit the 0.07m physical cylinder preloaded in the official world,
        # first far ahead of Waffle, then move into the front STOP zone.
        far=1.35+RADIUS
        x=world_x+far*math.cos(world_yaw);y=world_y+far*math.sin(world_yaw)
        fixture=admit_preloaded_fixture(x,y,folder,require_contact=False)
        result['fixture_ack']=bool(fixture['preloaded'])
        result['entity_preloaded_world']=True
        result['contact_topic_ack']=bool(fixture['contact_topic_proven'])
        result['collision_ground_truth_available']=False
        result['demo_scope']='SIMULATED_MVP_NO_CONTACT_CERTIFICATION'
        result['set_pose_ack']=bool(fixture['set_pose_ack'])
        # Observe a separate real physical SlowZone before StopZone, without
        # publishing any command or Nav2 Goal. Move ACK alone is not proof.
        mid=.65+RADIUS
        x=world_x+mid*math.cos(world_yaw);y=world_y+mid*math.sin(world_yaw)
        moved_at=time.monotonic()
        move_fixture(x,y)
        result['slowdown_pose_ack']=True
        slow=fresh_after(moved_at,8.0,
                         lambda v:.4<v<.75 and initial-v>=.10)
        if slow is None:
            raise RuntimeError('G07_REAL_MIDZONE_LASER_RESPONSE_UNVERIFIED')
        result['slowdown_front']=slow
        # MVP moving Goal uses a bounded stop dispatch distance (.43m), not
        # the original .52m that missed CM STOP in real Owner QrDCwq8W.
        # First validate the exact physical cylinder placement and real scan
        # while the Waffle remains stationary with NO Goal / NO Fault.
        dispatch=STOP_DISPATCH_M+RADIUS
        x=world_x+dispatch*math.cos(world_yaw)
        y=world_y+dispatch*math.sin(world_yaw)
        dispatch_started=time.monotonic()
        ack=move_fixture(x,y)
        dispatch_ack_at=time.monotonic()
        result['mvp_dispatch_pose_ack']=bool(ack)
        result['mvp_dispatch_ack_duration_sec']=dispatch_ack_at-dispatch_started
        dispatch_front=fresh_after(
            dispatch_ack_at,8.0,
            lambda v:pregoal_stop_probe_acceptable(v) and
            slow-v>=.08
        )
        result['mvp_dispatch_front']=dispatch_front
        result['mvp_dispatch_target_surface_m']=STOP_DISPATCH_M
        if dispatch_front is None:
            raise RuntimeError('G07_REAL_MVP_STOP_DISPATCH_SCAN_UNVERIFIED')
        print('G07_MVP_STOP_DISPATCH_REAL_LIDAR_PRECALIBRATED '
              +'front='+str(round(dispatch_front,3))
              +' target='+str(STOP_DISPATCH_M)
              +' NO_GOAL',flush=True)
        near=.34+RADIUS
        x=world_x+near*math.cos(world_yaw);y=world_y+near*math.sin(world_yaw)
        moved_at=time.monotonic()
        moved=move_fixture(x,y)
        near_ack_at=time.monotonic()
        result['near_pose_ack']=bool(moved)
        result['near_ack_duration_sec']=near_ack_at-moved_at
        stopped=fresh_after(
            near_ack_at,8.0,
            lambda v:stop_observed(initial,v,previous_front=dispatch_front))
        result['stopped_front']=stopped
        if stopped is None or not stop_observed(
                initial,stopped,previous_front=dispatch_front):
            raise RuntimeError('G07_REAL_LASER_OBSTACLE_RESPONSE_UNVERIFIED')
        # This proves a real simulated obstacle and LaserScan response only,
        # NOT absence of collisions (the native Contact topic was not proven).
        result['status']='G07_PHYSICAL_OBSTACLE_LASER_PROVEN'
        print('G07_THREE_ZONE_PHYSICAL_SCAN_PROVEN '
              +'clear='+str(round(initial,3))
              +' slow='+str(round(slow,3))
              +' stop='+str(round(stopped,3)),flush=True)
        print('G07_PHYSICAL_OBSTACLE_LASER_PROVEN '
              +'baseline='+str(round(initial,3))
              +' stop='+str(round(stopped,3))
              +' G07_ACCEPTED=false',flush=True)
        return 0
    except Exception as exc:
        result['reason']=type(exc).__name__+':'+str(exc)
        print('G07_PHYSICAL_PREFLIGHT_BLOCKED '+result['reason']+' G07_ACCEPTED=false',
              file=sys.stderr,flush=True)
        return 2
    finally:
        evidence.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        node.destroy_subscription(subscription)
        node.destroy_node()
        rclpy.shutdown()


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args(argv)
    return run(a.output)


if __name__=='__main__':
    raise SystemExit(main())
