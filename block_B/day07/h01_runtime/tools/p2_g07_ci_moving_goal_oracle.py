"""Independent CI-only real Gazebo moving-Goal evidence gate.

This is an integration *candidate*, never an Owner L3 acceptance verdict,
a collision ground-truth claim, or an E-Stop certification. The caller must
supply actual ROS/Gazebo observations, not synthetic test markers.
"""
import math

def first_delivery_breach(timestamps, *, start, end, limit, stop_ack=None):
    """Describe first actual callback interval violating a fixed safety bound.

    This is DIAGNOSTIC ONLY, never a substitute for the existing fail-closed
    oracle. Exclude pre-Goal samples; retain host-monotonic timestamps so
    the first exceeded TTL is not obscured by a later terminal exception.
    """
    if (not isinstance(timestamps,(list,tuple))
            or any(not _num(t) for t in timestamps)
            or not all(_num(v) for v in (start,end,limit))
            or not start<=end or limit<=0):
        raise ValueError("INVALID_DELIVERY_TIMELINE")
    selected=[float(t) for t in timestamps if start<=t<=end]
    if any(b<a for a,b in zip(selected,selected[1:])):
        raise ValueError("NONMONOTONIC_DELIVERY_TIMELINE")
    pairs=[(a,b,b-a) for a,b in zip(selected,selected[1:])]
    invalid=next(((a,b,dt) for a,b,dt in pairs if dt>=limit),None)
    if invalid is None:
        return {"samples":len(selected),"max_gap_sec":max((d for _,_,d in pairs),default=None),
                "first_violation_sec":None,"first_violation_at":None,
                "first_violation_from":None,"first_violation_stage":None}
    a,b,gap=invalid
    stage=("UNKNOWN_STOP_TIME" if stop_ack is None or not _num(stop_ack)
           else "PRE_STOP" if b<=stop_ack
           else "CROSSES_STOP" if a<stop_ack
           else "POST_STOP")
    return {"samples":len(selected),"max_gap_sec":max(d for _,_,d in pairs),
            "first_violation_sec":gap,"first_violation_at":b,
            "first_violation_from":a,"first_violation_stage":stage}



def first_pre_latch_delivery_timing(events, *, goal_start, end):
    """Failure-path chronology BEFORE physical STOP or final-stage oracle.

    Every event timestamp is a real observer callback on the host steady
    clock, NOT a Guard-internal CM receipt. No STOP ACK is implied. Return
    diagnostic evidence only; never turn a fatal Guard latch into PASS.
    """
    if (not isinstance(events, list) or not _num(goal_start) or
            not _num(end) or not 0 <= goal_start <= end):
        raise ValueError("INVALID_PRE_LATCH_EVENT_WINDOW")
    limits={"scan":.30,"pre_guard":.15,"supervised":.15,
            "supervisor":.15,"guard":.15,"odom":.30,"clock":.30}
    ticks={kind:[] for kind in limits}
    for event in events:
        if not isinstance(event,dict):
            raise ValueError("INVALID_PRE_LATCH_EVENT")
        kind,t=event.get("kind"),event.get("t")
        if kind in ticks:
            if not _num(t):
                raise ValueError("INVALID_PRE_LATCH_TIMESTAMP")
            if goal_start<=t<=end:
                ticks[kind].append(t)
    detail={kind:first_delivery_breach(
        values,start=goal_start,end=end,limit=limits[kind],stop_ack=None)
        for kind,values in ticks.items()}
    breaches=sorted(
        ({"channel":kind,"limit_sec":limits[kind],**v}
         for kind,v in detail.items() if v["first_violation_sec"] is not None),
        key=lambda v:v["first_violation_at"])
    return {
        "first_timing_violation":breaches[0] if breaches else None,
        "channels_with_violation":[item["channel"] for item in breaches],
        "channels":detail,
        "cm_observer_equals_guard_receipt":False,
        "stop_ack_verified":False,
        "diagnostic_only":True,
    }

