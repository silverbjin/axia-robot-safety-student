"""D13 public packaging/visualisation tests. Synthetic only, no ROS."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

DAY13=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(DAY13))
from run_lab import load_cases,evaluate_case,render_html,main

class D13Scaffold(unittest.TestCase):
    def test_fixture_eight_cases_and_sixteen_samples(self):
        items=load_cases()
        self.assertEqual(len(items),8)
        self.assertEqual(len(items[0]["robot_trajectory"]),16)
        self.assertEqual(round(items[0]["robot_trajectory"][-1]["t_sec"],2),13.1)
        self.assertEqual({x["expected"] for x in items},{"P","N","U"})

    def test_frame_mismatch_is_adapter_U_not_G09_TF(self):
        x=next(c for c in load_cases() if c["id"]=="U_frame_mismatch")
        result=evaluate_case(x)
        self.assertEqual(result["actual"],"U")
        self.assertEqual(result["reason"],"FRAME_MISMATCH_OR_UNKNOWN")

    def test_unknown_cases_return_U_with_TODO(self):
        # These test inputs are safety-relevant; they remain U even before learners fill TODO.
        for c in load_cases():
            if c["id"].startswith("U_"):
                with self.subTest(case=c["id"]):
                    self.assertEqual(evaluate_case(c)["actual"],"U")

    def test_viewer_offline_local_no_remote_script(self):
        c=load_cases()[0]
        text=render_html(c,evaluate_case(c))
        self.assertIn('id="step"',text)
        self.assertIn('id="robot"',text)
        self.assertIn('id="human"',text)
        self.assertIn("Math.hypot",text)
        self.assertNotIn("<script src=",text)
        self.assertNotIn("https://",text)

    def test_result_scope_is_explicit(self):
        result=evaluate_case(load_cases()[0])
        self.assertEqual(result["scope"],"SYNTHETIC_OFFLINE_L0_NOT_ROS_OR_GAZEBO")

if __name__=="__main__":
    unittest.main()
