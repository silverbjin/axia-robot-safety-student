"""D06 NO_GOAL Gazebo server shutdown race: RED->GREEN contract.
No ROS/Gazebo; synthetic process-exit launch lines only.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"block_B/day07/h01_runtime"
HELPER=RUNTIME/"tools/g07_gazebo_server_exit_guard.sh"
OWNER=RUNTIME/"scripts/p2_no_goal_smoke_ci.sh"

class D06GazeboNativeStopDrain(unittest.TestCase):
    def test_healthy_exit_marker_proves_child_only(self):
        with tempfile.TemporaryDirectory() as td:
            log=Path(td)/"launch.log"
            log.write_text("[INFO] [gz-21]: process has finished cleanly [pid 19280]\n")
            p=subprocess.run(["bash",str(HELPER),"--wait",str(log),"2"],
                             capture_output=True,text=True,timeout=6)
            self.assertEqual(p.returncode,0,(p.stdout,p.stderr))
            self.assertIn("G07_GAZEBO_SERVER_NATIVE_EXIT0_BEFORE_GROUP_SIGINT",p.stdout)

    def test_abnormal_exit_is_hold_not_success(self):
        with tempfile.TemporaryDirectory() as td:
            log=Path(td)/"launch.log"
            log.write_text("[ERROR] [gz-21]: process has died [pid 19280, exit code -11, cmd 'gz sim -s']\n")
            p=subprocess.run(["bash",str(HELPER),"--wait",str(log),"2"],
                             capture_output=True,text=True,timeout=6)
            self.assertEqual(p.returncode,3,(p.stdout,p.stderr))
            self.assertIn("G07_GAZEBO_SERVER_NATIVE_SIGSEGV_BEFORE_GROUP_SIGINT_HOLD",p.stdout+p.stderr)

    def test_ack_without_native_exit0_is_not_success(self):
        with tempfile.TemporaryDirectory() as td:
            log=Path(td)/"launch.log"
            log.write_text("G07_NO_GOAL_GAZEBO_SERVER_STOP_ACK_BEFORE_SIGINT\n")
            p=subprocess.run(["bash",str(HELPER),"--wait",str(log),"1"],
                             capture_output=True,text=True,timeout=5)
            self.assertEqual(p.returncode,3,(p.stdout,p.stderr))
            self.assertIn("G07_GAZEBO_SERVER_NATIVE_EXIT0_TIMEOUT_HOLD",p.stdout+p.stderr)

    def test_stop_is_observed_before_group_sigint(self):
        s=OWNER.read_text()
        self.assertIn('tools/g07_gazebo_server_exit_guard.sh',s)
        self.assertIn("G07_GAZEBO_SERVER_WAIT_NATIVE_EXIT0_BEFORE_GROUP_SIGINT",s)
        self.assertLess(s.index("G07_GAZEBO_SERVER_WAIT_NATIVE_EXIT0_BEFORE_GROUP_SIGINT"),
                        s.index('kill -INT -- "-$LAUNCH_PID"'))
        self.assertIn("G07_NO_GOAL_GAZEBO_SERVER_NATIVE_EXIT0_HOLD",s)
        self.assertIn("P2_L2_GRACEFUL_TEARDOWN",s)
        self.assertNotIn("MESA_D3D12_DEFAULT_ADAPTER_NAME=",s)

    def test_helper_is_readonly_and_no_simulation(self):
        s=HELPER.read_text()
        for f in ("G07_GAZEBO_SERVER_NATIVE_EXIT0_BEFORE_GROUP_SIGINT",
                  "G07_GAZEBO_SERVER_NATIVE_SIGSEGV_BEFORE_GROUP_SIGINT_HOLD",
                  "G07_GAZEBO_SERVER_NATIVE_EXIT0_TIMEOUT_HOLD"):
            self.assertIn(f,s)
        for bad in ("gz sim","ros2 launch","kill -INT","kill -TERM","sysctl -w","apt-get"):
            self.assertNotIn(bad,s)

if __name__=="__main__":unittest.main()
