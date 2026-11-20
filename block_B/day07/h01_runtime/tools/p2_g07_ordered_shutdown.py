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


def parameter_discovery_budget(service_name, remaining_sec):
    """One bounded fresh DDS participant discovery grace, never an ACK.

    G07 FV17 public real L2 #44650103452: actual Goal CLEAR/SLOW/STOP and
    exact cancel succeeded, but new shutdown client could not discover the
    already-running Nav manager parameter service within the old 3s.
    Allow at most 8s for THIS read-only service, still inside overall 60s
    shutdown. Do not alter Guard150/CM120/Scan300 or accept missing ACK.
    """
    if type(remaining_sec) not in (int,float) or not 0 < remaining_sec <= 65:
        raise ValueError("INVALID_G07_SHUTDOWN_DISCOVERY_DEADLINE")
    return min(8.0 if service_name=="/lifecycle_manager_navigation/get_parameters"
               else 3.0, remaining_sec)


def _call_isolated_stage(rclpy, *, manager, timeout_sec):
    """Reuse G07 Task04 per-manager short-lived native Nav2 service client.

    Real strict L2 #44476730420 had Navigation SHUTDOWN ACK but
    Localization SERVICE_TIMEOUT (Nav2 manager stayed alive). Eliminate
    possible previous executor/client-graph state, preserving official ACK.
    This issues exactly ONE request per manager, never a retry and never
    a replacement of Scan300 / CM120 / Guard150 safety requirements.
    """
    node=rclpy.create_node("axia_g07_shutdown_"+manager,
                           enable_rosout=False)
    try:
        return call_native_manage(node, manager=manager, command="shutdown",
                                  timeout_sec=timeout_sec)
    finally:
        node.destroy_node()




def _call_shutdown_stage_for_ab(rclpy, node, *, manager, timeout_sec, scope_env):
    """One native SHUTDOWN request; CI-only compare already-ready DDS participant.

    Actual #44698698767: get_parameters ACK on the persistent node, but
    a NEW participant's first /manage_nodes SHUTDOWN request timed out at
    40.000574s while a later /is_active service answered in 79.579ms.
    eProsima/Fast-DDS#6630 documents a possible newly joined discovery race.
    This A/B does not prove that root: NO extra call/retry, no time extension.
    CI-only for one exact Moving Goal, not an Owner default behavior change.
    Localization stage stays independently isolated.
    """
    if manager not in ("navigation", "localization"):
        raise ValueError("G07_WARM_NAV_PARTICIPANT_BAD_MANAGER")
    requested=scope_env.get("AXIA_G07_NAV_WARM_PARTICIPANT_CI_AB", "")
    if requested not in ("", "0", "1"):
        raise ValueError("G07_WARM_NAV_PARTICIPANT_BAD_SETTING")
    if requested=="1":
        allowed=(scope_env.get("GITHUB_ACTIONS")=="true"
                 and scope_env.get("AXIA_G07_CI_SIM_GOAL_ALLOWED")=="1"
                 and scope_env.get("AXIA_P0_SIM_ONLY")=="1"
                 and scope_env.get("ROS_DISTRO")=="jazzy"
                 and scope_env.get("GZ_PARTITION","").startswith("axia_p2_")
                 and scope_env.get("AXIA_G07_TASK04_OWNER_MOVING_L3")!="1")
        if not allowed:
            raise ValueError("G07_WARM_NAV_PARTICIPANT_SCOPE_DENIED")
        if manager=="navigation":
            print("G07_NAV_SHUTDOWN_AB=EXISTING_PARAMETER_ACKED_ROS_PARTICIPANT "
                  "ONE_REQUEST_ROOT_CAUSE_NOT_PROVEN",flush=True)
            return call_native_manage(node, manager=manager,command='shutdown',
                                      timeout_sec=timeout_sec)
    return _call_isolated_stage(rclpy,manager=manager,timeout_sec=timeout_sec)


