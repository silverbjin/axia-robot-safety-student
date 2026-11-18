"""Original WSLg failure must separate GPU range plausibility from wall/sim RTF.

No Goal, no ROS mocks. Read-only pure timing analysis of actual callback
pairs. Do not turn a near-ring anomaly into a STOP/Goal bypass.
"""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from g07_wslg_no_goal_sensor_probe import analyze_timing_separately

def readings(rtf, front, side, wall_hz=None):
    hz=wall_hz if wall_hz is not None else rtf*10.0
    n=31
    wall_step=1.0/hz
    safe=[{"recv":i*wall_step+10.0,"stamp":i*.1+5.0,
           "front":front,"side":side,"near":1.0 if front<.75 else .05,"beams":360}
          for i in range(n)]
    clock=[{"recv":10.0+i*.1,"sim":5.0+i*.1*rtf}
           for i in range(1+int((safe[-1]["recv"]-10.)/.1))]
    return {"safety":safe,"raw":list(safe),"odom":[],"clock":[],"clock_receipts":clock}

class IndependentPhysicalAxes(unittest.TestCase):
    def test_wslg_low_rtf_and_near_ring_have_separate_flags(self):
        r=analyze_timing_separately(readings(.30,.526,.629))
        self.assertAlmostEqual(r["ros_clock_rtf"],.30,places=3)
        self.assertAlmostEqual(r["safety_source_hz"],10.0,places=3)
        self.assertAlmostEqual(r["safety_wall_hz"],3.0,places=3)
        self.assertEqual(r["timing_pattern"],"SIMULATION_SLOWDOWN_CONSISTENT")
        self.assertTrue(r["distance_unsafe_independent_of_rtf"])
        self.assertFalse(r["gpu_causality_proven"])

    def test_normal_rtf_but_bad_ranges_remain_unsafe(self):
        r=analyze_timing_separately(readings(1.,.525,.63))
        self.assertAlmostEqual(r["ros_clock_rtf"],1.,places=3)
        self.assertEqual(r["timing_pattern"],"RTF_NORMAL")
        self.assertTrue(r["distance_unsafe_independent_of_rtf"])

    def test_bad_wall_receipt_with_good_rtf_is_not_bad_rtf(self):
        r=analyze_timing_separately(readings(1.,1.41,2.52,wall_hz=3.))
        self.assertAlmostEqual(r["ros_clock_rtf"],1.,places=3)
        self.assertAlmostEqual(r["safety_wall_hz"],3.,places=3)
        self.assertEqual(r["timing_pattern"],"POST_SIM_DELIVERY_OR_SCHEDULING_SUSPECT")
        self.assertFalse(r["distance_unsafe_independent_of_rtf"])

    def test_slow_rtf_with_good_ranges_is_separate_performance_failure(self):
        r=analyze_timing_separately(readings(.3,1.41,2.52))
        self.assertEqual(r["timing_pattern"],"SIMULATION_SLOWDOWN_CONSISTENT")
        self.assertFalse(r["distance_unsafe_independent_of_rtf"])

    def test_original_archive_clock_without_host_receipts_cannot_certify_rtf(self):
        d=readings(.3,.526,.63)
        del d["clock_receipts"]
        r=analyze_timing_separately(d)
        self.assertIsNone(r["ros_clock_rtf"])
        self.assertEqual(r["timing_pattern"],"RTF_UNMEASURED")

    def test_rtf_host_pairs_are_decimated_without_losing_clock_monotonic_check(self):
        src=(Path(__file__).with_name("g07_wslg_no_goal_sensor_probe.py")).read_text()
        self.assertIn('CLOCK_RTF_RECEIPT_MIN_STEP_SEC = .20',src)
        self.assertIn('recv - records["clock_receipts"][-1]["recv"]',src)
        self.assertIn('records["clock"].append(stamp)',src)
        self.assertIn('records["clock_receipts"].append({"recv": recv, "sim": stamp})',src)

    def test_first_raw_ttl_violation_before_safety_starts_is_labeled_not_ignored(self):
        from g07_wslg_no_goal_sensor_probe import correlate_first_raw_gap
        raw=[{"recv":float(i)*.1+10.0,"stamp":5.0+i*.1,
              "front":1.4,"side":2.5,"near":.3,"beams":360} for i in range(30)]
        raw[6]["recv"]=raw[5]["recv"]+.331547
        for i in range(7,30):raw[i]["recv"]+=.24
        safe=[dict(row) for row in raw[10:]]
        obs=correlate_first_raw_gap({"raw":raw,"safety":safe})
        self.assertEqual(obs["first_gap_sec"],.331547)
        self.assertEqual(obs["first_gap_index"],6)
        self.assertEqual(obs["phase"],"BEFORE_FIRST_SAFETY_SCAN")
        self.assertFalse(obs["raw_ttl_accepted"])
        self.assertFalse(obs["upstream_lidar_fault_proven"])

    def test_same_stamp_safety_on_time_raw_late_classifies_observer_path_only(self):
        from g07_wslg_no_goal_sensor_probe import correlate_first_raw_gap
        raw=[{"recv":20.0+i*.1,"stamp":10.+i*.1} for i in range(15)]
        safe=[dict(row) for row in raw]
        raw[9]["recv"]=raw[8]["recv"]+.40
        for i in range(10,len(raw)):raw[i]["recv"]+=.31
        obs=correlate_first_raw_gap({"raw":raw,"safety":safe})
        self.assertEqual(obs["phase"],"BOTH_TOPIC_ACTIVE")
        self.assertEqual(obs["hypothesis"],"RAW_RECEIVER_PATH_DELAY_SUSPECT")
        self.assertFalse(obs["raw_ttl_accepted"])
        self.assertFalse(obs["gpu_causality_proven"])

    def test_no_sim_advance_does_not_claim_rtf(self):
        d=readings(1.,1.4,2.5)
        for row in d["clock_receipts"]:row["sim"]=4.0
        r=analyze_timing_separately(d)
        self.assertIsNone(r["ros_clock_rtf"])
        self.assertEqual(r["timing_pattern"],"RTF_UNMEASURED")

if __name__=="__main__":
    unittest.main()
