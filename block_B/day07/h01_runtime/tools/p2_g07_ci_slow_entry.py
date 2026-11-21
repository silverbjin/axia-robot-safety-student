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
    if not (command>.05 and cm>.03 and final>.03 and front>.75):
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
