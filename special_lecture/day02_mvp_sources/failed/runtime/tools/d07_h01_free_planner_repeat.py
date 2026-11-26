"""H01 NO-GOAL repeated official free-space Planner output provenance.

One official ComputePathToPose baseline can be naturally unstable even while
the native Waffle is stationary and obstacle is parked AWAY. Measure TWO
independent successful planner results BEFORE physical intrusion to distinguish
free path variation from a true after-clear Planner residual.

This probe never admits motion, clearing, Contact, or causal safety TTL.
"""
from __future__ import annotations
import math
try:
    from .d07_h01_oracle import GOAL,_xy,_path,path_distance
except ImportError:
    from d07_h01_oracle import GOAL,_xy,_path,path_distance


def classify_two_free_official_paths(first,second):
    """Compare actual same-start/goal map-frame paths, not ROS fictitious data."""
    hold={
        "status":"FREE_PATH_PROVENANCE_HOLD_NO_GOAL",
        "reason":"TWO_REAL_SAME_START_GOAL_OFFICIAL_PATHS_NOT_PROVEN",
        "first_invalid_boundary":"FREE_PLANNER_RESULT_PROVENANCE",
        "restored_path_proven":False,
        "motion_admitted":False,"goal_sent":False,
        "collision_free_verified":False,"certified_estop":False,
        "official_free_path_stability_proven":False,
    }
    if not isinstance(first,dict) or not isinstance(second,dict):
        return hold
    if any(x.get("source")!="official_nav2" or x.get("frame_id")!="map"
           for x in (first,second)):
        return hold
    p,q=_path(first.get("poses")),_path(second.get("poses"))
    a,b=_xy(first.get("start")),_xy(second.get("start"))
    g,h=_xy(first.get("goal")),_xy(second.get("goal"))
    t0,t1=first.get("received_at"),second.get("received_at")
    if (p is None or q is None or a is None or b is None or
        g is None or h is None or
        any(type(t) not in (int,float) or not math.isfinite(t) or t<=0
            for t in (t0,t1)) or t1<=t0 or
        math.dist(a,b)>.01 or math.dist(g,h)>.01 or math.dist(g,GOAL)>.10 or
        math.dist(p[0],a)>.25 or math.dist(q[0],b)>.25 or
        math.dist(p[-1],g)>.25 or math.dist(q[-1],h)>.25):
        return hold
    delta_ab=max(path_distance(point,p) for point in q)
    delta_ba=max(path_distance(point,q) for point in p)
    delta=max(delta_ab,delta_ba)
    variant=delta>.15
    return {
        **hold,
        "status":("FREE_OFFICIAL_PATH_VARIATION_OBSERVED_NO_GOAL" if variant
                  else "FREE_OFFICIAL_PATH_REPEAT_STABLE_NO_GOAL"),
        "reason":"TWO_INDEPENDENT_OFFICIAL_PATHS_BEFORE_INTRUSION",
        "first_invalid_boundary":(
            "PRE_INTRUSION_PLANNER_PATH_VARIABILITY" if variant else None),
        "max_bidirectional_path_delta_m":round(delta,4),
        "first_to_second_path_delta_m":round(delta_ab,4),
        "second_to_first_path_delta_m":round(delta_ba,4),
        "first_path_points":len(p),"second_path_points":len(q),
        "first_received_monotonic":t0,"second_received_monotonic":t1,
        "official_free_path_stability_proven":not variant,
        "restored_path_proven":False,
        "motion_admitted":False,"goal_sent":False,
    }


def choose_bounded_free_official_pair(paths):
    """Select ONLY the newest two genuine consecutive stable free Nav2 plans.

    Real H01 #43670282482 had two free paths separated by 0.4277m,
    before any Gazebo cylinder intrusion. Read no more than FOUR official
    ComputePathToPose results and do not hide the first variation.
    A previously stable pair is invalid if the latest path differs.
    This is not path restoration, movement approval or a safety TTL proof.
    """
    hold={
        "schema":"axia_d07_h01_free_planner_stabilization_v1",
        "status":"FREE_OFFICIAL_PAIR_PROVENANCE_HOLD_NO_GOAL",
        "reason":"EXACT_BOUNDED_REAL_OFFICIAL_FREE_PATHS_NOT_PROVEN",
        "first_invalid_boundary":"PRE_INTRUSION_FREE_PLANNER_PROVENANCE",
        "pair_indices":None,
        "first_observed_variation_m":None,
        "obstacle_caused_detour_proven":False,
        "restored_path_proven":False,
        "motion_admitted":False,"goal_sent":False,
        "certified_estop":False}
    if not isinstance(paths,(list,tuple)) or not 2<=len(paths)<=4:
        return hold
    first_variation=None
    latest_status=None
    for i in range(len(paths)-1):
        comparison=classify_two_free_official_paths(paths[i],paths[i+1])
        state=comparison["status"]
        if state=="FREE_PATH_PROVENANCE_HOLD_NO_GOAL":
            return {**hold,"reason":"OFFICIAL_FREE_PATH_FRAME_START_GOAL_OR_RECEIPT_MISMATCH",
                    "failed_pair_indices":[i,i+1]}
        if state=="FREE_OFFICIAL_PATH_VARIATION_OBSERVED_NO_GOAL" and first_variation is None:
            first_variation=comparison["max_bidirectional_path_delta_m"]
        latest_status=state
    if latest_status=="FREE_OFFICIAL_PATH_REPEAT_STABLE_NO_GOAL":
        return {**hold,
                "status":"CONSECUTIVE_FREE_OFFICIAL_PATHS_STABLE_NO_GOAL",
                "reason":"LATEST_TWO_REAL_FREE_OFFICIAL_PATHS_CONSECUTIVE_STABLE",
                "first_invalid_boundary":None,
                "pair_indices":[len(paths)-2,len(paths)-1],
                "free_official_path_results":len(paths),
                "first_observed_variation_m":first_variation,
                "official_free_path_stability_proven":True,
                "obstacle_caused_detour_proven":False,
                "restored_path_proven":False,
                "motion_admitted":False,"goal_sent":False}
    return {**hold,
            "status":("NO_CONSECUTIVE_FREE_PATH_STABILITY_HOLD_NO_GOAL"
                      if len(paths)==4 else
                      "AWAITING_CONSECUTIVE_FREE_PATH_STABILITY_NO_GOAL"),
            "reason":"LATEST_FREE_OFFICIAL_PLANS_STILL_DIVERGE",
            "first_invalid_boundary":"PRE_INTRUSION_FREE_PLANNER_VARIATION",
            "free_official_path_results":len(paths),
            "first_observed_variation_m":first_variation,
            "motion_admitted":False,"goal_sent":False}
