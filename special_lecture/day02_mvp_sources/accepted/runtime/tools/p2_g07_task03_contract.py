"""Task03 exact public-native evidence gates, no ROS side effects.

SQLite is read-only. No raw bag or collision geometry is exported; only
bounded topic counts, integrity and SHA-256. Fail closed on any unknown.
"""
from __future__ import annotations
import hashlib
import math
from pathlib import Path
import sqlite3

REQ_TOPICS=(
    "/clock","/tf","/tf_static","/map","/scan","/safety/scan",
    "/odom","/cmd_vel_smoothed","/cmd_vel_supervised","/cmd_vel_pre_guard",
    "/cmd_vel","/axia/safety/state","/axia/p2/base_guard",
    "/navigate_to_pose/_action/status",
)


def _finite(v):
    return type(v) in (float,int) and math.isfinite(v)


def audit_bag_14(folder):
    hold={"status":"ORIGINAL_14_TOPIC_BAG_CUSTODY_UNVERIFIED_HOLD",
          "topic_message_counts":{},"total_messages":0,"sqlite_sha256":None}
    folder=Path(folder)
    try:
        if not (folder/"metadata.yaml").is_file():
            return hold
        dbs=list(folder.glob("*.db3"))
        if len(dbs)!=1:
            return hold
        db=dbs[0]
        if db.stat().st_size<=0 or db.stat().st_size>2*1024**3:
            return hold
        con=sqlite3.connect("file:"+str(db)+"?mode=ro",uri=True,timeout=3)
        try:
            if con.execute("pragma quick_check").fetchone()[0]!="ok":
                return hold
            rows=con.execute(
                "select topics.name,count(messages.id) from topics "
                "left join messages on topics.id=messages.topic_id "
                "group by topics.name").fetchall()
            counts=dict(rows)
            if not (len(rows)==len(REQ_TOPICS)
                    and len(counts)==len(rows)
                    and all(counts.get(t,0)>0 for t in REQ_TOPICS)):
                return {**hold,"topic_message_counts":{
                    t:counts.get(t,0) for t in REQ_TOPICS}}
            total=sum(counts.values())
            if total<=0:
                return hold
        finally:
            con.close()
        digest=hashlib.sha256()
        with db.open("rb") as f:
            for part in iter(lambda:f.read(1024*1024),b""):
                digest.update(part)
        return {"status":"ACTUAL_SQLITE_14_TOPIC_CUSTODY_PASS",
                "topic_message_counts":{t:counts[t] for t in REQ_TOPICS},
                "total_messages":total,"sqlite_sha256":digest.hexdigest(),
                "metadata_sha256":hashlib.sha256(
                    (folder/"metadata.yaml").read_bytes()).hexdigest()}
    except (sqlite3.Error,OSError,ValueError,TypeError):
        return hold


def audit_goal_terminal(goal_uuid, response_code, canceling_uuids,
                        final_status, guard_latched):
    result={"status":"EXACT_GOAL_UUID_TERMINAL_UNVERIFIED_HOLD",
            "goal_uuid":goal_uuid if isinstance(goal_uuid,str)
                and len(goal_uuid)==32 else None,
            "terminal_verified":False,"certified_estop":False}
    if not (isinstance(goal_uuid,str) and len(goal_uuid)==32
            and all(c in "0123456789abcdefABCDEF" for c in goal_uuid)
            and type(response_code) is int and response_code==0
            and isinstance(canceling_uuids,(tuple,list))
            and len(canceling_uuids)==1
            and canceling_uuids[0].lower()==goal_uuid.lower()
            and type(final_status) is int and final_status==5
            and guard_latched is False):
        return result
    return {**result,"status":"EXACT_GOAL_UUID_TERMINAL_CANCELED_PASS",
            "terminal_verified":True}