def guard_cm_receive_skew(observed_cm_events, first_guard_latch):
    """Diagnostic only: compare FIRST Guard latch with independent CM receipt.

    Both channels use the same Linux host monotonic clock. A later CM packet
    observed by another node before the latch is evidence of delivery skew,
    not proof that the CM publisher died or that Guard may ignore its TTL.
    Refuse malformed/unordered/out-of-window event traces.
    """
    unknown={"classification":"CM_DELIVERY_GAP_CAUSE_UNDETERMINED",
             "cm_publisher_stopped_proven":False}
    if not isinstance(observed_cm_events,list) or not isinstance(first_guard_latch,dict):
        return unknown
    rx=first_guard_latch.get("cm_rx_monotonic")
    tick=first_guard_latch.get("tick_monotonic")
    if not _num(rx) or not _num(tick) or not 0 <= rx <= tick:
        return unknown
    times=[]
    for row in observed_cm_events:
        if not isinstance(row,dict) or not _num(row.get("t")):
            return unknown
        at=row["t"]
        if at>tick or at<0 or (times and at<times[-1]):
            return unknown
        times.append(at)
    newer=[at for at in times if rx<at<=tick]
    if not newer:
        return unknown
    latest=newer[-1]
    return {
        "classification":"GUARD_RECEIPT_LAG_CANDIDATE",
        "cm_publisher_stopped_proven":False,
        "observer_minus_guard_sec":round(latest-rx,9),
        "observer_cm_age_at_latch_sec":round(tick-latest,9),
        "guard_cm_age_at_latch_sec":round(tick-rx,9),
        "observer_newer_cm_samples":len(newer),
    }



def first_guard_cm_delivery_boundary(events, first_guard_latch, *, goal_start):
    """Read-only cross-node post-Goal CM delivery boundary; never a PASS oracle.

    First_guard_latch is measured IN the Guard's subscriber/timer clock.
    Independent callback times (Observer) cannot identify the CM publisher's
    actual emit time. An absence of a completed Observer gap at failure is
    right-censored, not proof of a healthy 150ms upstream CM link.
    """
    default={
        "schema":"axia_g07_first_cm_guard_delivery_boundary_v1",
        "status":"INCONCLUSIVE_MALFORMED_GUARD_TRACE",
        "first_timing_violation":None,
        "latest_upstream_age_sec":None,
        "latest_cm_observer_age_sec":None,
        "cm_gap_right_censored_by_latch":False,
        "delivery_attribution":"UNVERIFIED",
        "cm_publisher_stopped_proven":False,
        "safety_pass":False,
    }
    if not isinstance(events,list) or not _num(goal_start) or goal_start<0:
        return default
    if first_guard_latch is None:
        return {**default,"status":"NO_FIRST_GUARD_LATCH_TRACE",
                "delivery_attribution":"NO_INTERNAL_GUARD_LATCH_EVIDENCE"}
    if not isinstance(first_guard_latch,dict):
        return default
    tick=first_guard_latch.get("tick_monotonic")
    cm_rx=first_guard_latch.get("cm_rx_monotonic")
    cm_age=first_guard_latch.get("cm_age_sec")
    supervisor_age=first_guard_latch.get("supervisor_age_sec")
    if (not all(_num(x) for x in (tick,cm_rx,cm_age,supervisor_age))
            or not goal_start<=cm_rx<=tick or not 0<=cm_age<10
            or abs(tick-cm_rx-cm_age)>0.005):
        return default
    ticks={"supervised":[],"pre_guard":[],"guard":[],"supervisor":[],
           "scan":[],"odom":[],"clock":[]}
    for e in events:
        if not isinstance(e,dict) or not _num(e.get("t")):
            return default
        kind=e.get("kind")
        if kind in ticks and goal_start<=e["t"]<=tick:
            ticks[kind].append(e["t"])
    if any(any(b<a for a,b in zip(ts,ts[1:])) for ts in ticks.values()):
        # Different subscribers interleave; only per-topic time must order.
        return default
    upstream=ticks["supervised"][-1] if ticks["supervised"] else None
    observed=ticks["pre_guard"][-1] if ticks["pre_guard"] else None
    upstream_age=round(tick-upstream,9) if upstream is not None else None
    observed_age=round(tick-observed,9) if observed is not None else None
    right_censored=bool(observed_age is not None and observed_age>=0.15)
    if upstream_age is None:
        attribution="UPSTREAM_RECEIPT_UNVERIFIED"
    elif (supervisor_age>0.5 or first_guard_latch.get("supervisor_fsm")
          not in ("NORMAL","LIMITED")
          or first_guard_latch.get("supervisor_authorized_goal") is not True):
        attribution="MULTIPLE_STALE_OR_SUPERVISOR_FAULT_UNVERIFIED"
    elif upstream_age>=0.15:
        attribution="UPSTREAM_AND_CM_DELIVERY_GAP_CANNOT_BE_SEPARATED"
    elif observed is None:
        attribution="CM_OBSERVER_UNVERIFIED"
    elif observed-cm_rx>0.03:
        # A genuinely newer sample reached another independent subscriber.
        # Still only a Guard-receipt-lag CANDIDATE, not publisher proof.
        attribution="GUARD_RECEIPT_LAG_CANDIDATE"
    else:
        attribution="CM_OUTPUT_OR_SHARED_TRANSPORT_GAP_UNDETERMINED"
    exceeded=(first_guard_latch.get("reason")=="UPSTREAM_STALE_AFTER_MOTION"
              and cm_age>0.15)
    first=({"channel":"guard_internal_cm",
            "limit_sec":0.15,
            "measured_age_sec":round(cm_age,9),
            "exceeded_sec":round(cm_age-0.15,9),
            "threshold_crossed_at":round(cm_rx+0.15,9),
            "latch_tick_monotonic":tick}
           if exceeded else None)
    return {**default,
        "status":("GUARD_INTERNAL_CM_TTL_BREACH" if exceeded
                  else "GUARD_LATCH_WITHOUT_CONFIRMED_CM_TTL_BREACH"),
        "first_timing_violation":first,
        "latest_upstream_age_sec":upstream_age,
        "latest_cm_observer_age_sec":observed_age,
        "cm_gap_right_censored_by_latch":right_censored,
        "delivery_attribution":attribution,
        "sample_counts":{k:len(v) for k,v in ticks.items()},
    }

