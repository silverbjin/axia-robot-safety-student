"""D07-H01 actual motion evidence oracle; pure Python and FAIL-CLOSED.

Exactly one teaching scenario: official Nav2 routes around a physically placed
human-proxy obstacle, followed by actual Waffle motion on the SAME Goal.
No planner/controller/safety command publications, no hardware safety claim.
A pure verdict is never an attestation of ROS/Gazebo provenance on its own.
"""
from __future__ import annotations
import math
import hashlib

GOAL=(-1.7,0.7)
MIN_MODEL_CLEARANCE_M=0.35  # robot_radius .20 + model .07 + margin .08
MIN_PATH_DELTA_M=0.15
MAX_CROSSTRACK_M=0.32
MAX_GOAL_ERROR_M=0.25
MAX_TTLS_SEC={"cm":0.15,"supervisor":0.15,"guard":0.15,
              "scan":0.30,"odom":0.30,"clock":0.30}



def costmap_roundtrip_evidence(baseline_cells, intruded_cells, restored_cells, *,
                               native_restore_ack, post_restore_scan_advanced,
                               post_restore_costmap_samples):
    """Read-only NO-GOAL Costmap obstacle insertion and baseline restoration.

    Compare against the SAME live official Costmap's measured pre-intrusion
    neighborhood. The static / global map need not have ZERO lethal cells.
    Never mistake an arbitrary reset or stale Costmap for clearing.
    """
    blocked = {
        "status": "BLOCKED",
        "reason": "COSTMAP_BASELINE_OR_FRESH_RESTORATION_NOT_PROVEN",
        "baseline_costmap_lethal_cells": baseline_cells,
        "intrusion_costmap_lethal_cells": intruded_cells,
        "restored_costmap_lethal_cells": restored_cells,
        "goal_sent": False,
        "motion_admitted": False,
        "collision_free_verified": False,
        "spatial_restoration_proven": False,
        "certified_estop": False,
    }
    if any(type(v) is not int or v < 0 for v in (
            baseline_cells, intruded_cells, restored_cells)):
        return blocked
    if (native_restore_ack is not True
            or post_restore_scan_advanced is not True
            or type(post_restore_costmap_samples) is not int
            or post_restore_costmap_samples < 2):
        return blocked
    difference = intruded_cells - baseline_cells
    if difference < 3:
        return {**blocked, "reason": "NO_REAL_COSTMAP_MARKING_DELTA",
                "intrusion_delta_cells": difference}
    if restored_cells != baseline_cells:
        return {**blocked, "reason": "COSTMAP_DID_NOT_RETURN_TO_MEASURED_BASELINE",
                "intrusion_delta_cells": difference}
    return {**blocked, "status": "LETHAL_COUNT_RETURNED_NO_GOAL",
            "reason": "LETHAL_COUNT_ONLY_SPATIAL_AND_PATH_SEPARATELY_REQUIRED",
            "intrusion_delta_cells": difference}


def _xy(x):
    if not isinstance(x,(list,tuple)) or len(x)!=2:
        return None
    if not all(type(v) in (int,float) and math.isfinite(v) for v in x):
        return None
    return (float(x[0]),float(x[1]))


def _path(x):
    if not isinstance(x,(list,tuple)) or len(x)<3:
        return None
    out=[_xy(p) for p in x]
    if any(v is None for v in out):
        return None
    return out


def segment_distance(p,a,b):
    """Point-to-closed-segment distance; tests mid-segment intrusions."""
    p,a,b=(_xy(v) for v in (p,a,b))
    if p is None or a is None or b is None:
        raise ValueError("INVALID_SEGMENT_COORDINATES")
    dx,dy=b[0]-a[0],b[1]-a[1]
    norm=dx*dx+dy*dy
    t=0.0 if norm<=1e-12 else max(0.,min(1.,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/norm))
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)


def path_distance(p,path):
    points=_path(path)
    if points is None or _xy(p) is None:
        raise ValueError("INVALID_PATH_GEOMETRY")
    return min(segment_distance(p,a,b) for a,b in zip(points,points[1:]))