def probe_localization_parameter_service(rclpy, *, timeout_sec):
    """Read-only first-failure classification after a *single* shutdown timeout.

    A response from /get_parameters shows the manager's parameter callbacks
    are servicing requests; it does NOT imply ManageLifecycleNodes SHUTDOWN ACK.
    Never resend SHUTDOWN or extend the 60s overall deadline.
    """
    started=monotonic()
    remaining=max(0.0, min(float(timeout_sec), 3.0))
    if remaining <= 0:
        return {"status":"NOT_RUN_DEADLINE_EXPIRED", "request_sent":False,
                "elapsed_sec":0.0}
    from rcl_interfaces.srv import GetParameters
    node=None
    client=None
    service="/lifecycle_manager_localization/get_parameters"
    result={"status":"PROBE_INCOMPLETE", "request_sent":False,
            "service":service}
    try:
        node=rclpy.create_node("axia_g07_localization_readonly_probe",
                               enable_rosout=False)
        client=node.create_client(GetParameters, service)
        if not client.wait_for_service(timeout_sec=0.5):
            result["status"]="PARAMETER_SERVICE_MISSING"
        else:
            request=GetParameters.Request()
            request.names=["node_names"]
            future=client.call_async(request)
            result["request_sent"]=True
            remaining=max(0.0, min(2.0, timeout_sec-(monotonic()-started)))
            if remaining<=0:
                result["status"]="PROBE_GLOBAL_DEADLINE"
            else:
                if remaining>=2.0:
                    rclpy.spin_until_future_complete(node, future, timeout_sec=2.0)
                else:
                    rclpy.spin_until_future_complete(node, future, timeout_sec=remaining)
                if not future.done() or future.result() is None:
                    result["status"]="PARAMETER_RESPONSE_TIMEOUT"
                else:
                    result["status"]="PARAMETER_SERVICE_RESPONSIVE"
                    # Count is diagnostic only; never treat it as Shutdown ACK.
                    values=getattr(future.result(),"values",[])
                    result["value_count"]=len(values)
    except Exception as exc:
        result["status"]="PARAMETER_PROBE_ERROR"
        result["error_type"]=type(exc).__name__
    finally:
        if client is not None:
            node.destroy_client(client)
        if node is not None:
            node.destroy_node()
    result["elapsed_sec"]=round(monotonic()-started,6)
    return result


def _probe_manage_callback_group(rclpy, *, manager, timeout_sec):
    """Read-only /is_active shares Nav2 manager's manage_nodes callback group.

    In official Nav2 Jazzy, /manage_nodes and /is_active use the same
    MutuallyExclusive callback_group and service executor; /get_parameters
    is on the regular node parameter callback path. This checks whether
    the service callback group is responding after one lost SHUTDOWN ACK.
    It NEVER retries ManageLifecycleNodes nor authorizes any motion.
    """
    if manager not in ("navigation","localization"):
        raise ValueError("UNRECOGNIZED_MANAGE_PROBE_TARGET")
    started=monotonic()
    if timeout_sec<=0:
        return {"status":"NOT_RUN_DEADLINE_EXPIRED","request_sent":False,
                "elapsed_sec":0.0}
    from std_srvs.srv import Trigger
    service={
        "localization":"/lifecycle_manager_localization/is_active",
        "navigation":"/lifecycle_manager_navigation/is_active",
    }[manager]
    out={"status":"MANAGE_CALLBACK_GROUP_NOT_MEASURED",
         "service":service,"request_sent":False}
    node=None;client=None
    try:
        node=rclpy.create_node("axia_g07_"+manager+"_manage_readonly_probe",
                               enable_rosout=False)
        client=node.create_client(Trigger,service)
        if not client.wait_for_service(timeout_sec=min(.5,timeout_sec)):
            out["status"]="MANAGE_CALLBACK_GROUP_SERVICE_MISSING"
        else:
            future=client.call_async(Trigger.Request())
            out["request_sent"]=True
            remaining=max(0.0,min(2.0,timeout_sec-(monotonic()-started)))
            if remaining<=0:
                out["status"]="MANAGE_CALLBACK_GROUP_DEADLINE"
            else:
                rclpy.spin_until_future_complete(node,future,timeout_sec=remaining)
                if not future.done() or future.result() is None:
                    out["status"]="MANAGE_CALLBACK_GROUP_NO_ACK"
                else:
                    out["status"]="MANAGE_CALLBACK_GROUP_RESPONSIVE"
                    out["is_active"]=bool(future.result().success)
    except Exception as exc:
        out["status"]="MANAGE_CALLBACK_GROUP_PROBE_EXCEPTION"
        out["error_type"]=type(exc).__name__
    finally:
        if node is not None:
            if client is not None:node.destroy_client(client)
            node.destroy_node()
    out["elapsed_sec"]=round(monotonic()-started,6)
    return out


