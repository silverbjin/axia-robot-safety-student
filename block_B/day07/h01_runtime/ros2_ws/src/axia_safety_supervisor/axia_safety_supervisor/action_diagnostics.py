"""Read-only graph snapshot for a Nav2 NavigateToPose action endpoint.

Discovery snapshot is diagnostics only; ActionClient.server_is_ready() remains
the actual fail-closed Supervisor readiness predicate.
"""


def action_graph_snapshot(node, action_name: str) -> dict:
    prefix = action_name.rstrip("/") + "/_action/"
    result = {
        "action_name": action_name,
        "graph_names_are_not_server_proof": True,
    }
    try:
        # ROS 2 graph name queries may include ActionClient service names.
        # Never use this snapshot for safety: only server_is_ready() decides.
        services = {name for name, _types in node.get_service_names_and_types()}
        for key in ("send_goal", "get_result", "cancel_goal"):
            result[key] = prefix + key in services
        # The server publishes feedback and status; counts are not
        # authentication or sufficient evidence of a functioning server.
        for key in ("feedback", "status"):
            result[key] = node.count_publishers(prefix + key) > 0
        result["missing_endpoints"] = [
            key for key in ("send_goal", "get_result", "cancel_goal",
                            "feedback", "status") if not result[key]
        ]
        result["endpoint_complete"] = not result["missing_endpoints"]
    except Exception as exc:
        # A graph query during shutdown may fail; never manufacture readiness.
        result.update(
            endpoint_complete=False,
            missing_endpoints=["UNAVAILABLE"],
            graph_error=type(exc).__name__,
        )
    return result
