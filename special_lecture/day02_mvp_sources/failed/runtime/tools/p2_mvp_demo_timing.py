"""Freshness-safe fast clear-phase capture for a short, consented G07 Goal.

Never creates ROS sensor values or bypasses safety/authorization. Only permits
existing real Observer samples that were received within a short monotonic age.
"""
import math


def clear_phase_reference(snapshot, *, max_age=.25):
    if not isinstance(snapshot,dict):
        return None
    now=snapshot.get('mono')
    if type(now) not in (float,int) or not math.isfinite(now):
        return None
    guard=snapshot.get('guard')
    if not isinstance(guard,dict) or guard.get('latched') is not False:
        return None
    if guard.get('reason') != 'FORWARDING_MONITORED_CM':
        return None
    times=[]
    for field in ('scan_at','supervised_at','pre_guard_at'):
        t=snapshot.get(field)
        if type(t) not in (float,int) or not math.isfinite(t) or not 0 <= now-t <= max_age:
            return None
        times.append(t)
    return min(times) - 0.000001
