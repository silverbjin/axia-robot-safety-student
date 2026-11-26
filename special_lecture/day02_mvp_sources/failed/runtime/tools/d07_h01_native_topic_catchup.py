"""One bounded NO-GOAL source/observer timestamp join after Costmap clearing fails.

Actual public Gazebo #43606752993: last OccupancyGrid header 80.028s has
two residual ROI lethal cells, but a later official native Master GetCostmap
header 82.617s shows their baseline costs and ObstacleLayer=0. Such *different
epochs* cannot support either a clearing failure cause or an acceptance PASS.

Require two genuinely later, source-stamped same-session OccupancyGrid
callbacks to assess whether the published map caught up. This is NOT
a safety TTL relaxation, a ROS Goal, or atomic PlannerServer evidence.
"""
from __future__ import annotations
import math
try:
    from .d07_h01_costmap_drift import _read
    from .d07_h01_native_costmap_layers import _to_occupancy
except ImportError:
    from d07_h01_costmap_drift import _read
    from d07_h01_native_costmap_layers import _to_occupancy


def assess_native_topic_catchup(before_topic,native_after,post_native_topics):
    hold={
        "schema":"axia_d07_h01_native_publish_catchup_v1",
        "status":"POST_NATIVE_PUBLISHED_MAP_PROVENANCE_HOLD",
        "reason":"MISSING_TWO_FRESH_SAME_SESSION_POST_NATIVE_GRIDS",
        "first_invalid_boundary":"SOURCE_TO_TOPIC_FRESHNESS_NOT_PROVEN",
        "source_causality_proven":False,
        "native_costmap_clearing_proven":False,
        "obstacle_layer_scan_consumed_proven":False,
        "planner_internal_costmap_proven":False,
        "collision_free_verified":False,
        "motion_admitted":False,"goal_sent":False,
        "certified_estop":False,
    }
    old=_read(before_topic)
    if (old is None or not isinstance(native_after,dict)
        or native_after.get("status")!="NATIVE_LAYER_SUSPECT_COSTS_OBSERVED_NO_GOAL"
        or native_after.get("motion_admitted") is not False
        or native_after.get("source_services",{}).get("costmap")!="/global_costmap/get_costmap"
        or native_after.get("atomic_snapshot_proven") is not False
        or not isinstance(post_native_topics,(list,tuple))
        or not 2<=len(post_native_topics)<=12):
        return hold
    stamp=native_after.get("service_stamps",{}).get("costmap")
    if (type(stamp) not in (float,int) or not math.isfinite(stamp)
        or stamp<=old["stamp"]):
        return hold
    native_samples=native_after.get("samples")
    if (not isinstance(native_samples,(tuple,list))
        or not 1<=len(native_samples)<=12):
        return hold
    expected={}
    for row in native_samples:
        if not isinstance(row,dict):
            return hold
        i,c,reported=(row.get("index"),row.get("master_raw"),
                       row.get("topic_occupancy"))
        if (type(i) is not int or not 0<=i<len(old["cells"])
            or i in expected or type(c) is not int or not 0<=c<=255
            or type(reported) is not int
            or reported!=old["cells"][i]):
            return hold
        expected[i]=_to_occupancy(c)
    post=[_read(item) for item in post_native_topics]
    if any(row is None or row["key"]!=old["key"] for row in post):
        return hold
    prev_stamp=stamp
    prev_receive=old["received"]
    for row in post:
        if row["stamp"]<=prev_stamp or row["received"]<=prev_receive:
            return hold
        prev_stamp=row["stamp"]
        prev_receive=row["received"]
    def mismatch(row):
        return sum(row["cells"][i]!=value for i,value in expected.items())
    prior_mismatch=[i for i,v in sorted(expected.items())
                    if old["cells"][i]!=v]
    after_mismatches=[mismatch(v) for v in post]
    latest_two=after_mismatches[-2:]
    stable_two=latest_two==[0,0]
    converged=stable_two and bool(prior_mismatch)
    # Actual L2 #43608469169: [12,0] is neither persistent mismatch
    # nor two verified matching updates. First source-stamp match is LATE,
    # not sufficient to establish stable clearing or grant motor authority.
    first_match_idx=next((i for i,n in enumerate(after_mismatches) if n==0),None)
    late_first_match=latest_two[0]>0 and latest_two[1]==0
    if converged:
        status="PUBLISHED_GRID_CAUGHT_UP_TO_NATIVE_CANDIDATE_NO_GOAL"
        first=None
    elif late_first_match:
        status="PUBLISHED_GRID_FIRST_MATCH_AFTER_DELAY_HOLD_NO_GOAL"
        first="FIRST_POST_NATIVE_PUBLISHED_COSTMAP_MISMATCH"
    elif any(latest_two):
        status="PUBLISHED_GRID_STILL_MISMATCHED_NATIVE_HOLD_NO_GOAL"
        first="POST_NATIVE_PUBLISHED_COSTMAP_MISMATCH"
    else:
        status="PUBLISHED_GRID_ALREADY_MATCHES_NATIVE_NO_CAUSAL_PROOF"
        first=None
    first_idx=prior_mismatch[0] if prior_mismatch else None
    return {**hold,
        "status":status,
        "reason":"ASYNCHRONOUS_NATIVE_MASTER_AND_TOPIC_ONLY_NOT_PLANNER_STATE_PROOF",
        "first_invalid_boundary":first,
        "native_master_header_stamp":float(stamp),
        "old_topic_header_stamp":old["stamp"],
        "old_grid_to_native_source_stamp_gap_sec":round(stamp-old["stamp"],6),
        "first_original_mismatch":(
            {"index":first_idx,"old_occupancy":old["cells"][first_idx],
             "native_translated_occupancy":expected[first_idx]}
            if first_idx is not None else None),
        "old_topic_mismatch_cells":len(prior_mismatch),
        "new_topic_header_stamps":[p["stamp"] for p in post],
        "last_two_post_native_mismatch_counts":latest_two,
        "first_match_grid_minus_native_stamp_sec":(
            round(post[first_match_idx]["stamp"]-stamp,6)
            if first_match_idx is not None else None),
        "two_consecutive_native_matches_verified":stable_two,
        "genuine_post_native_grid_samples":len(post),
        "native_topic_observed_convergence_candidate":converged,
        "source_causality_proven":False,
        "native_costmap_clearing_proven":False,
        "planner_internal_costmap_proven":False,
        "motion_admitted":False,"goal_sent":False,
    }
