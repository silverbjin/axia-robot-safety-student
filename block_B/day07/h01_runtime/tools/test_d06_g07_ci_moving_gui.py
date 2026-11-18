"""D06 experimental CI display profile must leave proven G07 safety untouched."""
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
SMOKE=ROOT/"scripts/p2_no_goal_smoke_ci.sh"

class D06CIIntegratedVisual(unittest.TestCase):
    def test_syntax(self):
        p=subprocess.run(["bash","-n",str(SMOKE)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)

    def test_xvfb_ci_only_admission(self):
        s=SMOKE.read_text()
        self.assertIn('AXIA_D06_G07_CI_MOVING_GUI:-0',s)
        self.assertIn('GITHUB_ACTIONS:-',s)
        self.assertIn('AXIA_G07_CI_SIM_GOAL_ALLOWED:-0',s)
        self.assertIn('AXIA_G07_TASK03_FORMAL_CI:-0',s)
        self.assertIn('D06_G07_CI_GUI_SCOPE_DENIED_NO_GOAL',s)
        self.assertIn('-n "${DISPLAY:-}"',s)

    def test_default_headless_unchanged_gui_optin_before_launch(self):
        s=SMOKE.read_text()
        self.assertIn('LAUNCH_ARGS=(headless:=True use_rviz:=False',s)
        self.assertIn("LAUNCH_ARGS[0]='headless:=False'",s)
        self.assertIn('D06_G07_CI_MOVING_GUI_SINGLE_OFFICIAL_GAZEBO_RENDER_WINDOW',s)
        self.assertLess(s.index("LAUNCH_ARGS[0]='headless:=False'"),
                        s.index('setsid ros2 launch "$LAUNCH"'))

    def test_existing_goal_and_safety_oracles_unchanged(self):
        s=SMOKE.read_text()
        self.assertIn('python3 tools/p2_g07_ci_moving_goal.py',s)
        self.assertIn('python3 tools/p2_g07_ordered_shutdown.py',s)
        self.assertIn('G07_MOVING_GOAL_CM_CLEAN_EXIT_AFTER_NAV2_ACK_PASS',s)
        self.assertNotIn('export GITHUB_ACTIONS=true',s)
        self.assertNotIn('AXIA_G07_CI_SIM_GOAL_ALLOWED=1',s)
        self.assertNotIn('AXIA_D06_G07_CI_MOVING_GUI=1',s)

if __name__=="__main__":
    unittest.main()