def normalize_cm_rmw_info(info):
    """Decode exact Jazzy rclpy 2-argument callback MessageInfo dictionary.

    Capture only timestamps and publication sequence, never the GID or
    private message content. A missing/unavailable RMW field is UNKNOWN.
    """
    if not isinstance(info,dict):
        return None
    source=info.get("source_timestamp")
    received=info.get("received_timestamp")
    seq=info.get("publication_sequence_number")
    if (type(source) is not int or type(received) is not int
            or source<=0 or received<source):
        return None
    if seq is not None and (type(seq) is not int or seq<0):
        return None
    return {"rmw_source_ns":source,"rmw_received_ns":received,
            "rmw_publication_seq":seq}


def cm_rmw_provenance(events, *, goal_start, end, limit_sec=0.15):
    """Evidence-only CM RMW publish/receive/observer interarrival analysis.

    Runs AFTER the Goal from the existing Observer ledger. Does NOT
    establish Guard receipt times, whole-system safety or CM process death.
    """
    default={"schema":"axia_p4_g07_cm_rmw_provenance_v1",
             "status":"RMW_MESSAGE_INFO_UNAVAILABLE",
             "attribution":"UNVERIFIED",
             "first_gap":None,
             "valid_rmw_samples":0,
             "publisher_stopped_proven":False,
             "safety_pass":False}
    if (not isinstance(events,list)
            or not all(_num(x) for x in (goal_start,end,limit_sec))
            or not 0<=goal_start<=end or limit_sec<=0):
        return default
    rows=[]
    for entry in events:
        if not isinstance(entry,dict):
            return default
        if entry.get("kind")!="pre_guard":
            continue
        at=entry.get("t")
        if not _num(at):
            return default
        if not goal_start<=at<=end:
            continue
        a,b,s=(entry.get("rmw_source_ns"),entry.get("rmw_received_ns"),
               entry.get("rmw_publication_seq"))
        if (type(a) is not int or type(b) is not int or a<=0 or b<a
                or (s is not None and (type(s) is not int or s<0))):
            return {**default,"valid_rmw_samples":len(rows)}
        if rows and at<rows[-1]["t"]:
            return default
        rows.append({"t":at,"src":a,"recv":b,"seq":s})
    if len(rows)<2:
        return {**default,"valid_rmw_samples":len(rows)}
    pairs=[(a,b,b["t"]-a["t"]) for a,b in zip(rows,rows[1:])]
    first=next(((a,b,gap) for a,b,gap in pairs if gap>=limit_sec),None)
    if first is None:
        return {**default,"status":"NO_CM_OBSERVED_GAP_IN_BOUND",
                "valid_rmw_samples":len(rows)}
    a,b,callback_gap=first
    source_gap=(b["src"]-a["src"])/1e9
    receive_gap=(b["recv"]-a["recv"])/1e9
    seq_gap=(b["seq"]-a["seq"] if a["seq"] is not None
             and b["seq"] is not None else None)
    if source_gap<0 or receive_gap<0 or (seq_gap is not None and seq_gap<=0):
        return {**default,"valid_rmw_samples":len(rows)}
    if seq_gap is not None and seq_gap>1:
        cause="MISSING_INTERMEDIATE_RMW_SEQUENCES_UNVERIFIED"
    elif source_gap>=limit_sec:
        cause=("CM_PUBLISH_INTERVAL_GAP_WITH_CONSECUTIVE_SEQ" if seq_gap==1
               else "CM_PUBLISH_GAP_CANDIDATE_SEQ_UNAVAILABLE")
    elif receive_gap>=limit_sec:
        cause="RMW_RECEIVE_DELAY_CANDIDATE"
    else:
        cause="OBSERVER_CALLBACK_DELAY_CANDIDATE"
    return {**default,
       "status":"CM_OBSERVED_CALLBACK_GAP_AT_LEAST_150MS",
       "attribution":cause,
       "valid_rmw_samples":len(rows),
       "first_gap":{
           "observer_callback_gap_sec":round(callback_gap,9),
           "rmw_source_gap_sec":round(source_gap,9),
           "rmw_received_gap_sec":round(receive_gap,9),
           "publication_sequence_gap":seq_gap,
       },
    }


