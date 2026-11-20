"""G07 Jazzy FastDDS RMW receive-gap: opt-in Observer executor A/B.

Root evidence: native Moving Goal #44683741133 saw CM source 48.499ms,
FastDDS reception 356.888ms, Observer callback 362.069ms. Official
ros2/rclpy#1452 documents pathological MultiThreadedExecutor subscription
latency; test one reversible observer-only hypothesis with NO safety changes.
"""
import os
from pathlib import Path
import subprocess
import unittest

SOURCE=Path(__file__).with_name("p2_g07_ci_moving_goal.py")


class OriginalObserverAblation(unittest.TestCase):
    def test_default_is_original_owner_two_workers(self):
        from p2_g07_ci_moving_goal import select_observer_executor_ab
        self.assertEqual(select_observer_executor_ab(None,owner_mode=False,
                                                     ci_authorized=False),"multi")
        self.assertEqual(select_observer_executor_ab("",owner_mode=True,
                                                     ci_authorized=False),"multi")

    def test_single_candidate_only_in_authorized_real_ci_or_owner(self):
        from p2_g07_ci_moving_goal import select_observer_executor_ab
        self.assertEqual(select_observer_executor_ab("single",owner_mode=False,
                                                     ci_authorized=True),"single")
        self.assertEqual(select_observer_executor_ab("single",owner_mode=True,
                                                     ci_authorized=False),"single")
        with self.assertRaisesRegex(ValueError,"RMW_EXECUTOR_SCOPE_DENIED"):
            select_observer_executor_ab("single",owner_mode=False,
                                        ci_authorized=False)

    def test_unsafe_setting_fails_closed(self):
        from p2_g07_ci_moving_goal import select_observer_executor_ab
        for value in ("MultiThreadedExecutor","2","--single","auto",""):
            if value=="":continue
            with self.assertRaises(ValueError):
                select_observer_executor_ab(value,owner_mode=True,
                                            ci_authorized=False)

    def test_actual_g07_node_switches_only_observer_not_cm_or_guard(self):
        s=SOURCE.read_text()
        self.assertIn('from rclpy.executors import SingleThreadedExecutor',s)
        self.assertIn('AXIA_G07_OBSERVER_EXECUTOR_AB',s)
        self.assertIn('SingleThreadedExecutor()',s)
        self.assertIn('MultiThreadedExecutor(num_threads=2 if owner_observer_parity else 3)',s)
        self.assertIn('AXIA_G07_OBSERVER_EXECUTOR_AB_SELECTED',s)
        self.assertNotIn('CM_TTL_SEC =',s)
        self.assertNotIn('stop_pub_timeout =',s)
        self.assertNotIn('RMW_IMPLEMENTATION=',s)


if __name__=="__main__":
    unittest.main()
