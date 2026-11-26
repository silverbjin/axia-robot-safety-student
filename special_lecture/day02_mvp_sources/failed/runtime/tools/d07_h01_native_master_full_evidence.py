"""D07 H01: bounded read-only full native GetCostmap master comparison.

Official Nav2 GetCostmap services are sequential, NOT atomic PlannerServer
snapshots. A whole published OccupancyGrid restored to its baseline cannot
prove that the internal Planner used the same master at Action execution.
This function never authorizes motion, clears Costmap or changes parameters.
"""
from __future__ import annotations
import hashlib
import math

def _read(source):
    if not isinstance(source,dict):
        return None
    w,h=source.get("width"),source.get("height")
    res=source.get("resolution")
    origin=source.get("origin")
    cells=source.get("cells")
    stamp,recv=source.get("stamp"),source.get("received_monotonic")
    if (source.get("service")!="/global_costmap/get_costmap"
        or source.get("frame")!="map"
        or type(w) is not int or type(h) is not int
        or not 0<w*h<=1000000 or w<1 or h<1
        or type(res) not in (int,float) or not math.isfinite(res) or res<=0
        or not isinstance(origin,(tuple,list)) or len(origin)!=2
        or any(type(v) not in (int,float) or not math.isfinite(v) for v in origin)
        or type(stamp) not in (int,float) or not math.isfinite(stamp) or stamp<=0
        or type(recv) not in (int,float) or not math.isfinite(recv) or recv<=0
        or not isinstance(cells,(list,tuple)) or len(cells)!=w*h
        or any(type(v) is not int or not 0<=v<=255 for v in cells)):
        return None
    return {"key":(w,h,float(res),tuple(origin)),
            "cells":cells,"stamp":float(stamp),"received":float(recv)}

def compare_full_native_master(free_raw, restored_raw):
    hold={"schema":"axia_d07_h01_full_native_master_restore_v1",
          "status":"NATIVE_FULL_MASTER_PROVENANCE_HOLD",
          "reason":"NONATOMIC_NATIVE_SOURCE_PARITY_NOT_VERIFIED",
          "source_causality_proven":False,
          "planner_internal_costmap_proven":False,
          "obstacle_layer_clearing_proven":False,
          "motion_admitted":False,"goal_sent":False,
          "certified_estop":False}
    a,b=_read(free_raw),_read(restored_raw)
    if a is None or b is None or a["key"]!=b["key"]:
        return hold
    if (b["stamp"]<=a["stamp"] or b["received"]<=a["received"]):
        return {**hold,"reason":"NATIVE_MASTER_SOURCE_STAMP_ORDER_INVALID"}
    first=[];changed=0;inc=dec=0
    for i,(x,y) in enumerate(zip(a["cells"],b["cells"])):
        if x==y:continue
        changed+=1
        inc+=int(y>x);dec+=int(y<x)
        if len(first)<12:first.append(i)
    same=changed==0
    return {**hold,
            "status":("NATIVE_FULL_MASTER_IDENTICAL_DIAGNOSTIC_ONLY"
                      if same else "NATIVE_FULL_MASTER_CHANGED_DIAGNOSTIC_ONLY"),
            "reason":"NONATOMIC_SERVICE_MASTER_NOT_PLANNER_ACTION_LOCK",
            "source_grids_identical":same,
            "source_sha256_before":hashlib.sha256(bytes(a["cells"])).hexdigest(),
            "source_sha256_after":hashlib.sha256(bytes(b["cells"])).hexdigest(),
            "native_master_before_stamp":a["stamp"],
            "native_master_after_stamp":b["stamp"],
            "changed_cell_count":changed,
            "increased_cell_count":inc,
            "decreased_cell_count":dec,
            "first_changed_indices":first,
            "source_causality_proven":False,
            "planner_internal_costmap_proven":False,
            "motion_admitted":False,
            "goal_sent":False,
            }

def assess_full_published_native_barrier(native_source, published_grids):
    """Strict full RAW-master -> published Grid two-update read-only barrier.

    Native service /get_costmap and Costmap topic are NOT atomic with the
    Planner action. Only request ONE extra official ComputePathToPose if two
    independently received, strictly newer Grid messages equal the native
    translated source at ALL cells. Does not infer Planner internal state or
    accept a detoured Path.
    """
    try:
        from .d07_h01_native_costmap_layers import _to_occupancy
        from .d07_h01_costmap_drift import _read as read_topic
    except ImportError:
        from d07_h01_native_costmap_layers import _to_occupancy
        from d07_h01_costmap_drift import _read as read_topic
    hold={"schema":"axia_d07_h01_post_native_full_grid_barrier_v1",
          "status":"POST_NATIVE_FULL_GRID_BARRIER_HOLD",
          "reason":"TWO_NEW_MATCHING_PUBLISHED_COSTMAPS_NOT_PROVEN",
          "eligible_for_readonly_replan":False,
          "planner_internal_costmap_proven":False,
          "source_causality_proven":False,
          "goal_sent":False,"motion_admitted":False,
          "certified_estop":False}
    source=_read(native_source)
    if (source is None or not isinstance(published_grids,(list,tuple))
        or len(published_grids)!=2):
        return hold
    parsed=[read_topic(x) for x in published_grids]
    if any(x is None or x["key"][:4]!=source["key"]
           for x in parsed):
        return {**hold,"reason":"PUBLISHED_MAP_SHAPE_OR_SOURCE_INVALID"}
    a,b=parsed
    if (a["stamp"]<=source["stamp"] or
        a["received"]<=source["received"] or
        b["stamp"]<=a["stamp"] or b["received"]<=a["received"]):
        return {**hold,"reason":"NATIVE_TO_PUBLISHED_SOURCE_EPOCH_NOT_MONOTONIC"}
    expected=[_to_occupancy(v) for v in source["cells"]]
    mismatch=[sum(actual!=baseline for actual,baseline in
                  zip(r["cells"],expected)) for r in parsed]
    ready=mismatch==[0,0]
    return {**hold,
            "status":("POST_NATIVE_FULL_GRID_BARRIER_READY_NO_GOAL"
                      if ready else "POST_NATIVE_FULL_GRID_BARRIER_HOLD"),
            "reason":("TWO_DISTINCT_FULL_GRID_NATIVE_EQUIVALENT_SNAPSHOTS"
                      if ready else "PUBLISHED_GLOBAL_COSTMAP_NOT_SOURCE_EQUIVALENT"),
            "native_source_stamp":source["stamp"],
            "post_native_topic_stamps":[a["stamp"],b["stamp"]],
            "latest_two_native_mismatches":mismatch,
            "eligible_for_readonly_replan":ready,
            "planner_internal_costmap_proven":False,
            "source_causality_proven":False,
            "motion_admitted":False,"goal_sent":False,
            }
