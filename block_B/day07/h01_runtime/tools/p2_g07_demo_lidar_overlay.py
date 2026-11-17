#!/usr/bin/env python3
"""G07 classroom-only temporary copy of official Waffle SDF with 10Hz LiDAR.

Jazzy's unmodified gz_waffle.sdf.xacro has a 5Hz hls_lfcd_lds GPU LiDAR,
nominal period 200ms versus G07's unchanged 300ms safety scan TTL. Real
Gazebo L2 #43147373532 failed a 300.044ms scan gap crossing native STOP
despite CM 142.085ms PASS and 1.009s odom STOP. Change exactly the named
LiDAR sensor's 5Hz->10Hz in a session-local copy; keep installed official
source, robot geometry, IMU, depth camera and collision monitor untouched.
No fake scans, no custom ROS publisher, no E-Stop certification.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

LIDAR_OPEN=b'<sensor name="hls_lfcd_lds" type="gpu_lidar">'
LIDAR_CLOSE=b"</sensor>"
FROM=b"<update_rate>5</update_rate>"
TO=b"<update_rate>10</update_rate>"

def generate(source:Path,destination:Path)->dict:
    if source.resolve()==destination.resolve():
        raise ValueError("OFFICIAL_MODEL_MUST_BE_UNCHANGED")
    raw=source.read_bytes()
    if not 200<=len(raw)<=100_000:
        raise ValueError("OFFICIAL_WAFFLE_SDF_SIZE_UNEXPECTED")
    if raw.count(LIDAR_OPEN)!=1:
        raise ValueError("EXACT_OFFICIAL_WAFFLE_LIDAR_SENSOR_REQUIRED")
    start=raw.index(LIDAR_OPEN)
    stop=raw.find(LIDAR_CLOSE,start+len(LIDAR_OPEN))
    if stop<0:
        raise ValueError("OFFICIAL_WAFFLE_LIDAR_NOT_TERMINATED")
    stop+=len(LIDAR_CLOSE)
    sensor=raw[start:stop]
    if sensor.count(FROM)!=1 or sensor.count(b"<update_rate>")!=1:
        raise ValueError("OFFICIAL_WAFFLE_LIDAR_5HZ_SOURCE_REQUIRED")
    changed=raw[:start]+sensor.replace(FROM,TO,1)+raw[stop:]
    if changed==raw or len(changed)!=len(raw)+1:
        raise ValueError("LIDAR_ONLY_UPDATE_RATE_EDIT_NOT_PROVEN")
    if raw.replace(sensor,sensor.replace(FROM,TO,1),1)!=changed:
        raise ValueError("SDF_BYTE_RANGE_NOT_EXACT")
    # Session-local output must be a NEW file inside the owner/CI evidence
    # folder. Never modify /opt/ros/jazzy or the original packaged SDF.
    with destination.open("xb") as fp:
        fp.write(changed)
    return {
        "schema":"axia_g07_demo_waffle_lidar_update_rate_v1",
        "status":"G07_SIM_ONLY_OFFICIAL_MODEL_TEMP_OVERLAY",
        "original_sha256":hashlib.sha256(raw).hexdigest(),
        "overlay_sha256":hashlib.sha256(changed).hexdigest(),
        "original_lidar_hz":5,"demo_lidar_hz":10,
        "changed_only_lidar_rate":True,"goal_sent":False,
        "gate_accepted":False,"certified_estop":False,
    }

def main(argv=None)->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--manifest",type=Path,required=True)
    args=ap.parse_args(argv)
    try:
        if args.source.name!="gz_waffle.sdf.xacro":
            raise ValueError("OFFICIAL_WAFFLE_MODEL_FILENAME_REQUIRED")
        if args.output.parent!=args.manifest.parent:
            raise ValueError("LIDAR_MANIFEST_MUST_SHARE_SESSION_DIR")
        report=generate(args.source,args.output)
        with args.manifest.open("x",encoding="utf-8") as f:
            json.dump(report,f,sort_keys=True,indent=2)
            f.write("\n")
        print("AXIA_G07_DEMO_LIDAR_ONLY_5HZ_TO_10HZ_TEMP_SDF_PASS "
              "ORIGINAL_OFFICIAL_MODEL_UNCHANGED TTL_300MS_UNCHANGED "
              "GOAL_NOT_SENT CERTIFIED_ESTOP=false",flush=True)
        return 0
    except (OSError,ValueError) as exc:
        print("AXIA_G07_DEMO_LIDAR_OVERLAY_BLOCKED_NO_GOAL "+
              type(exc).__name__+":"+str(exc),file=sys.stderr,flush=True)
        return 2

if __name__=="__main__":raise SystemExit(main())
