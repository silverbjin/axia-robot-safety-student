"""Task03 disposable public Gazebo ECM positive calibration; NEVER a Goal.

The official Waffle remains stationary; the existing Gazebo cylinder is
briefly moved into contact to prove that the *same* ECM witness can detect
a contact. This entire world is discarded before the one moving-Goal run.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from p2_l3_gz_fixture import move
from p2_g07_relocated_no_goal_probe import DEMO_WORLD_POSE
from p2_g07_spawn_contract import APPROVED_WORLD

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--source-sha",required=True)
    a.add_argument("--startup",type=Path,required=True)
    a.add_argument("--pregoal",type=Path,required=True)
    args=a.parse_args()
    e=os.environ
    for k,v in {
        "GITHUB_ACTIONS":"true","AXIA_P0_SIM_ONLY":"1",
        "AXIA_G07_CI_SIM_GOAL_ALLOWED":"1",
        "AXIA_G07_OWNER_STARTUP_PARITY":"1",
        "AXIA_G07_TASK03_ECM_WITNESS":"1",
        "AXIA_G07_TASK03_POSITIVE_ONLY":"1",
    }.items():
        if e.get(k)!=v:
            raise RuntimeError("TASK03_POSITIVE_PUBLIC_NO_GOAL_SCOPE_BLOCKED")
    source=subprocess.check_output(["git","rev-parse","HEAD"],text=True,timeout=5).strip()
    if source!=args.source_sha or tuple(APPROVED_WORLD[:2])!=(-2.0,-0.5):
        raise RuntimeError("TASK03_POSITIVE_SOURCE_OR_WORLD_NOT_PINNED")
    startup=json.loads(args.startup.read_text())
    pregoal=json.loads(args.pregoal.read_text())
    if (startup.get("status")!="SMOKE_READY"
            or startup.get("goal_sent") is not False
            or pregoal.get("status")!="P2_G07_OWNER_PREGOAL_L2_READY_NO_GOAL"
            or pregoal.get("native_set_pose_ack") is not True):
        raise RuntimeError("TASK03_POSITIVE_STATIONARY_PREFLIGHT_FAILED")
    print("AXIA_G07_TASK03_ECM_NO_GOAL_POSITIVE_CONTROL_STARTED",flush=True)
    moved=False
    try:
        # The original static Waffle is in the official Gazebo world at
        # (-2.0,-0.5). This physical contact is NOT the moving Goal world.
        move(-2.0,-0.5)
        moved=True
        time.sleep(3.0)
    finally:
        if moved:
            move(*DEMO_WORLD_POSE)
            time.sleep(.3)
    print("AXIA_G07_TASK03_ECM_POSITIVE_NO_GOAL_WORLD_DISCARD_REQUIRED",flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
