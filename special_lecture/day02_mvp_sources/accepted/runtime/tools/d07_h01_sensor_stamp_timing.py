"""H01 CI-only read-only sensor source-header vs ROS callback receipt audit.

Latest AXIA MVP Observer records host monotonic ROS callback interarrival.
A host-monotonic callback gap and a ROS simulation-time header-stamp delta
are DIFFERENT clocks. Never subtract one from the other as header age.
Observed input silence may mean scheduler congestion, missing packets,
Gazebo sensor publish delay, DDS delivery, or clock behavior; classify
only source-header advance vs host receipt timing *candidate*.

No producer changes, no publishers, no simulated messages, no Nav2 Goal,
no safety TTL adjustments, and no authorized motion or E-Stop claim.
"""
from __future__ import annotations
import math

if __package__:
    from .d07_h01_oracle import MAX_TTLS_SEC
else:
    from d07_h01_oracle import MAX_TTLS_SEC

KINDS=("odom","scan")
NS_PER_SEC=1_000_000_000


def compare_sensor_stamps_and_receipts(events):
    """Identify the earliest 300ms host-receipt gap and its ROS Header delta."""
    hold={
        "schema":"axia_d07_h01_source_header_receipt_v1",
        "status":"SENSOR_STAMP_RECEIPT_PROVENANCE_HOLD",
        "reason":"TWO_NATIVE_STAMPED_ODOM_AND_SCAN_CALLBACKS_NOT_PROVEN",
        "first_receipt_limit_crossing":None,
        "first_source_header_limit_crossing":None,
        "actual_causal_delivery_verified":False,
        "actual_header_age_verified":False,
        "motion_admitted":False,
        "goal_sent":False,
        "certified_estop":False,
    }
    if not isinstance(events,(tuple,list)) or not events or len(events)>20000:
        return hold
    groups={k:[] for k in KINDS}
    for event in events:
        if not isinstance(event,dict):
            return hold
        kind=event.get("kind")
        if kind not in groups:
            continue
        t,ns=event.get("t"),event.get("header_stamp_ns")
        if (type(t) not in (int,float) or not math.isfinite(t) or t<=0
            or type(ns) is not int or ns<=0):
            return {**hold,"reason":"MALFORMED_ACTUAL_SENSOR_HEADER_OR_HOST_RECEIPT"}
        groups[kind].append((float(t),ns))
    if any(len(values)<2 for values in groups.values()):
        return hold
    receipt_crossings=[]
    source_crossings=[]
    metrics={}
    for kind,values in groups.items():
        values.sort(key=lambda x:x[0])
        if any(b[0]<=a[0] or b[1]<=a[1] for a,b in zip(values,values[1:])):
            return {**hold,"reason":"NONMONOTONIC_ACTUAL_SENSOR_HEADER_OR_RECEIPT"}
        limit=MAX_TTLS_SEC[kind]
        receipt_gaps=[]
        stamp_gaps=[]
        for a,b in zip(values,values[1:]):
            receipt=b[0]-a[0]
            header=(b[1]-a[1])/NS_PER_SEC
            receipt_gaps.append(receipt)
            stamp_gaps.append(header)
            classified=(
                "ROS_SOURCE_HEADER_ADVANCE_ABOVE_NOMINAL" if header>=limit
                else "RECEIPT_GAP_WITH_SMALL_HEADER_ADVANCE")
            common={
                "kind":kind,
                "receipt_gap_sec":round(receipt,6),
                "header_gap_sec":round(header,6),
                "header_first_ns":a[1],
                "header_last_ns":b[1],
                "classification":classified,
                "host_received_later_at":round(b[0],6),
            }
            if receipt>=limit:
                receipt_crossings.append({
                    **common,
                    "first_crossing_at_host_mono":round(a[0]+limit,6),
                })
            if header>=limit:
                source_crossings.append({
                    **common,
                    "observed_at_host_mono":round(b[0],6),
                })
        metrics[kind]={
            "count":len(values),
            "max_receipt_gap_sec":round(max(receipt_gaps),6),
            "max_source_header_advance_sec":round(max(stamp_gaps),6),
        }
    first_receipt=min(
        receipt_crossings,key=lambda x:x["first_crossing_at_host_mono"],
        default=None)
    first_source=min(
        source_crossings,key=lambda x:x["observed_at_host_mono"],
        default=None)
    return {
        **hold,
        "status":"SENSOR_STAMP_RECEIPT_CANDIDATES_NO_GOAL",
        "reason":"SOURCE_AND_OBSERVER_GAPS_SEPARATED_CAUSAL_ORIGIN_UNVERIFIED",
        "first_receipt_limit_crossing":first_receipt,
        "first_source_header_limit_crossing":first_source,
        "metrics":metrics,
        "source_clock":"ROS_Header_sim_time_ns",
        "receipt_clock":"host_monotonic_sec",
        "actual_causal_delivery_verified":False,
        "actual_header_age_verified":False,
        "motion_admitted":False,
        "goal_sent":False,
    }