def audit_guard_internal_cm_age(events, *, goal_start, window_end):
    """Respect the actual Guard policy's immutable first-motion TTL boundary.

    State.step() deliberately forwards ZERO and tolerates stale or absent CM
    *before* it ever forwards motion (ever_moved=False). AFTER the first
    nonzero forwarded command ever_moved stays True, and the unchanged
    CM_TTL_SEC=.15 enforces a permanent stale latch. We must not count
    pre-motion NO_FRESH_PAIR ages as an after-motion safety violation, and
    must not ignore any post-motion age >=150ms or missing evidence.
    """
    hold={"status":"GUARD_INTERNAL_CM_AGE_UNVERIFIED_HOLD",
          "max_cm_age_ms":None,"samples":0,
          "excluded_pre_motion_ticks":0,"first_forwarded_motion_proven":False}
    if not (isinstance(events,list) and 0<len(events)<=100000
            and _finite(goal_start) and _finite(window_end)
            and goal_start<window_end):
        return hold
    ages=[]
    ignored=0
    started=False
    last_t=None
    for event in events:
        if not isinstance(event,dict) or event.get("kind")!="guard":
            continue
        t=event.get("t")
        if not _finite(t) or not goal_start<=t<=window_end:
            continue
        if last_t is not None and t<last_t:
            return hold
        last_t=t
        data=event.get("data")
        if not isinstance(data,dict) or data.get("latched") is not False:
            return hold
        # This field is recorded on the exact native Guard 20Hz timer tick.
        # Unknown, absent, or a True->False regression never passes.
        moved=data.get("guard_ever_moved")
        if type(moved) is not bool:
            return hold
        if not moved:
            if started or data.get("reason") not in ("NO_FRESH_PAIR","BOOT_ZERO",
                                                      "FORWARDING_MONITORED_CM",
                                                      "NORMAL"):
                return hold
            ignored+=1
            continue
        started=True
        cm=data.get("cm_age_sec")
        sup=data.get("supervisor_age_sec")
        if (not _finite(cm) or not _finite(sup)
                or cm<0 or sup<0):
            return hold
        ages.append(cm)
    if not started or len(ages)<10:
        return {**hold,"excluded_pre_motion_ticks":ignored}
    mm=max(ages)*1000
    facts={"max_cm_age_ms":round(mm,6),"samples":len(ages),
           "excluded_pre_motion_ticks":ignored,
           "first_forwarded_motion_proven":True}
    if mm>150:
        return {**hold,**facts,"status":"GUARD_INTERNAL_CM_AGE_GT150_HOLD"}
    return {**facts,"status":"GUARD_NATIVE_CM_AGE_TTL150_PASS"}


def audit_native_ecm_contact(positive, motion, *, goal_sim_ns,stop_sim_ns):
    hold={"status":"S02_NATIVE_ECM_CONTACT_UNVERIFIED_HOLD",
          "contact_zero_proven":False,"certified_estop":False}
    if not (isinstance(positive,dict) and isinstance(motion,dict)
            and type(goal_sim_ns) is int and type(stop_sim_ns) is int
            and goal_sim_ns>=0 and stop_sim_ns>goal_sim_ns):
        return hold
    sha=positive.get("source_sha")
    if (not isinstance(sha,str) or not sha or
            motion.get("source_sha")!=sha):
        return hold
    for v in (positive,motion):
        if (v.get("sensor_found") is not True
                or v.get("report_complete") is not True
                or type(v.get("observed_iterations")) is not int
                or v["observed_iterations"]<20
                or v.get("missing_iterations")!=0
                or not all(type(v.get(k)) is int and v[k]>=0
                    for k in ("positive_contacts","first_sim_ns","last_sim_ns"))
                or v["last_sim_ns"]<=v["first_sim_ns"]):
            return hold
    if (positive["positive_contacts"]<=0
            or motion["positive_contacts"]!=0
            or not (motion["first_sim_ns"]<=goal_sim_ns<
                    stop_sim_ns<=motion["last_sim_ns"])):
        return hold
    return {"status":"S02_NATIVE_ECM_GOAL_WINDOW_CONTACT_ZERO_PASS",
            "contact_zero_proven":True,
            "sensor_found":True,
            "positive_control_contacts":positive["positive_contacts"],
            "motion_contact_count":0,
            "motion_observed_iterations":motion["observed_iterations"],
            "goal_sim_ns":goal_sim_ns,"stop_sim_ns":stop_sim_ns,
            "certified_estop":False}
