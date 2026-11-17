#!/usr/bin/env python3
"""Read-only official ComputePathToPose Path relay for D07-H01 classroom GUI.

No ROS action server, no navigation Goal, no Twist, no invented path data.
The calling geometry runner supplies the EXACT Path from a successful official
ComputePathToPose Action response. Pure validators are independent of ROS.
"""
from __future__ import annotations

import math
from typing import Mapping

PHASES=("before","intrusion","restored")
MOTION_FLAGS=(
    "AXIA_G07_CI_SIM_GOAL_ALLOWED",
    "AXIA_P3_S01_CI_GOAL_ALLOWED",
    "AXIA_P3_S03_CI_COMPOUND_ALLOWED",
    "AXIA_P3_S04_CI_PNU_ALLOWED",
    "AXIA_P3_S05_CI_GOAL_ALLOWED",
)


def admit_gui_simulation(env: Mapping[str,str]) -> bool:
    """Explicit *simulation* GUI authorization, independent of CI-only Gate 1.

    Caller separately validates H01 original startup/pregoal JSON and its
    private Git SHA. Never interpret a GUI authorization as a motion approval.
    """
    required={
        "ROS_DISTRO":"jazzy",
        "AXIA_P0_SIM_ONLY":"1",
        "AXIA_D07_H01_GUI_NO_GOAL":"1",
        "AXIA_G07_OWNER_STARTUP_PARITY":"1",
        "AXIA_P2_G07_PHYSICAL_PREFLIGHT":"1",
    }
    return (
        all(env.get(k)==v for k,v in required.items())
        and env.get("GZ_PARTITION","").startswith("axia_p2_")
        and all(env.get(flag,"0")!="1" for flag in MOTION_FLAGS)
    )


def _stamp(stamp) -> float:
    try:
        sec=float(stamp.sec)
        nanosec=int(stamp.nanosec)
    except (AttributeError,TypeError,ValueError) as exc:
        raise ValueError("D07_H01_PATH_STAMP_MISSING") from exc
    if (not math.isfinite(sec) or sec<0 or not 0<=nanosec<1000000000):
        raise ValueError("D07_H01_PATH_STAMP_INVALID")
    return sec+nanosec*1e-9


def validate_official_path(path_msg, *, phase: str, current_clock: float) -> dict:
    """Reject wrong frame/stale/future/invalid original nav_msgs/Path."""
    if phase not in PHASES:
        raise ValueError("D07_H01_PATH_STAGE_INVALID")
    if (getattr(getattr(path_msg,"header",None),"frame_id",None)!="map"):
        raise ValueError("D07_H01_OFFICIAL_PATH_NOT_MAP")
    stamp=_stamp(path_msg.header.stamp)
    if (stamp<=0 or not math.isfinite(current_clock) or
            current_clock<=0 or stamp>current_clock+1.0):
        raise ValueError("D07_H01_OFFICIAL_PATH_CLOCK_INVALID")
    poses=getattr(path_msg,"poses",None)
    if poses is None or len(poses)<3:
        raise ValueError("D07_H01_OFFICIAL_PATH_TOO_SHORT")
    for pose in poses:
        try:
            p=pose.pose.position
            if not all(math.isfinite(float(v)) for v in (p.x,p.y,p.z)):
                raise ValueError("D07_H01_OFFICIAL_PATH_NONFINITE_POSE")
        except (AttributeError,TypeError,OverflowError) as exc:
            raise ValueError("D07_H01_OFFICIAL_PATH_POSE_INVALID") from exc
    return {"stage":phase,"source":"official_compute_path_to_pose",
            "frame":"map","source_header_stamp":stamp,"pose_count":len(poses),
            "goal_sent":False,"robot_moved":False}


def publish_official_path(publisher, original_path_msg, *, phase: str,
                          scan_stamp: float,costmap_stamp: float,
                          current_clock: float) -> dict:
    """Preserve EXACT ROS message object/pose/stamp; publish only after checks."""
    data=validate_official_path(
        original_path_msg,phase=phase,current_clock=current_clock)
    if (not math.isfinite(scan_stamp) or scan_stamp<=0 or
            not math.isfinite(costmap_stamp) or costmap_stamp<=0):
        raise ValueError("D07_H01_REAL_SENSOR_OR_GRID_STAMP_ABSENT")
    publisher.publish(original_path_msg)
    return {**data,"real_scan_stamp":float(scan_stamp),
            "real_costmap_stamp":float(costmap_stamp),
            "visualization_only":True,"native_action_result_relayed":True}


def assess_gui_stages(phases, *, source_sha: str, actual_ros: bool,
                      actual_gazebo: bool, rviz_window: bool) -> dict:
    """Three REAL source-stamped stages; no accepted claim from mocked L0 data.

    Unit fixture can test this decision, but only an actual public ROS/Gazebo
    run can set the three runtime booleans to True.
    """
    def hold(why,idx=None):
        return {"status":"D07_H01_GUI_EVIDENCE_HOLD_NO_GOAL",
                "ready":False,"first_failed_boundary":why,
                "first_failed_phase_index":idx,"moving_goal_admitted":False}
    if (len(source_sha)!=40 or
            any(c not in "0123456789abcdef" for c in source_sha)):
        return hold("UNPINNED_PRIVATE_SOURCE")
    if not (actual_ros is True and actual_gazebo is True and rviz_window is True):
        return hold("ACTUAL_GAZEBO_OR_ROS_OR_RVIZ_WINDOW_UNPROVEN")
    if not isinstance(phases,(tuple,list)) or len(phases)!=3:
        return hold("THREE_DISTINCT_GUI_PHASES_REQUIRED")
    previous_scan=previous_grid=0.0
    for i,(name,p) in enumerate(zip(PHASES,phases)):
        if not isinstance(p,dict) or p.get("stage")!=name:
            return hold("GUI_PHASE_ORDER_INVALID",i)
        if (p.get("source")!="official_compute_path_to_pose"
                or p.get("frame")!="map"
                or p.get("native_action_result_relayed") is not True
                or p.get("visualization_only") is not True
                or p.get("goal_sent") is not False
                or p.get("robot_moved") is not False):
            return hold("NOT_REAL_READONLY_OFFICIAL_PATH",i)
        try:
            scan=float(p["real_scan_stamp"])
            grid=float(p["real_costmap_stamp"])
            path=float(p["source_header_stamp"])
            count=int(p["pose_count"])
            rviz=int(p["rviz_subscription_count"])
        except (KeyError,ValueError,TypeError,OverflowError):
            return hold("SOURCE_STAMP_OR_RVIZ_SUBSCRIPTION_MISSING",i)
        if not all(math.isfinite(x) and x>0 for x in (scan,grid,path)):
            return hold("INVALID_REAL_SOURCE_STAMP",i)
        if scan<=previous_scan or grid<=previous_grid:
            return hold("ROS_SCAN_OR_COSTMAP_STAMP_NOT_PROGRESSING",i)
        if count<3 or rviz<1:
            return hold("OFFICIAL_PATH_OR_RVIZ_SUBSCRIBER_MISSING",i)
        previous_scan,previous_grid=scan,grid
    return {"status":"D07_H01_GUI_PATH_TF_AND_TOPIC_REAL_VERIFIED",
            "ready":True,"stages":list(PHASES),
            "source_sha":source_sha,"moving_goal_admitted":False,
            "owner_wsl2_accepted":False}
