"""RED regression: preGoal read-only ROS scan observer must not detach per callback.

Actual upstream rclpy Jazzy spin_once(node, ...) adds/removes a node
on EVERY call when no explicit executor is supplied. At ~300Hz /clock
plus scan/odom this causes unnecessary global wait-set rebuilds and
can corrupt sampling cadence. Keep one existing single-thread executor;
NO new ROS node, DDS participant, QoS change, TTL relaxation or Goal.
Fix is a measured candidate, not proof of scan 300ms root or native PASS.
"""
import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
PREGOAL=ROOT/"tools/p2_g07_scan_wall_pregoal.py"


class PersistentScanPreGoalExecutor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=PREGOAL.read_text(encoding="utf-8")
        cls.tree=ast.parse(cls.text)

    def test_no_global_rclpy_spin_once_per_callback(self):
        calls=[item for item in ast.walk(self.tree)
               if isinstance(item,ast.Call)
               and isinstance(item.func,ast.Attribute)
               and isinstance(item.func.value,ast.Name)
               and item.func.value.id=="rclpy"
               and item.func.attr=="spin_once"]
        self.assertEqual(calls,[])  # Comments documenting the old bug are allowed.

    def test_one_singlethreaded_executor_is_reused_by_default(self):
        self.assertIn("from rclpy.executors import SingleThreadedExecutor",self.text)
        self.assertIn("executor=SingleThreadedExecutor()",self.text)
        self.assertIn("executor.add_node(node)",self.text)
        self.assertEqual(self.text.count("executor.spin_once(timeout_sec=.04)"),2)

    def test_shutdown_executor_before_subscriptions_node(self):
        self.assertIn("executor.shutdown(timeout_sec=2)",self.text)
        self.assertLess(self.text.index("executor.shutdown(timeout_sec=2)"),
                        self.text.index("for sub in subs:node.destroy_subscription(sub)"))
        self.assertIn("rclpy.try_shutdown()",self.text)

    def test_actual_safety_and_evidence_contract_not_changed(self):
        for expected in (
            "SCAN_LIMIT_MS=300.0",
            "HEADER_SIM_LIMIT_MS=150.0",
            "WINDOW_SEC=12.0",
            "DISCOVERY_WARMUP_MAX_SEC=8.0",
            "SCAN_PREFLIGHT_CLOCK_ODOM_INTERVAL_BREACH",
            '("scan","safety_scan","clock","odom")',
            'qos_profile_sensor_data',
            "return 3",
            "goal_sent=False",
        ):
            self.assertIn(expected,self.text)
        self.assertNotIn("create_publisher(",self.text)


if __name__=="__main__":
    unittest.main()
