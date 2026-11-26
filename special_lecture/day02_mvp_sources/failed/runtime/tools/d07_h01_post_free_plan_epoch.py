"""D07 H01 official Free Planner source epoch alignment (read-only).

Real Gazebo L2 #43792298836 emitted original Before Path at ROS stamp
56.256s BEFORE the accepted pre-intrusion Free Grid pair 56.706/58.704s.
When a restored map equals that later Grid/master exactly, an older
before-Path cannot be an authoritative baseline for restoration.
This admission only checks source timestamp/provenance; never authorizes
motion, claims Planner internal source lock or weakens path geometry.
"""
from __future__ import annotations
import math

def assess_post_free_path_epoch(paths, *, grid_stamp, native_stamp):
    blocked={
        "schema":"axia_d07_h01_post_free_official_path_epoch_v1",
        "status":"POST_FREE_OFFICIAL_PATH_EPOCH_HOLD",
        "reason":"GENUINE_POST_FREE_OFFICIAL_PATH_SOURCE_NOT_VERIFIED",
        "first_invalid_boundary":"POST_FREE_PATH_SOURCE_PROVENANCE",
        "source_epoch_ready":False,
        "planner_internal_costmap_proven":False,
        "source_causality_proven":False,
        "motion_admitted":False,"goal_sent":False,
        "certified_estop":False,
    }
    if (not isinstance(paths,(list,tuple)) or len(paths)!=2
            or any(type(x) not in (int,float) or not math.isfinite(x)
                   or x<=0 for x in (grid_stamp,native_stamp))
            or native_stamp<grid_stamp):
        return blocked
    stamps=[]
    for p in paths:
        if (not isinstance(p,dict) or p.get("source")!="official_nav2"
            or p.get("frame_id")!="map"
            or not isinstance(p.get("poses"),(list,tuple))
            or len(p["poses"])<3
            or type(p.get("source_header_stamp")) not in (int,float)
            or not math.isfinite(p["source_header_stamp"])
            or p["source_header_stamp"]<=0):
            return blocked
        stamps.append(float(p["source_header_stamp"]))
    if min(stamps)<=max(grid_stamp,native_stamp):
        return {**blocked,
            "reason":"PRE_STABILIZATION_OFFICIAL_PATH_NOT_ACCEPTABLE",
            "first_invalid_boundary":"OFFICIAL_PATH_PREDATES_FREE_GRID",
            "path_header_stamps":stamps,
            "free_grid_stamp":float(grid_stamp),
            "native_master_stamp":float(native_stamp)}
    if stamps[1]<=stamps[0]:
        return {**blocked,
                "reason":"TWO_OFFICIAL_PATH_HEADER_STAMPS_NOT_ADVANCING",
                "first_invalid_boundary":"OFFICIAL_PATH_EPOCH_NONMONOTONIC"}
    return {**blocked,
            "status":"POST_FREE_OFFICIAL_PLAN_EPOCH_READY_NO_GOAL",
            "reason":"TWO_REAL_PLANNER_PATHS_AFTER_SELECTED_FREE_SOURCE",
            "first_invalid_boundary":None,
            "path_header_stamps":stamps,
            "free_grid_stamp":float(grid_stamp),
            "native_master_stamp":float(native_stamp),
            "source_epoch_ready":True}
