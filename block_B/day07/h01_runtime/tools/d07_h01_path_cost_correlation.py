"""Read-only original official Nav2 path vs native global Costmap correlation.

The published /global_costmap/costmap callback is NOT proved to be the exact
planner server internal costmap at the instant ComputePathToPose executes.
This module measures only same-session grid receipt, changed cells along the
baseline path with a 0.12 m band, and the actual official returned path.
No publishers, collision clearing, simulated evidence, TTL or motion PASS.
"""
from __future__ import annotations
import math
if __package__:
    from .d07_h01_costmap_drift import _read
    from .d07_h01_oracle import baseline_path_restoration
else:
    from d07_h01_costmap_drift import _read
    from d07_h01_oracle import baseline_path_restoration


def correlate_official_path_cost(baseline_a,baseline_b,restored_grid,
                                 baseline_path,restored_path,*,obstacle_map_xy):
    """Evidence-only contrast: extra cost on original path vs other detour."""
    hold={
        "schema":"axia_d07_h01_path_costmap_correlation_v1",
        "status":"COSTMAP_PLANNER_PROVENANCE_HOLD",
        "reason":"INVALID_REAL_COSTMAP_OR_OFFICIAL_PLANNER_PROVENANCE",
        "path_restored_proven":False,
        "planner_internal_costmap_proven":False,
        "motion_admitted":False,"goal_sent":False,
        "collision_free_verified":False,"certified_estop":False,
    }
    maps=[_read(g) for g in (baseline_a,baseline_b,restored_grid)]
    if any(v is None for v in maps):
        return hold
    a,b,r=maps
    if any(x["key"]!=a["key"] for x in maps[1:]):
        return {**hold,"reason":"GRID_FRAME_OR_SESSION_MISMATCH"}
    if not (a["stamp"]<b["stamp"]<r["stamp"]
            and a["received"]<b["received"]<r["received"]):
        return {**hold,"reason":"COSTMAP_SOURCE_STAMPS_OR_RECEIPTS_UNORDERED"}
    if (not isinstance(baseline_path,dict) or not isinstance(restored_path,dict)
        or any(v.get("source")!="official_nav2" or v.get("frame_id")!="map"
               for v in (baseline_path,restored_path))):
        return {**hold,"reason":"UNVERIFIED_OFFICIAL_NAV2_PATH"}
    planner_at=restored_path.get("received_at")
    if (type(planner_at) not in (float,int) or not math.isfinite(planner_at)
            or planner_at<=0):
        return hold
    if planner_at<=r["received"]:
        return {**hold,"reason":"GRID_RECEIVED_AFTER_PLANNER_RESULT"}
    path_check=baseline_path_restoration(
        baseline_path,restored_path,obstacle_map_xy=obstacle_map_xy,
        costmap_roundtrip_ready=True,scan_stamp_advanced=True)
    if (path_check.get("status")!="RESTORED_OFFICIAL_NAV2_BASELINE_NO_GOAL"
            and path_check.get("reason")!="OFFICIAL_PATH_STILL_DETOURED"):
        return {**hold,"reason":"OFFICIAL_PATH_START_GOAL_OR_GEOMETRY_INVALID"}
    points=baseline_path.get("poses")
    if (not isinstance(points,(tuple,list)) or len(points)<3
        or not all(isinstance(p,(tuple,list)) and len(p)==2 and
                   all(type(v) in (float,int) and math.isfinite(v) for v in p)
                   for p in points)):
        return hold
    width,height,res,origin=a["key"][:4]
    corridor=set()
    samples=0
    for u,v in zip(points,points[1:]):
        length=math.dist(u,v)
        segments=max(1,math.ceil(length/(res*.5)))
        samples+=segments+1
        if samples>3000:
            return {**hold,"reason":"OFFICIAL_BASELINE_PATH_SAMPLING_BUDGET"}
        for step in range(segments+1):
            alpha=step/segments
            x=u[0]+alpha*(v[0]-u[0])
            y=u[1]+alpha*(v[1]-u[1])
            col=math.floor((x-origin[0])/res)
            row=math.floor((y-origin[1])/res)
            for rr in range(row-2,row+3):
                if not 0<=rr<height:
                    continue
                for cc in range(col-2,col+3):
                    if not 0<=cc<width:
                        continue
                    cx=origin[0]+(cc+.5)*res
                    cy=origin[1]+(rr+.5)*res
                    if math.dist((cx,cy),(x,y))<=.12:
                        corridor.add(rr*width+cc)
    if not corridor:
        return {**hold,"reason":"OFFICIAL_PATH_OUTSIDE_COSTMAP"}
    base0,base1,new=(row["cells"] for row in maps)
    if any(min(base0[i],base1[i],new[i])<0 for i in corridor):
        return {**hold,"reason":"UNKNOWN_NATIVE_COST_INSIDE_ORIGINAL_CORRIDOR",
                "unknown_corridor_cells":sum(
                    min(base0[i],base1[i],new[i])<0 for i in corridor)}
    increased=[i for i in sorted(corridor) if new[i]>max(base0[i],base1[i])]
    new_lethal=[i for i in increased if max(base0[i],base1[i])<95<=new[i]]
    if (not isinstance(obstacle_map_xy,(tuple,list)) or len(obstacle_map_xy)!=2
        or any(type(x) not in (float,int) or not math.isfinite(x)
               for x in obstacle_map_xy)):
        return hold
    def location(i):
        return (origin[0]+(i%width+.5)*res,
                origin[1]+(i//width+.5)*res)
    local=[i for i in increased if math.dist(location(i),obstacle_map_xy)<=.75]
    first=[]
    for i in sorted(increased,key=lambda idx:(
            math.dist(location(idx),obstacle_map_xy),idx))[:8]:
        first.append({
            "index":i,
            "map_xy":[round(z,5) for z in location(i)],
            "baseline_a":base0[i],
            "baseline_b":base1[i],
            "restored":new[i],
            "near_physical_obstacle":math.dist(location(i),obstacle_map_xy)<=.75,
        })
    detoured=path_check["status"]=="BLOCKED"
    status=("POSITIVE_ORIGINAL_PATH_CORRIDOR_COST" if increased else
            "OFFICIAL_PATH_DETOUR_WITH_NO_NEW_CORRIDOR_COST" if detoured
            else "ORIGINAL_CORRIDOR_COST_UNCHANGED_NO_GOAL")
    return {
        **hold,
        "status":status,
        "reason":"READONLY_CORRELATION_NOT_PLANNER_INTERNAL_COSTMAP_PROOF",
        "restored_costmap_header_stamp":r["stamp"],
        "baseline_grid_header_stamps":[a["stamp"],b["stamp"]],
        "grid_to_planner_receipt_sec":round(planner_at-r["received"],6),
        "corridor_half_width_m":.12,
        "original_path_corridor_cells":len(corridor),
        "new_positive_original_corridor_cells":len(increased),
        "new_lethal_original_corridor_cells":len(new_lethal),
        "positive_near_obstacle_cells":len(local),
        "first_positive_cell_details":first,
        "planner_path_still_detoured":detoured,
        "path_return_delta_m":path_check.get("path_return_delta_m"),
        "baseline_path_points":len(points),
        "restore_path_points":len(restored_path["poses"]),
        "planner_internal_costmap_proven":False,
        "path_restored_proven":False,
        "motion_admitted":False,"goal_sent":False,
    }
