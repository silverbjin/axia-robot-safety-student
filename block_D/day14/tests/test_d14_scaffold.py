"""D14 fixture and policy visualisation scaffold: always GREEN independent of TODO."""
import sys
import unittest
from pathlib import Path

DAY=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(DAY))
from run_lab import load_cases,load_g10_events,replay,render_html

class D14StudentScaffold(unittest.TestCase):
    def test_policy_fixture_envelope(self):
        cases=load_cases()
        self.assertEqual(len(cases),16)
        self.assertEqual(len({c["id"] for c in cases}),16)
    def test_g10_event_order_and_no_actual_fault(self):
        events=load_g10_events()
        self.assertEqual(len(events),15)
        names=[x["event"] for x in events]
        self.assertEqual(names[:4],["GOAL_EXECUTING","ODOM_MOVING","SCAN_FAULT","CM_LOST"])
        self.assertIn("RESET_REJECTED_ACTIVE_FAULT",names)
        self.assertEqual(names[-1],"NO_AUTO_RESUME")
    def test_figure_contains_normal_limited_and_no_auto_clear(self):
        cases=load_cases()
        data=[replay(x) for x in cases]
        view=render_html(cases,data,load_g10_events())
        self.assertIn("NORMAL_POLICY",view)
        self.assertIn("LIMITED_REQUEST",view)
        self.assertIn("해제 금지",view)
        self.assertNotIn("<script src=",view)
        self.assertNotIn("http://",view)
        self.assertNotIn("https://",view)
    def test_every_result_explicitly_synthetic(self):
        for case in load_cases():
            self.assertEqual(replay(case)["verification"],"OFFLINE_SYNTHETIC_L0_NOT_REAL_SUPERVISOR_OR_GAZEBO")
    def test_no_cmd_vel_or_ros_dependencies(self):
        for f in (DAY/"risk_policy_student.py",DAY/"run_lab.py"):
            text=f.read_text()
            self.assertNotIn("import rclpy",text)
            self.assertNotIn("create_publisher(",text)
            self.assertNotIn("send_goal_async(",text)

if __name__=="__main__":
    unittest.main()