def costmap_spatial_diff(before, restored, *, obstacle_map_xy=Ellipsis):
    """Read-only exact grid comparison, not a safety/collision acceptance.

    Same lethal COUNT can hide different cell positions or changed inflation
    costs. Compare complete live OccupancyGrid values and metadata; emit only
    bounded mismatch examples and SHA256, never inferred motion evidence.
    """
    blocked={"status":"BLOCKED","reason":"INVALID_OR_MISMATCHED_COSTMAP_GRID",
             "goal_sent":False,"motion_admitted":False,
             "collision_free_verified":False,"certified_estop":False}
    def parse(raw):
        if not isinstance(raw,dict):
            return None
        w,h=raw.get("width"),raw.get("height")
        res=raw.get("resolution")
        frame=raw.get("frame")
        origin=raw.get("origin")
        vals=raw.get("cells")
        if (type(w) is not int or type(h) is not int or not 1<=w*h<=1000000
                or w<=0 or h<=0 or frame!="map"
                or type(res) not in (int,float)
                or not math.isfinite(res) or not 0<res<=.5
                or not isinstance(origin,(list,tuple)) or len(origin)!=2
                or any(type(t) not in (int,float) or not math.isfinite(t)
                       for t in origin)
                or not isinstance(vals,(list,tuple)) or len(vals)!=w*h
                or any(type(v) is not int or not -1<=v<=100 for v in vals)):
            return None
        return ((w,h,float(res),tuple(float(t) for t in origin),frame),
                tuple(vals))
    b,a=parse(before),parse(restored)
    if b is None or a is None or b[0]!=a[0]:
        return blocked
    meta=b[0]
    width,height,res,origin,_=meta
    if obstacle_map_xy is Ellipsis:
        obstacle=None
    else:
        obstacle=_xy(obstacle_map_xy)
        if (obstacle is None or
              not (origin[0]<=obstacle[0]<origin[0]+width*res) or
              not (origin[1]<=obstacle[1]<origin[1]+height*res)):
            return {**blocked,"reason":"OBSTACLE_OUTSIDE_REAL_COSTMAP_FRAME"}
    x,y=b[1],a[1]
    changed=[i for i,(v,w) in enumerate(zip(x,y)) if v!=w]
    increased=sum(1 for i in changed if y[i]>x[i])
    decreased=len(changed)-increased
    new_lethal=sum(1 for i in changed if x[i]<95<=y[i])
    removed_lethal=sum(1 for i in changed if y[i]<95<=x[i])
    def center(i):
        return (origin[0]+((i%width)+.5)*res,
                origin[1]+((i//width)+.5)*res)
    changed_centers=[center(i) for i in changed]
    bounds=(None if not changed else {
        "min_x":round(min(v[0] for v in changed_centers),4),
        "max_x":round(max(v[0] for v in changed_centers),4),
        "min_y":round(min(v[1] for v in changed_centers),4),
        "max_y":round(max(v[1] for v in changed_centers),4),
    })
    changed_near=(None if obstacle is None else
                  sum(1 for xy in changed_centers
                      if math.dist(xy,obstacle)<=.75))
    before_hash=hashlib.sha256(bytes(v & 255 for v in x)).hexdigest()
    after_hash=hashlib.sha256(bytes(v & 255 for v in y)).hexdigest()
    return {**blocked,
            "status":"GRID_IDENTICAL_NO_GOAL" if not changed
                     else "GRID_DIFFERENT_NO_GOAL",
            "reason":"COSTMAP_SPATIAL_IDENTICAL" if not changed
                     else "COSTMAP_SPATIAL_CHANGED_NEEDS_REVIEW",
            "baseline_sha256":before_hash,
            "restored_sha256":after_hash,
            "different_cell_count":len(changed),
            "increased_cell_count":increased,
            "decreased_cell_count":decreased,
            "new_lethal_cell_count":new_lethal,
            "removed_lethal_cell_count":removed_lethal,
            "changed_inside_0p75m_obstacle":changed_near,
            "changed_bounds_map_xy":bounds,
            "first_changed_cells":[
                {"index":i,"row":i//b[0][0],"col":i%b[0][0],
                 "before":x[i],"restored":y[i]} for i in changed[:12]],
            "width":b[0][0],"height":b[0][1]}


def baseline_path_restoration(before, restored, *, obstacle_map_xy,
                              costmap_roundtrip_ready, scan_stamp_advanced):
    """Check live official ComputePathToPose returns near the original path.

    A Costmap's lethal-cell count can recover before PlannerServer updates its
    own costmap. This read-only check requires the SAME Goal/start, genuine
    map-frame Nav2 paths, fresh actual scan and restored Costmap. No motor Goal.
    """
    blocked = {"status": "BLOCKED", "reason": "BASELINE_PATH_PROVENANCE_MISSING",
               "goal_sent": False, "robot_moved": False,
               "motion_admitted": False, "certified_estop": False}
    if costmap_roundtrip_ready is not True or scan_stamp_advanced is not True:
        return {**blocked, "reason": "FRESH_LIDAR_OR_COSTMAP_NOT_RESTORED"}
    if not isinstance(before, dict) or not isinstance(restored, dict):
        return blocked
    if any(entry.get("source") != "official_nav2" or entry.get("frame_id") != "map"
           for entry in (before, restored)):
        return blocked
    old, new = _path(before.get("poses")), _path(restored.get("poses"))
    ref = _xy(obstacle_map_xy)
    starts = [_xy(entry.get("start")) for entry in (before, restored)]
    goals = [_xy(entry.get("goal")) for entry in (before, restored)]
    if (old is None or new is None or ref is None
            or any(v is None for v in starts + goals)):
        return blocked
    if (math.dist(starts[0], starts[1]) > .20
            or any(math.dist(g, GOAL) > .10 for g in goals)
            or math.dist(old[0], starts[0]) > .25
            or math.dist(new[0], starts[1]) > .25
            or math.dist(old[-1], GOAL) > .25
            or math.dist(new[-1], GOAL) > .25):
        return {**blocked, "reason": "OFFICIAL_PLANNER_GOAL_OR_START_CHANGED"}
    baseline_min = path_distance(ref, old)
    restored_min = path_distance(ref, new)
    path_delta = max(path_distance(pt, old) for pt in new)
    values = {"baseline_path_min_m": round(baseline_min, 4),
              "restored_path_min_m": round(restored_min, 4),
              "path_return_delta_m": round(path_delta, 4),
              "before_points": len(old), "restored_points": len(new)}
    if restored_min > baseline_min + .10 or path_delta > .15:
        return {**blocked, **values, "reason": "OFFICIAL_PATH_STILL_DETOURED"}
    return {**blocked, **values,
            "status": "RESTORED_OFFICIAL_NAV2_BASELINE_NO_GOAL",
            "reason": "FRESH_OFFICIAL_PLANNER_PATH_RETURNED_AFTER_COSTMAP_CLEAR"}


def select_route_intrusion(path, *, map_pose, world_pose,
                           min_range_m=.60,max_range_m=1.40,
                           second_free_path=Ellipsis):
    """One stationary-Gazebo obstacle candidate ON the actual Nav2 baseline.

    Uses a real map/world anchor already verified by the G07 startup. Computes
    candidate only; never creates, moves or commands a Gazebo entity.
    """
    points=_path(path)
    # Existing callers remain unchanged. H01 real runner passes a SECOND
    # independent official free-space path; any malformed explicit second
    # reference must fail before changing the physical Gazebo obstacle pose.
    other=None
    if second_free_path is not Ellipsis:
        other=_path(second_free_path)
        if other is None:
            raise ValueError("D07_H01_SECOND_FREE_OFFICIAL_PATH_INVALID")
    def _anchor(v):
        if not isinstance(v,(tuple,list)) or len(v)!=3 or not all(
                type(z) in (int,float) and math.isfinite(z) for z in v):
            return None
        return tuple(float(z) for z in v)
    mp,wp=_anchor(map_pose),_anchor(world_pose)
    if (points is None or mp is None or wp is None
            or math.dist((wp[0],wp[1]),(-2.,-.5))>.20
            or abs(wp[2])>.15
            or math.dist(points[0],mp[:2])>.30
            or type(min_range_m) not in (int,float)
            or type(max_range_m) not in (int,float)
            or not math.isfinite(min_range_m)
            or not math.isfinite(max_range_m)
            or not .55<=min_range_m<max_range_m<=1.50):
        raise ValueError("D07_H01_INVALID_OFFICIAL_ROUTE_OR_FRAME_ANCHOR")
    length=[math.dist(a,b) for a,b in zip(points,points[1:])]
    total=sum(length)
    if total<.9:
        raise ValueError("D07_H01_OFFICIAL_ROUTE_TOO_SHORT_FOR_INTRUSION")
    heading=wp[2]-mp[2]
    # Preserve exact legacy preference and all physical/map/world/Goal
    # boundaries. Real L2 #43666176258 found two valid official FREE paths
    # differing 0.4515m; four sparse fractions missed their shared section.
    # Only when an independently witnessed second path exists, sample
    # bounded arc-length candidates at approximately 0.025m. No widened
    # clearance or shortcut to motion. Long/implausible paths fail closed.
    proposals=[(f,"FOUR_PREFERRED_ARC_FRACTION")
               for f in (.55,.65,.45,.70)]
    if other is not None:
        sample_count=math.ceil(total/.025)
        if sample_count>400:
            raise ValueError("D07_H01_SHARED_ARC_SEARCH_BUDGET_EXCEEDED")
        proposals.extend(
            (k/sample_count,"BOUNDED_SHARED_ARC_SAMPLE")
            for k in range(1,sample_count))
    for fraction,search_kind in proposals:
        target=total*fraction
        accum=0.
        xy=None
        for i,seg in enumerate(length):
            if accum+seg>=target and seg>1e-8:
                alpha=(target-accum)/seg
                xy=(points[i][0]+alpha*(points[i+1][0]-points[i][0]),
                    points[i][1]+alpha*(points[i+1][1]-points[i][1]))
                break
            accum+=seg
        if xy is None:
            continue
        dist=math.dist(xy,mp[:2])
        dx,dy=xy[0]-mp[0],xy[1]-mp[1]
        wx=wp[0]+math.cos(heading)*dx-math.sin(heading)*dy
        wy=wp[1]+math.sin(heading)*dx+math.cos(heading)*dy
        bearing=math.atan2(dy,dx)-mp[2]
        bearing=math.atan2(math.sin(bearing),math.cos(bearing))
        if (min_range_m<=dist<=max_range_m
                and -2.6<=wx<=-1.0 and -.95<=wy<=1.55
                and -2.40<=xy[0]<=-1.30 and -.25<=xy[1]<=.95
                and math.dist(xy,GOAL)>.30):
            second_distance=(path_distance(xy,other) if other is not None
                             else None)
            # A naturally detoured second FREE Planner path is not evidence
            # of a physical obstacle causing a later replan. Require the
            # actual cylinder to intersect both independently observed paths.
            if second_distance is not None and second_distance>.20:
                continue
            return {"map_xy":list(xy),"world_xy":[wx,wy],
                    "bearing_rad":bearing,"robot_distance_m":dist,
                    "fraction":fraction,"source":"OFFICIAL_NAV2_BASELINE_PATH",
                    "search_kind":search_kind,
                    "second_free_min_m":(
                        round(second_distance,4) if second_distance is not None
                        else None),
                    "both_official_free_paths_cross_obstacle":other is not None,
                    "goal_sent":False,"motion_admitted":False}
    if other is not None:
        raise ValueError("D07_H01_NO_COMMON_OFFICIAL_FREE_PATH_FOR_INTRUSION")
    raise ValueError("D07_H01_NO_ADMISSIBLE_BASELINE_ROUTE_INTRUSION")


def route_evidence(before,after,*,obstacle_map_xy,scan_stamp_advanced,
                   costmap_observed,contact_topic_proven,frame_anchor_attested):
    """Conservatively validate candidate route change before any motion claim.

    Inputs MUST originate from live same-session official Nav2 Action/Path
    streams and verified map↔world transform, not synthetic classroom fixture.
    """
    fail={"status":"BLOCKED","geometry_ready":False,"goal_sent":False,
          "robot_moved":False,"certified_estop":False,
          "contact_ready":False,"motion_admitted":False,
          "reason":"INVALID_REAL_NAV2_ROUTE_EVIDENCE"}
    # Contact ground truth is a requirement for a later *moving* Goal, not for
    # recording a physical sensor / Costmap / official Planner NO-GOAL lesson.
    # If absent, permit geometry-only evidence with an explicit CONTACT_HOLD,
    # but NEVER grant motor authority or a collision-free result.
    if any(v is not True for v in (scan_stamp_advanced,costmap_observed,
                                  frame_anchor_attested)):
        return {**fail,"reason":"REAL_SCAN_COSTMAP_OR_FRAME_MISSING"}
    contact_ready = contact_topic_proven is True
    if not isinstance(before,dict) or not isinstance(after,dict):
        return fail
    if before.get("frame_id")!="map" or after.get("frame_id")!="map":
        return {**fail,"reason":"MISMATCHED_MAP_FRAME"}
    if before.get("source")!="official_nav2" or after.get("source")!="official_nav2":
        return {**fail,"reason":"NOT_OFFICIAL_NAV2_PATH"}
    p=_xy(obstacle_map_xy)
    a,b=_path(before.get("poses")),_path(after.get("poses"))
    if p is None or a is None or b is None:
        return fail
    if any(math.dist(points[0],(before.get("start") or ()))>.20 for points in (a,b)
           if _xy(before.get("start")) is not None):
        return {**fail,"reason":"START_POSE_MISMATCH"}
    if (math.dist(a[-1],GOAL)>.25 or math.dist(b[-1],GOAL)>.25
          or math.dist(a[0],b[0])>.20):
        return {**fail,"reason":"GOAL_OR_START_CHANGED"}
    if not all((-2.50<=x<=-1.0 and -1.0<=y<=1.55) for x,y in (*a,*b)):
        return {**fail,"reason":"PATH_OUTSIDE_VERIFIED_DEMO_REGION"}
    db=path_distance(p,a); da=path_distance(p,b)
    delta=max(path_distance(point,a) for point in b)
    if db>MIN_MODEL_CLEARANCE_M or da<MIN_MODEL_CLEARANCE_M or delta<MIN_PATH_DELTA_M:
        return {**fail,"reason":"NO_VERIFIED_NAV2_DETOUR",
                "before_min_m":round(db,4),"after_min_m":round(da,4),
                "path_delta_m":round(delta,4)}
    return {"status":("D07_H01_ROUTE_GEOMETRY_CANDIDATE" if contact_ready
                      else "D07_H01_ROUTE_GEOMETRY_CANDIDATE_CONTACT_HOLD"),
            "geometry_ready":True,
            "goal_sent":False,"robot_moved":False,
            "contact_ready":contact_ready,"motion_admitted":False,
            "certified_estop":False,"obstacle_map_xy":list(p),
            "before_min_m":round(db,4),"after_min_m":round(da,4),
            "path_delta_m":round(delta,4),"goal_map":list(GOAL),
            "reason":"PHYSICAL_MOTION_NOT_YET_PROVEN"}


def motion_evidence(route,*,goal_uuids,terminal_status,odom_map_xy,
                    post_intrusion_odom_map_xy,contact_ground_truth,
                    contact_sample_count,contact_events,
                    guard_latched,ttls_sec,final_cmd_publisher_count,
                    scan_after_intrusion,costmap_after_intrusion):
    """Strict actual-L2 gate. Only real raw evidence may be supplied.

    Contact sensor publication being present does NOT establish contact-free:
    contact counting + topic ground-truth provenance must independently pass.
    """
    blocked={"status":"BLOCKED","real_motion_avoidance":False,
             "certified_estop":False,"formal_accepted":False}
    if not isinstance(route,dict) or route.get("geometry_ready") is not True:
        return {**blocked,"reason":"NO_PREAPPROVED_REAL_ROUTE"}
    if route.get("contact_ready") is not True:
        return {**blocked,"reason":"CONTACT_HOLD_NO_GOAL_PERMITTED"}
    if (not isinstance(goal_uuids,(list,tuple)) or len(goal_uuids)!=1
            or not isinstance(goal_uuids[0],str) or len(goal_uuids[0])!=32
            or terminal_status!="SUCCEEDED"):
        return {**blocked,"reason":"GOAL_CHANGED_OR_NOT_SUCCEEDED"}
    if (guard_latched is not False or final_cmd_publisher_count!=1
            or scan_after_intrusion is not True or costmap_after_intrusion is not True):
        return {**blocked,"reason":"FIRST_SAFETY_GRAPH_OR_SENSOR_BOUNDARY"}
    if not isinstance(ttls_sec,dict) or any(
          type(ttls_sec.get(k)) not in (int,float)
          or not math.isfinite(ttls_sec[k]) or ttls_sec[k]>=limit
          for k,limit in MAX_TTLS_SEC.items()):
        return {**blocked,"reason":"FIRST_CROSS_NODE_TTL_BOUNDARY"}
    if (contact_ground_truth is not True or type(contact_sample_count) is not int
            or contact_sample_count<2 or type(contact_events) is not int
            or contact_events!=0):
        return {**blocked,"reason":"CONTACT_GROUND_TRUTH_UNAVAILABLE_OR_POSITIVE"}
    p=_xy(route.get("obstacle_map_xy"))
    rows=_path(odom_map_xy)
    post=_path(post_intrusion_odom_map_xy)
    if p is None or rows is None or post is None:
        return {**blocked,"reason":"REAL_ODOM_FRAME_OR_SAMPLES_MISSING"}
    displacement=math.dist(rows[0],rows[-1])
    moved_after=math.dist(post[0],post[-1])
    clearance=min(math.dist(p,xy) for xy in post)
    if (displacement<.20 or moved_after<.10 or
        math.dist(rows[-1],GOAL)>MAX_GOAL_ERROR_M or
        clearance<MIN_MODEL_CLEARANCE_M):
        return {**blocked,"reason":"MOTION_GOAL_OR_CONTACT_CLEARANCE_NOT_PROVEN",
                "odom_displacement_m":round(displacement,4),
                "post_intrusion_displacement_m":round(moved_after,4),
                "post_intrusion_clearance_m":round(clearance,4)}
    return {**blocked,"status":"D07_H01_ACTUAL_GAZEBO_L2_SCOPED_CANDIDATE",
            "real_motion_avoidance":True,"goal_uuid":goal_uuids[0],
            "odom_displacement_m":round(displacement,4),
            "post_intrusion_displacement_m":round(moved_after,4),
            "minimum_observed_center_clearance_m":round(clearance,4),
            "contact_ground_truth":True,"contact_events":0,
            "reason":"SCOPED_TEACHING_SIMULATION_ONLY_OWNER_NOT_ACCEPTED"}


def assess_h01_pre_goal(geometry_report: dict, contact_report: dict,
                        timing_report: dict, *, source_sha: str,
                        runtime_sha: str) -> dict:
    """Pure pre-Goal evidence gate; never an actual ROS Goal sender.

    This only evaluates externally recorded, source-pinned data. It must
    additionally pass the PUBLIC exact-SHA GitHub simulation admission
    contract and re-check actual graph/TTL during physical motion.
    """
    blocked={"status":"H01_PRE_GOAL_BLOCKED","authorized":False,
             "goal_sent":False,"motion_admitted":False,
             "certified_estop":False,"reason":"MISSING_PROVENANCE_OR_SAFETY_GATE"}
    if (not isinstance(geometry_report,dict) or
        not isinstance(contact_report,dict) or
        not isinstance(timing_report,dict)):
        return blocked
    geo,contact,timing=geometry_report,contact_report,timing_report
    validsha=(type(source_sha) is str and len(source_sha)==40
              and all(c in "0123456789abcdef" for c in source_sha))
    digest=(type(runtime_sha) is str and runtime_sha.startswith("sha256:")
            and len(runtime_sha)==71
            and all(c in "0123456789abcdef" for c in runtime_sha[7:]))
    if (not validsha or not digest
        or geo.get("source_sha")!=source_sha
        or contact.get("source_sha")!=source_sha
        or timing.get("source_sha")!=source_sha
        or timing.get("runtime_digest")!=runtime_sha
        or timing.get("scope")!="PUBLIC_CI_SIM_ONLY"):
        return {**blocked,"reason":"EXACT_SHA_RUNTIME_OR_CI_SCOPE_NOT_PROVEN"}
    if (geo.get("status")!="D07_H01_REAL_NAV2_GEOMETRY_READY_NO_GOAL"
        or geo.get("goal_sent") is not False
        or geo.get("spatial_restoration_proven") is not True
        or geo.get("first_invalid_boundary") is not None
        or any(geo.get(k) is not True for k in (
            "real_nav2","real_laser_scan","path_viable",
            "post_ack_scan_stamp_progressed",
            "actual_costmap_obstacle_observed",
            "path_changed","obstacle_restored_away"))):
        return {**blocked,"reason":"REAL_SPATIAL_PATH_PRE_GOAL_GATE_HOLD"}
    if (contact.get("status")!="CONTACT_WINDOW_VALIDATED_NO_GOAL"
        or contact.get("robot_obstacle_contact_count")!=0
        or any(contact.get(k) is not True for k in (
            "contact_ground_truth_ready","source_verified",
            "positive_control_verified","monitor_window_covered"))):
        return {**blocked,"reason":"NATIVE_CONTACT_GROUND_TRUTH_NOT_PROVEN"}
    if (timing.get("first_safety_transition") is not None
        or timing.get("first_ttl_violation") is not None):
        return {**blocked,"reason":"FIRST_SAFETY_OR_TTL_VIOLATION",
                "first_safety_transition":timing.get("first_safety_transition"),
                "first_ttl_violation":timing.get("first_ttl_violation")}
    if (any(timing.get(k) is not True for k in (
            "sim_clock_advancing","actual_graph_verified",
            "exclusive_final_command_authority",
            "actual_timestamps_verified"))
        or timing.get("nav_goal_count_before_admission")!=0):
        return {**blocked,"reason":"ACTUAL_GRAPH_OR_ONE_GOAL_OWNER_NOT_PROVEN"}
    ages=timing.get("ages_sec")
    samples=timing.get("samples")
    if not isinstance(ages,dict) or not isinstance(samples,dict):
        return {**blocked,"reason":"REAL_CROSS_NODE_PERIOD_MISSING"}
    for key,limit in MAX_TTLS_SEC.items():
        age=ages.get(key)
        count=samples.get(key)
        if (type(age) not in (int,float) or not math.isfinite(age)
            or age<0 or age>=limit
            or type(count) is not int or count<2):
            return {**blocked,"reason":"REAL_CROSS_NODE_TTL_OR_SAMPLES_EXCEEDED",
                    "first_invalid_edge":key}
    return {**blocked,
            "status":"H01_CI_ONE_GOAL_ADMITTED_NO_GOAL_SENT",
            "authorized":True,"reason":"EVIDENCE_GATES_ONLY_RUNTIME_GOAL_STILL_NOT_SENT"}


def assess_h01_pre_goal(geometry_report: dict, contact_report: dict,
                        timing_report: dict, *, source_sha: str,
                        runtime_sha: str) -> dict:
    """Pure fail-closed CI simulation evidence predicate, never a ROS Goal.

    The final public environment admission must independently verify source,
    graph ownership, permissions, and actual in-motion safety TTL.
    """
    blocked={"status":"H01_PRE_GOAL_BLOCKED","authorized":False,
             "goal_sent":False,"motion_admitted":False,
             "certified_estop":False,"reason":"MISSING_PROVENANCE_OR_SAFETY_GATE"}
    if any(not isinstance(v,dict) for v in (
            geometry_report,contact_report,timing_report)):
        return blocked
    geo,contact,timing=geometry_report,contact_report,timing_report
    validsha=(type(source_sha) is str and len(source_sha)==40
              and all(c in "0123456789abcdef" for c in source_sha))
    digest=(type(runtime_sha) is str and runtime_sha.startswith("sha256:")
            and len(runtime_sha)==71
            and all(c in "0123456789abcdef" for c in runtime_sha[7:]))
    if (not validsha or not digest
        or geo.get("source_sha")!=source_sha
        or contact.get("source_sha")!=source_sha
        or timing.get("source_sha")!=source_sha
        or timing.get("runtime_digest")!=runtime_sha
        or timing.get("scope")!="PUBLIC_CI_SIM_ONLY"):
        return {**blocked,"reason":"EXACT_SHA_RUNTIME_OR_CI_SCOPE_NOT_PROVEN"}
    if (geo.get("status")!="D07_H01_REAL_NAV2_GEOMETRY_READY_NO_GOAL"
        or geo.get("goal_sent") is not False
        or geo.get("spatial_restoration_proven") is not True
        or geo.get("first_invalid_boundary") is not None
        or any(geo.get(k) is not True for k in (
            "real_nav2","real_laser_scan","path_viable",
            "post_ack_scan_stamp_progressed",
            "actual_costmap_obstacle_observed",
            "path_changed","obstacle_restored_away"))):
        return {**blocked,"reason":"REAL_SPATIAL_PATH_PRE_GOAL_GATE_HOLD"}
    if (contact.get("status")!="CONTACT_WINDOW_VALIDATED_NO_GOAL"
        or contact.get("robot_obstacle_contact_count")!=0
        or any(contact.get(k) is not True for k in (
            "contact_ground_truth_ready","source_verified",
            "positive_control_verified","monitor_window_covered"))):
        return {**blocked,"reason":"NATIVE_CONTACT_GROUND_TRUTH_NOT_PROVEN"}
    if (timing.get("first_safety_transition") is not None
        or timing.get("first_ttl_violation") is not None):
        return {**blocked,"reason":"FIRST_SAFETY_OR_TTL_VIOLATION",
                "first_safety_transition":timing.get("first_safety_transition"),
                "first_ttl_violation":timing.get("first_ttl_violation")}
    if (any(timing.get(k) is not True for k in (
            "sim_clock_advancing","actual_graph_verified",
            "exclusive_final_command_authority",
            "actual_timestamps_verified"))
        or timing.get("nav_goal_count_before_admission")!=0):
        return {**blocked,"reason":"ACTUAL_GRAPH_OR_ONE_GOAL_OWNER_NOT_PROVEN"}
    ages=timing.get("ages_sec")
    samples=timing.get("samples")
    if not isinstance(ages,dict) or not isinstance(samples,dict):
        return {**blocked,"reason":"REAL_CROSS_NODE_PERIOD_MISSING"}
    for key,limit in MAX_TTLS_SEC.items():
        age=ages.get(key)
        count=samples.get(key)
        if (type(age) not in (int,float) or not math.isfinite(age)
            or age<0 or age>=limit
            or type(count) is not int or count<2):
            return {**blocked,"reason":"REAL_CROSS_NODE_TTL_OR_SAMPLES_EXCEEDED",
                    "first_invalid_edge":key}
    return {**blocked,"status":"H01_CI_ONE_GOAL_ADMITTED_NO_GOAL_SENT",
            "authorized":True,"reason":"EVIDENCE_GATES_ONLY_RUNTIME_GOAL_STILL_NOT_SENT"}
