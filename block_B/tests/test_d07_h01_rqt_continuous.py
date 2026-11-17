"""RED→GREEN: student H01 rqt_graph classroom loop, no robot Goal.

No ROS required in L0. Tests actual packaged source contracts and the pure
four-stage placement policy; public Gazebo L2 verifies real messages separately.
"""
from pathlib import Path
import importlib.util
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"block_B/day07"
RUNTIME=BASE/"h01_runtime"
TOOL=RUNTIME/"tools/d07_h01_teaching_loop.py"
WRAPPER=BASE/"run_d07_h01_gazebo_rviz_student_once.sh"
SMOKE=RUNTIME/"scripts/p2_no_goal_smoke_ci.sh"
GUIDE=BASE/"D07_H01_STUDENT_LIVE_DEMO_GUIDE_KO.md"
CI=ROOT/".github/workflows/d07-h01-student-physical-gazebo-rviz-l2.yml"


class D07H01RqtContinuous(unittest.TestCase):
    def test_loop_exact_world_positions_and_stationary_scope(self):
        sys.path.insert(0,str(RUNTIME/"tools"))
        spec=importlib.util.spec_from_file_location("teaching_loop",TOOL)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        p=mod.teaching_positions((-1.85,.15),(-1.1,.0))
        self.assertEqual([x[0] for x in p],["free","intrusion","lateral","restored"])
        self.assertEqual(p[0][1:],(-1.1,.0))
        self.assertEqual(p[1][1:],(-1.85,.15))
        self.assertEqual(p[-1][1:],(-1.1,.0))
        self.assertNotEqual(p[1][1:],p[2][1:])
        with self.assertRaises(ValueError):mod.teaching_positions((-3.7,2.0),(-1.1,0))
        with self.assertRaises(ValueError):mod.teaching_positions((-1.85,.15),(5.0,0))
        self.assertFalse(hasattr(mod,"send_navigate_to_pose"))

    def test_cli_exposes_bounded_ci_cycle_but_unbounded_local_ctrl_c(self):
        t=TOOL.read_text()
        s=SMOKE.read_text()
        w=WRAPPER.read_text()
        self.assertIn("D07_H01_TEACHING_CYCLE",t)
        self.assertIn("D07_H01_TEACHING_CTRL_C_STOP",t)
        self.assertIn("signal.SIGINT",t)
        self.assertIn("ComputePathToPose",t)
        self.assertIn("D07_H01_TEACHING_MAX_CYCLES",s)
        self.assertIn("AXIA_D07_H01_TEACHING_LOOP",w)
        self.assertIn("GITHUB_ACTIONS",t)
        self.assertIn("AXIA_G07_CI_SIM_GOAL_ALLOWED=0",w)
        self.assertNotIn("NavigateToPose.Goal(",t)
        self.assertNotIn("create_publisher(Twist",t)
        for script in (WRAPPER,SMOKE):
            p=subprocess.run(["bash","-n",str(script)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)

    def test_classroom_stop_uses_existing_managed_26s_shutdown_budget(self):
        # Actual public L2 #44063399501: all 4 real physical positions and
        # official Nav2 paths PASSED; only 10s launch exit budget timed out.
        # G07_MANAGED_LAUNCH_EXIT_GRACE_SEC=26 already exists; reuse it ONLY
        # in the H01 no-moving-Goal classroom lane, never change CM/Scan TTL.
        src=SMOKE.read_text()
        start=src.index("   local launch_grace_steps=25")
        end=src.index("   for ((i=0;i<launch_grace_steps;i++));",start)
        teardown=src[start:end]
        self.assertIn('AXIA_D07_H01_TEACHING_LOOP',teardown)
        self.assertIn('G07_MANAGED_LAUNCH_EXIT_GRACE_SEC * 5 / 2',teardown)
        self.assertIn('AXIA_D07_H01_GUI_NO_GOAL',teardown)

    def test_three_rqt_graph_filter_layers_are_explained_and_readonly(self):
        doc=GUIDE.read_text()
        for required in ("rqt_graph","인지·계획","네비게이션·제어",
                         "안전·물리 증거","Nodes/Topics (all)","/scan",
                         "/global_costmap/costmap","/axia/d07/h01/path_visual",
                         "/cmd_vel_supervised","/cmd_vel_pre_guard",
                         "/axia/p2/base_guard","/odom","/clock",
                         "Ctrl+C","토픽 필터","노드 필터","GZ_PARTITION",
                         "gazebo","ROS_DOMAIN_ID=95","NO_GOAL"):
            self.assertIn(required,doc,required)
        self.assertIn("ros-jazzy-rqt-graph",doc)

    def test_rqt_live_log_is_not_hashed_before_ci_gui_closes(self):
        # Actual merged student main L2 #44066252082 was SUCCESS with native
        # sensors/Path/62+ original hashes, but zip rqt_graph.log changed after
        # wrapper manifest: Xvfb exited while rqt GUI process was still alive.
        w=WRAPPER.read_text()
        ci=CI.read_text()
        self.assertIn('! -name rqt_graph.log',w)
        self.assertIn('setsid bash -c',ci)
        self.assertIn('kill -INT -- "-$RQT_PID"',ci)
        self.assertIn('wait "$RQT_PID"',ci)
        cleanup=ci[ci.index('cleanup_gui() {'):ci.index("trap cleanup_gui EXIT")]
        self.assertLess(cleanup.index('kill -INT -- "-$RQT_PID"'),
                        cleanup.index('kill "$XVPID"'))
        self.assertIn('student_live_stdout.log',w)

    def test_ctrl_c_shutdown_does_not_shutdown_an_already_shutdown_ros_context(self):
        # Owner WSL2 L3 2026-11-17 first teardown fault:
        # RCLError: rcl_shutdown already called on the given context.
        # Verify the shutdown boundary without running real ROS in L0.
        sys.path.insert(0,str(RUNTIME/"tools"))
        spec=importlib.util.spec_from_file_location("teaching_loop_sigint",TOOL)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        class Stub:
            def __init__(self,alive):
                self.alive=alive
                self.count=0
            def ok(self): return self.alive
            def shutdown(self):
                if not self.alive: raise RuntimeError("rcl_shutdown already called")
                self.alive=False
                self.count+=1
        already_dead=Stub(False)
        self.assertFalse(mod.shutdown_rclpy_once(already_dead))
        self.assertEqual(already_dead.count,0)
        alive=Stub(True)
        self.assertTrue(mod.shutdown_rclpy_once(alive))
        self.assertEqual(alive.count,1)
        self.assertFalse(mod.shutdown_rclpy_once(alive))
        self.assertEqual(alive.count,1)
        source=TOOL.read_text()
        self.assertIn("shutdown_rclpy_once(rclpy)",source)

    def test_open_xvfb_log_is_not_hashed_while_display_is_alive(self):
        # ZIP rehash of actual L2 #44067733098: closed 61/61 raw files
        # matched, but OUTER Xvfb.log changed after wrapper SHA256SUMS.
        # Only CI-owned still-open logs are exempt, not native evidence.
        w=WRAPPER.read_text()
        ci=CI.read_text()
        self.assertIn('! -name xvfb.log',w)
        self.assertIn('D07_H01_OPEN_XVFB_GUI_LOG_IN_SHA_MANIFEST_DENIED',ci)
        self.assertIn('sha256sum -c SHA256SUMS',ci)
        self.assertIn('! -name rqt_graph.log',w)
        self.assertIn('student_live_stdout.log',w)

    def test_h01_official_world_xacro_finishes_before_gazebo_server_starts(self):
        # Public student MAIN L2 #44084070517: first native failure was
        # [gz] unable to find /tmp/nav2_*.sdf exit255; CLOCK_MISSING secondary.
        # Official Jazzy launches xacro/gz as independent ExecuteProcess.
        # Scope serialized startup ONLY to H01 physical NO_GOAL sim.
        src=(RUNTIME/"ros2_ws/src/axia_safety_bringup/launch/axia_tb3_p2.launch.py").read_text()
        self.assertIn("AXIA_D07_H01_GUI_NO_GOAL",src)
        self.assertIn("AXIA_G07_CI_SIM_GOAL_ALLOWED",src)
        self.assertIn("AXIA_P0_SIM_ONLY",src)
        self.assertIn("OnProcessExit",src)
        self.assertIn("target_action=world_xacro",src)
        self.assertIn("on_exit=[gazebo_server]",src)
        self.assertIn("RegisterEventHandler",src)
        self.assertIn("D07_H01_OFFICIAL_WORLD_PROCESS_SHAPE_CHANGED",src)
        self.assertIn("d.entities.insert(d.entities.index(world_xacro),",src)
        self.assertLess(src.index("d.entities.insert(d.entities.index(world_xacro),"),
                        src.index("RegisterEventHandler(OnProcessExit"))
        self.assertNotIn("time.sleep(",src)

    def test_public_ci_runs_actual_rqt_window_and_one_bounded_loop(self):
        w=CI.read_text()
        for expected in ("ros-jazzy-rqt-graph",
                         "AXIA_D07_H01_TEACHING_LOOP",
                         "AXIA_D07_H01_TEACHING_MAX_CYCLES",
                         "D07_H01_TEACHING_CYCLE",
                         "rqt_graph","D07_H01_STUDENT_REAL_GAZEBO_RVIZ_XVFB_L2_PASS_NO_GOAL"):
            self.assertIn(expected,w,expected)


if __name__=="__main__":
    unittest.main()
