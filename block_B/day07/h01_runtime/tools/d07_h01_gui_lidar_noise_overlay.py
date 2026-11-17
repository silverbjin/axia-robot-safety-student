#!/usr/bin/env python3
"""D07 no-moving-goal GUI ONLY: exact temporary official Waffle LiDAR-noise overlay.

Official Jazzy nav2_minimal_tb3_sim/gz_waffle.sdf.xacro has Gaussian
GPU LiDAR stddev=0.01m. Genuine L2 #43789445411 measured zero XY odom
change in 205 samples and continued global Costmap baseline lethal
flicker with 74 ROS scans (max callback gap .120095s). Test the noise
hypothesis ONLY in read-only classroom simulation. Never change /opt/ros,
Costmap, safety TTL, motor authority, or existing G07 P2 moving profiles.
This profile must NOT stand in for noisy-physical-sensor safety acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

SENSOR=b'<sensor name="hls_lfcd_lds" type="gpu_lidar">'
CLOSE=b'</sensor>'
OLD=b'<stddev>0.01</stddev>'
NEW=b'<stddev>0.0</stddev>'

def generate(source:Path,destination:Path)->dict:
    if source.name!="g07_demo_waffle.sdf.xacro":
        raise ValueError("PINNED_OFFICIAL_10HZ_TEMP_WAFFLE_REQUIRED")
    if source.resolve()==destination.resolve() or destination.exists():
        raise ValueError("ORIGINAL_OR_EXISTING_MODEL_MUST_NOT_BE_MODIFIED")
    raw=source.read_bytes()
    if not 200<=len(raw)<=100000:
        raise ValueError("OFFICIAL_MODEL_SIZE_NOT_VERIFIED")
    if raw.count(SENSOR)!=1:
        raise ValueError("EXACT_NAMED_OFFICIAL_GPU_LIDAR_REQUIRED")
    start=raw.index(SENSOR)
    stop=raw.find(CLOSE,start+len(SENSOR))
    if stop<0:
        raise ValueError("OFFICIAL_LIDAR_ELEMENT_UNTERMINATED")
    stop+=len(CLOSE)
    sensor=raw[start:stop]
    if (sensor.count(OLD)!=1 or sensor.count(b'<stddev>')!=1
        or sensor.count(b'<update_rate>10</update_rate>')!=1
        or sensor.count(b'<type>gaussian</type>')!=1):
        raise ValueError("UNEXPECTED_10HZ_GAUSSIAN_1CM_LIDAR_SOURCE")
    after_sensor=sensor.replace(OLD,NEW,1)
    changed=raw[:start]+after_sensor+raw[stop:]
    if (changed==raw or changed!=raw.replace(sensor,after_sensor,1)
        or len(changed)!=len(raw)-1):
        raise ValueError("NOISE_ONLY_BYTE_RANGE_EDIT_NOT_PROVEN")
    with destination.open("xb") as stream:
        stream.write(changed)
    return {
        "schema":"axia_d07_h01_gui_only_noise_free_sensor_overlay_v1",
        "status":"D07_SIM_ONLY_LIDAR_NOISE_FREE_TEST_PROFILE",
        "original_sha256":hashlib.sha256(raw).hexdigest(),
        "overlay_sha256":hashlib.sha256(changed).hexdigest(),
        "original_lidar_noise_stddev_m":0.01,
        "classroom_lidar_noise_stddev_m":0.0,
        "source_is_temporary_10hz_official_waffle_overlay":True,
        "changed_only_named_gpu_lidar_gaussian_noise":True,
        "real_sensor_noise_verified":False,
        "motion_admitted":False,"goal_sent":False,
        "certified_estop":False,"formal_accepted":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        if a.output.parent!=a.manifest.parent:
            raise ValueError("ONE_SESSION_SOURCE_AND_MANIFEST_ONLY")
        report=generate(a.source,a.output)
        with a.manifest.open("x",encoding="utf-8") as fp:
            json.dump(report,fp,indent=2,sort_keys=True)
            fp.write("\n")
        print("AXIA_D07_GUI_LIDAR_NOISE_FREE_SIM_ONLY_SOURCE_VERIFIED "+
              "NO_MOVING_GOAL NOT_REAL_SENSOR_SAFETY_CERTIFICATION",flush=True)
        return 0
    except (OSError,ValueError) as ex:
        print("AXIA_D07_GUI_LIDAR_NOISE_OVERLAY_BLOCKED "+
              type(ex).__name__+":"+str(ex),file=sys.stderr,flush=True)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
