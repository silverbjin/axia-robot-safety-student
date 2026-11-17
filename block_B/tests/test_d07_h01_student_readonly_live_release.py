"""D07 student *public* H01 companion regression. No ROS during L0.

This checks the independently runnable official Nav2 L1, NOT instructor's
private physical Gazebo H01. Student TODO is intentionally left RED.
"""
from pathlib import Path
import json
import re
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/"block_B/day07/run_d07_student_live_once.sh"
GUIDE=ROOT/"block_B/day07/D07_H01_STUDENT_LIVE_DEMO_GUIDE_KO.md"
TODO=ROOT/"block_B/day07/route_todo.py"
PIN="158b7c6032d987177d1e1302bf85fd741120fd9e"


class StudentD07H01LiveContract(unittest.TestCase):
    def test_guide_exists_and_separates_l1_from_physical_h01(self):
        txt=GUIDE.read_text(encoding="utf-8")
        for needle in ("실제 Gazebo", "훈련생 독립 실행", "공식 Nav2",
                       "ComputePathToPose", "NavigateToPose",
                       "Before", "Intrusion", "Restored",
                       "L1", "L2", "L3", "VISUAL_HOLD",
                       "goal_sent=false", "AXIA_MVP_DEMO_ACCEPTED=HOLD",
                       "ROS_DOMAIN_ID=95", "NO_GOAL",
                       "run_d07_student_live_once.sh",
                       "D07_STUDENT_NAV2_L1_REAL_PASS"):
            self.assertIn(needle,txt,needle)
        self.assertNotIn("YES-P2-G07-GOAL",txt)
        self.assertNotIn("ros2 topic pub /cmd_vel",txt)

    def test_student_script_is_readonly_and_source_sha_pinned(self):
        src=RUN.read_text(encoding="utf-8")
        self.assertIn(PIN,src)
        self.assertIn("d07/scripts/d07_nav2_planner_l1.py",src)
        self.assertIn("d07/params/nav2_d07_planner.yaml",src)
        self.assertIn("PASS_OFFICIAL_NAV2_COSTMAP_REPLAN_L1",src)
        self.assertIn("gazebo_actual",src)
        self.assertIn("navigate_to_pose_sent",src)
        self.assertIn("cmd_vel_published",src)
        self.assertNotIn("YES-P2-G07-GOAL",src)
        self.assertNotIn("ros2 action send_goal",src)
        self.assertNotIn("ros2 topic pub /cmd_vel",src)
        self.assertNotIn("axia-robot-safety-instructor.git",src)
        self.assertIn("D07_STUDENT_NAV2_L1_REAL_PASS",src)

    def test_script_shell_syntax_and_genuine_static_mode(self):
        syntax=subprocess.run(["bash","-n",str(RUN)],capture_output=True,text=True)
        self.assertEqual(syntax.returncode,0,syntax.stderr)
        x=subprocess.run(["bash",str(RUN),"--self-check"],
                         capture_output=True,text=True,timeout=12)
        self.assertEqual(x.returncode,0,x.stdout+x.stderr)
        self.assertIn("NAV2_NOT_RUN_GAZEBO_NOT_RUN",x.stdout)

    def test_existing_two_todos_remain_student_owned(self):
        src=TODO.read_text(encoding="utf-8")
        self.assertIn("TODO_D07_ROUTE_OBSTACLE",src)
        self.assertIn("TODO_D07_REPLAN_EVIDENCE",src)
        self.assertFalse((ROOT/"block_B/day07/d07_route_reference.py").exists())


if __name__=="__main__":
    unittest.main()
