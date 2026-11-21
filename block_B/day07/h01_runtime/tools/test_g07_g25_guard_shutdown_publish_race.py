"""RED regression from real G07 Native #44881017415 first Guard exception.

Goal/physical CLEAR/SLOW/STOP completed within same simulator run (runner rc0),
but the Guard timer tried self._status.publish after ROS SIGINT and
rclpy context invalidation, then process exit1. Existing P2 Supervisor
already uses a narrow post-shutdown classifier: REUSE, not broad catch.
"""
import importlib.util
import unittest
from pathlib import Path

MODULE=Path(__file__).resolve().parents[1]/(
    "ros2_ws/src/axia_safety_supervisor/axia_safety_supervisor/p2_shutdown_context.py")
GUARD=MODULE.with_name("p2_base_guard_node.py")
SUPERVISOR=MODULE.with_name("p2_supervisor_node.py")

def load():
    spec=importlib.util.spec_from_file_location("g07_g25_existing_shutdown",MODULE)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class GuardPostSIGINTPublishRace(unittest.TestCase):
    def test_actual_guard_first_exception_accepted_only_when_context_invalid(self):
        class RCLError(Exception):pass
        observed=("Failed to publish: publisher's context is invalid, "
                  "at ./src/rcl/publisher.c:423")
        classify=load().is_context_publish_shutdown
        self.assertTrue(classify(RCLError(observed),context_ok=False))
        self.assertFalse(classify(RCLError(observed),context_ok=True))

    def test_live_context_other_publish_errors_must_still_fail_closed(self):
        class RCLError(Exception):pass
        classify=load().is_context_publish_shutdown
        for err,ok in (
            ("Failed to publish: publisher's context is invalid",True),
            ("Failed to publish: publisher's context is invalid",None),
            ("Failed to publish: publisher handle is invalid",False),
            ("Failed to publish: invalid data pointer",False)):
            self.assertFalse(classify(RCLError(err),context_ok=ok))

    def test_guard_entrypoint_must_match_proven_supervisor_shutdown_boundary(self):
        src=GUARD.read_text()
        supervisor=SUPERVISOR.read_text()
        for token in ("is_context_publish_shutdown","is_context_waitset_shutdown",
                      "context_ok=rclpy.ok()","rclpy.try_shutdown()"):
            self.assertIn(token,supervisor)
            self.assertIn(token,src)
        self.assertIn("or is_context_publish_shutdown(exc,context_ok=context_ok)",src)
        self.assertIn("raise",src)
        self.assertIn("self._status.publish(status)",src)
        self.assertIn("self._final.publish(_twist(out))",src)
        self.assertNotIn("except Exception:\n        pass",src)

if __name__=="__main__":
    unittest.main()
