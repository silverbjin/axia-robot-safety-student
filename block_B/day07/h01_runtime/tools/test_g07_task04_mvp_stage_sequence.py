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



    def test_historical_slow_negative_speed_and_heading_turn_remains_hold(self):
        from p2_g07_ci_stop_stage import classify_slow_fixture_alignment
        # Actual #44871515361 Cycle2: 97 SLOW samples; forward vx negative
        # when front was 0.6776m, eventual yaw 1.520 rad and no SLOW pass.
        d=classify_slow_fixture_alignment(
            start_pose=(0.,0.,0.), live_odom=(0.1248,0.006,0.1257),
            odom_speed=-0.00252508298, odom_yaw_rate=0.045,
            supervised_speed=-0.01668697596, goal_status=2, guard_latched=False)
        self.assertEqual(d["status"],"FORWARD_ALIGNMENT_NOT_PROVEN_HOLD")
        self.assertFalse(d["aligned_for_positive_slow_demo"])
        self.assertAlmostEqual(d["yaw_change_rad"],0.1257)
        self.assertFalse(d["root_cause_proven"])
        self.assertEqual(d["release"],"HOLD")
        self.assertFalse(d["certified_estop"])

    def test_slow_alignment_is_diagnostic_never_changes_speed_or_goal(self):
        from p2_g07_ci_stop_stage import classify_slow_fixture_alignment
        d=classify_slow_fixture_alignment(
            start_pose=(0.,0.,0.),live_odom=(0.125,0.,0.01),
            odom_speed=0.08, odom_yaw_rate=0.01,
            supervised_speed=0.08, goal_status=2, guard_latched=False)
        self.assertEqual(d["status"],"FORWARD_ALIGNMENT_CANDIDATE_ONLY")
        self.assertTrue(d["aligned_for_positive_slow_demo"])
        self.assertFalse(d["timing_safety_pass"])
        self.assertEqual(d["release"],"HOLD")
        src=RUNNER.read_text()
        self.assertIn('classify_slow_fixture_alignment(',src)
        self.assertIn('"slow_fixture_alignment_before_move"',src)
        self.assertLess(src.index('classify_slow_fixture_alignment('),
                        src.index('slow_ack=move_ci_verified('))
        self.assertIn('rows["slow"]=wait(phase("slow")',src)


    def test_physical_slow_fixture_waits_for_fresh_forward_alignment_before_set_pose(self):
        # Actual native #44871515361 and #44877524595 SLOW attempts:
        # negative/near-zero forward speed during Nav2 rotation cannot prove
        # 0.4–0.75m positive command and CM SLOW reduction.
        src=RUNNER.read_text()
        cleared=src.index('wait(clear_motion_ready,8,"CLEAR_DISTANCE")')
        admission=src.index('wait(slow_forward_alignment_ready,3,"SLOW_FORWARD_ALIGNMENT")')
        slow_ack=src.index('slow_ack=move_ci_verified(')
        slow_obs=src.index('rows["slow"]=wait(phase("slow")')
        self.assertLess(cleared,admission)
        self.assertLess(admission,slow_ack)
        self.assertLess(slow_ack,slow_obs)
        self.assertIn('_fresh(s,("scan","odom","guard","clock",',src)
        self.assertIn('classify_slow_fixture_alignment(',src)
        self.assertIn('"slow_fixture_alignment_before_move"',src)
        self.assertNotIn('SLOW_REQUIREMENT_RELAXED',src)
        self.assertNotIn('NAV2_NEW_GOAL_FOR_ALIGNMENT',src)


    def test_native_first_slow_aligned_live_heading_despite_accumulated_path_turn(self):
        # Actual native #44901777431 C1: odom vx=0.014034, wz=0.00558,
        # supervisor vx=0.043752, cumulative yaw since Goal=0.21088.
        # The same physical cylinder is projected from the robot CURRENT pose.
        # Cumulative path rotation is not current yaw/angular motion.
        from p2_g07_ci_stop_stage import classify_slow_fixture_alignment
        candidate=classify_slow_fixture_alignment(
            start_pose=(0.,0.,0.),live_odom=(0.16,0.03,0.21088),
            odom_speed=0.014034,odom_yaw_rate=0.00558,
            supervised_speed=0.043752,goal_status=2,guard_latched=False)
        self.assertTrue(candidate["aligned_for_positive_slow_demo"],candidate)
        self.assertEqual(candidate["status"],"FORWARD_ALIGNMENT_CANDIDATE_ONLY")
        self.assertAlmostEqual(candidate["yaw_change_rad"],0.21088)
        turning=classify_slow_fixture_alignment(
            start_pose=(0.,0.,0.),live_odom=(0.16,0.03,0.21),
            odom_speed=0.014,odom_yaw_rate=0.08,
            supervised_speed=0.044,goal_status=2,guard_latched=False)
        self.assertFalse(turning["aligned_for_positive_slow_demo"])
        reversing=classify_slow_fixture_alignment(
            start_pose=(0.,0.,0.),live_odom=(0.16,0.03,0.21),
            odom_speed=-0.014,odom_yaw_rate=0.005,
            supervised_speed=0.044,goal_status=2,guard_latched=False)
        self.assertFalse(reversing["aligned_for_positive_slow_demo"])

if __name__ == "__main__":
    unittest.main()
