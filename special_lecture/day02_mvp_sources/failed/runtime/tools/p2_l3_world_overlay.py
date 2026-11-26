#!/usr/bin/env python3
"""G07-only original TB3 sandbox world overlay: add official Gazebo Contact system.

The upstream world is never overwritten. No robot/Navigation/CM code copied.
Only this exact registered plugin is added; all other world content intact.
"""
import argparse
import hashlib
import os
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
from p2_l3_gz_fixture import sdf_model, NAME, RADIUS, Z

CONTACT_PLUGIN = '''    <plugin filename="gz-sim-contact-system"
            name="gz::sim::systems::Contact"/>\n'''


def patch_world(source, *, task03_ecm=False):
    if not isinstance(source,str) or source.count('<world name="default">')!=1:
        raise ValueError('EXPECTED_ONE_OFFICIAL_DEFAULT_WORLD')
    if source.count('</world>')!=1:
        raise ValueError('EXPECTED_ONE_WORLD_CLOSURE')
    if 'gz::sim::systems::Contact' in source:
        raise ValueError('DUPLICATED_CONTACT_PLUGIN')
    if 'gz::sim::systems::UserCommands' not in source:
        raise ValueError('MISSING_GAZEBO_USER_COMMANDS')
    if NAME in source:
        raise ValueError('DUPLICATED_G07_PHYSICAL_FIXTURE')
    # Gazebo Harmonic dynamically spawned Contact sensors may not be
    # registered (gz-sim #2223 / #3295). Load the physical obstacle and
    # sensor as part of the world BEFORE Gazebo starts, then set_pose only.
    model=ET.fromstring(sdf_model()).find('model')
    if model is None or model.get('name')!=NAME:
        raise ValueError('G07_SDF_MODEL_NOT_UNIQUE')
    pose=ET.Element('pose')
    pose.text=(str(round(-2.0+1.35+RADIUS,2))
               +' -0.5 '+str(Z)+' 0 0 0')
    model.insert(0,pose)
    fixture=ET.tostring(model,encoding='unicode')
    # The existing UserCommands plugin comes first; Contact follows it,
    # then the physical sensor-bearing model in the world SDF.
    plugin = ('''    <plugin filename="libaxia_g07_s02_ecm_witness.so"
            name="axia::G07S02Witness"/>\n''' if task03_ecm else '')
    return source.replace('</world>',CONTACT_PLUGIN+plugin+'    '+fixture+'\n  </world>')


def owner_ecm_witness_scope(env, kernel_release, actual_source_sha):
    """Read-only S02 witness scope for real WSL2 Owner, NOT Goal admission.

    The world overlay runs BEFORE manual TTY authorization. This only adds
    an already verified Contact sensor, never sends Goal/fault/motion.
    TTY/PID/UUID admission remains in the existing moving runner.
    """
    if not isinstance(env,dict) and not hasattr(env,"get"):
        return False
    expected=env.get("AXIA_G07_TASK04_EXPECTED_STUDENT_SHA")
    domain=env.get("ROS_DOMAIN_ID")
    partition=env.get("GZ_PARTITION")
    return bool(
        isinstance(expected,str) and re.fullmatch(r"[a-f0-9]{40}",expected)
        and actual_source_sha==expected
        and isinstance(kernel_release,str)
        and ("microsoft" in kernel_release.lower() or "wsl" in kernel_release.lower())
        and env.get("GITHUB_ACTIONS")!="true"
        and env.get("AXIA_G07_CI_SIM_GOAL_ALLOWED")!="1"
        and env.get("AXIA_G07_TASK04_OWNER_MOVING_L3")=="1"
        and env.get("AXIA_P0_SIM_ONLY")=="1"
        and env.get("AXIA_P2_G07_PHYSICAL_PREFLIGHT")=="1"
        and env.get("ROS_DISTRO")=="jazzy"
        and isinstance(domain,str) and domain.isascii() and domain.isdecimal()
        and 0<=int(domain)<=101
        and isinstance(partition,str)
        and re.fullmatch(r"axia_p2_[A-Za-z0-9_]+",partition)
    )


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--manifest',required=True,type=Path)
    a=p.parse_args(argv)
    try:
        raw=a.source.read_bytes()
        task03=os.environ.get('AXIA_G07_TASK03_ECM_WITNESS')=='1'
        if task03:
            # Preserve the already-successful public Actions scope verbatim.
            required={'GITHUB_ACTIONS':'true','AXIA_P0_SIM_ONLY':'1',
                      'AXIA_P2_G07_PHYSICAL_PREFLIGHT':'1'}
            ci=(all(os.environ.get(k)==v for k,v in required.items())
                and (os.environ.get('AXIA_G07_CI_SIM_GOAL_ALLOWED')=='1' or
                     os.environ.get('AXIA_D07_H01_CONTACT_CALIBRATION_ONLY')=='1'))
            owner=False
            if (os.environ.get('AXIA_G07_TASK04_OWNER_MOVING_L3')=='1'
                    and os.environ.get('GITHUB_ACTIONS')!='true'):
                # Exact public Student source and genuine WSL kernel. This
                # authorizes only the read-only Contact witness, not Goal.
                runtime=Path(__file__).resolve().parents[1]
                actual=subprocess.check_output(
                    ['git','-C',str(runtime),'rev-parse','HEAD'],
                    text=True,timeout=5).strip()
                kernel=Path('/proc/sys/kernel/osrelease').read_text()
                owner=owner_ecm_witness_scope(os.environ,kernel,actual)
            if not (ci or owner):
                raise ValueError('TASK03_NATIVE_ECM_WITNESS_SCOPE_DENIED')
        new=patch_world(raw.decode('utf-8'), task03_ecm=task03)
        with a.output.open('x',encoding='utf-8') as f:f.write(new)
        with a.manifest.open('x',encoding='utf-8') as f:
            f.write(json.dumps({'original_sha256':hashlib.sha256(raw).hexdigest(),
              'overlay_sha256':hashlib.sha256(new.encode()).hexdigest(),
              'added_plugin':'gz::sim::systems::Contact',
              'task03_native_read_only_witness':task03,
              'raw_review_required':True,'gate_accepted':False},indent=2)+'\n')
        print('P2_G07_CONTACT_WORLD_OVERLAY_STATIC_ONLY')
        return 0
    except (OSError,ValueError,UnicodeError,subprocess.CalledProcessError,subprocess.TimeoutExpired) as e:
        print('P2_G07_WORLD_OVERLAY_BLOCKED:'+type(e).__name__)
        return 2

if __name__=='__main__':raise SystemExit(main())
