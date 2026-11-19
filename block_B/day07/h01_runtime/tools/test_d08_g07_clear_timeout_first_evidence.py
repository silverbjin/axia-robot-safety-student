"""D08/G07 actual CLEAR timeout first-boundary evidence RED→GREEN.

Static L0 contract: do not change safety TTL, moving speed thresholds,
Goal authority, or official Collision Monitor. If moving CLEAR fails,
capture bounded ROS Observer values rather than only the final RuntimeError.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/"tools/p2_g07_ci_moving_goal.py").read_text()

class TestFirstClearTimeoutEvidence(unittest.TestCase):
    def test_clear_in_existing_bounded_timeout_sampling(self):
        self.assertIn('if label in ("CLEAR","SLOW","STOP") and now-last_sample>=.35:',SOURCE)
        self.assertIn('"supervised_vx":snap.get("supervised_speed")',SOURCE)
        self.assertIn('"cm_vx":snap.get("pre_guard_speed")',SOURCE)
        self.assertIn('"final_vx":snap.get("final_speed")',SOURCE)
        self.assertIn('"guard_reason":g.get("reason")',SOURCE)
        self.assertIn('"_timeout_trace.json"',SOURCE)

    def test_fail_closed_no_moving_gate_relaxed(self):
        self.assertIn('raise RuntimeError("CI_MOVING_GOAL_TIMEOUT_"+label)',SOURCE)
        self.assertIn('for name,secs in (("clear",8),("slow",35),("stop",40)):',SOURCE)
        self.assertIn('condition=front>.75 and cm>.03 and final>.03',SOURCE)
        self.assertIn('if g.get("latched") is True:',SOURCE)

if __name__=="__main__":
    unittest.main()
