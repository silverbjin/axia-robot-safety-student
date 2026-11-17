"""Read-only *effective* Nav2 global ObstacleLayer scan raytrace config audit.

Only accepts values returned by exact live /global_costmap/global_costmap
ROS parameter services. The parameters describe intended raytracing, NOT
proof that the clearing LaserScan was consumed or the internal map updated.
Never writes parameters, clears Costmap, sends Goal, or relaxes safety TTLs.
"""
from __future__ import annotations
import math

NAMES=(
 "obstacle_layer.observation_sources",
 "obstacle_layer.scan.topic",
 "obstacle_layer.scan.data_type",
 "obstacle_layer.scan.clearing",
 "obstacle_layer.scan.marking",
 "obstacle_layer.scan.inf_is_valid",
 "obstacle_layer.scan.raytrace_max_range",
)
def assess_live_obstacle_clear_config(values):
    hold={"schema":"axia_d07_h01_live_obstacle_config_v1",
          "status":"OBSTACLE_LAYER_PARAMETER_PROVENANCE_HOLD",
          "reason":"EXACT_LIVE_OBSTACLE_LAYER_VALUES_NOT_PROVEN",
          "first_invalid_boundary":"NAV2_PARAMETER_PROVENANCE",
          "clearing_configured":False,
          "inf_is_valid":None,
          "obstacle_cell_clearing_proven":False,
          "scan_consumed_by_obstacle_layer_proven":False,
          "planner_internal_costmap_proven":False,
          "motion_admitted":False,"goal_sent":False,
          "certified_estop":False}
    if not isinstance(values,dict) or any(k not in values for k in NAMES):
        return hold
    p=values
    for key in ("clearing","marking","inf_is_valid"):
        if type(p["obstacle_layer.scan."+key]) is not bool:
            return hold
    range_value=p["obstacle_layer.scan.raytrace_max_range"]
    if (type(range_value) not in (int,float)
        or not math.isfinite(range_value) or range_value<=0):
        return hold
    if (p["obstacle_layer.observation_sources"].strip()!="scan"
        or p["obstacle_layer.scan.topic"] not in ("scan","/scan")
        or p["obstacle_layer.scan.data_type"]!="LaserScan"
        or p["obstacle_layer.scan.marking"] is not True):
        return hold
    if p["obstacle_layer.scan.clearing"] is not True:
        return {**hold,
            "status":"OBSTACLE_CLEARING_DISABLED_CANDIDATE",
            "reason":"ACTUAL_NAV2_GLOBAL_OBSTACLE_SCAN_CLEARING_FALSE",
            "first_invalid_boundary":"NAV2_OBSTACLE_LAYER_SCAN_CLEARING_CONFIG",
            "inf_is_valid":p["obstacle_layer.scan.inf_is_valid"],
            "raytrace_max_range_m":float(range_value)}
    return {**hold,
        "status":"OBSTACLE_RAYTRACE_CONFIG_OBSERVED_NO_GOAL",
        "reason":"RAYTRACING_CONFIGURED_EFFECTIVE_SCAN_CONSUMPTION_UNVERIFIED",
        "first_invalid_boundary":None,
        "clearing_configured":True,
        "inf_is_valid":p["obstacle_layer.scan.inf_is_valid"],
        "raytrace_max_range_m":float(range_value),
        "data_source":p["obstacle_layer.observation_sources"],
        "scan_topic":p["obstacle_layer.scan.topic"],
        "obstacle_cell_clearing_proven":False,
        "scan_consumed_by_obstacle_layer_proven":False,
        "planner_internal_costmap_proven":False,
        "motion_admitted":False,"goal_sent":False,
    }
