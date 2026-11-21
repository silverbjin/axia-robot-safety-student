#!/usr/bin/env python3
"""First Scan take-complete vs callback dispatch; opt-in D08 helper reuse only.

The D08 helper records AFTER rclpy handle.take_message, NOT native rcl_take.
Only same-host monotonic deltas and exact ROS Header stamps are compared.
No safety authority, Executor settings, Goal or synthetic ROS publisher.
"""
import math

def _ok(x):
    return type(x) in (int,float) and math.isfinite(x)

def summarize_first_take_pair(first,events):
    r=dict(schema="axia.g07.g10.first_scan_take_complete.v1",status="D08_TAKE_EXACT_PAIR_UNAVAILABLE_HOLD",
           release="HOLD",root_cause="UNDETERMINED",root_cause_proven=False,
           rcl_native_take_timestamp_proven=False,transport_root_proven=False,
           certified_estop=False,owner_l3_accepted=False,safety_ttl_changed=False,
           clock_progress_inside_gap=False)
    if not isinstance(first,dict) or first.get("topic")!="scan" or not isinstance(events,(tuple,list)):
        return r
    try:
        a,b=first["previous_header_sim"],first["current_header_sim"]
        gap=first["gap_ms"]
        if not all(_ok(x) for x in (a,b,gap)) or not 0<a<b or not 0<gap<10000:
            return r
        stamps=[round(a*1e9),round(b*1e9)]
        if not 0<stamps[0]<stamps[1]:
            return r
    except (KeyError,TypeError,ValueError):
        return r
    matched={}
    for stamp in stamps:
        for stage in ("take_complete","callback_dispatch"):
            rows=[e for e in events if isinstance(e,dict) and
                  e.get("stage")==stage and e.get("source_stamp_ns")==stamp]
            if len(rows)!=1 or not _ok(rows[0].get("at")):
                return r
            matched[(stamp,stage)]=float(rows[0]["at"])
    at,bt=(matched[(stamp,"take_complete")] for stamp in stamps)
    ad,bd=(matched[(stamp,"callback_dispatch")] for stamp in stamps)
    if not (0<at<=ad<bt<=bd and 0<bt-at<10 and 0<bd-ad<10):
        return r
    take_ms=(bt-at)*1000
    dispatch_ms=(bd-ad)*1000
    after_ms=(bd-bt)*1000
    r.update(take_complete_gap_ms=round(take_ms,6),
             callback_dispatch_gap_ms=round(dispatch_ms,6),
             current_take_to_dispatch_ms=round(after_ms,6),
             clock_progress_inside_gap=(type(first.get("clock_callback_count_inside_gap")) is int
                 and first["clock_callback_count_inside_gap"]>0))
    if gap>300 and take_ms>300 and after_ms<100:
        r["status"]="ORIGINAL_TAKE_COMPLETE_LATE_CANDIDATE_HOLD"
    elif gap>300 and take_ms<=300 and after_ms>300:
        r["status"]="POST_TAKE_DISPATCH_LATE_CANDIDATE_HOLD"
    else:
        r["status"]="EXACT_TAKE_PAIR_OBSERVED_CAUSAL_ROOT_UNDETERMINED_HOLD"
    return r