def cm_upstream_rmw_gap_window(events, *, goal_start, end, limit_sec=0.15):
    """Compare the FIRST CM publication gap with upstream *publication* evidence.

    Jazzy RMW source timestamps from both topics share the publisher's host
    system-clock domain in this one-host G07 simulator; Observer callback
    times use a different monotonic clock and select only the Goal window.
    This is a pure diagnostic: it cannot distinguish CM's internal processing
    from operating-system scheduling, and NEVER grants a safety PASS.
    """
    unknown={
        "schema":"axia_p4_g07_cm_supervisor_publication_window_v1",
        "status":"RMW_PROVENANCE_MISSING_OR_INVALID",
        "classification":"UNVERIFIED",
        "cm_source_gap_sec":None,
        "cm_publication_sequence_gap":None,
        "upstream_publications_inside_gap":0,
        "upstream_max_coverage_gap_sec":None,
        "cm_callback_processing_delay_proven":False,
        "guard_safety_pass":False,
        "formal_accepted":False,
    }
    if (not isinstance(events,list) or not all(
            _num(v) for v in (goal_start,end,limit_sec))
            or not 0 <= goal_start < end or limit_sec<=0):
        return unknown
    streams={"pre_guard":[],"supervised":[]}
    for event in events:
        if not isinstance(event,dict):
            return unknown
        kind=event.get("kind")
        if kind not in streams:
            continue
        callback=event.get("t")
        if not _num(callback):
            return unknown
        if not goal_start<=callback<=end:
            continue
        src=event.get("rmw_source_ns")
        recv=event.get("rmw_received_ns")
        seq=event.get("rmw_publication_seq")
        if (type(src) is not int or type(recv) is not int
                or src<=0 or recv<src or type(seq) is not int or seq<0):
            return unknown
        streams[kind].append({"src":src,"recv":recv,"seq":seq})
    cm=streams["pre_guard"]
    upstream=streams["supervised"]
    if len(cm)<2:
        return {**unknown,"status":"NO_CM_SOURCE_GAP_OBSERVED"}
    for rows in (cm,upstream):
        if any(b["src"]<=a["src"] or b["seq"]<=a["seq"]
               for a,b in zip(rows,rows[1:])):
            return unknown
    first=next(((a,b,(b["src"]-a["src"])/1e9)
                for a,b in zip(cm,cm[1:])
                if (b["src"]-a["src"])/1e9>=limit_sec),None)
    if first is None:
        return {**unknown,"status":"NO_CM_SOURCE_GAP_OBSERVED"}
    left,right,dt=first
    seq_gap=right["seq"]-left["seq"]
    inside=[row for row in upstream
            if left["src"]<row["src"]<right["src"]]
    timestamps=[left["src"]]+[row["src"] for row in inside]+[right["src"]]
    coverage=max((b-a)/1e9 for a,b in zip(timestamps,timestamps[1:]))
    if seq_gap!=1:
        reason="CM_INTERMEDIATE_PUBLICATIONS_UNOBSERVED"
    elif len(inside)<2:
        reason="SUPERVISOR_RMW_COVERAGE_UNVERIFIED"
    elif any(b["seq"]-a["seq"] != 1 for a,b in zip(inside,inside[1:])):
        reason="SUPERVISOR_RMW_SEQUENCES_UNOBSERVED"
    elif coverage>=limit_sec:
        reason="SUPERVISOR_PUBLISH_GAP_OVERLAPS_CM_GAP"
    else:
        # Input was published while CM did not publish; without internal CM
        # tracing, cannot separate queued callback, source processing or CPU.
        reason="CM_POST_INPUT_EXECUTION_OR_SCHEDULING_GAP_CANDIDATE"
    return {
        **unknown,
        "status":"CM_SOURCE_GAP_EXCEEDS_150MS",
        "classification":reason,
        "cm_source_gap_sec":round(dt,9),
        "cm_publication_sequence_gap":seq_gap,
        "upstream_publications_inside_gap":len(inside),
        "upstream_max_coverage_gap_sec":round(coverage,9),
    }

