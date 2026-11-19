"""Task04 one-runner shell integration: minimal no-ROS regression contracts."""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "scripts/p2_no_goal_smoke_ci.sh"

class OwnerMovingShellContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SHELL.read_text(encoding="utf-8")

    def test_bash_syntax(self):
        subprocess.run(["bash", "-n", str(SHELL)], check=True)

    def test_owner_never_borrows_github_ci_authority(self):
        self.assertIn("AXIA_G07_TASK04_OWNER_MOVING_L3", self.text)
        self.assertIn("GITHUB_ACTIONS", self.text)
        self.assertIn("AXIA_G07_OWNER_COMMON_RUNNER_AUTHORIZED", self.text)
        self.assertIn("AXIA_P2_OWNER_PINNED_SHA", self.text)

    def test_real_controlling_tty_phrase_before_one_goal(self):
        self.assertIn("YES-P2-G07-GOAL", self.text)
        self.assertRegex(self.text, r"read -r[^\n]*<\s*/dev/tty")
        self.assertIn('--owner-launch-pid "$LAUNCH_PID"', self.text)

    def test_owner_reuses_bag_shutdown_and_cm_exit(self):
        self.assertIn("AXIA_G07_CI_OWNER_BAG_PARITY", self.text)
        self.assertIn("p2_g07_ordered_shutdown.py", self.text)
        self.assertIn("p2_g07_owner_shutdown_audit.py", self.text)
        self.assertIn("g07_ordered_shutdown.json", self.text)

    def test_gui_single_gazebo_server_headless_client_only(self):
        self.assertIn("d07_h01_scene_broadcaster_overlay.py", self.text)
        self.assertIn("gz sim -g", self.text)
        self.assertIn("rviz2 -d", self.text)
        self.assertNotIn("pkill -f", self.text)

if __name__ == "__main__":
    unittest.main()
