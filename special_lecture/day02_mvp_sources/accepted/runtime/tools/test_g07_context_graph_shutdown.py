"""Regression for native Gazebo #44912769355 cycle2 post-SIGINT graph query.

This test must RED on Student #89 (unhandled context-invalid publisher graph
introspection); GREEN only for the exact already-dead context + rclpy RCLError.
An active ROS context must NOT swallow genuine graph/safety failures.
No ROS/Gazebo stub or native acceptance is claimed by this unit test.
"""
from pathlib import Path
import importlib.util
import unittest


ROOT=Path(__file__).resolve().parents[1]
PKG=(ROOT/"ros2_ws/src/axia_safety_supervisor/axia_safety_supervisor")
SRC=PKG/"p2_shutdown_context.py"
SUPERVISOR=PKG/"p2_supervisor_node.py"


def target():
    spec=importlib.util.spec_from_file_location("axia_shutdown_classification",SRC)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NativeGraphIntrospectionAfterShutdown(unittest.TestCase):
    def test_native_exact_post_sigint_error_classified_only_after_shutdown(self):
        class RCLError(Exception):
            pass

        exact=("Failed to get information by topic for publishers: "
               "rcl node's context is invalid, at ./src/rcl/node.c:404")
        classify=target().is_context_graph_shutdown
        self.assertTrue(classify(RCLError(exact),context_ok=False))
        self.assertFalse(classify(RCLError(exact),context_ok=True))
        self.assertFalse(classify(RCLError(exact),context_ok=None))

    def test_critical_or_other_telemetry_errors_never_swallowed(self):
        class RCLError(Exception):
            pass
        class RuntimeError(Exception):
            pass

        classify=target().is_context_graph_shutdown
        messages=(
            "Failed to get information by topic for publishers: permission denied",
            "Failed to get information by topic for subscriptions: timeout",
            "Failed to get information by topic for publishers: rcl node's context is invalid",
            "Failed to publish: publisher's context is invalid",
            "Failed to get information by topic for publishers: rcl node's context is invalid, at ./src/rcl/node.c:999",
        )
        for message in messages:
            with self.subTest(message=message):
                self.assertFalse(classify(RCLError(message),context_ok=False))
        exact=("Failed to get information by topic for publishers: "
               "rcl node's context is invalid, at ./src/rcl/node.c:404")
        self.assertFalse(classify(RuntimeError(exact),context_ok=False))

    def test_entrypoint_remains_fail_closed_for_active_context(self):
        main=SUPERVISOR.read_text()
        self.assertIn("is_context_graph_shutdown",main)
        self.assertIn("context_ok=rclpy.ok()",main)
        self.assertIn("raise",main)
        self.assertIn("rclpy.try_shutdown()",main)
        self.assertNotIn("except BaseException:",main)
        self.assertNotIn("except Exception: pass",main)

    def test_existing_waitset_and_publish_handlers_unchanged(self):
        handler=target()
        class RCLError(Exception):
            pass
        self.assertTrue(handler.is_context_waitset_shutdown(
            RCLError("failed to initialize wait set: context is not valid"),
            context_ok=False))
        self.assertTrue(handler.is_context_publish_shutdown(
            RCLError("Failed to publish: publisher's context is invalid"),
            context_ok=False))


if __name__=="__main__":
    unittest.main()
