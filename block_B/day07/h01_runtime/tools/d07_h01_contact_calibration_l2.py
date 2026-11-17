#!/usr/bin/env python3
"""D07-H01 native Contact stationary positive control in PUBLIC CI only.

A single already-existing Gazebo cylinder touches the stationary Waffle while
there is NO NavigateToPose Goal. This is a dedicated disposable simulator run:
never reuse its world for moving acceptance. A positive contact proves sensor
ability at this instant, NOT no-contact during future motion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from d07_h01_contact_probe import (
    NATIVE_CONTACT_TOPIC, discover_contact_advertisement,
    parse_positive_contact_calibration)
from p2_g07_relocated_no_goal_probe import DEMO_WORLD_POSE
from p2_l3_gz_fixture import move
from p2_g07_spawn_contract import APPROVED_WORLD


def check(args):
    expected = {
        "GITHUB_ACTIONS": "true",
        "AXIA_P0_SIM_ONLY": "1",
        "AXIA_G07_CI_SIM_GOAL_ALLOWED": "1",
        "AXIA_D07_H01_CI_ALLOWED": "1",
        "AXIA_D07_H01_CONTACT_CALIBRATION_ONLY": "1",
        "AXIA_G07_OWNER_STARTUP_PARITY": "1",
        "ROS_DISTRO": "jazzy",
    }
    if any(os.environ.get(k) != v for k,v in expected.items()):
        raise RuntimeError("CONTACT_CALIBRATION_PUBLIC_SIM_NO_GOAL_ONLY")
    if any(os.environ.get(k) == "1" for k in (
        "AXIA_D07_H01_GEOMETRY_ONLY", "AXIA_P3_S01_CI_GOAL_ALLOWED",
        "AXIA_P3_S04_CI_PNU_ALLOWED", "AXIA_P3_S05_CI_GOAL_ALLOWED",
        "AXIA_P3_S03_CI_COMPOUND_ALLOWED")):
        raise RuntimeError("OTHER_MOTION_OR_FAULT_BRANCH_FORBIDDEN")
    if not os.environ.get("GZ_PARTITION","").startswith("axia_p2_"):
        raise RuntimeError("ISOLATED_GAZEBO_REQUIRED")
    repo=Path(__file__).resolve().parents[1]
    sha=subprocess.check_output(
        ["git","-c","safe.directory="+str(repo),"-C",str(repo),
         "rev-parse","HEAD"],text=True,timeout=6).strip()
    if len(args.source_sha)!=40 or sha!=args.source_sha:
        raise RuntimeError("PRIVATE_EXACT_SHA_MISMATCH")
    startup=json.loads(args.startup.read_text())
    pre=json.loads(args.pregoal.read_text())
    if not (
        startup.get("status")=="SMOKE_READY"
        and startup.get("goal_sent") is False
        and startup.get("fault_injected") is False
        and pre.get("status")=="P2_G07_OWNER_PREGOAL_L2_READY_NO_GOAL"
        and pre.get("goal_sent") is False
        and pre.get("stationary_odom_checked") is True
        and pre.get("native_set_pose_ack") is True
        and pre.get("post_ack_distinct_ros_scan_count",0)>=2
    ):
        raise RuntimeError("STATIONARY_PREG0AL_PHYSICAL_SOURCE_NOT_PROVEN")


def gz(args, seconds=8):
    r=subprocess.run(["gz",*args],capture_output=True,text=True,
                     timeout=seconds,check=False)
    if r.returncode!=0:
        raise RuntimeError("NATIVE_GZ_TOPIC_COMMAND_FAILED_"+str(r.returncode))
    return r.stdout+r.stderr


def run(args):
    check(args)
    args.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    evidence=args.output/"native_contact_stdout.log"
    result={"status":"CONTACT_CALIBRATION_BLOCKED","goal_sent":False,
            "motion_admitted":False,"robot_moving_goal_count":0,
            "source_sha":args.source_sha,"positive_control_proven":False,
            "contact_ground_truth_ready":False,"certified_estop":False,
            "owner_l3_accepted":False,"reason":"START"}
    def save():
        (args.output/"contact_calibration.json").write_text(
            json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    save()
    moved=False
    proc=None
    try:
        topics=gz(["topic","-l"])
        info=gz(["topic","-i","-t",NATIVE_CONTACT_TOPIC])
        (args.output/"native_contact_topic_list.log").write_text(topics)
        (args.output/"native_contact_topic_info.log").write_text(info)
        advert=discover_contact_advertisement(topics,info)
        result["native_contact_advertisement"]=advert
        save()
        if advert["topic_type_proven"] is not True:
            raise RuntimeError("NATIVE_CONTACT_TOPIC_OR_GZ_MSG_TYPE_NOT_PROVEN")
        # The bounded subscriber starts BEFORE contact is introduced; silence
        # before it is not counted as a valid zero-contact observation.
        with evidence.open("w",encoding="utf-8") as output:
            proc=subprocess.Popen(["gz","topic","-e","-t",NATIVE_CONTACT_TOPIC],
                                  stdout=output,stderr=subprocess.STDOUT,
                                  start_new_session=True,text=True)
            time.sleep(1.3)
            if proc.poll() is not None:
                raise RuntimeError("NATIVE_CONTACT_ECHO_NOT_ALIVE_BEFORE_CONTROL")
            # CI ONLY. The official Waffle is at (-2,-0.5) in WORLD, not
            # /odom=(0,0). An overlapping stationary physical calibration
            # may push the robot: the world MUST be discarded after this run.
            if tuple(APPROVED_WORLD[:2])!=(-2.0,-0.5):
                raise RuntimeError("OFFICIAL_ROBOT_WORLD_POSE_CONTRACT_CHANGED")
            moved=True
            move(-2.0,-0.5)
            time.sleep(3.0)
            move(*DEMO_WORLD_POSE)
            moved=False
            time.sleep(1.0)
            proc.terminate()
            try:proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                proc.kill();proc.wait(timeout=3)
        raw=evidence.read_text(encoding="utf-8",errors="replace")
        calib=parse_positive_contact_calibration(topics,info,raw)
        result.update(calibration=calib,
                      raw_contact_sha256=hashlib.sha256(raw.encode()).hexdigest(),
                      raw_contact_bytes=len(raw),
                      source_subscriber_exit_code=proc.returncode,
                      reason=calib["reason"],goal_sent=False)
        # Original Gazebo positive-control absence cannot be diagnosed from
        # the final RuntimeError alone; the public CI deletes private files.
        # Emit a bounded view of the *native* message, not any source file.
        bounded_raw_lines=[line[:180] for line in raw.splitlines()[:16]]
        result["first_contact_evidence"]={
            "raw_contact_bytes":len(raw),
            "raw_contact_sha256":result["raw_contact_sha256"],
            "source_subscriber_exit_code":proc.returncode,
            "bounded_raw_lines":bounded_raw_lines,
            "topic_type_proven":advert["topic_type_proven"],
            "positive_control_observed":calib["positive_control_observed"]}
        save()
        print("AXIA_D07_H01_CONTACT_RAW_BEFORE_POSITIVE_HOLD "+
              json.dumps(result["first_contact_evidence"],sort_keys=True),
              flush=True)
        if calib["positive_control_observed"] is not True:
            save()
            raise RuntimeError("NATIVE_CONTACT_POSITIVE_CONTROL_NOT_OBSERVED")
        result.update(status="CONTACT_STATIONARY_L2_POSITIVE_ONLY_NO_GOAL",
                      positive_control_proven=True,
                      contact_ground_truth_ready=False,
                      motion_admitted=False)
        save()
        print("AXIA_D07_H01_REAL_GAZEBO_CONTACT_POSITIVE_CONTROL_ONLY_NO_GOAL "
              +json.dumps({"status":result["status"],
                           "contact_count":calib["calibration_event_count"],
                           "native_type_verified":True,
                           "goal_sent":False,
                           "motion_ground_truth_proven":False},sort_keys=True),
              flush=True)
        return 0
    except Exception as exc:
        result["reason"]=type(exc).__name__+":"+str(exc)
        save()
        print("AXIA_D07_H01_FIRST_CONTACT_CALIBRATION_BOUNDARY "+
              result["reason"],flush=True)
        return 2
    finally:
        if moved:
            try:move(*DEMO_WORLD_POSE)
            except Exception as exc:
                print("AXIA_D07_H01_CONTACT_MODEL_RESTORE_UNVERIFIED "
                      +str(exc),flush=True)
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=3)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
        print("AXIA_D07_H01_DISPOSABLE_CONTACT_CALIBRATION_WORLD "
              "NO_GOAL_NO_MOTION_ACCEPTANCE",flush=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--startup",type=Path,required=True)
    p.add_argument("--pregoal",type=Path,required=True)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    return run(p.parse_args())


if __name__=="__main__":
    sys.exit(main())
