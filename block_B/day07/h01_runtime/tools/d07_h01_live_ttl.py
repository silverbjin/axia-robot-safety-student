"""D07-H01 actual Observer callback-entry timing analysis (read-only).

This measures each real ROS topic's host monotonic delivery gaps, preserving
the FIRST failing edge and unexpected safety state. It does NOT prove causal
Supervisor->CM->Guard data transfer, or grant moving-Goal authorization.
"""
from __future__ import annotations
import math
# Imported both as tools.d07_h01_live_ttl in tests and as
# d07_h01_live_ttl from the real tools/ entrypoint in Gazebo CI.
if __package__:
    from .d07_h01_oracle import MAX_TTLS_SEC
else:
    from d07_h01_oracle import MAX_TTLS_SEC

KINDS={"supervisor":"supervised","cm":"pre_guard","guard":"final",
       "scan":"scan","odom":"odom","clock":"clock"}


def assess_callback_gaps(events, *, observation_window=None):
    blocked={"status":"LIVE_TTL_OR_PROVENANCE_HOLD_NO_GOAL",
             "reason":"MISSING_ACTUAL_NODE_CALLBACK_EVIDENCE",
             "first_ttl_violation":None,
             "first_safety_transition":None,
             "actual_causal_delivery_verified":False,
             "actual_timestamps_verified":False,
             "motion_admitted":False,"goal_sent":False,
             "certified_estop":False}
    if not isinstance(events,(list,tuple)) or not events:
        return {**blocked,"missing_edges":list(KINDS)}
    ordered=[]
    for event in events:
        if (not isinstance(event,dict)
            or not isinstance(event.get("kind"),str)
            or type(event.get("t")) not in (int,float)
            or not math.isfinite(event["t"]) or event["t"]<=0):
            return {**blocked,"reason":"MALFORMED_OR_NONMONOTONIC_RECEIPT"}
        ordered.append(event)
    ordered.sort(key=lambda e:e["t"])
    window=None
    if observation_window is not None:
        if not isinstance(observation_window,dict):
            return {**blocked,"reason":"MALFORMED_CAPTURE_WINDOW"}
        start,end=(observation_window.get(k) for k in ("start","end"))
        if (any(type(v) not in (int,float) or not math.isfinite(v)
                or v<=0 for v in (start,end))
                or end<=start
                or ordered[0]["t"]<start
                or ordered[-1]["t"]>end):
            return {**blocked,"reason":"MALFORMED_CAPTURE_WINDOW"}
        window=(float(start),float(end))
    violations=[]
    metrics={}
    missing=[]
    for edge,kind in KINDS.items():
        rows=[e for e in ordered if e["kind"]==kind]
        if len(rows)<2:
            missing.append(edge)
            continue
        # For the FIRST timing violation, the TTL first expires at
        # previous_callback_receipt+limit, NOT when the next callback
        # eventually arrives. Otherwise unrelated edges can be misordered
        # (real H01 L2 #43665136936: odom cutoff before later clock recovery).
        gaps=[(b["t"]-a["t"],a["t"],b["t"])
              for a,b in zip(rows,rows[1:])]
        metrics[edge]={"count":len(rows),
                       "max_callback_gap_sec":round(max(x[0] for x in gaps),6)}
        if window is not None:
            # Observed within a defined ROS callback window. No receipt at
            # the start or after the last sample is NOT evidence of liveness.
            # Report the earliest breached threshold boundary, not the
            # later exception or final sample's wall time.
            initial=rows[0]["t"]-window[0]
            trailing=window[1]-rows[-1]["t"]
            if initial>=MAX_TTLS_SEC[edge]:
                violations.append({
                    "edge":edge,"at":round(window[0]+MAX_TTLS_SEC[edge],6),
                    "age_sec":round(initial,6),
                    "reason":"LIVE_CALLBACK_SILENCE_AT_WINDOW_START"})
            if trailing>=MAX_TTLS_SEC[edge]:
                violations.append({
                    "edge":edge,"at":round(rows[-1]["t"]+MAX_TTLS_SEC[edge],6),
                    "age_sec":round(trailing,6),
                    "reason":"LIVE_CALLBACK_SILENCE_AT_WINDOW_END"})
        for gap,previous_at,received_at in gaps:
            if gap<=0:
                violations.append({"edge":edge,"at":received_at,
                                   "age_sec":gap,
                                   "reason":"CALLBACK_RECEIPT_NONMONOTONIC"})
            elif gap>=MAX_TTLS_SEC[edge]:
                violations.append({
                    "edge":edge,
                    "at":round(previous_at+MAX_TTLS_SEC[edge],6),
                    "receipt_end_at":round(received_at,6),
                    "age_sec":round(gap,6),
                    "reason":"LIVE_CALLBACK_GAP_LIMIT"})
        if edge=="clock":
            last_ns=None
            for e in rows:
                ns=e.get("ns")
                if type(ns) is not int or ns<0 or (
                    last_ns is not None and ns<=last_ns):
                    violations.append({"edge":"clock","at":e["t"],"age_sec":0,
                                       "reason":"ROS_CLOCK_NONMONOTONIC"})
                    break
                last_ns=ns
    safety=[]
    for e in ordered:
        data=e.get("data")
        if e["kind"]=="guard" and isinstance(data,dict) and data.get("latched") is True:
            safety.append({"state":"GUARD_LATCHED","at":e["t"]})
        elif e["kind"]=="supervisor" and isinstance(data,dict) and (
                data.get("state") in (
                    "PROTECTIVE_STOP","RECOVERY_REQUIRED","SW_STOP_LATCHED")):
            safety.append({"state":data["state"],"at":e["t"]})
    first_violation=min(violations,key=lambda x:x["at"]) if violations else None
    first_safety=min(safety,key=lambda x:x["at"]) if safety else None
    result={**blocked,
            "first_ttl_violation":first_violation,
            "first_safety_transition":first_safety,
            "missing_edges":missing,
            # Monotonic callback receipt is not a sensor Header stamp and
            # not a correlated source→sink command delivery timestamp.
            "callback_receipts_verified":not missing,
            "actual_timestamps_verified":False,
            "callback_metrics":metrics,
            "observation_window":observation_window}
    if missing:
        return result
    if first_violation or first_safety:
        return {**result,"reason":"FIRST_LIVE_TTL_OR_SAFETY_BOUNDARY"}
    return {**result,"status":"CALLBACK_PERIODS_CANDIDATE_NO_GOAL",
            "reason":"PER_TOPIC_RECEIPT_OK_CAUSAL_LINK_AND_MOTION_UNVERIFIED"}
