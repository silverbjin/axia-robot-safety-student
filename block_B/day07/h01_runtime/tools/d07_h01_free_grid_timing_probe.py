"""No-Goal H01 first PRE_INTRUSION Costmap drift source timing probe.

All receipt timestamps MUST be monotonic host clock, while ROS header stamps
MUST be compared only against each other within the SAME message category.
Never infer causal LaserScan -> ObstacleLayer consumption, CM/Guard TTL, or
motor acceptance from mere coincident callbacks.
"""
from __future__ import annotations
import math

def _number(n):
    return type(n) in (int,float) and math.isfinite(n)

def assess_preintrusion_timing(odom_events, grid_callbacks, scan_callbacks, *,
                               first_changed_indices):
    hold={"schema":"axia_d07_h01_preintrusion_sensor_grid_timing_v1",
          "status":"FREE_GRID_TIMING_PROVENANCE_HOLD",
          "reason":"REAL_ODOM_GRID_SCAN_RECEIPT_JOIN_UNAVAILABLE",
          "first_invalid_boundary":"PRE_INTRUSION_BASELINE_LETHAL_VARIATION",
          "source_causality_proven":False,
          "obstacle_layer_scan_consumed_proven":False,
          "cross_node_ttl_proven":False,
          "motion_admitted":False,"goal_sent":False,
          "certified_estop":False}
    if (not isinstance(odom_events,(list,tuple))
        or not isinstance(grid_callbacks,(list,tuple))
        or not isinstance(scan_callbacks,(list,tuple))
        or not isinstance(first_changed_indices,(list,tuple))
        or not first_changed_indices or len(first_changed_indices)>12
        or any(type(i) is not int or i<0 for i in first_changed_indices)
        or len(set(first_changed_indices))!=len(first_changed_indices)):
        return hold
    if len(grid_callbacks)<2:
        return hold
    grid=list(grid_callbacks)
    if any(not isinstance(g,dict)
           or not _number(g.get("received_monotonic"))
           or not _number(g.get("ros_stamp"))
           or g["ros_stamp"]<=0 for g in grid):
        return hold
    if any(b["received_monotonic"]<=a["received_monotonic"]
           or b["ros_stamp"]<=a["ros_stamp"]
           for a,b in zip(grid,grid[1:])):
        return {**hold,"reason":"NONMONOTONIC_GRID_RECEIPT_OR_HEADER"}
    start=grid[0]["received_monotonic"]-.25
    finish=grid[-1]["received_monotonic"]+.25
    odom=[x for x in odom_events if isinstance(x,dict)
          and x.get("kind")=="odom"
          and all(_number(x.get(k)) for k in ("t","x","y"))
          and start<=x["t"]<=finish]
    scans=[x for x in scan_callbacks if isinstance(x,dict)
           and all(_number(x.get(k))
                   for k in ("received_monotonic","ros_stamp"))
           and x["ros_stamp"]>0
           and start<=x["received_monotonic"]<=finish]
    odom.sort(key=lambda x:x["t"])
    scans.sort(key=lambda x:x["received_monotonic"])
    if len(odom)<2 or len(scans)<2:
        return {**hold,"reason":"REAL_WINDOWED_ODOM_OR_SCAN_SAMPLES_MISSING",
                "odom_samples":len(odom),"scan_samples":len(scans)}
    if any(b["t"]<=a["t"] for a,b in zip(odom,odom[1:])):
        return {**hold,"reason":"NONMONOTONIC_ACTUAL_ODOM_RECEIPTS"}
    if any(b["received_monotonic"]<=a["received_monotonic"]
           or b["ros_stamp"]<=a["ros_stamp"]
           for a,b in zip(scans,scans[1:])):
        return {**hold,"reason":"NONMONOTONIC_ACTUAL_SCAN_RECEIPTS_OR_HEADERS"}
    # Spread is descriptive, NOT a new stationary tolerance or safety gate.
    pts=[(float(row["x"]),float(row["y"])) for row in odom]
    max_span=max(math.dist(a,b) for a in pts for b in pts)
    gaps=[b["received_monotonic"]-a["received_monotonic"]
          for a,b in zip(scans,scans[1:])]
    return {**hold,
            "status":"FREE_GRID_TEMPORAL_SOURCE_DIAGNOSTIC_ONLY",
            "reason":"SCOPED_ACTUAL_RECEIPTS_NOT_RAY_CONSUMPTION_CAUSALITY",
            "first_changed_indices":list(first_changed_indices),
            "odom_samples":len(odom),
            "odom_max_xy_span_m":round(max_span,6),
            "scan_samples":len(scans),
            "scan_max_callback_gap_sec":round(max(gaps),6),
            "scan_ros_header_first_last":[scans[0]["ros_stamp"],
                                          scans[-1]["ros_stamp"]],
            "grid_ros_header_first_last":[grid[0]["ros_stamp"],
                                          grid[-1]["ros_stamp"]],
            "real_callback_window_sec":round(grid[-1]["received_monotonic"]-
                                             grid[0]["received_monotonic"],6)}
