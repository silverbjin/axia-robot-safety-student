"""H01 official Jazzy native Costmap layer read-only candidate attribution.

Do NOT assume native Costmap2DPublisher layer services share an atomic
snapshot. Source names are verified service paths, NOT metadata.layer
(which official code reports as 'master' for each GetCostmap response).
0..255 native values must not be compared directly with translated
-1..100 /global_costmap/costmap OccupancyGrid display values.
No ROS publishing, no clearing services, no goal or safety PASS.
"""
from __future__ import annotations
import math
try:
    from .d07_h01_costmap_drift import _read
except ImportError:
    from d07_h01_costmap_drift import _read

NAMES=("obstacle_layer","static_layer","costmap")
OPTIONAL=("inflation_layer",)


def _native(raw,name,required_key):
    if not isinstance(raw,dict):
        return None
    size=raw.get("width"),raw.get("height")
    origin=raw.get("origin")
    values=raw.get("cells")
    stamp=raw.get("stamp")
    recv=raw.get("received_monotonic")
    res=raw.get("resolution")
    if (raw.get("service")!="/global_costmap/get_"+name
        or raw.get("frame")!="map"
        or any(type(x) is not int or x<=0 for x in size)
        or not 0<size[0]*size[1]<=1000000
        or not isinstance(origin,(tuple,list)) or len(origin)!=2
        or any(type(x) not in (float,int) or not math.isfinite(x) for x in origin)
        or type(res) not in (int,float) or not math.isfinite(res) or res<=0
        or not isinstance(values,(tuple,list)) or len(values)!=size[0]*size[1]
        or any(type(x) is not int or not 0<=x<=255 for x in values)
        or any(type(x) not in (float,int) or not math.isfinite(x) or x<=0
               for x in (stamp,recv))):
        return None
    w,h,base_res,base_origin=required_key[:4]
    if (size!=(w,h) or abs(res-base_res)>1e-5
        or any(abs(x-y)>1e-5 for x,y in zip(origin,base_origin))):
        return None
    return {"cells":values,"stamp":float(stamp),"received":float(recv)}


def _to_occupancy(raw):
    # Exact Costmap2DPublisher Jazzy cost_translation_table_.
    if raw==255:
        return -1
    if raw==254:
        return 100
    if raw==253:
        return 99
    if raw==0:
        return 0
    return 1+(97*(raw-1))//251


def _source_neighborhood(layers, topic, idx):
    """Bounded read-only neighbours of a high native master cost.

    L2 #43770723300: indices 82733/83116 had master=253, but the
    inspected ObstacleLayer and StaticLayer at those exact cells were zero.
    Search 0.30m around each suspect for *candidate* high source cells.
    A neighbour is NOT proof a Scan ray was consumed or inflation updated.
    Missing neighbours are also NOT proof that the layers are cleared.
    """
    width,height,res,_=topic["key"][:4]
    col,row=idx%width,idx//width
    max_step=math.ceil(.30/res)
    candidates={"obstacle_layer":None,"static_layer":None}
    for name in candidates:
        found=None
        cells=layers[name]["cells"]
        for r in range(max(0,row-max_step),min(height,row+max_step+1)):
            for c in range(max(0,col-max_step),min(width,col+max_step+1)):
                distance=math.hypot(c-col,r-row)*res
                if distance>.30+1e-9:
                    continue
                other=r*width+c
                raw=cells[other]
                if raw<253:
                    continue
                if found is None or (distance,other)<(found[0],found[1]):
                    found=(distance,other,raw)
        if found is not None:
            candidates[name]={
                "index":found[1],
                "distance_m":round(found[0],5),
                "raw_cost":found[2]}
    return candidates


