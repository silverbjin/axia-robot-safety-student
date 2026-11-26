"""D07-H01 read-only costmap natural drift versus physical obstacle residue.

Four *independent, time-ordered, real official Nav2* OccupancyGrid snapshots
are required. This does not publish ROS messages or grant motion authority.
"""
from __future__ import annotations
import hashlib
import math


def _read(raw):
    if not isinstance(raw, dict):
        return None
    w,h=raw.get("width"),raw.get("height")
    res=raw.get("resolution")
    frame=raw.get("frame")
    src=raw.get("source")
    session=raw.get("session_id")
    origin=raw.get("origin")
    cells=raw.get("cells")
    stamp=raw.get("stamp")
    received=raw.get("received_monotonic")
    if (type(w) is not int or type(h) is not int
        or not (0<w*h<=1000000) or w<=0 or h<=0
        or frame!="map" or src!="official_nav2_global_costmap"
        or not isinstance(session,str) or not session
        or type(res) not in (int,float) or not math.isfinite(res)
        or not 0<res<=.5
        or not isinstance(origin,(tuple,list)) or len(origin)!=2
        or any(type(v) not in (int,float) or not math.isfinite(v) for v in origin)
        or not isinstance(cells,(tuple,list)) or len(cells)!=w*h
        or any(type(v) is not int or not -1<=v<=100 for v in cells)
        or type(stamp) not in (int,float) or not math.isfinite(stamp) or stamp<=0
        or type(received) not in (int,float) or
        not math.isfinite(received) or received<=0):
        return None
    return {"key":(w,h,float(res),tuple(float(v) for v in origin),
                   frame,src,session),
            "cells":tuple(cells),"stamp":float(stamp),
            "received":float(received)}


