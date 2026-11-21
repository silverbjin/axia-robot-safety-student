#!/usr/bin/env python3
"""CI/Owner G07 physical SLOW cylinder forward-entry admission only.

No Goal/cmd_vel publication, no synthetic sensor values, no safety TTL changes.
A physical set_pose is permitted only while the original live Nav2 Goal
has fresh positive forward authority and odom shows non-turning motion.
Actual SLOW and STOP success remain separate strict real-sensor oracles.
"""
import math

def _num(v):
    return type(v) in (int,float) and math.isfinite(v)

def forward_entry(snap,data):
    if not isinstance(snap,dict) or not isinstance(data,dict):
        return None
    now=snap.get("mono")
    if not _num(now) or snap.get("action_status")!=2:
        return None
    guard=snap.get("guard")
    if not isinstance(guard,dict) or guard.get("latched") is not False:
        return None
    for topic in ("scan","supervised","pre_guard","final","odom","guard","clock"):
        at=snap.get(topic+"_at")
        if not _num(at) or not 0<=now-at<=.3:
            return None
    command=snap.get("supervised_speed")
    cm=snap.get("pre_guard_speed")
    final=snap.get("final_speed")
    front=data.get("scan")
    pose=data.get("pose")
    if not all(_num(x) for x in (command,cm,final,front)):
        return None
    # Same forward motion proof already used by original CLEAR stage.
    if not (command>.03 and cm>.03 and final>.03 and front>.75):
        return None
    if (not isinstance(pose,(tuple,list)) or len(pose)!=3
            or not all(_num(x) for x in pose)):
        return None
    odom=data.get("odom")
    if not isinstance(odom,(list,tuple)):
        return None
    recent=[x for x in odom if isinstance(x,dict)
            and _num(x.get("t")) and 0<=now-x["t"]<=.55]
    if (len(recent)<3 or recent[-1]["t"]-recent[0]["t"]<.35):
        return None
    if not all(_num(x.get("vx")) and _num(x.get("wz"))
               and x["vx"]>.015 and abs(x["wz"])<.05 for x in recent):
        return None
    return {
        "forward_entry_proven":True,
        "pose":[float(x) for x in pose],
        "front_m":round(float(front),4),
        "supervised_vx":round(float(command),6),
        "max_abs_odom_wz":round(max(abs(x["wz"]) for x in recent),6),
        "odom_samples":len(recent)
    }

def diagnose_forward_entry(snap,data):
    """Bounded numeric-only reason on NO physical set_pose, not a safety PASS.

    Reports the first unmet entry condition (fixed order), no pose/UUID
    or raw samples, for exact native SLOW_ENTRY_FORWARD timeout triage.
    """
    result=dict(schema="axia.g07.g20.forward_entry_blocker.v1",
                first_blocker="INVALID_OBSERVER_SAMPLE",
                supervised_vx=None,entry_proven=False,
                release="HOLD",root_cause_proven=False,certified_estop=False)
    if not isinstance(snap,dict) or not isinstance(data,dict):
        return result
    v=snap.get("supervised_speed")
    if _num(v):
        result["supervised_vx"]=round(float(v),6)
    now=snap.get("mono")
    if not _num(now) or snap.get("action_status")!=2:
        result["first_blocker"]="GOAL_NOT_EXECUTING_OR_NO_TIME"
        return result
    guard=snap.get("guard")
    if not isinstance(guard,dict) or guard.get("latched") is not False:
        result["first_blocker"]="GUARD_LATCH_OR_UNVERIFIED"
        return result
    for topic in ("scan","supervised","pre_guard","final","odom","guard","clock"):
        at=snap.get(topic+"_at")
        if not _num(at) or not 0<=now-at<=.3:
            result["first_blocker"]="STALE_OR_MISSING_"+topic.upper()
            return result
    front=data.get("scan")
    cm=snap.get("pre_guard_speed")
    final=snap.get("final_speed")
    if not all(_num(x) for x in (front,cm,final,v)):
        result["first_blocker"]="MISSING_REAL_VELOCITY_OR_SCAN"
        return result
    if front<=.75:
        result["first_blocker"]="FRONT_NOT_CLEAR"
        return result
    if v<=.03:
        result["first_blocker"]="SUPERVISED_FORWARD_BELOW_ENTRY_GATE"
        return result
    if cm<=.03 or final<=.03:
        result["first_blocker"]="CM_OR_FINAL_FORWARD_BELOW_ENTRY_GATE"
        return result
    odom=data.get("odom")
    if not isinstance(odom,(list,tuple)):
        result["first_blocker"]="ODOM_SAMPLE_MISSING"
        return result
    recent=[x for x in odom if isinstance(x,dict)
            and _num(x.get("t")) and 0<=now-x["t"]<=.55]
    if len(recent)<3 or recent[-1]["t"]-recent[0]["t"]<.35:
        result["first_blocker"]="ODOM_RECENT_WINDOW_INSUFFICIENT"
        return result
    if not all(_num(x.get("vx")) and _num(x.get("wz")) for x in recent):
        result["first_blocker"]="ODOM_VELOCITY_UNAVAILABLE"
        return result
    if any(abs(x["wz"])>=.05 for x in recent):
        result["first_blocker"]="ODOM_YAW_RATE_NOT_STABLE"
        return result
    if any(x["vx"]<=.015 for x in recent):
        result["first_blocker"]="ODOM_POSITIVE_FORWARD_NOT_STABLE"
        return result
    result["first_blocker"]="ENTRY_CONDITIONS_SATISFIED_BUT_WAIT_UNVERIFIED"
    return result