def _num(v):
    return type(v) in (int,float) and math.isfinite(v)

def post_stop_odom_zero_dwell(odom, stop_ack_at):
    """Strictly real, gap-bounded /odom ZERO dwell AFTER native STOP ACK.

    Pre-Goal idle samples cannot count. A missing odom callback >300ms after
    ACK invalidates evidence. A moving odom frame resets the dwell start.
    This does not claim contact ground truth or certified E-Stop.
    """
    if (not isinstance(odom,list) or len(odom)<2
            or not _num(stop_ack_at) or stop_ack_at<0):
        return 0.0
    previous=None
    start=None
    last=None
    samples=0
    for row in odom:
        if (not isinstance(row,dict)
                or any(not _num(row.get(k)) for k in ("t","vx","wz"))):
            return 0.0
        timestamp=row["t"]
        if timestamp<stop_ack_at:
            if previous is not None and timestamp<=previous:
                return 0.0
            previous=timestamp
            continue
        if last is not None and not 0 < timestamp-last <= .3:
            return 0.0
        samples+=1
        last=timestamp
        if abs(row["vx"])>=.03 or abs(row["wz"])>=.05:
            start=None
        elif start is None:
            start=timestamp
    if samples<2 or start is None or last is None:
        return 0.0
    return max(0.,last-start)


def _blocked(reason):
    return {"status":"BLOCKED","reason":reason,
            "gate_accepted":False,"owner_l3_accepted":False,
            "certified_estop":False,"collision_ground_truth":False}

def clear_action_evidence_valid(status_at_clear, same_goal_executing_after_clear):
    """A delayed ActionStatus callback cannot erase measured post-Goal cruise.

    The caller must later observe EXECUTING for the same single Goal UUID.
    Terminal or unknown action statuses never count as CLEAR evidence.
    """
    return (same_goal_executing_after_clear is True
            and (status_at_clear is None
                 or (type(status_at_clear) is int and status_at_clear in (1, 2))))


