"""No-Goal diagnostic: entire original official Nav2 corridor's native master cost.

Observed real Gazebo #43604899891: two pre-intrusion official free paths
identical; after removal 151 published corridor cells show no added cost,
yet four real ComputePathToPose results still detour ~0.4096m.

Join *one* read-only native master Costmap baseline before physical intrusion
with a read-only native master snapshot collected after last planner attempt.
Do not treat asynchronous GetCostmap calls as the exact planner internal map,
do not claim root causality, change Nav2 or admit a motion Goal.
"""
from __future__ import annotations
import math
try:
    from .d07_h01_native_costmap_layers import _native
    from .d07_h01_oracle import _xy,_path,path_distance
except ImportError:
    from d07_h01_native_costmap_layers import _native
    from d07_h01_oracle import _xy,_path,path_distance


def audit_native_master_path_corridor(before,after,base_path,restore_path,
                                      *,corridor_radius_m=0.12):
    hold={
        "schema":"axia_d07_h01_native_master_original_path_corridor_v1",
        "status":"NATIVE_PATH_CORRIDOR_PROVENANCE_HOLD",
        "reason":"NON_ATOMIC_NATIVE_MASTER_SOURCE_OR_OFFICIAL_PATH_INVALID",
        "source_causality_proven":False,
        "planner_internal_costmap_proven":False,
        "obstacle_layer_clearing_proven":False,
        "path_restored_proven":False,
        "motion_admitted":False,"goal_sent":False,
        "collision_free_verified":False,"certified_estop":False,
    }
    if (not isinstance(before,dict) or not isinstance(after,dict)
        or before.get("service")!="/global_costmap/get_costmap"
        or after.get("service")!="/global_costmap/get_costmap"
        or before.get("frame")!="map" or after.get("frame")!="map"
        or type(corridor_radius_m) not in (int,float)
        or not math.isfinite(corridor_radius_m)
        or not .05<=corridor_radius_m<=.20):
        return hold
    width=before.get("width")
    height=before.get("height")
    res=before.get("resolution")
    origin=before.get("origin")
    if (type(width) is not int or type(height) is not int
        or type(res) not in (int,float) or not math.isfinite(res) or res<=0
        or not isinstance(origin,(list,tuple)) or len(origin)!=2
        or any(type(x) not in (int,float) or not math.isfinite(x)
               for x in origin)):
        return hold
    key=(width,height,res,tuple(origin),"map")
    b=_native(before,"costmap",key)
    a=_native(after,"costmap",key)
    if (b is None or a is None or a["stamp"]<=b["stamp"]
        or a["received"]<=b["received"]):
        return hold
    if not isinstance(base_path,dict) or not isinstance(restore_path,dict):
        return hold
    if (any(x.get("source")!="official_nav2" or x.get("frame_id")!="map"
            for x in (base_path,restore_path))):
        return hold
    original=_path(base_path.get("poses"))
    restored=_path(restore_path.get("poses"))
    begin0,end0=_xy(base_path.get("start")),_xy(base_path.get("goal"))
    begin1,end1=_xy(restore_path.get("start")),_xy(restore_path.get("goal"))
    if (original is None or restored is None
        or any(p is None for p in (begin0,end0,begin1,end1))
        or math.dist(begin0,begin1)>.01 or math.dist(end0,end1)>.01
        or math.dist(original[0],begin0)>.25
        or math.dist(original[-1],end0)>.25
        or math.dist(restored[0],begin1)>.25
        or math.dist(restored[-1],end1)>.25):
        return hold
    corridor=set()
    sampled=0
    max_samples=5000
    ox,oy=origin
    for p,q in zip(original,original[1:]):
        steps=max(1,math.ceil(math.dist(p,q)/(res*.5)))
        sampled+=steps+1
        if sampled>max_samples:
            return {**hold,"reason":"CORRIDOR_SAMPLE_LIMIT_REACHED"}
        for k in range(steps+1):
            x=p[0]+(q[0]-p[0])*k/steps
            y=p[1]+(q[1]-p[1])*k/steps
            col=math.floor((x-ox)/res)
            row=math.floor((y-oy)/res)
            vicinity=math.ceil(corridor_radius_m/res)+1
            for rr in range(max(0,row-vicinity),min(height,row+vicinity+1)):
                for cc in range(max(0,col-vicinity),min(width,col+vicinity+1)):
                    cx=ox+(cc+.5)*res
                    cy=oy+(rr+.5)*res
                    if math.hypot(cx-x,cy-y)<=corridor_radius_m:
                        corridor.add(rr*width+cc)
    if not corridor:
        return {**hold,"reason":"BASELINE_OFFICIAL_PATH_OUTSIDE_NATIVE_MASTER"}
    delta_ab=max(path_distance(point,original) for point in restored)
    delta_ba=max(path_distance(point,restored) for point in original)
    detoured=max(delta_ab,delta_ba)>.15
    increased=[i for i in sorted(corridor) if a["cells"][i]>b["cells"][i]]
    lethal=[i for i in increased if b["cells"][i]<254<=a["cells"][i]]
    changed=[i for i in sorted(corridor) if a["cells"][i]!=b["cells"][i]]
    decreased=[i for i in changed if a["cells"][i]<b["cells"][i]]
    def detail(i):
        return {"index":i,
                "map_xy":[round(ox+(i%width+.5)*res,5),
                          round(oy+(i//width+.5)*res,5)],
                "native_master_before":b["cells"][i],
                "native_master_after":a["cells"][i],
                "new_lethal":i in lethal}
    status=("NATIVE_ORIGINAL_PATH_CORRIDOR_NEW_COST_NO_GOAL" if increased
            else "NATIVE_ORIGINAL_PATH_CORRIDOR_UNCHANGED_DETOUR_NO_GOAL"
                 if detoured else "NATIVE_ORIGINAL_PATH_CORRIDOR_UNCHANGED_NO_GOAL")
    return {**hold,
        "status":status,
        "reason":"POST_PLANNER_NON_ATOMIC_NATIVE_MASTER_DIAGNOSTIC_ONLY",
        "source_service":"/global_costmap/get_costmap",
        "native_master_before_stamp":b["stamp"],
        "native_master_after_stamp":a["stamp"],
        "native_snapshot_received_after_planner":True,
        "corridor_half_width_m":round(float(corridor_radius_m),4),
        "corridor_cells":len(corridor),
        "changed_native_corridor_cells":len(changed),
        "decreased_native_corridor_cells":len(decreased),
        "increased_native_corridor_cells":len(increased),
        "new_lethal_native_corridor_cells":len(lethal),
        "first_increased_cells":[detail(i) for i in increased[:12]],
        "max_bidirectional_path_delta_m":round(max(delta_ab,delta_ba),4),
        "planner_path_still_detoured":detoured,
        "source_causality_proven":False,
        "planner_internal_costmap_proven":False,
        "path_restored_proven":False,
        "motion_admitted":False,"goal_sent":False,
    }
