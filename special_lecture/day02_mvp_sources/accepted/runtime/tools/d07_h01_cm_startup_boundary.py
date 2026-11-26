"""First actual collision_monitor Nav2 lifecycle STARTUP failure (H01 NO-GOAL).

Grounded real Gazebo public CI #43668837849: CM responded to the H01
GetState preflight but official lifecycle_manager_navigation later reported
collision_monitor/get_state async_send_request failed, before any H01
Geometry or moving Goal. This classifier never conflates a manager-level
GetState request exception with proven CM process death or safety TTL.
"""
from __future__ import annotations

def classify_first_cm_startup_failure(manager,pre,post,launch_log):
    hold={
        "schema":"axia_d07_h01_first_cm_startup_boundary_v1",
        "status":"CM_MANAGER_STARTUP_BOUNDARY_HOLD_NO_GOAL",
        "reason":"MANAGER_FIRST_NATIVE_CM_SERVICE_ERROR_UNVERIFIED",
        "first_manager_error":None,
        "prestart_state_id":None,
        "post_manager_state_id":None,
        "cm_process_death_proven":False,
        "source_root_cause_proven":False,
        "navigation_startup_proven":False,
        "cm_guard_ttl_proven":False,
        "goal_sent":False,
        "motion_admitted":False,
        "certified_estop":False,
    }
    if (not isinstance(manager,dict) or not isinstance(pre,dict)
        or not isinstance(post,dict) or not isinstance(launch_log,str)
        or manager.get("manager")!="navigation"
        or manager.get("command")!="startup"
        or manager.get("request_sent") is not True
        or manager.get("status")!="REJECTED"
        or manager.get("success") is not False
        or manager.get("goal_sent") is not False
        or pre.get("status")!="CM_GET_STATE_ACK_NO_GOAL"
        or pre.get("native_get_state_responded") is not True
        or pre.get("state_id") not in (1,2)
        or pre.get("goal_sent") is not False):
        return hold
    failures=[line.strip() for line in launch_log.splitlines()
              if "[lifecycle_manager-" in line
              and "[ERROR]" in line
              and "[lifecycle_manager_navigation]" in line]
    if not failures:
        return {**hold,"reason":"FIRST_NAVIGATION_MANAGER_ERROR_NOT_IN_LOG"}
    first=failures[0]
    if not ("Failed to change state for node: collision_monitor" in first
            and "collision_monitor/get_state service client: async_send_request failed." in first):
        return {**hold,"reason":"DIFFERENT_FIRST_NAVIGATION_MANAGER_ERROR",
                "first_manager_error":first[:500]}
    state=post.get("state_id") if (
        post.get("status")=="CM_AFTER_FAILED_MANAGER_STATE_OBSERVED_NO_GOAL"
        and post.get("native_get_state_responded") is True
        and type(post.get("state_id")) is int
        and post.get("state_id") in (1,2,3)) else None
    return {**hold,
            "status":"CM_MANAGER_GET_STATE_ASYNC_FAILED_NO_GOAL",
            "reason":"PRESTART_SERVICE_RESPONDED_BUT_MANAGER_GET_STATE_SEND_FAILED",
            "first_manager_error":first[:500],
            "prestart_state_id":pre["state_id"],
            "post_manager_state_id":state,
            "post_manager_probe_status":post.get("status","NOT_RUN"),
            "cm_process_death_proven":False,
            "source_root_cause_proven":False,
            "navigation_startup_proven":False,
            "goal_sent":False,"motion_admitted":False}
