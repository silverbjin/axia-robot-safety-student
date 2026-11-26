"""Actual #44697450829 second-run native Supervisor SIGINT publish race.

When Jazzy default rclpy SIGINT invalidates the context during an already
running timer callback, P2 Supervisor may throw "Failed to publish:
publisher's context is invalid" from _state_pub.publish() after its Goal
already canceled. Only exact *already invalid* context race is ignorable.
No regular safety fault may be swallowed while ROS context is active.
"""
from pathlib import Path
import importlib.util
import unittest


SRC=(Path(__file__).resolve().parents[1]/
     "ros2_ws/src/axia_safety_supervisor/axia_safety_supervisor/p2_shutdown_context.py")
P2=SRC.with_name("p2_supervisor_node.py")


def classifier():
    sp=importlib.util.spec_from_file_location("g07_p2_shutdown_context_actual",SRC)
    mod=importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    return mod.is_context_publish_shutdown


class RealPublishAfterShutdown(unittest.TestCase):
    def test_first_real_shutdown_invalid_publisher_only(self):
        class RCLError(Exception):pass
        exact="Failed to publish: publisher's context is invalid, at ./src/rcl/publisher.c:423"
        self.assertTrue(classifier()(RCLError(exact),context_ok=False))
        self.assertFalse(classifier()(RCLError(exact),context_ok=True))
        self.assertFalse(classifier()(RCLError(exact),context_ok=None))

    def test_other_publisher_critical_errors_must_raise(self):
        class RCLError(Exception):pass
        for msg in ("Failed to publish: invalid data pointer",
                    "Failed to publish: client not authorized",
                    "Failed to publish: publisher handle is invalid",
                    "failed to publish: publisher's context is invalid"):
            self.assertFalse(classifier()(RCLError(msg),context_ok=False))

    def test_not_catch_falsely_named_non_rclpy_exception(self):
        class RuntimeError(Exception):pass
        msg="Failed to publish: publisher's context is invalid"
        self.assertFalse(classifier()(RuntimeError(msg),context_ok=False))

    def test_actual_p2_entrypoint_uses_exact_classifier_no_broad_ignore(self):
        src=P2.read_text()
        self.assertIn("is_context_publish_shutdown",src)
        self.assertIn("is_context_waitset_shutdown",src)
        self.assertIn("context_ok=rclpy.ok()",src)
        self.assertIn("raise",src)
        self.assertIn("rclpy.try_shutdown()",src)


if __name__=="__main__":
    unittest.main()
