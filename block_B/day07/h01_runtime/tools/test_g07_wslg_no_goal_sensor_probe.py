"""Regression: new diagnostic can never turn non-clear/slow sensors into motion."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from g07_wslg_no_goal_sensor_probe import assess_window

def rows(front=.9,side=1.4,recv_gap=.1,stamp_gap=.1,n=23,near=.05):
    return [{"recv":float(i)*recv_gap+1.0,
             "stamp":float(i)*stamp_gap+1.0,
             "front":front,"side":side,"near":near,"beams":360}
            for i in range(n)]
def sample(front=.9,side=1.4,recv_gap=.1):
    return {"safety":rows(front,side,recv_gap),
            "raw":rows(front,side,recv_gap),
            "odom":[{"vx":0.0,"wz":0.0} for _ in range(6)],
            "clock":[1.0,1.1,1.2]}

class NoGoalReadOnlySensor(unittest.TestCase):
    def test_actual_337_near_beam_field_values_fail_closed(self):
        d=sample(.526377,.629360,.1)
        for k in ("raw","safety"):
            d[k]=rows(.526377,.629360,.1,n=337,near=1.0)
        r=assess_window(d)
        self.assertEqual(r["status"],"NO_GOAL_SENSOR_UNSAFE_HOLD")
        self.assertIn("OWNER_PREGOAL_NOT_CLEAR_BEFORE_FIXTURE",r["reasons"])
        self.assertTrue(r["metrics"]["safety"]["all_azimuths_near_unexplained"])
        self.assertEqual(r["metrics"]["safety"]["clear_count"],0)
        self.assertFalse(r["goal_sent"])

    def test_original_threshold_strict_and_300ms_receipt_ttl(self):
        good=assess_window(sample(.751,1.201,.1))
        self.assertEqual(good["status"],"NO_GOAL_SENSOR_WINDOW_CLEAR_CANDIDATE")
        for front,side in ((.75,1.3),(.8,1.2)):
            self.assertEqual(assess_window(sample(front,side))["status"],
                             "NO_GOAL_SENSOR_UNSAFE_HOLD")
        bad=assess_window(sample(.9,1.4,.819175))
        self.assertIn("SAFETY_RECEIPT_TTL_300MS_BLOCKED",bad["reasons"])
        self.assertGreater(bad["metrics"]["safety"]["max_receipt_gap_sec"],.3)

    def test_clock_missing_nonstationary_or_source_stale_hold(self):
        d=sample()
        d["clock"]=[1.0]
        self.assertIn("CLOCK_TIME_NOT_MONOTONIC",assess_window(d)["reasons"])
        d=sample()
        d["odom"][1]["vx"]=.1
        self.assertIn("ODOM_NOT_STATIONARY_NO_GOAL",assess_window(d)["reasons"])
        d=sample()
        d["raw"][3]["stamp"]=d["raw"][2]["stamp"]
        self.assertIn("RAW_SOURCE_STAMP_NOT_MONOTONIC",assess_window(d)["reasons"])

    def test_missing_samples_hold_and_no_authority_claim(self):
        d=sample()
        d["safety"]=d["safety"][:2]
        r=assess_window(d)
        self.assertEqual(r["status"],"NO_GOAL_SENSOR_UNSAFE_HOLD")
        self.assertFalse(r["goal_sent"])
        self.assertFalse(r["fixture_moved"])
        self.assertFalse(r["certified_estop"])
        self.assertFalse(r["owner_l3_accepted"])

    def test_no_goal_gui_load_matches_owner_after_nav2_readiness(self):
        src=(ROOT/"scripts/p2_no_goal_smoke_ci.sh").read_text()
        self.assertIn('|| "$SENSOR_NO_GOAL" == 1',src)
        self.assertIn('if [[ "$OWNER_MOVING" == 1 || "$CI_MOVING_GUI" == 1\\n   || "$SENSOR_NO_GOAL" == 1 ]];then',src)
        self.assertIn('setsid gz sim -g',src)
        self.assertIn('setsid rviz2 -d',src)
        self.assertIn('G07_WSLG_NO_GOAL_SENSOR_UNSAFE_HOLD',src)
        self.assertIn('QT_QPA_PLATFORM=xcb AXIA_P0_SIM_ONLY=1',src)
        self.assertNotIn('export AXIA_G07_CI_SIM_GOAL_ALLOWED=1',src)

    def test_same_original_world_no_noise_override_no_goal_gate(self):
        sh=(ROOT/"scripts/p2_no_goal_smoke_ci.sh").read_text()
        launch=(ROOT/"ros2_ws/src/axia_safety_bringup/launch/axia_tb3_p2.launch.py").read_text()
        self.assertIn('SENSOR_NO_GOAL="${AXIA_G07_OWNER_SENSOR_TRUTH_NO_GOAL:-0}"',sh)
        self.assertIn("G07_WSLG_SENSOR_NO_GOAL_AUTHORITY_DENIED",sh)
        self.assertIn("G07_WSLG_NO_GOAL_SENSOR_UNSAFE_HOLD",sh)
        self.assertIn('elif [[ "${AXIA_D07_H01_GUI_NO_GOAL:-0}" == 1 ]]; then',sh)
        self.assertIn("g07_wslg_no_goal_sensor_probe.py",sh)
        self.assertIn('sensor_no_goal = (',launch)
        self.assertIn('if not (h01 or owner or ci or sensor_no_goal):',launch)
        self.assertLess(sh.index('P2_NO_GOAL_STATIC_AND_RUNTIME_READINESS_OBSERVED'),
                        sh.index('if [[ "$SENSOR_NO_GOAL" == 1 ]]; then\n  duration='))

if __name__=="__main__":
    unittest.main()
