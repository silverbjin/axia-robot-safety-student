"""Single MVP regression: one physical Goal, early CLEAR, then SLOW/STOP.

No ROS/Gazebo is mocked or claimed here; native L2 is the integration check.
"""
import unittest
from pathlib import Path

from p2_g07_ci_moving_goal_oracle import clear_action_evidence_valid

RUNNER = Path(__file__).with_name("p2_g07_ci_moving_goal.py")


class MVPStageSequence(unittest.TestCase):
    def test_clear_before_delayed_executing_ack_is_allowed_only_when_verified(self):
        self.assertTrue(clear_action_evidence_valid(None, True))
        self.assertTrue(clear_action_evidence_valid(1, True))
        self.assertTrue(clear_action_evidence_valid(2, True))
        for status in (None, 1, 2, 3, 4, 5, 6):
            self.assertFalse(clear_action_evidence_valid(status, False))
        for status in (0, 3, 4, 5, 6):
            self.assertFalse(clear_action_evidence_valid(status, True))

    def test_physical_slow_position_after_clear_before_slow_observation(self):
        source = RUNNER.read_text(encoding="utf-8")
        clear = source.index('rows["clear"]=wait(phase("clear")')
        executing = source.index('15,"ACTION_EXECUTING"')
        slow_ack = source.index('AXIA_G07_MVP_SLOW_PHYSICAL_FIXTURE_ACK')
        slow = source.index('rows["slow"]=wait(phase("slow")')
        self.assertLess(clear, executing)
        self.assertLess(executing, slow_ack)
        self.assertLess(slow_ack, slow)
        self.assertIn('plan_stop_fixture(', source)


if __name__ == "__main__":
    unittest.main()
