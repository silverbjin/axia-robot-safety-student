#!/usr/bin/env python3
"""D07-only, fail-closed NO-GOAL state attestation after lost Nav2 STARTUP ACK.

Never retries ManageLifecycleNodes.STARTUP. Never admits motion.
Two independent read-only ROS service samples are required: official manager
/is_active + map_server/amcl /get_state. This is not a genuine ACK.
"""
import argparse
import json
import os
from pathlib import Path
import time

ACTIVE = {"id": 3, "label": "active"}
SERVICE = "/lifecycle_manager_localization/manage_nodes"


def scope_kind(env):
    """D07 no-Goal legacy or specifically authorized G07 simulation startup.

    This allows only a read-only lifecycle STATE gate, never motion authority.
    Actual AMCL pose+TF and all safety gates run separately BEFORE any Goal.
    """
    if not (env.get("ROS_DISTRO") == "jazzy"
            and env.get("AXIA_P0_SIM_ONLY") == "1"
            and env.get("AXIA_G07_OWNER_STARTUP_PARITY") == "1"
            and env.get("GZ_PARTITION", "").startswith("axia_p2_")):
        return None
    if (env.get("AXIA_D07_H01_GUI_NO_GOAL") == "1"
            and env.get("AXIA_G07_CI_SIM_GOAL_ALLOWED", "0") == "0"):
        return "D07_NO_GOAL"
    if (env.get("AXIA_G07_STARTUP_READONLY_RECONCILE")=="1"
            and env.get("AXIA_P2_G07_PHYSICAL_PREFLIGHT")=="1"
            and (
                (env.get("GITHUB_ACTIONS")=="true"
                 and env.get("AXIA_G07_CI_SIM_GOAL_ALLOWED")=="1")
                or (env.get("GITHUB_ACTIONS")!="true"
                    and env.get("AXIA_G07_TASK04_OWNER_MOVING_L3")=="1"
                    and env.get("AXIA_G07_CI_SIM_GOAL_ALLOWED","0")!="1"))):
        return "G07_MOVING_STARTUP_STATE_ONLY"
    return None


def allowed_scope(env):
    return scope_kind(env) is not None


def _active_sample(row):
    return (type(row) is dict and row.get("manager_active") is True
            and all(type(row.get(name)) is dict
                    and row[name].get("id") == ACTIVE["id"]
                    and row[name].get("label") == ACTIVE["label"]
                    for name in ("map_server", "amcl")))


def first_stable_active_pair(attempts):
    """Require two CONSECUTIVE complete official read-only ACTIVE samples.

    The first service discovery may be incomplete just after Nav2 STARTUP.
    No state mutation, no lifecycle replay, and no motion admission.
    """
    if not isinstance(attempts, list) or len(attempts) < 2:
        return []
    for prev, curr in zip(attempts, attempts[1:]):
        if _active_sample(prev) and _active_sample(curr):
            return [prev, curr]
    return []


def assess_reconciliation(native, samples, env):
    """Pure L0 fail-closed contract. service ACK is NEVER fabricated."""
    valid_native = (type(native) is dict
                    and native.get("schema") == "axia_g07_native_lifecycle_service_v1"
                    and native.get("manager") == "localization"
                    and native.get("command") == "startup"
                    and native.get("service") == SERVICE
                    and native.get("status") == "SERVICE_TIMEOUT"
                    and native.get("success") is False
                    and native.get("request_sent") is True
                    and native.get("goal_sent") is False)
    kind=scope_kind(env)
    admitted = (valid_native and kind is not None
                and type(samples) is list and len(samples) == 2
                and all(_active_sample(s) for s in samples))
    return {
        "schema": "axia_d07_h01_localization_noack_readonly_v1",
        "status": "READONLY_ACTIVE_RECONCILED_NO_ACK"
                  if admitted else "READONLY_RECONCILIATION_HOLD",
        "admitted_for_d07_no_goal": bool(admitted and kind=="D07_NO_GOAL"),
        "admitted_for_g07_startup_state_only":
            bool(admitted and kind=="G07_MOVING_STARTUP_STATE_ONLY"),
        "scope_kind":kind,
        "amcl_pose_and_tf_still_required_before_goal":True,
        "lifecycle_ack_received": False,
        "original_service_response": "MISSING",
        "original_native_status": (native.get("status")
                                  if type(native) is dict else None),
        "observed_samples": len(samples) if type(samples) is list else 0,
        "official_manager_active_and_nodes_active_twice": bool(admitted),
        "startup_resent": False,
        "goal_sent": False,
        "owner_l3_accepted": False,
        "certified_estop": False,
        "moving_goal_admitted": False,
        "motion_admitted": False,
        "safety_ttl_proven": False,
    }


