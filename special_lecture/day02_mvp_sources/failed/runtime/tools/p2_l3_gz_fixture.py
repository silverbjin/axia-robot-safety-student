#!/usr/bin/env python3
"""Simulator-only *physical* G07 cylinder and native Gazebo contact sensor.

Fails closed if expected /world/default UserCommands services or contact
publisher are absent. No ROS command publisher, Goal, or certifiable E-Stop.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

NAME = 'axia_p2_g07_obstacle'
CONTACT_TOPIC = '/axia_p2_g07/contacts'
RADIUS = 0.07
Z = 0.24


def sdf_model():
    return '''<?xml version="1.0"?>
<sdf version="1.9"><model name="axia_p2_g07_obstacle">
  <static>true</static><link name="obstacle_link">
    <collision name="obstacle_collision"><geometry>
      <cylinder><radius>0.07</radius><length>0.48</length></cylinder>
    </geometry></collision>
    <visual name="obstacle_visual"><geometry>
      <cylinder><radius>0.07</radius><length>0.48</length></cylinder>
    </geometry><material><diffuse>1 0.15 0.12 1</diffuse></material></visual>
    <sensor name="axia_contact" type="contact"><always_on>true</always_on>
      <update_rate>30</update_rate><topic>/axia_p2_g07/contacts</topic>
      <contact><collision>obstacle_collision</collision></contact>
    </sensor>
  </link>
  <plugin filename="gz-sim-touchplugin-system" name="gz::sim::systems::TouchPlugin">
    <target>turtlebot3_waffle</target><namespace>axia_p2_g07</namespace>
    <time>0.001</time><enabled>true</enabled>
  </plugin>
</model></sdf>
'''


def _gz(argv, timeout=8, *, low_priority=False):
    # G07's ONE real native STOP service request forks an expensive gz CLI
    # while Nav2 publishes CM->Guard at a strict 150ms TTL. CI real runs
    # #43139031871 / #43141038305 measured 163/169ms CM gaps during STOP.
    # Keep original G05/G06 Gazebo calls unchanged. Constrain only this
    # low-priority CLI child to one available core when >=2 are available,
    # leaving other cores schedulable for the safety graph. This is a
    # candidate contention mitigation, not proof of fixed delivery timing.
    prefix = ['gz']
    if low_priority:
        prefix = ['nice','-n','19','gz']
        try:
            allowed = os.sched_getaffinity(0)
        except (AttributeError, OSError):
            allowed = ()
        if len(allowed) >= 2 and shutil.which('taskset'):
            prefix = ['nice','-n','19','taskset','-c',str(max(allowed)),'gz']
    result = subprocess.run([*prefix, *argv], capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError('GAZEBO_SERVICE_FAILED:'+str(result.returncode))
    return result.stdout + result.stderr


def _service(name, message, req):
    info = _gz(['service', '-is', '/world/default/'+name], timeout=6)
    if req not in info or 'gz.msgs.Boolean' not in info:
        raise ValueError('GAZEBO_SERVICE_TYPE_MISMATCH:'+name)
    result = _gz(['service','-s','/world/default/'+name,'--reqtype',req,
                  '--reptype','gz.msgs.Boolean','--timeout','5000','--req',message],timeout=10)
    if not re.search(r'\bdata:\s*true\b', result, re.I):
        raise ValueError('GAZEBO_SERVICE_NOT_ACKNOWLEDGED:'+name)
    return result


def _valid_xy(x,y,*,demo_corridor=False):
    if any(type(t) not in (int,float) or not math.isfinite(t) for t in (x,y)):
        raise ValueError('INVALID_OBSTACLE_POSE')
    if demo_corridor:
        # Opt-in G07-only sandbox lane; the relative map/odom/world anchor
        # and a bounded robot center are checked BEFORE calling move().
        # No safety polygons, hardware limits or static world changed.
        if not (-2.6 <= x <= -1.0 and -0.95 <= y <= 1.55):
            raise ValueError('UNAPPROVED_G07_DEMO_ZONE_OUT_OF_BOUNDS')
    else:
        # Existing immutable G05/G06/G07 world placement contract.
        if not (-2.6 <= x <= -0.4 and -1.3 <= y <= 0.3):
            raise ValueError('UNAPPROVED_G07_ZONE_OUT_OF_BOUNDS')



def _await_contact_topic(folder, max_attempts=20, pause_sec=.2, required=True):
    """Gazebo create ACK precedes asynchronous SDF sensor activation.

    Require the exact native contact sensor topic. Retain the last discovery
    response and alternatives for diagnosis; never infer a zero collision.
    """
    if not 1<=max_attempts<=25 or not 0<=pause_sec<=.5:
        raise ValueError('G07_CONTACT_PROBE_BOUNDS_INVALID')
    latest=''
    seen=[]
    for attempt in range(max_attempts):
        latest=_gz(['topic','-l'],timeout=5)
        seen=[x.strip() for x in latest.splitlines() if x.strip()]
        found=CONTACT_TOPIC in seen
        (folder/'g07_topics_after_spawn.log').write_text(latest)
        record={'attempts':attempt+1,'contact_found':found,
                'contact_topic':CONTACT_TOPIC,'topic_count':len(seen),
                'other_contact_topics':[x for x in seen if 'contact' in x.lower()]}
        (folder/'g07_contact_topic_probe.json').write_text(
            json.dumps(record,indent=2,sort_keys=True)+'\n')
        if found:return True
        if attempt+1 < max_attempts:time.sleep(pause_sec)
    if required:
        raise ValueError('CONTACT_TOPIC_NOT_PROVEN_AFTER_BOUNDED_WAIT')
    return False


def create(x,y,folder):
    _valid_xy(x,y)
    if not folder.is_dir() or (folder.stat().st_mode & 0o077):
        raise ValueError('PRIVATE_EVIDENCE_DIR_REQUIRED')
    filename = folder / 'g07_obstacle.sdf'
    with filename.open('x',encoding='utf-8') as stream:stream.write(sdf_model())
    request=f'sdf_filename: "{filename}", name: "{NAME}", pose: {{position: {{x: {x:.6f}, y: {y:.6f}, z: {Z}}}, orientation: {{w: 1}}}}'
    output=_service('create',request,'gz.msgs.EntityFactory')
    (folder/'g07_spawn_ack.log').write_text(output)
    # The create ACK confirms the entity request, not immediate sensor
    # advertisement. Poll for a bounded interval before failing closed.
    _await_contact_topic(folder)
    return {'created':True,'contact_topic':CONTACT_TOPIC,'x':x,'y':y,
            'collision_ground_truth':False,'gate_accepted':False}


def admit_preloaded(x,y,folder,require_contact=True):
    """Admit a preloaded physical cylinder and verified Gazebo set_pose ACK.

    Full acceptance mode requires native Contact topic. Educational MVP
    demo mode allows missing Contact topic but retains raw absence evidence,
    collision_ground_truth=False and never fabricates collision_count=0.
    """
    _valid_xy(x,y)
    if not folder.is_dir() or (folder.stat().st_mode & 0o077):
        raise ValueError('PRIVATE_EVIDENCE_DIR_REQUIRED')
    contact_present=_await_contact_topic(
        folder,max_attempts=20 if require_contact else 1,
        pause_sec=.2 if require_contact else 0.0,required=require_contact)
    reply=move(x,y)
    (folder/'g07_preloaded_pose_ack.log').write_text(reply)
    return {'preloaded':True,'set_pose_ack':True,
            'created_dynamically':False,
            'contact_topic':CONTACT_TOPIC if contact_present else None,
            'contact_topic_proven':bool(contact_present),
            'x':x,'y':y,
            'collision_ground_truth':False,'gate_accepted':False}


def move(x,y,*,demo_corridor=False):
    _valid_xy(x,y,demo_corridor=demo_corridor)
    request=(f'name: "{NAME}", position: {{x: {x:.6f}, y: {y:.6f}, z: {Z}}}, '
             'orientation: {w: 1}')
    return _service('set_pose',request,'gz.msgs.Pose')


def move_ci_verified(x, y, *, sim_env, pregoal_native_verified,
                     owner_admitted=False):
    """One bounded low-priority native set_pose after real pre-Goal type proof.

    The public CI has already exercised the SAME /world/default/set_pose
    service/type/Boolean ACK before Goal. Avoid repeat `gz service -is` while
    the Nav2 Goal is moving, and keep the real native ACK a hard gate.
    Original Owner/G05/G06 move() still performs both service checks.
    """
    required={
        'GITHUB_ACTIONS':'true',
        'AXIA_G07_CI_SIM_GOAL_ALLOWED':'1',
        'AXIA_P0_SIM_ONLY':'1',
        'AXIA_P2_G07_PHYSICAL_PREFLIGHT':'1',
    }
    if owner_admitted:
        # Owner can use the same ONE native STOP request only AFTER the
        # shared runner has verified exact SHA + controlling-TTY approval
        # + three owned process PIDs. This transport helper cannot approve
        # any Goal; it enforces a second simulation-only boundary.
        required={
            'AXIA_G07_OWNER_COMMON_RUNNER_AUTHORIZED':'1',
            'AXIA_P0_SIM_ONLY':'1',
            'ROS_DISTRO':'jazzy',
        }
        if sim_env.get('GITHUB_ACTIONS')=='true':
            raise ValueError('OWNER_NATIVE_STOP_CANNOT_USE_CI_SCOPE')
    if (not hasattr(sim_env, 'get')
            or any(sim_env.get(key)!=value for key,value in required.items())
            or pregoal_native_verified is not True):
        raise ValueError('CI_NATIVE_STOP_PREGOAL_SCOPE_NOT_ADMITTED')
    _valid_xy(x,y,demo_corridor=True)
    request=(f'name: "{NAME}", position: {{x: {x:.6f}, y: {y:.6f}, z: {Z}}}, '
             'orientation: {w: 1}')
    response=_gz([
        'service','-s','/world/default/set_pose','--reqtype','gz.msgs.Pose',
        '--reptype','gz.msgs.Boolean','--timeout','5000','--req',request,
    ], timeout=10, low_priority=True)
    if not re.search(r'\bdata:\s*true\b',response,re.I):
        raise ValueError('GAZEBO_SERVICE_NOT_ACKNOWLEDGED:set_pose')
    return response


def main():
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['create','move'])
    p.add_argument('--x',type=float,required=True)
    p.add_argument('--y',type=float,required=True)
    p.add_argument('--evidence-dir',type=Path)
    a=p.parse_args()
    try:
        if a.action=='create':
            if a.evidence_dir is None:raise ValueError('EVIDENCE_DIR_REQUIRED')
            result=create(a.x,a.y,a.evidence_dir)
        else:
            result={'pose_ack':True,'service_reply':move(a.x,a.y),
                    'collision_ground_truth':False,'gate_accepted':False}
        print(json.dumps(result,sort_keys=True))
        return 0
    except (ValueError,RuntimeError,OSError,subprocess.TimeoutExpired) as e:
        print('P2_G07_FIXTURE_BLOCKED:'+str(e))
        return 2

if __name__=='__main__':raise SystemExit(main())