def probe_localization_manage_callback_group(rclpy, *, timeout_sec):
    """One read-only Trigger on official localization management service group."""
    return _probe_manage_callback_group(rclpy, manager="localization",
                                        timeout_sec=timeout_sec)


def probe_navigation_manage_callback_group(rclpy, *, timeout_sec):
    """One read-only Trigger after missing Navigation SHUTDOWN ACK; no retry."""
    return _probe_manage_callback_group(rclpy, manager="navigation",
                                        timeout_sec=timeout_sec)


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
    # Record the actual DDS/RMW implementation used by the ROS service
    # requester. An issue hypothesis must never be treated as a measured RMW.
    try:
        from rclpy.utilities import get_rmw_implementation_identifier
        stages["rmw_implementation_identifier"]=get_rmw_implementation_identifier()
    except (ImportError, AttributeError, RuntimeError) as exc:
        stages["rmw_implementation_identifier"]="UNDETERMINED"
        stages["rmw_identification_error_type"]=type(exc).__name__
    try:
        node = rclpy.create_node("axia_g07_ordered_shutdown_guard",
                                 enable_rosout=False)
        def call(kind, name, request, max_response=15.0):
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise RuntimeError("ORDERED_SHUTDOWN_DEADLINE")
            client = node.create_client(kind, name)
            try:
                discovery_started=monotonic()
                ready=client.wait_for_service(timeout_sec=parameter_discovery_budget(name, remaining))
                if name=="/lifecycle_manager_navigation/get_parameters":
                    stages["parameter_service_discovery_elapsed_sec"]=round(
                        monotonic()-discovery_started,6)
                    stages["parameter_service_available"]=bool(ready)
                if not ready:
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
            ack=_call_shutdown_stage_for_ab(rclpy, node, manager=key,
                                            timeout_sec=budget, scope_env=os.environ)
            # Preserve FIRST lifecycle service response boundary, not just
            # the final shell rc. This is diagnostic, NEVER a substitute
            # for the required actual Navigation + Localization ACK.
            stages[key+"_response_elapsed_sec"]=ack.get("elapsed_sec")
            stages[key+"_service_request_sent"]=ack.get("request_sent",False)
            stages[key+"_service_status"]=ack.get("status")
            if key=="navigation" and ack["status"]=="SERVICE_TIMEOUT":
                # Existing D06 confirmed read-only same-callback-group probe:
                # never retries or replaces the missing official Shutdown ACK.
                stages["navigation_manage_group_probe"]=(
                    probe_navigation_manage_callback_group(
                        rclpy, timeout_sec=max(0.0,deadline-monotonic())))
            if key=="localization" and ack["status"]=="SERVICE_TIMEOUT":
                stages["localization_parameter_probe"]=(
                    probe_localization_parameter_service(
                        rclpy, timeout_sec=max(0.0,deadline-monotonic())))
                stages["localization_manage_group_probe"]=(
                    probe_localization_manage_callback_group(
                        rclpy, timeout_sec=max(0.0,deadline-monotonic())))
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
