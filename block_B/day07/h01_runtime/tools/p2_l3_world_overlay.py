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
            required={'GITHUB_ACTIONS':'true','AXIA_P0_SIM_ONLY':'1',
                      'AXIA_P2_G07_PHYSICAL_PREFLIGHT':'1'}
            if any(os.environ.get(k)!=v for k,v in required.items()):
                raise ValueError('TASK03_PUBLIC_SIM_ONLY_ECM_DENIED')
            if not (os.environ.get('AXIA_G07_CI_SIM_GOAL_ALLOWED')=='1' or
                    os.environ.get('AXIA_D07_H01_CONTACT_CALIBRATION_ONLY')=='1'):
                raise ValueError('TASK03_NO_GOAL_OR_CALIBRATION_AUTHORITY')
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
    except (OSError,ValueError,UnicodeError) as e:
        print('P2_G07_WORLD_OVERLAY_BLOCKED:'+type(e).__name__)
        return 2

if __name__=='__main__':raise SystemExit(main())
