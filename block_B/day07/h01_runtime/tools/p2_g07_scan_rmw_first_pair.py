"""G07 native Scan first exact ROS RMW MessageInfo pair (diagnostic only).

All gaps are differences *within* the same clock/timebase. Never subtract
ROS simulated Header absolute times from RMW real/system ns or host monotonic.
Missing publication sequence leaves exact publication provenance unverified.
Never affects Scan/Clock/Odom 300ms or Goal admission.
"""
import math


def normalize_scan_message_info(info):
    def get_int(k):
        try:
            v=info.get(k) if isinstance(info,dict) else getattr(info,k)
            if type(v) is not int or v<=0:return -1
            return v
        except (TypeError,ValueError,AttributeError,OverflowError):
            return -1
    return (get_int("source_timestamp"),get_int("received_timestamp"),
            get_int("publication_sequence_number"))


def first_scan_rmw_pair(boundary,rows):
    base={"schema":"axia.g07.scan_first_rmw_exact_pair.v1",
          "status":"SCAN_EXACT_RMW_METADATA_UNAVAILABLE_HOLD",
          "release":"HOLD","root_cause_proven":False,
          "owner_l3_accepted":False,"goal_sent":False,
          "certified_estop":False,"safety_ttl_changed":False,
          "source_gap_ms":None,"received_gap_ms":None,
          "observer_gap_ms":None,"header_sim_gap_ms":None,
          "publication_seq_gap":None,
          "publisher_stall_proven":False,"dds_take_root_proven":False,
          "executor_root_proven":False}
    if not isinstance(boundary,dict) or not isinstance(rows,(list,tuple)):
        return base
    topic=boundary.get("topic")
    if topic not in ("scan","safety_scan"):return base
    expected=[]
    for host,sim in (("previous_rx_host_monotonic","previous_header_sim"),
                     ("current_rx_host_monotonic","current_header_sim")):
        t=boundary.get(host);v=boundary.get(sim)
        if (type(t) not in (float,int) or type(v) not in (float,int)
                or not math.isfinite(t) or not math.isfinite(v)):
            return base
        expected.append((float(t),float(v)))
    pairs=[]
    for t,sim in expected:
        found=[row for row in rows if isinstance(row,dict)
               and row.get("topic")==topic
               and type(row.get("at")) in (int,float)
               and type(row.get("header_sim")) in (int,float)
               and abs(row["at"]-t)<=.020
               and abs(row["header_sim"]-sim)<=.000002]
        if len(found)!=1:return base
        pairs.append(found[0])
    a,b=pairs
    observer=(b["at"]-a["at"])*1000
    header=(b["header_sim"]-a["header_sim"])*1000
    if observer<=0 or header<=0:return base
    base["observer_gap_ms"]=round(observer,6)
    base["header_sim_gap_ms"]=round(header,6)
    src=(a.get("rmw_source_ns"),b.get("rmw_source_ns"))
    recv=(a.get("rmw_received_ns"),b.get("rmw_received_ns"))
    seq=(a.get("rmw_publication_seq"),b.get("rmw_publication_seq"))
    if any(type(v) is not int or v<=0 for v in (*src,*recv,*seq)):
        return base
    source_gap=(src[1]-src[0])/1e6
    received_gap=(recv[1]-recv[0])/1e6
    seq_gap=seq[1]-seq[0]
    if source_gap<=0 or received_gap<=0 or seq_gap<=0:
        return base
    base.update(source_gap_ms=round(source_gap,6),
                received_gap_ms=round(received_gap,6),
                publication_seq_gap=seq_gap)
    if seq_gap!=1:
        base["status"]="SCAN_NONCONSECUTIVE_PUBLICATIONS_UNVERIFIED_HOLD"
    elif source_gap>300:
        base["status"]="SCAN_SOURCE_INTERVAL_OVERRUN_CANDIDATE_HOLD"
    elif received_gap>300:
        base["status"]="SCAN_SUBSCRIBER_RMW_RECEIVE_OR_TAKE_DELAY_CANDIDATE_HOLD"
    elif observer>300:
        base["status"]="SCAN_OBSERVER_TAKE_OR_EXECUTOR_DELAY_CANDIDATE_HOLD"
    else:
        base["status"]="SCAN_EXACT_RMW_PAIR_NO_OVERRUN_SCOPED_HOLD"
    return base
