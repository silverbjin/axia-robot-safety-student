#!/usr/bin/env python3
"""H01-only real /collision_monitor/get_state pre-navigation read-only probe.

Actual Gazebo L2 #43661330404 first failed on official Nav2 Lifecycle
Manager collision_monitor/get_state async_send_request. Before asking the
original manager for STARTUP, establish that the underlying CM lifecycle
service has replied with a genuine UNCONFIGURED or INACTIVE state.

This is diagnostic/preflight only: a positive read is not proof that the
manager can later configure/activate CM or that CM/Guard TTL meets 150 ms.
No repeated lifecycle STARTUP, no state transition, motor Goal or parameter
changes. The same public CI workflow supports ROS Jazzy/Gazebo parity.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import time

CM_SERVICE="/collision_monitor/get_state"

def permitted_no_goal_probe(env):
    """Original Gate1 scope unchanged; classroom GUI admits ONLY no motion.

    This is a read-only CM GetState query, never lifecycle STARTUP, and it
    does not certify Collision Monitor/Guard delivery TTL.
    """
    if (env.get("ROS_DISTRO")!="jazzy"
        or env.get("AXIA_P0_SIM_ONLY")!="1"
        or not env.get("GZ_PARTITION","").startswith("axia_p2_")):
        return False
    if env.get("AXIA_D07_H01_GEOMETRY_ONLY")=="1":
        return True
    return (env.get("AXIA_D07_H01_GUI_NO_GOAL")=="1"
            and all(env.get(k,"0")!="1" for k in (
              "AXIA_G07_CI_SIM_GOAL_ALLOWED",
              "AXIA_P3_S01_CI_GOAL_ALLOWED",
              "AXIA_P3_S03_CI_COMPOUND_ALLOWED",
              "AXIA_P3_S04_CI_PNU_ALLOWED",
              "AXIA_P3_S05_CI_GOAL_ALLOWED")))



def assess_cm_lifecycle_state(state_id, label, *, service=CM_SERVICE):
    hold={
        "schema":"axia_d07_h01_cm_get_state_prestart_v1",
        "status":"CM_GET_STATE_PROVENANCE_HOLD_NO_GOAL",
        "reason":"NO_GENUINE_PRESTART_CM_LIFECYCLE_RESPONSE",
        "service":CM_SERVICE,
        "native_get_state_responded":False,
        "navigation_startup_proven":False,
        "collision_monitor_active_proven":False,
        "cm_guard_ttl_proven":False,
        "goal_sent":False,
        "motion_admitted":False,
        "certified_estop":False,
    }
    if (service!=CM_SERVICE or type(state_id) is not int
        or (state_id,label) not in ((1,"unconfigured"),(2,"inactive"))):
        return hold
    return {**hold,
        "status":"CM_GET_STATE_ACK_NO_GOAL",
        "reason":"NATIVE_CM_LIFECYCLE_RESPONDED_BEFORE_NAV_START_ONLY",
        "native_get_state_responded":True,
        "state_id":state_id,
        "state_label":label,
    }



def assess_cm_post_failed_startup_state(state_id,label,*,service=CM_SERVICE):
    """Observe post-failure CM lifecycle ONLY, never promote STARTUP or TTL."""
    hold={
        "schema":"axia_d07_h01_cm_post_manager_failure_v1",
        "status":"CM_AFTER_FAILED_MANAGER_PROVENANCE_HOLD_NO_GOAL",
        "reason":"NO_GENUINE_POST_FAILURE_CM_GET_STATE_RESPONSE",
        "native_get_state_responded":False,
        "navigation_startup_proven":False,
        "cm_guard_ttl_proven":False,
        "goal_sent":False,
        "motion_admitted":False,
        "certified_estop":False,
    }
    if (service!=CM_SERVICE or type(state_id) is not int
        or (state_id,label) not in (
            (1,"unconfigured"),(2,"inactive"),(3,"active"))):
        return hold
    return {**hold,
            "status":"CM_AFTER_FAILED_MANAGER_STATE_OBSERVED_NO_GOAL",
            "reason":"POST_REJECT_CM_GET_STATE_REPLIED_NOT_NAVIGATION_ACK",
            "native_get_state_responded":True,
            "state_id":state_id,"state_label":label}

def probe(timeout_sec,*,after_failed_manager=False):
    """Bounded first GetState response; no retries of failed STARTUP."""
    hold=(assess_cm_post_failed_startup_state(None,None)
          if after_failed_manager else assess_cm_lifecycle_state(None,None))
    if not permitted_no_goal_probe(os.environ):
        return {**hold,"reason":"H01_SIM_ONLY_SCOPE_MISSING"}
    if not 2<=timeout_sec<=15:
        return {**hold,"reason":"INVALID_PRESTART_DEADLINE"}
    from lifecycle_msgs.srv import GetState
    import rclpy
    start=time.monotonic()
    node=None
    client=None
    try:
        rclpy.init()
        node=rclpy.create_node("axia_d07_h01_cm_prestart_readonly",
                                enable_rosout=False)
        client=node.create_client(GetState,CM_SERVICE)
        if not client.wait_for_service(timeout_sec=min(9.,timeout_sec)):
            return {**hold,"reason":"CM_GET_STATE_SERVICE_NOT_DISCOVERED",
                    "elapsed_sec":round(time.monotonic()-start,6)}
        remaining=timeout_sec-(time.monotonic()-start)
        if remaining<=0:
            return {**hold,"reason":"CM_GET_STATE_BUDGET_EXHAUSTED"}
        future=client.call_async(GetState.Request())
        rclpy.spin_until_future_complete(node,future,timeout_sec=remaining)
        if (not future.done() or future.exception() is not None
            or future.result() is None):
            return {**hold,"reason":"CM_GET_STATE_NO_REPLY",
                    "elapsed_sec":round(time.monotonic()-start,6)}
        state=future.result().current_state
        result=(assess_cm_post_failed_startup_state(
                    int(state.id),str(state.label))
                if after_failed_manager else
                assess_cm_lifecycle_state(int(state.id),str(state.label)))
        return {**result,"elapsed_sec":round(time.monotonic()-start,6)}
    except Exception as error:
        return {**hold,"reason":"CM_GET_STATE_READ_EXCEPTION",
                "error_type":type(error).__name__,
                "elapsed_sec":round(time.monotonic()-start,6)}
    finally:
        if client is not None and node is not None:
            node.destroy_client(client)
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.try_shutdown()


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--timeout-sec",type=float,default=12.)
    p.add_argument("--after-failed-manager",action="store_true")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args(argv)
    result=probe(args.timeout_sec,after_failed_manager=args.after_failed_manager)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",
                           encoding="utf-8")
    print("AXIA_D07_H01_CM_NATIVE_GET_STATE_PRESTART "+
          json.dumps(result,sort_keys=True),flush=True)
    return 0 if result["status"] in (
        "CM_GET_STATE_ACK_NO_GOAL",
        "CM_AFTER_FAILED_MANAGER_STATE_OBSERVED_NO_GOAL") else 2


if __name__=="__main__":
    raise SystemExit(main())