def assess_spatial_drift(baseline_a:dict, baseline_b:dict,
                         intruded:dict, restored:dict,
                         obstacle_map_xy:tuple)->dict:
    """Classify 4 physically observed maps without hiding uncertainty.

    A changed restored value is *observed natural variation* only if its
    index was changing before intrusion and it matches an observed value.
    Compatible drift remains NO-GOAL; it cannot establish safety on its own.
    """
    fail={"status":"BLOCKED","reason":"INVALID_OR_STALE_OFFICIAL_COSTMAP",
          "spatial_restoration_proven":False,"motion_admitted":False,
          "goal_sent":False,"contact_ground_truth_proven":False,
          "certified_estop":False,
          "first_invalid_boundary":"COSTMAP_PROVENANCE_OR_TIME"}
    entries=[_read(x) for x in
             (baseline_a,baseline_b,intruded,restored)]
    if any(v is None for v in entries):
        return fail
    a,b,i,r=entries
    if any(v["key"]!=a["key"] for v in entries[1:]):
        return {**fail,"reason":"COSTMAP_METADATA_OR_SESSION_MISMATCH"}
    if (any(entries[j+1]["stamp"]<=entries[j]["stamp"]
            or entries[j+1]["received"]<=entries[j]["received"]
            for j in range(3))):
        return {**fail,"reason":"COSTMAP_NOT_FRESH_AND_ORDERED"}
    key=a["key"];width,height,res,origin=key[:4]
    xy=obstacle_map_xy
    if (not isinstance(xy,(list,tuple)) or len(xy)!=2
        or any(type(v) not in (int,float) or not math.isfinite(v) for v in xy)
        or not(origin[0]<=xy[0]<origin[0]+width*res
               and origin[1]<=xy[1]<origin[1]+height*res)):
        return {**fail,"reason":"OBSTACLE_MAP_XY_UNVERIFIED"}
    b0,b1,inserted,cleared=(v["cells"] for v in entries)
    def center(idx):
        return (origin[0]+(idx%width+.5)*res,
                origin[1]+(idx//width+.5)*res)
    near=[idx for idx in range(len(b0)) if math.dist(center(idx),xy)<=.75]
    original_both_safe={idx for idx in near if b0[idx]<95 and b1[idx]<95}
    marked=sum(inserted[idx]>=95 for idx in original_both_safe)
    if marked<1:
        return {**fail,"reason":"PHYSICAL_INTRUSION_NOT_MARKED",
                "first_invalid_boundary":"SCAN_TO_OBSTACLE_LAYER"}
    # A previously-free cell becoming lethal after removal is unacceptable,
    # even if the total lethal count equals the initial total.
    persistent=sum(cleared[idx]>=95 for idx in original_both_safe)
    natural={idx for idx in range(len(b0)) if b0[idx]!=b1[idx]}
    restored_changed={idx for idx in range(len(b0)) if cleared[idx]!=b1[idx]}
    unexplained={idx for idx in restored_changed
                 if idx not in natural or
                    cleared[idx] not in (b0[idx],b1[idx])}
    # Preserve bounded per-cell physical provenance from the ACTUAL received
    # OccupancyGrid. Distinguish unexplained inflation beside the moved model
    # from unrelated costmap variability without granting any motion authority.
    # No threshold is relaxed, and no synthetic scan/costmap is published.
    unexplained_near={idx for idx in unexplained
                      if math.dist(center(idx),xy)<=.75}
    def cell_detail(idx):
        cx,cy=center(idx)
        distance=math.dist((cx,cy),xy)
        return {
            "index":idx,"row":idx//width,"col":idx%width,
            "map_xy":[round(cx,5),round(cy,5)],
            "distance_to_obstacle_m":round(distance,5),
            "inside_obstacle_0p75m":distance<=.75,
            "costs":{"baseline_a":b0[idx],"baseline_b":b1[idx],
                     "intruded":inserted[idx],"restored":cleared[idx]},
        }
    out={**fail,
         "unexplained_near_obstacle_count":len(unexplained_near),
         "unexplained_outside_obstacle_count":len(unexplained)-len(unexplained_near),
         "first_unexplained_details":[cell_detail(idx)
                                      for idx in sorted(
                                          unexplained,
                                          key=lambda idx: (
                                              idx not in unexplained_near,
                                              math.dist(center(idx), xy),
                                              idx))[:12]],
         "natural_drift_cells":len(natural),
         "post_restore_diff_cells":len(restored_changed),
         "unexplained_cell_count":len(unexplained),
         "residual_lethal_near_obstacle":persistent,
         "intrusion_new_lethal_near_obstacle":marked,
         "baseline_a_sha256":hashlib.sha256(bytes(x&255 for x in b0)).hexdigest(),
         "baseline_b_sha256":hashlib.sha256(bytes(x&255 for x in b1)).hexdigest(),
         "restored_sha256":hashlib.sha256(bytes(x&255 for x in cleared)).hexdigest(),
         "first_unexplained_cells":sorted(unexplained)[:12]}
    if persistent:
        return {**out,"reason":"PERSISTENT_LETHAL_NEAR_OBSTACLE",
                "first_invalid_boundary":"OBSTACLE_LAYER_CLEARING"}
    if unexplained:
        return {**out,"status":"DRIFT_UNCLASSIFIED_NO_GOAL",
                "reason":"DIFFERENCE_NOT_IN_OBSERVED_PRE_INTRUSION_VARIATION",
                "first_invalid_boundary":"POST_RESTORE_COSTMAP_DRIFT"}
    if len(natural)>0:
        return {**out,"status":"BASELINE_VARIATION_OBSERVED_NO_GOAL",
                "reason":"OBSERVED_NATURAL_VARIATION_NOT_MOTION_AUTHORITY",
                "first_invalid_boundary":None}
    return {**out,"status":"SPATIAL_BASELINE_EXACT_NO_GOAL",
            "reason":"ENTIRE_GRID_MATCHED_BASELINE_STILL_NO_MOTION_AUTHORITY",
            "first_invalid_boundary":None,"spatial_restoration_proven":True}



def assess_roi_clearing(baseline_a:dict, baseline_b:dict, intruded:dict,
                        restored:dict, *, obstacle_map_xy:tuple)->dict:
    """Read-only PHYSICAL ROI cost evidence, not full Grid/Path/Goal approval.

    Byte-identical global OccupancyGrid restoration is neither required nor
    sufficient for the unrelated one-Goal moving avoidance claim. Instead,
    measure *all* grid values within 0.75m of the real observed obstacle and
    fail closed on any increased restored cost against BOTH baselines.
    No path, Contact, safety TTL, or motor authority can be proven here.
    """
    fail={"status":"ROI_PROVENANCE_HOLD_NO_GOAL",
          "reason":"INVALID_NATIVE_GRID_PROVENANCE",
          "first_invalid_boundary":"COSTMAP_PROVENANCE_OR_TIME",
          "spatial_restoration_proven":False,
          "motion_admitted":False,"goal_sent":False,
          "collision_free_verified":False,"certified_estop":False}
    entries=[_read(v) for v in (baseline_a,baseline_b,intruded,restored)]
    if any(v is None for v in entries):
        return fail
    a,b,intrusion,r=entries
    if (any(v["key"]!=a["key"] for v in entries[1:])
        or any(entries[i+1]["stamp"]<=entries[i]["stamp"]
               or entries[i+1]["received"]<=entries[i]["received"]
               for i in range(3))):
        return {**fail,"reason":"GRID_OR_FRESH_TIMESTAMP_MISMATCH"}
    w,h,res,origin=a["key"][:4]
    xy=obstacle_map_xy
    if (not isinstance(xy,(tuple,list)) or len(xy)!=2
        or any(type(v) not in (int,float) or not math.isfinite(v) for v in xy)
        or not (origin[0]<=xy[0]<origin[0]+w*res
                and origin[1]<=xy[1]<origin[1]+h*res)):
        return {**fail,"reason":"UNVERIFIED_PHYSICAL_OBSTACLE_MAP_XY"}
    b0,b1,bi,br=(v["cells"] for v in entries)
    positive_near=[]
    positive_far=[]
    decreased_near=[]
    new_lethal=[]
    marked=[]
    for idx in range(w*h):
        before_a,before_b=b0[idx],b1[idx]
        # Unknown cells are not evidence of a previously-free position.
        if before_a<0 or before_b<0 or br[idx]<0 or bi[idx]<0:
            continue
        cx=origin[0]+(idx%w+.5)*res
        cy=origin[1]+(idx//w+.5)*res
        inside=math.dist((cx,cy),xy)<=.75
        if inside and max(before_a,before_b)<95 and bi[idx]>=95:
            marked.append(idx)
        if br[idx]>max(before_a,before_b):
            (positive_near if inside else positive_far).append(idx)
        if inside and br[idx]<min(before_a,before_b):
            decreased_near.append(idx)
        if inside and max(before_a,before_b)<95 and br[idx]>=95:
            new_lethal.append(idx)
    if not marked:
        return {**fail,"reason":"PHYSICAL_INTRUSION_MARKING_NOT_OBSERVED",
                "first_invalid_boundary":"SCAN_TO_OBSTACLE_LAYER"}
    out={**fail,
         "physical_marked_cells":len(marked),
         "positive_excess_near_obstacle":len(positive_near),
         "positive_excess_outside_obstacle":len(positive_far),
         "decreased_near_obstacle":len(decreased_near),
         "persistent_new_lethal_near_obstacle":len(new_lethal),
         "first_suspect_roi_indices":sorted(positive_near)[:12],
         "source_grid_stamps":[v["stamp"] for v in entries],
         "source_session_id":a["key"][-1]}
    if positive_near or new_lethal:
        return {**out,"status":"ROI_SUSPECT_RESIDUE_HOLD_NO_GOAL",
                "reason":"RESTORED_COST_EXCEEDS_BOTH_FREE_BASELINES",
                "first_invalid_boundary":"POST_RESTORE_POSITIVE_ROI_COST"}
    return {**out,"status":"ROI_NO_POSITIVE_RESIDUE_CANDIDATE_NO_GOAL",
            "reason":"NO_INCREASED_ROI_COST_BUT_PLANNER_CONTACT_TTL_UNVERIFIED",
            "first_invalid_boundary":None}

def select_fresh_baselines(samples, *, earliest_received):
    """Return two distinct stamped costmaps received after real free scan.

    Samples are (monotonic receipt, ROS header stamp, original grid). Never
    infer two updates from two receipt times with a duplicate header stamp.
    """
    if (type(earliest_received) not in (int,float) or
        not math.isfinite(earliest_received)):
        return None
    valid=[]
    for item in samples:
        if not isinstance(item,(tuple,list)) or len(item)!=3:
            return None
        received,stamp,_=item
        if any(type(x) not in (int,float) or not math.isfinite(x)
               for x in (received,stamp)):
            return None
        if received>earliest_received and stamp>0:
            valid.append(tuple(item))
    if len(valid)<2:
        return None
    first,second=valid[-2:]
    if not(first[0]<second[0] and first[1]<second[1]):
        return None
    return [first,second]


def trace_post_restore_lethal_history(
        baseline_a:dict, baseline_b:dict, intruded:dict,
        post_restore_grids:list, *, obstacle_map_xy:tuple,
        clear_scan_received_monotonic:float, clear_scan_stamp:float)->dict:
    """Pin first *new* lethal cell to actual post-removal Grid receipts.

    Detect whether a previously nonlethal cell stays lethal on TWO successive
    fresh Costmap publications after a separately observed clear LaserScan.
    The map Header stamp only orders source publications, NOT proof that the
    obstacle layer consumed that scan. No Nav2 clear service, threshold change,
    synthetic ROS messages, or motor authority. Evidence stays bounded.
    """
    hold={"status":"POST_RESTORE_ROI_PROVENANCE_HOLD",
          "first_invalid_boundary":"COSTMAP_OR_CLEAR_SCAN_PROVENANCE",
          "reason":"UNVERIFIED_NATIVE_GRID_SEQUENCE_OR_CLEAR_SCAN",
          "goal_sent":False,"motion_admitted":False,
          "obstacle_layer_clearing_proven":False,
          "collision_free_verified":False,"certified_estop":False,
          "source_cause_proven":False}
    if (not isinstance(post_restore_grids,(list,tuple))
        or not 2<=len(post_restore_grids)<=12
        or not all(type(t) in (float,int) and math.isfinite(t) and t>0
                    for t in (clear_scan_received_monotonic,clear_scan_stamp))):
        return hold
    rows=[_read(v) for v in
          (baseline_a,baseline_b,intruded,*post_restore_grids)]
    if any(r is None for r in rows):
        return hold
    a,b,marked,*post=rows
    if any(r["key"]!=a["key"] for r in rows[1:]):
        return {**hold,"reason":"MISMATCHED_COSTMAP_FRAME_GRID_SESSION"}
    if any(rows[i+1]["stamp"]<=rows[i]["stamp"]
           or rows[i+1]["received"]<=rows[i]["received"]
           for i in range(len(rows)-1)):
        return {**hold,"reason":"NONMONOTONIC_NATIVE_COSTMAP_STAMP_OR_RECEIPT"}
    if (post[0]["stamp"]<=clear_scan_stamp
        or post[0]["received"]<=clear_scan_received_monotonic
        or marked["stamp"]>=clear_scan_stamp
        or marked["received"]>=clear_scan_received_monotonic):
        return {**hold,"reason":"COSTMAP_NOT_FRESH_AFTER_PHYSICAL_CLEAR_SCAN"}
    width,height,res,origin=a["key"][:4]
    xy=obstacle_map_xy
    if (not isinstance(xy,(list,tuple)) or len(xy)!=2
        or any(type(x) not in (float,int) or not math.isfinite(x) for x in xy)
        or not (origin[0]<=xy[0]<origin[0]+width*res
                and origin[1]<=xy[1]<origin[1]+height*res)):
        return {**hold,"reason":"PHYSICAL_OBSTACLE_MAP_POSITION_INVALID"}
    base0,base1,insert=(r["cells"] for r in (a,b,marked))
    near=[]
    for idx in range(width*height):
        x=origin[0]+(idx%width+.5)*res
        y=origin[1]+(idx//width+.5)*res
        if math.dist((x,y),xy)<=.75:
            near.append(idx)
    comparable=[idx for idx in near
                if base0[idx]>=0 and base1[idx]>=0 and insert[idx]>=0]
    if not any(max(base0[idx],base1[idx])<95 and insert[idx]>=95
               for idx in comparable):
        return {**hold,"reason":"ACTUAL_INTRUSION_LETHAL_MARKING_NOT_PROVEN"}
    snapshots=[]
    new_lethal_rows=[]
    for grid in post:
        cells=grid["cells"]
        new_lethal={idx for idx in comparable
                    if cells[idx]>=95 and max(base0[idx],base1[idx])<95}
        excess={idx for idx in comparable if cells[idx]>max(base0[idx],base1[idx])}
        snapshots.append({
            "grid_stamp":grid["stamp"],
            "received_monotonic":grid["received"],
            "grid_stamp_minus_clear_scan_sec":round(grid["stamp"]-clear_scan_stamp,6),
            "new_lethal_count":len(new_lethal),
            "roi_positive_excess_count":len(excess)})
        new_lethal_rows.append(new_lethal)
    persistent=new_lethal_rows[-2] & new_lethal_rows[-1]
    ever_new=set().union(*new_lethal_rows)
    # Include first appearance, exact map coordinate and actual grid costs.
    # Sort by distance to the obstacle first rather than by raw flat index:
    # the former is relevant to physical LiDAR/Inflation diagnosis.
    def detail(idx):
        x=origin[0]+(idx%width+.5)*res
        y=origin[1]+(idx//width+.5)*res
        first=next(k for k,ids in enumerate(new_lethal_rows) if idx in ids)
        return {
            "index":idx,"row":idx//width,"col":idx%width,
            "map_xy":[round(x,5),round(y,5)],
            "distance_to_obstacle_m":round(math.dist((x,y),xy),5),
            "costs":{"baseline_a":base0[idx],"baseline_b":base1[idx],
                     "intruded":insert[idx]},
            "first_post_restore_grid_stamp":post[first]["stamp"],
            "last_post_restore_cost":post[-1]["cells"][idx],
            "new_lethal_in_last_two_grids":idx in persistent,
            "was_lethal_during_intrusion":insert[idx]>=95,
        }
    first_details=[detail(i) for i in
        sorted(ever_new,key=lambda idx:(
            (origin[0]+(idx%width+.5)*res-xy[0])**2+
            (origin[1]+(idx//width+.5)*res-xy[1])**2,idx))[:12]]
    if persistent:
        boundary="POST_RESTORE_NEW_LETHAL_CELL"
    elif new_lethal_rows[-1]:
        boundary="LATEST_NEW_LETHAL_NOT_YET_PERSISTENT"
    elif snapshots[-1]["roi_positive_excess_count"]:
        boundary="POST_RESTORE_NONLETHAL_ROI_EXCESS"
    else:
        boundary=None
    return {
        **hold,
        "status":"POST_RESTORE_ROI_RESIDUE_DIAGNOSTIC_ONLY",
        "reason":"ACTUAL_COSTMAP_CELL_HISTORY_NO_SOURCE_CAUSAL_PROOF",
        "first_invalid_boundary":boundary,
        "first_new_lethal_details":first_details,
        "ever_new_lethal_count":len(ever_new),
        "persistent_new_lethal_last_two":len(persistent),
        "roi_excess_last_sample":snapshots[-1]["roi_positive_excess_count"],
        "history":snapshots,
        "physical_obstacle_map_xy":[round(xy[0],5),round(xy[1],5)],
        "clear_scan_stamp":float(clear_scan_stamp),
        "clear_scan_received_monotonic":float(clear_scan_received_monotonic),
        "source_session_id":a["key"][-1],
        "goal_sent":False,"motion_admitted":False,
        "obstacle_layer_clearing_proven":False,
        "source_cause_proven":False,
    }


def classify_readonly_roi_path_probe(
        roi:dict, global_drift:dict, lethal_count_roundtrip:dict,
        *, native_restore_ack:bool, post_restore_scan_advanced:bool)->dict:
    """Allow read-only official Planner probes; NEVER grant robot motion.

    Real L2 #43590584866: 0 excess ROI, 0 new ROI lethal, 312 unexplained
    global Grid cells and one still-detoured official path. Whole global Grid
    hash equality is neither needed nor enough for *further observation*.
    Only a fresh, physically witnessed ROI return can trigger a bounded
    ComputePathToPose check, and its returned path decides the next boundary.
    No global clear service and NO safety/contact/TTL/Goal acceptance.
    """
    hold={
        "status":"ROI_OR_RESTORE_PROVENANCE_HOLD_NO_GOAL",
        "path_probe_allowed":False,
        "path_restored_proven":False,
        "spatial_restoration_proven":False,
        "goal_sent":False,"motion_admitted":False,
        "collision_free_verified":False,"certified_estop":False,
        "formal_accepted":False,
        "reason":"ROI_NEEDS_FRESH_PHYSICAL_CLEARING",
    }
    if (not isinstance(roi,dict) or not isinstance(global_drift,dict)
        or not isinstance(lethal_count_roundtrip,dict)
        or native_restore_ack is not True
        or post_restore_scan_advanced is not True
        or roi.get("status")!="ROI_NO_POSITIVE_RESIDUE_CANDIDATE_NO_GOAL"
        or lethal_count_roundtrip.get("status")!="LETHAL_COUNT_RETURNED_NO_GOAL"
        or global_drift.get("status") not in (
            "DRIFT_UNCLASSIFIED_NO_GOAL",
            "BASELINE_VARIATION_OBSERVED_NO_GOAL",
            "SPATIAL_BASELINE_EXACT_NO_GOAL")
        or any(x.get("motion_admitted") is not False for x in
               (roi,global_drift,lethal_count_roundtrip))
        or roi.get("goal_sent") is not False
        or lethal_count_roundtrip.get("goal_sent") is not False
        or type(roi.get("physical_marked_cells")) is not int
        or roi["physical_marked_cells"]<1
        or type(roi.get("positive_excess_near_obstacle")) is not int
        or roi["positive_excess_near_obstacle"]!=0
        or type(roi.get("persistent_new_lethal_near_obstacle")) is not int
        or roi["persistent_new_lethal_near_obstacle"]!=0):
        return hold
    unclassified=global_drift.get("unexplained_cell_count")
    if (unclassified is not None
        and (type(unclassified) is not int or unclassified<0)):
        return hold
    return {
        **hold,
        "status":"ROI_CLEAN_PLANNER_PROBE_REQUIRED_NO_GOAL",
        "reason":"ROI_CLEAR_BUT_OFFICIAL_NAV2_PATH_RETURN_UNVERIFIED",
        "path_probe_allowed":True,
        "unexplained_global_grid_cells":unclassified,
        "physical_marked_cells":roi["physical_marked_cells"],
        "first_invalid_boundary":None,
        # This deliberately remains FALSE even when the full Grid matches.
        # Independent real Planner Path must be checked and no actual
        # NavigateToPose or final motor authority is exercised here.
        "path_restored_proven":False,
        "spatial_restoration_proven":False,
        "goal_sent":False,"motion_admitted":False,
    }
