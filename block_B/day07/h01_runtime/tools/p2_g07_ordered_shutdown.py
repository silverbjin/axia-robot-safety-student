#!/usr/bin/env python3
"""G07 SIM-ONLY: Nav2 managed shutdown before launch process-group SIGINT.

After real Goal STOP/odom or staged no-Goal readiness, transition official
Nav2 nodes via lifecycle_manager_navigation then lifecycle_manager_localization.
No Goal, motion, fault, process signal, or certified E-Stop is issued here.
A positive service ACK means lifecycle shutdown was requested and completed,
NOT proof that collision_monitor later exits cleanly (audit launch.log).
"""
import argparse
import json
import os
from pathlib import Path
import sys
from time import monotonic
from p2_g07_lifecycle_service import call_native_manage


NAV_MANAGER = "/lifecycle_manager_navigation/manage_nodes"
LOC_MANAGER = "/lifecycle_manager_localization/manage_nodes"


def result(status, **extra):
    return {
        "schema": "axia_g07_ordered_nav2_shutdown_v1",
        "status": status,
        "navigation_ack": False,
        "localization_ack": False,
        "cm_managed_by_navigation": False,
        "cm_clean_process_exit_verified": False,
        "owner_l3_accepted": False,
        "certified_estop": False,
        "sim_only": True,
        **extra,
    }


def shutdown_stage_budget(manager, remaining_sec):
    """Bounded lifecycle RESPONSE time after a stopped/canceled Goal.

    Public native Gazebo #44221460587 had Navigation ACK but Localization
    service missed the old arbitrary 13s reply limit. Nav2 performs ordered
    deactivate/cleanup/shutdown. We allow at most 30s for its legitimate
    response within the SAME overall 60s deadline; a missing ACK still
    BLOCKS acceptance. No motion, CM120, Guard150 or sensor TTL changes.
    """
    if manager not in ("navigation", "localization"):
        raise ValueError("UNRECOGNIZED_LIFECYCLE_MANAGER")
    return min(40.0 if manager == "navigation" else 30.0,
               max(0.01, remaining_sec))


def wait_for_service_bounded(client, remaining):
    """Allow bounded ROS 2 discovery jitter in new shutdown observer process.

    A 3s one-shot discovery missed the actually running Lifecycle Manager on
    public Gazebo #44455727595. No Scan/CM/Guard safety TTL is affected.
    The original global shutdown deadline and fail-closed response remain.
    """
    budget=min(12.0,max(0.0,float(remaining)))
    while budget>0:
        delta=min(1.0,budget)
        if client.wait_for_service(timeout_sec=delta):
            return True
        budget-=delta
    return False


def run(*, limit=60.0):
    if (os.environ.get("ROS_DISTRO") != "jazzy"
            or os.environ.get("AXIA_P0_SIM_ONLY") != "1"
            or not os.environ.get("GZ_PARTITION", "").startswith("axia_p2_")):
        return result("BLOCKED_NONISOLATED_NONJAZZY_NO_GOAL")
    import rclpy
    from nav2_msgs.srv import ManageLifecycleNodes
    from rcl_interfaces.srv import GetParameters

    rclpy.init()
    node = None
    deadline = monotonic() + limit
    stages = {}
    try:
        node = rclpy.create_node("axia_g07_ordered_shutdown_guard",
                                 enable_rosout=False)
        def call(kind, name, request, max_response=15.0):
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise RuntimeError("ORDERED_SHUTDOWN_DEADLINE")
            client = node.create_client(kind, name)
            try:
                if not wait_for_service_bounded(client, remaining):
                    raise RuntimeError("SERVICE_MISSING:" + name)
                fut = client.call_async(request)
                wait_budget = min(max_response, deadline-monotonic())
                if wait_budget <= 0:
                    raise RuntimeError("SERVICE_DEADLINE:" + name)
                rclpy.spin_until_future_complete(
                    node, fut, timeout_sec=wait_budget)
                if not fut.done() or fut.result() is None:
                    raise RuntimeError("SERVICE_TIMEOUT:" + name)
                return fut.result()
            finally:
                node.destroy_client(client)

        # Fail closed if the official navigation manager does not actually
        # manage Collision Monitor. Never signal an unmanaged active CM.
        params = GetParameters.Request()
        params.names = ["node_names"]
        response = call(
            GetParameters, "/lifecycle_manager_navigation/get_parameters",
            params, max_response=5.0)
        nodes = list(response.values[0].string_array_value) if response.values else []
        if "collision_monitor" not in nodes:
            return result("BLOCKED_CM_NOT_MANAGED_BY_NAVIGATION",
                          managed_names_count=len(nodes))
        stages["cm_managed_by_navigation"] = True

        # Reuse the EXACT startup service execution engine here.
        # G07 native ManageLifecycleNodes.Request.SHUTDOWN is mapped by
        # p2_g07_lifecycle_service.py, not an unrelated shutdown-only client.
        for key,service in (("navigation", NAV_MANAGER),
                            ("localization", LOC_MANAGER)):
            budget=shutdown_stage_budget(key, deadline-monotonic())
            ack=call_native_manage(node, manager=key, command="shutdown",
                                   timeout_sec=budget)
            if ack["status"]!="ACK":
                return result("BLOCKED_LIFECYCLE_"+key.upper()+"_"+ack["status"],
                              **stages)
            stages[key+"_ack"] = True
        return result("NAV2_LIFECYCLE_SHUTDOWN_ACK",
                      **stages)
    except (RuntimeError, AttributeError, IndexError, OSError) as exc:
        return result("BLOCKED_LIFECYCLE_CALL",
                      failure_type=type(exc).__name__,
                      failure_stage=str(exc)[:110],**stages)
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--timeout-sec",type=float,default=60.0)
    args=p.parse_args(argv)
    if not 5 <= args.timeout_sec <= 65:
        print("G07_ORDERED_SHUTDOWN_INVALID_TIMEOUT",file=sys.stderr)
        return 2
    try:
        verdict=run(limit=args.timeout_sec)
    except Exception as exc:
        verdict=result("BLOCKED_LIFECYCLE_RUNTIME_EXCEPTION",
                       error_type=type(exc).__name__)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(verdict,sort_keys=True,indent=2)+"\n")
    print("G07_NAV2_ORDERED_SHUTDOWN "+json.dumps(verdict,sort_keys=True),flush=True)
    return 0 if verdict["status"]=="NAV2_LIFECYCLE_SHUTDOWN_ACK" else 2


if __name__=="__main__":
    raise SystemExit(main())
