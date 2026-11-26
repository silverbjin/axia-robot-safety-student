"""Bounded, fail-closed acknowledgement of the official Jazzy AMCL SetInitialPose service.

The service calls AMCL's initialPoseReceived callback, but its response is
empty and DOES NOT prove localization. Caller must still verify /amcl_pose,
scan/odom freshness and map -> base_link TF before starting navigation.
"""
from __future__ import annotations
import time


def wait_for_amcl_ack(node, client, request, *, spin_once,
                      clock=time.monotonic, wait_sec=12.0,
                      response_sec=12.0) -> dict:
    """No retries that could conceal errors. All deadlines are wall-monotonic."""
    report = {
        "service": "/set_initial_pose",
        "status": "BLOCKED",
        "acknowledged": False,
        "request_sent": False,
        "localization_verified": False,
    }
    if wait_sec <= 0 or response_sec <= 0:
        report["status"] = "INVALID_DEADLINE"
        return report

    began = clock()
    while True:
        remaining = wait_sec - (clock() - began)
        if remaining <= 0:
            report["status"] = "SERVICE_UNAVAILABLE"
            report["service_wait_wall_sec"] = round(clock() - began, 3)
            return report
        try:
            if client.wait_for_service(timeout_sec=min(0.25, remaining)):
                break
        except Exception as exc:
            report["status"] = "SERVICE_DISCOVERY_ERROR"
            report["error"] = repr(exc)
            return report
    report["service_wait_wall_sec"] = round(clock() - began, 3)

    try:
        future = client.call_async(request)
    except Exception as exc:
        report["status"] = "SERVICE_REQUEST_ERROR"
        report["error"] = repr(exc)
        return report
    report["request_sent"] = True
    began = clock()
    while True:
        if future.done():
            try:
                response = future.result()
            except Exception as exc:
                report["status"] = "SERVICE_RESPONSE_ERROR"
                report["error"] = repr(exc)
                return report
            if response is None:
                report["status"] = "SERVICE_RESPONSE_MISSING"
                return report
            report["status"] = "SERVICE_ACKNOWLEDGED"
            report["acknowledged"] = True
            report["response_wait_wall_sec"] = round(clock() - began, 3)
            return report
        remaining = response_sec - (clock() - began)
        if remaining <= 0:
            report["status"] = "SERVICE_RESPONSE_TIMEOUT"
            report["response_wait_wall_sec"] = round(clock() - began, 3)
            return report
        try:
            spin_once(node, timeout_sec=min(0.15, remaining))
        except Exception as exc:
            report["status"] = "SERVICE_SPIN_ERROR"
            report["error"] = repr(exc)
            return report