def _call(node, srv_type, name, remaining):
    import rclpy
    client = node.create_client(srv_type, name)
    try:
        if not client.wait_for_service(timeout_sec=max(0.01, min(1.0, remaining))):
            return None
        future = client.call_async(srv_type.Request())
        rclpy.spin_until_future_complete(node, future,
                                         timeout_sec=max(0.01, min(2.0, remaining)))
        if not future.done():
            return None
        return future.result()
    finally:
        node.destroy_client(client)


def _sample(node, deadline):
    from lifecycle_msgs.srv import GetState
    from std_srvs.srv import Trigger
    results = {}
    for name, service, kind in (
        ("manager_active", "/lifecycle_manager_localization/is_active", Trigger),
        ("map_server", "/map_server/get_state", GetState),
        ("amcl", "/amcl/get_state", GetState),
    ):
        remaining = deadline - time.monotonic()
        if remaining <= 0.0:
            return results
        reply = _call(node, kind, service, remaining)
        if name == "manager_active":
            results[name] = reply.success if reply is not None else None
        elif reply is not None:
            results[name] = {
                "id": int(reply.current_state.id),
                "label": str(reply.current_state.label),
            }
    return results


def collect_readonly_samples(timeout_sec):
    import rclpy
    node = None
    attempts = []
    rclpy.init()
    try:
        node = rclpy.create_node("axia_d07_h01_noack_readonly_state_probe",
                                enable_rosout=False)
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            # Read-only queries ONLY. A temporary missing is_active/get_state
            # during discovery must not be promoted, nor cause STARTUP replay.
            attempts.append(_sample(node, deadline))
            pair = first_stable_active_pair(attempts)
            if pair:
                return pair, attempts
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                break
            time.sleep(min(0.25, remaining))
        return [], attempts
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-sec", type=float, default=14.0)
    args = parser.parse_args(argv)
    native = {}
    samples = []
    attempts = []
    error = None
    if not (1 <= args.timeout_sec <= 16):
        error = "INVALID_BOUNDED_PROBE_TIMEOUT"
    else:
        try:
            native = json.loads(args.native.read_text(encoding="utf-8"))
            if not (type(native) is dict
                    and native.get("status") == "SERVICE_TIMEOUT"
                    and native.get("request_sent") is True
                    and allowed_scope(os.environ)):
                error = "NATIVE_TIMEOUT_OR_READONLY_SCOPE_MISSING"
            else:
                samples, attempts = collect_readonly_samples(args.timeout_sec)
        except (OSError, ValueError, RuntimeError, ImportError) as exc:
            error = type(exc).__name__
    result = assess_reconciliation(native, samples, os.environ)
    if error:
        result["first_readonly_probe_error"] = error
    result["samples"] = samples
    result["read_only_probe_attempt_count"] = len(attempts)
    result["first_read_only_probe_sample"] = attempts[0] if attempts else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print("AXIA_D07_H01_LOCALIZATION_NOACK_READONLY "
          + json.dumps(result, sort_keys=True), flush=True)
    return 0 if (result["admitted_for_d07_no_goal"]
                 or result["admitted_for_g07_startup_state_only"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
