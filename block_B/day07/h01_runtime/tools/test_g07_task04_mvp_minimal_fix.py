"""Owner KwcTfR01 minimum regression; no ROS/Gazebo success inferred.

RED input: 402.019ms scan gap was diagnosed before exact UUID cancellation;
CLEAR->SLOW physical move was launched after an invisible 8.5cm cruise.
"""
import unittest
from pathlib import Path

RUNNER = Path(__file__).with_name("p2_g07_ci_moving_goal.py")


class MVPMinimumFix(unittest.TestCase):
    def test_clear_real_distance_gates_existing_slow_set_pose(self):
        text = RUNNER.read_text(encoding="utf-8")
        cleared = text.index('rows["clear"]=wait(phase("clear")')
        moved = text.index('wait(clear_motion_ready,8,"CLEAR_DISTANCE")')
        slow = text.index("slow_target=obstacle_world_pose(")
        self.assertLess(cleared, moved)
        self.assertLess(moved, slow)
        self.assertIn("CLEAR_MIN_TRAVEL_M = 0.12", text)

    def test_exact_uuid_cancel_precedes_unchanged_timing_oracle(self):
        text = RUNNER.read_text(encoding="utf-8")
        stopped = text.index('stop_dwell=wait(dwell,3.5,"ODOM_STOP_DWELL")')
        canceled = text.index("task03_goal=_task03_exact_goal_terminal(")
        assessed = text.index("verdict=assess(report,owner_authorized=")
        self.assertLess(stopped, canceled)
        self.assertLess(canceled, assessed)
        self.assertIn('report.update(goal_cancel_ack=True',text)

    def test_exception_cleanup_records_actual_cancel_not_fake_success(self):
        text=RUNNER.read_text(encoding="utf-8")
        self.assertIn('best_effort_cancel_attempted',text)
        self.assertIn('best_effort_cancel_failure',text)
        self.assertIn('first_failure_preserved',text)
        self.assertIn('report.update(status="BLOCKED"',text)


if __name__ == "__main__":
    unittest.main()
