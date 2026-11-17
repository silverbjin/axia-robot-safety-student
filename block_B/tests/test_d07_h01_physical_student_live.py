"""D07 physical student H01: exact real Gazebo Waffle + Nav2 Path + RViz.

Public student runtime is an allowlisted no-Goal teaching subset of the
verified Instructor source. Never distribute Instructor route answer/tests.
"""
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"block_B/day07"
RUNTIME=BASE/"h01_runtime"
ENTRY=BASE/"run_d07_h01_gazebo_rviz_student_once.sh"
GUIDE=BASE/"D07_H01_STUDENT_LIVE_DEMO_GUIDE_KO.md"

class StudentPhysicalH01(unittest.TestCase):
    def test_student_public_entry_has_real_physical_no_goal_contract(self):
        src=ENTRY.read_text()
        for s in ("--self-check", "--doctor", "--run",
                  "D07_H01_STUDENT_GAZEBO_RVIZ_L2",
                  "AXIA_D07_H01_GUI_NO_GOAL", "AXIA_P0_SIM_ONLY",
                  "AXIA_G07_CI_SIM_GOAL_ALLOWED=0", "p2_no_goal_smoke_ci.sh"):
            self.assertIn(s,src)
        self.assertNotIn("YES-P2-G07-GOAL",src)
        self.assertNotIn("axia-robot-safety-instructor.git",src)
        x=subprocess.run(["bash","-n",str(ENTRY)],capture_output=True,text=True)
        self.assertEqual(x.returncode,0,x.stderr)

    def test_public_runtime_has_real_gazebo_rviz_path_oracle(self):
        for p in ("scripts/p2_no_goal_smoke_ci.sh",
                  "scripts/p2_g07_shared_staged_startup.sh",
                  "tools/d07_h01_geometry_l2.py",
                  "tools/d07_h01_scene_broadcaster_overlay.py",
                  "tools/d07_h01_path_visual.py",
                  "tools/d07_h01_gpu_gui_watcher.sh",
                  "training/block_B/instructor/rviz/d07_h01_physical_replan.rviz",
                  "ros2_ws/src/axia_safety_bringup/launch/axia_tb3_p2.launch.py"):
            self.assertTrue((RUNTIME/p).is_file(),p)
        text=(RUNTIME/"tools/d07_h01_geometry_l2.py").read_text()
        self.assertIn("ComputePathToPose",text)
        self.assertIn("path_visual",text)

    def test_no_private_answers_or_secret_material(self):
        forbidden=("training/block_B/instructor/d07_route_reference.py",
                   "training/block_B/instructor/hidden_tests",
                   ".env","rclone.conf","credentials.json")
        for name in forbidden:
            self.assertFalse((RUNTIME/name).exists(),name)
        for p in RUNTIME.rglob("*"):
            if p.is_file():
                self.assertNotIn("BEGIN OPENSSH PRIVATE KEY",p.read_text(errors="replace"))

    def test_guide_explains_same_actual_gazebo_rviz_and_holds(self):
        s=GUIDE.read_text()
        for x in ("Gazebo Harmonic", "RViz2", "실제 Waffle",
                  "Before", "Intrusion", "Restored", "ComputePathToPose",
                  "NO_GOAL", "AXIA_MVP_DEMO_ACCEPTED=HOLD",
                  "run_d07_h01_gazebo_rviz_student_once.sh"):
            self.assertIn(x,s,x)

if __name__=="__main__":
    unittest.main()
