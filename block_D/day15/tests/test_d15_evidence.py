"""D15 public evidence analysis regression. Initially RED until analysis package lands."""
import json
import sys
import unittest
from pathlib import Path
DAY=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(DAY))
from evidence_review import review_baseline, load_evidence, validate_g09_g10_separation

class D15BaselineContract(unittest.TestCase):
    def setUp(self):
        self.data=load_evidence()
    def test_jrcigogl_provenance_and_numeric_scope(self):
        x=review_baseline(self.data)
        self.assertEqual(x["baseline_id"],"AXIA-G07-T04-DEMO-BASELINE-20261120-jrCIgoGl")
        self.assertEqual(x["numeric_gate"],"EDUCATION_NUMERIC_ACCEPTED")
        self.assertTrue(x["checks"]["source_provenance"])
        self.assertTrue(x["checks"]["field_numeric_21_of_21"])
    def test_clear_slow_stop_actual_measurements(self):
        x=review_baseline(self.data)
        self.assertTrue(x["checks"]["clear_slow_stop"])
        self.assertGreater(self.data["clear_front_m"],self.data["slow_front_m"])
        self.assertGreater(self.data["slow_front_m"],self.data["stop_front_m"])
        self.assertGreater(self.data["slow_supervised_vx_mps"],self.data["slow_final_vx_mps"])
        self.assertEqual(self.data["stop_final_vx_mps"],0)
    def test_goal_cancel_and_post_zero_odom_dwell(self):
        x=review_baseline(self.data)
        self.assertTrue(x["checks"]["goal_cancel"])
        self.assertTrue(x["checks"]["odom_zero_dwell"])
        self.assertEqual(self.data["goal_cancel_status"],5)
        self.assertGreaterEqual(self.data["zero_dwell_sec"],1)
    def test_ttl_scoped_boundaries(self):
        x=review_baseline(self.data)
        self.assertTrue(x["checks"]["reported_ttl_boundaries"])
        self.assertEqual(x["threshold_ms"]["scan_gap_max_ms"],300)
        self.assertEqual(x["threshold_ms"]["guard_internal_cm_age_max_ms"],150)
        self.assertIsNone(x["first_violation_timestamp"])
    def test_guard_and_clock_status(self):
        x=review_baseline(self.data)
        self.assertTrue(x["checks"]["guard_clock_and_shutdown"])
        self.assertFalse(self.data["guard_latched"])
    def test_original_hold_visual_formal_and_estop_unmodified(self):
        x=review_baseline(self.data)
        self.assertTrue(x["checks"]["scope_preserved"])
        self.assertFalse(x["formal_accepted"])
        self.assertFalse(x["certified_estop"])
        self.assertFalse(x["visual_verified"])
        self.assertEqual(x["raw_machine_status"],"HOLD_RAW_REVIEW_AND_VISUAL_PENDING")
    def test_tampered_scan_301ms_is_rejected(self):
        x=dict(self.data,scan_gap_max_ms=301.0)
        r=review_baseline(x)
        self.assertFalse(r["checks"]["reported_ttl_boundaries"])
        self.assertIn("scan_gap_max_ms",r["failed_gates"])
        self.assertEqual(r["numeric_gate"],"NOT_ACCEPTED")
    def test_tampered_guard_151ms_is_rejected(self):
        x=dict(self.data,guard_internal_cm_age_max_ms=151.0)
        r=review_baseline(x)
        self.assertFalse(r["checks"]["reported_ttl_boundaries"])
        self.assertIn("guard_internal_cm_age_max_ms",r["failed_gates"])
    def test_tampered_goal_and_dwell_rejected(self):
        x=dict(self.data,exact_goal_uuid_cancelled=False,zero_dwell_sec=.5)
        r=review_baseline(x)
        self.assertFalse(r["checks"]["goal_cancel"])
        self.assertFalse(r["checks"]["odom_zero_dwell"])
    def test_wrong_release_or_unsafe_scope_rejected(self):
        x=dict(self.data,raw_machine_l3_accepted=True,certified_estop=True)
        r=review_baseline(x)
        self.assertFalse(r["checks"]["scope_preserved"])
    def test_pnu_provenance_is_separate_from_real_g07_owner(self):
        x=validate_g09_g10_separation()
        self.assertTrue(x["safe_separation"])
        self.assertEqual(x["g09_labels"],["N","P","U"])
        self.assertFalse(x["g07_owner_human_detector_attested"])
        self.assertEqual(x["g10_level"],"SYNTHETIC_L0_ONLY")
if __name__=="__main__":
    unittest.main()
