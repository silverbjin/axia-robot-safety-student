"""AXIA P1 G01-R ROS graph observer: safe, read-only, fail-closed.

No graph observation alone proves physical stopping, certified E-Stop, CM
lifecycle ACTIVE, or publisher ownership against malicious ROS participants.
"""
import argparse
import json
import time

try:
    from .p1_t08_provenance import stamp_live_record
except ImportError:
    from p1_t08_provenance import stamp_live_record



CHAIN = (
    ("/cmd_vel_smoothed", "velocity_smoother", "axia_safety_supervisor"),
    ("/cmd_vel_supervised", "axia_safety_supervisor", "collision_monitor"),
    ("/cmd_vel", "collision_monitor", None),
)
TWIST = "geometry_msgs/msg/Twist"


def assess_graph(snapshot):
    """Pure contract for ROS graph, separate from live ROS fetch."""
    reasons = []
    for topic, publisher, consumer in CHAIN:
        record = snapshot.get(topic)
        if not isinstance(record, dict):
            reasons.append("TOPIC_MISSING:" + topic)
            continue
        publishers = record.get("publishers", [])
        subs = record.get("subscriptions", [])
        if len(publishers) != 1 or publishers[0].get("node_name") != publisher:
            reasons.append("PUBLISHER_TOPOLOGY:" + topic)
        if any(p.get("topic_type") != TWIST for p in publishers):
            reasons.append("PUBLISHER_TYPE:" + topic)
        if consumer and not any(
            sub.get("node_name") == consumer and sub.get("topic_type") == TWIST
            for sub in subs
        ):
            reasons.append("SUBSCRIBER_TOPOLOGY:" + topic)
    return {"passed": not reasons, "reasons": reasons, "scope": "ROS_GRAPH_ONLY"}


def collect_live_graph(node):
    result = {}
    for topic, _pub, _sub in CHAIN:
        result[topic] = {
            "publishers": [{
                "node_name": endpoint.node_name,
                "node_namespace": endpoint.node_namespace,
                "topic_type": endpoint.topic_type,
            } for endpoint in node.get_publishers_info_by_topic(topic)],
            "subscriptions": [{
                "node_name": endpoint.node_name,
                "node_namespace": endpoint.node_namespace,
                "topic_type": endpoint.topic_type,
            } for endpoint in node.get_subscriptions_info_by_topic(topic)]
        }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.timeout <= 0:
        raise SystemExit("timeout must be positive")
    import rclpy
    from rclpy.node import Node
    rclpy.init()
    node = Node("axia_p1_t05_graph_oracle")
    best = None
    try:
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.2)
            graph = collect_live_graph(node)
            best = {"graph": graph, "verdict": assess_graph(graph)}
            if best["verdict"]["passed"]:
                break
        if best is None:
            best = {"graph": {}, "verdict": {"passed": False, "reasons": ["NO_SAMPLE"],
                                             "scope": "ROS_GRAPH_ONLY"}}
        from pathlib import Path
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        best = stamp_live_record(best, source_root=Path(__file__).resolve().parents[1])
        out.write_text(json.dumps(best, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(best["verdict"], ensure_ascii=False))
        return 0 if best["verdict"]["passed"] else 2
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