def assess(v, *, owner_authorized=False):
    if not isinstance(v,dict):
        return _blocked("INVALID_EVIDENCE")
    # The same exact physical phases, source TTL, Guard and odom criteria
    # apply to BOTH environments. Authority is independent: CI is admitted
    # only in real GitHub Actions, Owner only after shell TTY + exact SHA +
    # three-owned-PID admission. This PURE oracle never issues a Goal.
    ci_scope=(v.get("ci_specific") is True and owner_authorized is False)
    owner_scope=(v.get("ci_specific") is False and owner_authorized is True
                 and v.get("shared_execution_mode")=="owner"
                 and v.get("owner_authority_verified") is True)
    if (v.get("sim_only") is not True or not (ci_scope or owner_scope)
        or v.get("real_gazebo_world") is not True
        or v.get("actual_physical_scan") is not True
        or v.get("native_obstacle_set_pose_ack") is not True):
        return _blocked("REAL_GAZEBO_SENSOR_AND_SCOPED_CI_REQUIRED")
    if (v.get("fault_injected") is not False
        or v.get("certified_estop") is not False
        or v.get("collision_ground_truth_available") is not False):
        return _blocked("UNSUPPORTED_FAULT_OR_CERTIFICATION_CLAIM")
    if (not isinstance(v.get("source_sha"),str)
        or len(v["source_sha"])!=40
        or not isinstance(v.get("goal_uuid"),str)
        or len(v["goal_uuid"])!=32
        or v.get("goal_status_executing") is not True
        or not (v.get("goal_status_at_clear")==2 or (
            v.get("clear_before_action_ack") is True
            and clear_action_evidence_valid(
                v.get("goal_status_at_clear"),
                v.get("same_goal_executing_after_clear"))))
        or any(v.get(k)!=2 for k in ("goal_status_at_slow",
                                      "goal_status_at_stop"))):
        return _blocked("MOVING_NAV2_GOAL_EXECUTING_NOT_PROVEN")
    if v.get("guard_latched") is not False:
        return _blocked("GUARD_LATCHED_DURING_GOAL")
    # The pre-goal side obstacle alone did not enter STOP in real CI.
    # Require ONE native moving-simulation set_pose and two distinct actual
    # LaserScans AFTER its ACK; no simulated scan values count as proof.
    if (v.get("stop_native_set_pose_ack") is not True
        or type(v.get("stop_post_ack_distinct_ros_scan_count")) is not int
        or v["stop_post_ack_distinct_ros_scan_count"] < 2
        or not _num(v.get("stop_pre_move_front_m"))):
        return _blocked("NATIVE_STOP_INTRUSION_NEW_SCAN_NOT_PROVEN")
    if not _num(v.get("observed_odom_moved_m")) or v["observed_odom_moved_m"]<.05:
        return _blocked("ACTUAL_ODOM_DISPLACEMENT_NOT_PROVEN")
    for key in ("max_source_interval_sec","max_cm_interval_sec",
                "max_guard_interval_sec","max_supervisor_fsm_interval_sec"):
        if not _num(v.get(key)) or not 0<v[key]<.15:
            return _blocked("SAFETY_DELIVERY_TTL_BOUNDARY_"+key)
    for key in ("max_scan_interval_sec","max_odom_interval_sec",
                "max_clock_interval_sec"):
        if not _num(v.get(key)) or not 0<v[key]<.30:
            return _blocked("SENSOR_DELIVERY_TTL_BOUNDARY_"+key)
    a,b,c=[v.get(k) for k in ("clear","slow","stop")]
    if any(not isinstance(stage,dict) for stage in (a,b,c)):
        return _blocked("ACTUAL_LIDAR_PHASE_MISSING")
    for phase in (a,b,c):
        if any(not _num(phase.get(k)) for k in
               ("front_m","supervised_vx","cm_vx","final_vx","age_sec")):
            return _blocked("PHASE_NUMERIC_EVIDENCE_INVALID")
        if not 0<=phase["age_sec"]<=.30:
            return _blocked("PHASE_SENSOR_OR_CMD_STALE")
    if not (a["front_m"]>.75 and a["supervised_vx"]>.03
            and a["cm_vx"]>.03 and a["final_vx"]>.03):
        return _blocked("REAL_CLEAR_MOTION_NOT_PROVEN")
    if not (.4<b["front_m"]<.75 and b["supervised_vx"]>.005
            and 0<b["cm_vx"]<=.30*b["supervised_vx"]+.01
            and 0<b["final_vx"]<=.30*b["supervised_vx"]+.01):
        return _blocked("REAL_SLOWDOWN_30PCT_NOT_PROVEN")
    if not (v["stop_pre_move_front_m"]-c["front_m"]>=.10):
        return _blocked("PHYSICAL_STOP_POST_ACK_RANGE_CHANGE_NOT_PROVEN")
    # A real Nav2 controller can reverse while approaching a physical
    # obstacle. STOP protects BOTH travel directions: a fresh real STOP
    # scan plus actual CM/final ZERO and a moving Goal remain mandatory.
    # The sign of the *requested* velocity is not proof of a failed stop.
    if not (.14<=c["front_m"]<.4 and .005<abs(c["supervised_vx"])<=.22
            and abs(c["cm_vx"])<.01 and abs(c["final_vx"])<.01):
        return _blocked("REAL_STOP_ZONE_FINAL_ZERO_NOT_PROVEN")
    if not _num(v.get("odom_stopped_dwell_sec")) or v["odom_stopped_dwell_sec"]<1.0:
        return _blocked("ACTUAL_ODOM_STOP_DWELL_NOT_PROVEN")
    return {
        "status":"CI_GAZEBO_MOVING_GOAL_CANDIDATE",
        "reason":"ACTUAL_NAV2_MOVING_GOAL_CLEAR_SLOW_STOP_OBSERVED_CI_ONLY",
        "gate_accepted":False,"owner_l3_accepted":False,
        "certified_estop":False,"collision_ground_truth":False,
    }
