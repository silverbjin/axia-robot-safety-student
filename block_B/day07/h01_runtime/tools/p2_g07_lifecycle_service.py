#!/usr/bin/env python3
"""G07 shared native Nav2 Lifecycle Manager client for PUBLIC CI and WSL2.

The original MKZsyUy6 WSL2 failure was a ROS 2 CLI ManageLifecycleNodes
STARTUP request with no response for 95.103s after localization succeeded.
This module removes the *CLI request path* but does not mask a hung manager.
STARTUP and SHUTDOWN use this SAME bounded rclpy client; no Goal, cmd_vel,
fault, safety-latch bypass, signals, or certified E-Stop action occurs here.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from time import monotonic

SERVICE = {
    "navigation": "/lifecycle_manager_navigation/manage_nodes",
    "localization": "/lifecycle_manager_localization/manage_nodes",
}
COMMANDS = {"startup": 0, "shutdown": 4}


def permitted(env):
    return (env.get("ROS_DISTRO") == "jazzy"
            and env.get("AXIA_P0_SIM_ONLY") == "1"
            and env.get("GZ_PARTITION", "").startswith("axia_p2_"))


def service_result(*, status, manager, command, elapsed_sec=0.0, **detail):
    return {
        "schema": "axia_g07_native_lifecycle_service_v1",
        "status": status,
        "service": SERVICE[manager],
        "manager": manager,
        "command": command,
        "success": status == "ACK",
        "elapsed_sec": round(elapsed_sec, 6),
        "goal_sent": False,
        "fault_injected": False,
        "owner_l3_accepted": False,
        "certified_estop": False,
        "sim_only": True,
        **detail,
    }


def ci_simulated_lost_ack(env, *, manager, command):
    """CI-only client-observation probe after a genuine official STARTUP ACK.

    Used to regress the D07 no-Goal no-ACK recovery branch. Does NOT drop
    DDS traffic or prevent Nav2 from replying. Never permitted on Owner WSL2
    or any moving Goal/safety acceptance pathway.
    """
    return (env.get("GITHUB_ACTIONS") == "true"
            and env.get("AXIA_D07_H01_CI_INJECT_LOST_ACK") == "1"
            and env.get("ROS_DISTRO") == "jazzy"
            and env.get("AXIA_P0_SIM_ONLY") == "1"
            and env.get("AXIA_D07_H01_GUI_NO_GOAL") == "1"
            and env.get("AXIA_G07_OWNER_STARTUP_PARITY") == "1"
            and env.get("AXIA_G07_CI_SIM_GOAL_ALLOWED", "0") == "0"
            and env.get("GZ_PARTITION", "").startswith("axia_p2_")
            and manager == "localization" and command == "startup")


def call_native_manage(node, *, manager, command, timeout_sec):
    """Call official ManageLifecycleNodes service with ROS-level async ACK.

    Shared by staged STARTUP and the ordered SHUTDOWN runner. The invoking
    process owns the rclpy node; this function NEVER signals other processes.
    """
    from nav2_msgs.srv import ManageLifecycleNodes
    import rclpy

    if manager not in SERVICE or command not in COMMANDS:
        raise ValueError("INVALID_LIFECYCLE_OPERATION")
    if not 0 < timeout_sec <= 100:
        raise ValueError("INVALID_LIFECYCLE_DEADLINE")
    at = monotonic()
    client = node.create_client(ManageLifecycleNodes, SERVICE[manager])
    try:
        if not client.wait_for_service(timeout_sec=min(5.0, timeout_sec)):
            return service_result(status="SERVICE_MISSING", manager=manager,
                                  command=command, elapsed_sec=monotonic()-at)
        request = ManageLifecycleNodes.Request()
        request.command = (ManageLifecycleNodes.Request.STARTUP if command == "startup"
                           else ManageLifecycleNodes.Request.SHUTDOWN)
        future = client.call_async(request)
        remaining = timeout_sec-(monotonic()-at)
        if remaining <= 0:
            return service_result(status="SERVICE_TIMEOUT", manager=manager,
                                  command=command, elapsed_sec=monotonic()-at,
                                  request_sent=True)
        rclpy.spin_until_future_complete(node, future, timeout_sec=remaining)
        if not future.done() or future.result() is None:
            return service_result(status="SERVICE_TIMEOUT", manager=manager,
                                  command=command, elapsed_sec=monotonic()-at,
                                  request_sent=True)
        response = future.result()
        if response.success is True and ci_simulated_lost_ack(
                os.environ, manager=manager, command=command):
            # Real service has replied ACK. Synthesize ONLY the client verdict
            # to exercise the existing read-only reconciliation branch.
            # No extra ManageLifecycleNodes call and no shell/Owner effect.
            return service_result(
                status="SERVICE_TIMEOUT", manager=manager, command=command,
                elapsed_sec=monotonic()-at, request_sent=True,
                ci_ack_loss_injected_after_actual_ack=True)
        return service_result(status="ACK" if response.success is True else "REJECTED",
                              manager=manager, command=command,
                              elapsed_sec=monotonic()-at, request_sent=True)
    finally:
        node.destroy_client(client)


def execute(*, manager, command, timeout_sec):
    started=monotonic()
    if not permitted(os.environ):
        return service_result(status="BLOCKED_SIMULATION_SCOPE", manager=manager,
                              command=command)
    import rclpy
    node=None
    try:
        rclpy.init()
        node=rclpy.create_node("axia_g07_shared_lifecycle_request",
                               enable_rosout=False)
        return call_native_manage(node, manager=manager, command=command,
                                  timeout_sec=timeout_sec)
    except Exception as exc:
        return service_result(status="BLOCKED_LIFECYCLE_EXCEPTION",
                              manager=manager, command=command,
                              elapsed_sec=monotonic()-started,
                              error_type=type(exc).__name__)
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--manager",choices=sorted(SERVICE),required=True)
    parser.add_argument("--command",choices=sorted(COMMANDS),required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--timeout-sec",type=float,default=90.0)
    args=parser.parse_args(argv)
    if not 1 <= args.timeout_sec <= 95:
        v=service_result(status="BLOCKED_TIMEOUT_ARGUMENT",
                         manager=args.manager, command=args.command)
    else:
        v=execute(manager=args.manager, command=args.command,
                  timeout_sec=args.timeout_sec)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n",
                           encoding="utf-8")
    print("AXIA_G07_SHARED_NATIVE_LIFECYCLE "+json.dumps(v,sort_keys=True),flush=True)
    return 0 if v["status"]=="ACK" else 2


if __name__=="__main__":
    raise SystemExit(main())
