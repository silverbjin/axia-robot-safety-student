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

    def test_container_git_source_sha_uses_process_scoped_safe_directory(self):
        # Actual public L2 #44039011558: git -C nested runtime returned rc128
        # before launching Gazebo (GitHub runner mount ownership mismatch).
        s=ENTRY.read_text()
        self.assertIn("GIT_CONFIG_COUNT=1",s)
        self.assertIn("GIT_CONFIG_KEY_0=safe.directory",s)
        self.assertIn("GIT_CONFIG_VALUE_0",s)
        self.assertNotIn("git config --global",s)

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

    def test_all_private_runtime_python_dependencies_are_present_publicly(self):
        # Actual PUBLIC L2 #44039481753: official launch could not import
        # p2_zone_overlay. Catch ALL same-tree H01 modules BEFORE real Gazebo.
        import ast
        module_paths=(
            list((RUNTIME/"tools").glob("*.py"))+
            list((RUNTIME/"ros2_ws/src/axia_safety_bringup/launch").glob("*.py"))
        )
        names={p.stem for p in module_paths}
        missing={}
        for path in module_paths:
            refs=set()
            for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(n,ast.Import):
                    refs.update(x.name.split(".")[0] for x in n.names)
                if isinstance(n,ast.ImportFrom) and n.module:
                    refs.add(n.module.split(".")[0])
            # Standard and ROS package imports are outside this copied tree;
            # these exact prefixes name local H01/P0/P1/P2 helper modules.
            required={x for x in refs if x.startswith(
                ("p0_","p1_","p2_","d07_h01_","axia_p0_","axia_p1_","axia_p2_"))}
            diff=required-names
            if diff: missing[path.name]=sorted(diff)
        self.assertFalse(missing,missing)

    def test_no_private_answers_or_secret_material(self):
        forbidden=("training/block_B/instructor/d07_route_reference.py",
                   "training/block_B/instructor/hidden_tests",
                   ".env","rclone.conf","credentials.json")
        for name in forbidden:
            self.assertFalse((RUNTIME/name).exists(),name)
        for p in RUNTIME.rglob("*"):
            if p.is_file():
                self.assertNotIn("BEGIN OPENSSH PRIVATE KEY",p.read_text(errors="replace"))

    def test_actual_l2_stage_ledger_schema_regression(self):
        # Real public Gazebo L2 #44040221819: all 3 physical stages passed,
        # but student wrapper misread the original 'stage' key as 'phase'.
        # Keep original instructor evidence format unchanged.
        source=ENTRY.read_text(encoding="utf-8")
        workflow=(ROOT/".github/workflows/d07-h01-student-physical-gazebo-rviz-l2.yml").read_text()
        self.assertIn('r.get("stage")',source)
        self.assertIn('r.get("stage")',workflow)
        self.assertNotIn('r.get("phase")',source)
        self.assertNotIn('r.get("phase")',workflow)

    def test_real_l2_native_teardown_stops_executor_before_ros_destroy(self):
        # Actual public L2 #44040942877 completed all physical H01 stages,
        # then sporadically SIGABRT ("terminate called without an active
        # exception") on interpreter teardown after reporter printed READY.
        # Static contract keeps async worker quiesced before destroying ROS.
        src=(RUNTIME/"tools/d07_h01_geometry_l2.py").read_text()
        tail=src[src.rfind("    finally:\n        if moved:"):]
        self.assertIn("D07_H01_GEOMETRY_EXECUTOR_QUIESCENT",tail)
        self.assertIn("th.join(",tail)
        self.assertIn("th.is_alive()",tail)
        self.assertLess(tail.index("executor.shutdown("),
                        tail.index("node.destroy_subscription(scan_sub)"))
        self.assertLess(tail.index("th.join("),
                        tail.index("node.destroy_subscription(scan_sub)"))

    def test_checksum_manifest_excludes_live_ci_stdout_and_is_verified(self):
        # CI artifact #44042258675: 62/63 SHA matched, only live_stdout.log
        # was still growing in the workflow stdout redirect during hashing.
        # The successful, CLOSED runtime log remains hash-covered.
        wrapper=ENTRY.read_text(encoding="utf-8")
        workflow=(ROOT/".github/workflows/d07-h01-student-physical-gazebo-rviz-l2.yml").read_text()
        self.assertIn("! -name live_stdout.log", wrapper)
        self.assertIn("sha256sum -c SHA256SUMS", workflow)
        self.assertNotIn("grep -Fq 'live_stdout.log' SHA256SUMS",workflow)
        self.assertIn("grep -Eq '[[:space:]]+\\./live_stdout\\.log

    def test_guide_explains_same_actual_gazebo_rviz_and_holds(self):
        s=GUIDE.read_text()
        for x in ("Gazebo Harmonic", "RViz2", "실제 Waffle",
                  "Before", "Intrusion", "Restored", "ComputePathToPose",
                  "NO_GOAL", "AXIA_MVP_DEMO_ACCEPTED=HOLD",
                  "run_d07_h01_gazebo_rviz_student_once.sh"):
            self.assertIn(x,s,x)

if __name__=="__main__":
    unittest.main()
",workflow)
        self.assertIn("student_live_stdout.log", wrapper)

    def test_guide_explains_same_actual_gazebo_rviz_and_holds(self):
        s=GUIDE.read_text()
        for x in ("Gazebo Harmonic", "RViz2", "실제 Waffle",
                  "Before", "Intrusion", "Restored", "ComputePathToPose",
                  "NO_GOAL", "AXIA_MVP_DEMO_ACCEPTED=HOLD",
                  "run_d07_h01_gazebo_rviz_student_once.sh"):
            self.assertIn(x,s,x)

if __name__=="__main__":
    unittest.main()
