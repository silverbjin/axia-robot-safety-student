"""D07-H01 read-only delivery from actual Nav2 configured /scan source.

Real Gazebo #43600799195: after native restore /safety/scan reported a
fresh finite >1.7m ray but published Costmap at the same ROI flickered.
The running official global Costmap's actual ObstacleLayer scan.topic is
/scan, NOT /safety/scan. Compare both live callback streams; NEVER
equate receiving /scan with proof that ObstacleLayer consumed it.
No parameter write, synthetic message, motor, Goal, or safety TTL acceptance.
"""
from __future__ import annotations
import math


def assess_real_nav2_scan_delivery(
        raw_scan_samples,safety_scan_samples,*,
        restore_received_monotonic,intrusion_ros_stamp,
        minimum_clear_range_m):
    hold={
        "schema":"axia_d07_h01_nav2_scan_delivery_v1",
        "status":"NAV2_RAW_SCAN_SOURCE_PROVENANCE_HOLD",
        "reason":"RAW_NAV2_OR_SAFETY_SCAN_FRESHNESS_UNVERIFIED",
        "first_invalid_boundary":"NAV2_CONFIGURED_RAW_SCAN_OR_SAFETY_SCAN_MISSING",
        "raw_scan_progress_count":0,
        "safety_scan_progress_count":0,
        "raw_clear_finite_beam_observed":False,
        "safety_clear_finite_beam_observed":False,
        "obstacle_layer_consumed_scan_proven":False,
        "cross_node_ttl_proven":False,
        "motion_admitted":False,"goal_sent":False,"certified_estop":False,
    }
    values=(restore_received_monotonic,intrusion_ros_stamp,
            minimum_clear_range_m)
    if (any(type(x) not in (int,float) or not math.isfinite(x) or x<=0
            for x in values)
        or not isinstance(raw_scan_samples,(tuple,list))
        or not isinstance(safety_scan_samples,(tuple,list))):
        return hold
    def parse(rows,topic):
        if len(rows)<2 or len(rows)>160:
            return None
        result=[]
        for row in rows:
            if not isinstance(row,dict) or row.get("topic")!=topic:
                return None
            at,stamp,distance=(row.get(k) for k in
                ("received_monotonic","ros_stamp","corridor_range_m"))
            if (type(at) not in (int,float) or not math.isfinite(at) or at<=0
                or type(stamp) not in (int,float) or not math.isfinite(stamp)
                or stamp<=0
                or distance is not None and
                   (type(distance) not in (int,float)
                    or not math.isfinite(distance) or distance<0)):
                return None
            if at>restore_received_monotonic and stamp>intrusion_ros_stamp:
                result.append((float(at),float(stamp),
                               None if distance is None else float(distance)))
        if (len(result)<2 or
            any(b[0]<=a[0] or b[1]<=a[1]
                for a,b in zip(result,result[1:]))):
            return None
        return result
    raw=parse(raw_scan_samples,"/scan")
    safety=parse(safety_scan_samples,"/safety/scan")
    if raw is None or safety is None:
        return hold
    raw_clear=raw[-1][2] is not None and raw[-1][2]>minimum_clear_range_m
    safety_clear=(safety[-1][2] is not None and
                  safety[-1][2]>minimum_clear_range_m)
    outcome=("BOTH_REAL_SCAN_SOURCES_OBSERVED_CLEAR_NO_GOAL"
             if raw_clear and safety_clear else
             "NAV2_RAW_SCAN_CLEAR_BEAM_NOT_VERIFIED_NO_GOAL"
             if not raw_clear else
             "SAFETY_SCAN_CLEAR_BEAM_NOT_VERIFIED_NO_GOAL")
    return {
        **hold,
        "status":outcome,
        "reason":"OBSERVED_SUBSCRIBER_DELIVERY_NOT_OBSTACLE_LAYER_CONSUMPTION",
        "first_invalid_boundary":(
            None if raw_clear and safety_clear else
            "NAV2_RAW_SCAN_CLEAR_OBSERVATION" if not raw_clear else
            "SAFETY_SCAN_CLEAR_OBSERVATION"),
        "raw_scan_progress_count":len(raw),
        "safety_scan_progress_count":len(safety),
        "raw_clear_finite_beam_observed":raw_clear,
        "safety_clear_finite_beam_observed":safety_clear,
        "raw_last_scan_stamp":raw[-1][1],
        "safety_last_scan_stamp":safety[-1][1],
        "raw_last_corridor_range_m":raw[-1][2],
        "safety_last_corridor_range_m":safety[-1][2],
        "raw_to_safety_last_stamp_delta_sec":round(raw[-1][1]-safety[-1][1],6),
        "raw_max_callback_gap_sec":round(
            max(b[0]-a[0] for a,b in zip(raw,raw[1:])),6),
        "safety_max_callback_gap_sec":round(
            max(b[0]-a[0] for a,b in zip(safety,safety[1:])),6),
        "obstacle_layer_consumed_scan_proven":False,
        "cross_node_ttl_proven":False,
        "motion_admitted":False,"goal_sent":False,
    }
