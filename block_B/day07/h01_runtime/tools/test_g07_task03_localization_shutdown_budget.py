"""G07 Task03: actual post-STOP Nav2 localization shutdown 13s response timeout.

Original public Gazebo #44221460587: physical STOP/odom dwell PASS,
exact Goal CANCELED PASS, Navigation lifecycle ACK TRUE,
Localization ManageLifecycleNodes response missed old 13s arbitrary ceiling.
This isolated *post-cancel* lifecycle response budget MUST NOT modify
CM120, Guard150, Scan300, source_timeout, polygon, or command control.
"""
import inspect
import unittest

from p2_g07_ordered_shutdown import shutdown_stage_budget
import p2_g07_ordered_shutdown as ordered


class BoundedPostGoalLocalizationShutdown(unittest.TestCase):
    def test_real_localization_response_old_13s_boundary_extended_only_to_30s(self):
        self.assertEqual(shutdown_stage_budget("localization",60.0),30.0)
        self.assertEqual(shutdown_stage_budget("localization",32.0),30.0)
        self.assertEqual(shutdown_stage_budget("localization",18.0),18.0)
        self.assertEqual(shutdown_stage_budget("localization",0.005),0.01)

    def test_navigation_stage_and_total_budget_remain_unchanged(self):
        self.assertEqual(shutdown_stage_budget("navigation",60.0),40.0)
        self.assertEqual(shutdown_stage_budget("navigation",15.0),15.0)
        source=inspect.getsource(ordered.run)
        self.assertIn("deadline = monotonic() + limit",source)
        self.assertIn('shutdown_stage_budget(key, deadline-monotonic())',source)
        self.assertIn('ack["status"]!="ACK"',source)

    def test_invalid_manager_does_not_skip_real_ack(self):
        for bad in ("cm","monitor","goal",None):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                shutdown_stage_budget(bad,45.0)


if __name__=="__main__":
    unittest.main()
