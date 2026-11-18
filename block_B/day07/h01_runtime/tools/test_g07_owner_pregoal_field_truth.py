"""User WSL2 first PRE-GOAL unsafe LiDAR boundary, without ROS/Goal.

The immutable user's raw ROS bag was read locally; ONLY derived numeric
measurements are used here. CI cannot reproduce actual WSLg GPU rendering.
"""
import tempfile
import unittest
from pathlib import Path

from p2_g07_owner_pregoal_l2 import diagnose_pregoal_baseline, near_ring_fraction

class FieldPregoalTruth(unittest.TestCase):
    def test_actual_owner_scan_must_block_without_fixture_or_goal(self):
        # user TAR: /safety/scan 337/337 non-clear, median front=0.526m,
        # median side=0.629m, 100% of all valid beams within [0.4,0.85]m.
        result=diagnose_pregoal_baseline(front_m=.526377,side_m=.629360,
                                         valid_beams=360,near_fraction=1.0,
                                         scan_count=337)
        self.assertEqual(result["status"],"NO_GOAL_BASELINE_UNSAFE")
        self.assertEqual(result["reason"],"FRONT_AND_SIDE_NOT_CLEAR")
        self.assertEqual(result["near_ring_diagnostic"],"ALL_AZIMUTHS_NEAR_UNEXPLAINED")
        self.assertFalse(result["goal_sent"])
        self.assertFalse(result["safe_to_reposition_fixture"])

    def test_clear_still_requires_original_unrelaxed_thresholds(self):
        r=diagnose_pregoal_baseline(front_m=.751,side_m=1.201,
                                    valid_beams=360,near_fraction=.05,
                                    scan_count=3)
        self.assertEqual(r["status"],"BASELINE_CLEAR_NO_GOAL")
        for f,s in [(.75,1.21),(.76,1.2),(.52,.63)]:
            self.assertEqual(diagnose_pregoal_baseline(front_m=f,side_m=s,
              valid_beams=360,near_fraction=.4,scan_count=3)["status"],
              "NO_GOAL_BASELINE_UNSAFE")

    def test_invalid_or_missing_data_is_not_clear(self):
        for f,s,n,c in [(None,1.3,360,3),(.9,None,360,3),
                        (float("nan"),2.0,360,3),(.9,2.0,0,3),(.9,2.0,360,2)]:
            r=diagnose_pregoal_baseline(front_m=f,side_m=s,
                                        valid_beams=n,near_fraction=None,
                                        scan_count=c)
            self.assertNotEqual(r["status"],"BASELINE_CLEAR_NO_GOAL")

    def test_all_azimuth_diagnostic_only_not_safety_authority(self):
        class Scan:
            ranges=[.55]*360
            range_min=.00001
            range_max=20.0
        fraction,valid=near_ring_fraction(Scan())
        self.assertEqual(valid,360)
        self.assertEqual(fraction,1.0)
        r=diagnose_pregoal_baseline(front_m=.9,side_m=1.3,
            valid_beams=360,near_fraction=1.0,scan_count=3)
        self.assertEqual(r["status"],"BASELINE_CLEAR_NO_GOAL")
        self.assertFalse(r["goal_sent"])

    def test_post_pose_native_reader_consumes_exact_legacy_four_field_scan(self):
        src=Path(__file__).with_name("p2_g07_owner_pregoal_l2.py").read_text()
        self.assertIn('scans.append((time.monotonic(),stamp,min(values),side))',src)
        self.assertIn('t,stamp,front,side=scans[-1]',src)
        self.assertIn('scan_ring_metrics.append((near_fraction,valid_beams))',src)
        self.assertNotIn('side,near_fraction,valid_beams))',src)

    def test_original_run_fail_closed_before_native_set_pose_and_writes_baseline_evidence(self):
        src=Path(__file__).with_name("p2_g07_owner_pregoal_l2.py").read_text()
        self.assertIn('owner_pregoal_baseline.json',src)
        self.assertLess(src.index('owner_pregoal_baseline.json'),
                        src.index('admit_preloaded_fixture(*DEMO_WORLD_POSE'))
        self.assertIn("OWNER_PREGOAL_NOT_CLEAR_BEFORE_FIXTURE",src)

if __name__=="__main__":
    unittest.main()