def audit_native_layer_costs(native,topic_grid,suspect_indices):
    hold={"schema":"axia_d07_h01_native_layers_v1",
          "status":"NATIVE_LAYER_PROVENANCE_HOLD_NO_GOAL",
          "reason":"NATIVE_GET_COSTMAP_SERVICE_GRID_OR_TIME_MISSING",
          "source_causality_proven":False,
          "planner_internal_costmap_proven":False,
          "obstacle_layer_clearing_proven":False,
          "motion_admitted":False,"goal_sent":False,
          "collision_free_verified":False,"certified_estop":False}
    topic=_read(topic_grid)
    if (topic is None or not isinstance(native,dict)
        or not isinstance(suspect_indices,(tuple,list))
        or not 1<=len(suspect_indices)<=12
        or any(type(x) is not int for x in suspect_indices)
        or len(set(suspect_indices))!=len(suspect_indices)
        or any(not 0<=idx<len(topic["cells"]) for idx in suspect_indices)):
        return hold
    vals={name:_native(native.get(name),name,topic["key"]) for name in NAMES}
    if any(row is None for row in vals.values()):
        return hold
    # Official Jazzy's InflationLayer is not a CostmapLayer with a
    # separately readable GetCostmap. It inflates master on updateBounds/
    # updateCosts. Preserve any optional external snapshot only if genuine.
    optional_inflation=native.get("inflation_layer")
    if optional_inflation is not None:
        vals["inflation_layer"]=_native(
            optional_inflation,"inflation_layer",topic["key"])
        if vals["inflation_layer"] is None:
            return {**hold,"reason":"INVALID_OPTIONAL_INFLATION_SERVICE_GRID"}
    if any(row["received"]<=topic["received"] for row in vals.values()):
        return {**hold,"reason":"NATIVE_LAYER_SNAPSHOT_NOT_AFTER_OBSERVED_TOPIC"}
    samples=[]
    width,height,res,origin=topic["key"][:4]
    for idx in suspect_indices:
        raw={name:vals[name]["cells"][idx] for name in NAMES}
        raw["inflation_layer"]=(vals["inflation_layer"]["cells"][idx]
                                if "inflation_layer" in vals else None)
        obs,static,infl,master=(raw[n] for n in
            ("obstacle_layer","static_layer","inflation_layer","costmap"))
        # These are source candidates only. Async layer services are not a
        # simultaneous atomic update or direct per-ray source trace.
        if obs>=253 and static<253:
            source="OBSTACLE_LAYER_HIGH_RAW_COST"
        elif static>=253 and obs<253:
            source="STATIC_LAYER_HIGH_RAW_COST"
        elif infl is not None and infl>=253 and max(static,obs)<253:
            source="INFLATION_LAYER_HIGH_RAW_COST"
        elif master>=253:
            source="MASTER_COMPOSITE_UNATTRIBUTED"
        elif master>0 and obs==0 and static==0:
            # Physical L2 #43596533373: obstacle=static=0,
            # native master=64..143, and stale translated topic=26..57.
            # Inflation or other unobserved source is a CANDIDATE only.
            source="MASTER_INFLATION_OR_UNOBSERVED_LAYER_COST_CANDIDATE"
        elif master==0:
            source="NO_NATIVE_MASTER_COST_AT_TOPIC_SUSPECT"
        else:
            source="NONZERO_NATIVE_LAYER_COST_UNATTRIBUTED"
        samples.append({
            "index":idx,
            "map_xy":[round(origin[0]+(idx%width+.5)*res,5),
                      round(origin[1]+(idx//width+.5)*res,5)],
            "topic_occupancy":topic["cells"][idx],
            "obstacle_layer_raw":obs,
            "static_layer_raw":static,
            "inflation_layer_raw":infl,
            "master_raw":master,
            "master_has_nonzero_raw_cost":master>0,
            "obstacle_and_static_are_free_here":obs==0 and static==0,
            "topic_matches_master_now":(
                _to_occupancy(master)==topic["cells"][idx]),
            "attribution_candidate":source,
            "source_neighborhood":_source_neighborhood(vals,topic,idx)})
    return {**hold,
        "status":"NATIVE_LAYER_SUSPECT_COSTS_OBSERVED_NO_GOAL",
        "reason":"NON_ATOMIC_READONLY_LAYER_COSTS_NEED_PHYSICAL_SCAN_JOIN",
        "samples":samples,
        "source_services":{n:native[n]["service"] for n in vals},
        "service_stamps":{n:vals[n]["stamp"] for n in vals},
        "inflation_layer_service_expected":False,
        "inflation_layer_service_observed":"inflation_layer" in vals,
        "topic_stamp":topic["stamp"],
        "atomic_snapshot_proven":False,
        "source_causality_proven":False,
        "obstacle_layer_clearing_proven":False,
        "planner_internal_costmap_proven":False,
        "motion_admitted":False,"goal_sent":False,
    }


def compare_native_layer_roundtrip(
        before, after, topic_grid, suspect_indices):
    """Read-only native RAW master baseline vs after at exact ROI cells.

    This is two non-atomic sets of official GetCostmap service responses.
    Timestamp/order and grid geometry must match. Even a positive master
    delta with zero Obstacle/Static is an inflation/unobserved-Layer CANDIDATE,
    never a proven source cause, raytrace, motion or collision-free PASS.
    """
    hold={"schema":"axia_d07_h01_native_roundtrip_v1",
          "status":"NATIVE_ROUNDTRIP_PROVENANCE_HOLD",
          "reason":"NATIVE_BASELINE_AND_RESTORE_SERVICE_GRIDS_NOT_VERIFIED",
          "source_causality_proven":False,
          "obstacle_layer_clearing_proven":False,
          "planner_internal_costmap_proven":False,
          "goal_sent":False,"motion_admitted":False,
          "certified_estop":False}
    topic=_read(topic_grid)
    if (topic is None or not isinstance(before,dict)
        or not isinstance(after,dict)
        or not isinstance(suspect_indices,(tuple,list))
        or not 1<=len(suspect_indices)<=12
        or any(type(i) is not int or not 0<=i<len(topic["cells"])
               for i in suspect_indices)
        or len(set(suspect_indices))!=len(suspect_indices)):
        return hold
    a={n:_native(before.get(n),n,topic["key"]) for n in NAMES}
    b={n:_native(after.get(n),n,topic["key"]) for n in NAMES}
    if any(v is None for v in [*a.values(),*b.values()]):
        return hold
    if (any(b[n]["stamp"]<=a[n]["stamp"]
            or b[n]["received"]<=a[n]["received"]
            for n in NAMES)
        or any(b[n]["received"]<=topic["received"] for n in NAMES)):
        return {**hold,"reason":"NATIVE_LAYER_ORDER_OR_RECEIPT_INVALID"}
    width,height,res,origin=topic["key"][:4]
    samples=[]
    for i in suspect_indices:
        bm=a["costmap"]["cells"][i]
        am=b["costmap"]["cells"][i]
        samples.append({
            "index":i,
            "map_xy":[round(origin[0]+(i%width+.5)*res,5),
                      round(origin[1]+(i//width+.5)*res,5)],
            "master_before_raw":bm,
            "master_after_raw":am,
            "master_increase_raw":max(0,am-bm),
            "obstacle_layer_before_raw":a["obstacle_layer"]["cells"][i],
            "obstacle_layer_after_raw":b["obstacle_layer"]["cells"][i],
            "static_layer_before_raw":a["static_layer"]["cells"][i],
            "static_layer_after_raw":b["static_layer"]["cells"][i],
        })
    increased=sum(x["master_increase_raw"]>0 for x in samples)
    return {
        **hold,
        "status":("NATIVE_MASTER_INCREASE_CANDIDATE_NO_GOAL" if increased
                  else "NATIVE_MASTER_NOT_INCREASED_NO_GOAL"),
        "reason":"NON_ATOMIC_NATIVE_MASTER_CHANGE_ONLY_NOT_SOURCE_CAUSALITY",
        "positive_master_delta_cells":increased,
        "samples":samples,
        "baseline_stamps":{n:a[n]["stamp"] for n in NAMES},
        "restore_stamps":{n:b[n]["stamp"] for n in NAMES},
        "source_causality_proven":False,
        "obstacle_layer_clearing_proven":False,
        "planner_internal_costmap_proven":False,
        "goal_sent":False,"motion_admitted":False,
    }



def prioritize_native_layer_suspects(roi, lethal_history, *, max_count=12):
    """Choose FIRST real persistent lethal before benign ROI cost differences.

    Public actual Gazebo #43600093293: index 77738 persisted after the clear
    LaserScan, while the first twelve ascending positive ROI cost indices
    (76960...) excluded it. That omission concealed the relevant native
    ObstacleLayer/StaticLayer/master state at the first safety boundary.

    Diagnostic prioritization only; never changes costmap or motor authority.
    """
    if (not isinstance(roi,dict) or not isinstance(lethal_history,dict)
        or type(max_count) is not int or not 1<=max_count<=12
        or lethal_history.get("status")!=
                "POST_RESTORE_ROI_RESIDUE_DIAGNOSTIC_ONLY"):
        return []
    suspects=roi.get("first_suspect_roi_indices",[])
    details=lethal_history.get("first_new_lethal_details",[])
    if (not isinstance(suspects,list) or not isinstance(details,list)
        or len(suspects)>12 or len(details)>12
        or any(type(v) is not int or not 0<=v<=1000000
               for v in suspects)
        or any(not isinstance(x,dict)
               or type(x.get("index")) is not int
               or not 0<=x["index"]<=1000000
               or type(x.get("new_lethal_in_last_two_grids")) is not bool
               or type(x.get("first_post_restore_grid_stamp")) not in (int,float)
               or not math.isfinite(x["first_post_restore_grid_stamp"])
               or x["first_post_restore_grid_stamp"]<=0
               for x in details)):
        return []
    ordered=sorted(details,key=lambda x:(
        not x["new_lethal_in_last_two_grids"],
        x["first_post_restore_grid_stamp"],
        x["index"]))
    output=[]
    for i in [x["index"] for x in ordered]+suspects:
        if i not in output:
            output.append(i)
        if len(output)>=max_count:
            break
    return output
