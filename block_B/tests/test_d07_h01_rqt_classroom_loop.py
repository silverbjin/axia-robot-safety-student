"""D07-H01 classroom rqt_graph live-loop contract (L0).

Do not replace actual Gazebo/RViz L2 acceptance with these tests.
The original three-phase geometry and strict NO_GOAL admission stay intact.
"""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"block_B/day07"
RUNTIME=BASE/"h01_runtime"
LOOP=RUNTIME/"tools/d07_h01_classroom_replan_loop.py"
SMOKE=RUNTIME/"scripts/p2_no_goal_smoke_ci.sh"
ENTRY=BASE/"run_d07_h01_gazebo_rviz_student_once.sh"
GUIDE=BASE/"D07_H01_STUDENT_LIVE_DEMO_GUIDE_KO.md"

class D07H01RqtClassroomLoop(unittest.TestCase):
    def test_bounded_cycle_policy_no_moving_goal(self):
        spec=importlib.util.spec_from_file_location("d07_h01_classroom_replan_loop",LOOP)
        mod=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=mod
        spec.loader.exec_module(mod)
        self.assertEqual(mod.parse_cycle_limit("0"),0)
        self.assertEqual(mod.parse_cycle_limit("2"),2)
        for invalid in ("-1","999","abc","1.5",""," 1 "):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError): mod.parse_cycle_limit(invalid)
        src=LOOP.read_text()
        self.assertIn("ComputePathToPose",src)
        self.assertIn("/axia/d07/h01/path_visual",src)
        self.assertIn("/global_costmap/costmap",src)
        self.assertIn("/scan",src)
        self.assertIn("SIGINT",src)
        self.assertIn("classroom_replan_cycles.jsonl",src)
        self.assertIn("D07_H01_CLASSROOM_CYCLE_PASS",src)
        self.assertNotIn("NavigateToPose",src)
        self.assertNotIn('create_publisher(Twist',src)

    def test_original_runtime_invokes_loop_only_after_real_three_phases(self):
        src=SMOKE.read_text()
        first=src.index("D07_H01_GUI_H01_GEOMETRY_RETURNED_NO_GOAL")
        later=src.index("d07_h01_classroom_replan_loop.py")
        self.assertLess(first,later)
        self.assertIn('AXIA_D07_H01_CLASSROOM_LOOP',src)
        self.assertIn('AXIA_D07_H01_CLASSROOM_MAX_CYCLES',src)
        self.assertIn('classroom_loop.ready',src)
        self.assertIn("P2_L2_SMOKE_RC",src)
        self.assertEqual(subprocess.run(["bash","-n",str(SMOKE)]).returncode,0)

    def test_student_one_shot_no_goal_same_process_session(self):
        s=ENTRY.read_text()
        self.assertIn('export AXIA_D07_H01_CLASSROOM_LOOP="${AXIA_D07_H01_CLASSROOM_LOOP:-1}"',s)
        self.assertIn("AXIA_D07_H01_CLASSROOM_MAX_CYCLES",s)
        self.assertIn("Ctrl+C",s)
        self.assertNotIn("YES-P2-G07-GOAL",s)
        self.assertEqual(subprocess.run(["bash","-n",str(ENTRY)]).returncode,0)

    def test_rqt_three_layer_filter_guide_and_boundaries(self):
        t=GUIDE.read_text()
        for word in (
            "rqt_graph","ros-jazzy-rqt-graph","ros2 run rqt_graph rqt_graph",
            "Ctrl+C","인지와 계획","내비게이션과 제어","안전과 물리 증거",
            "Node","Topic","Refresh","/scan","/global_costmap/costmap",
            "/axia/d07/h01/path_visual","/compute_path_to_pose",
            "/cmd_vel_supervised","/cmd_vel_pre_guard","/axia/p2/base_guard",
            "/odom","/clock","gz topic -l","ROS_DOMAIN_ID=95",
            "ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST","goal_sent=false",
            "AXIA_MVP_DEMO_ACCEPTED=HOLD","NavigateToPose"):
            self.assertIn(word,t,word)
        self.assertNotIn("ros2 topic pub /cmd_vel",t)

if __name__=="__main__":
    unittest.main()
