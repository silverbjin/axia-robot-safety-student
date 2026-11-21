import unittest
from p2_g07_scan_wall_pregoal import assess_pregoal_samples

class ScanPreGoalContract(unittest.TestCase):
    def healthy(self,wall_step=.10,scan_sim_step=.10):
        return dict(
          scan=[(i*wall_step,i*scan_sim_step) for i in range(125)],
          safety_scan=[(i*wall_step+.001,i*scan_sim_step) for i in range(125)],
          clock=[(i*.05,i*.05) for i in range(245)],
          odom=[(i*.10,i*.10) for i in range(125)])

    def test_nominal_10hz_receipt_only_scoped_pass(self):
        r=assess_pregoal_samples(self.healthy())
        self.assertEqual(r["status"],"PASS_SCOPED_RECEIVED_SCAN_ONLY")
        self.assertFalse(r["goal_sent"])
        self.assertEqual(r["native_gazebo_publication_boundary"],"NOT_MEASURED")

    def test_wsl2_318ms_scan_102ms_sim_diagnostic_when_clock_odom_healthy(self):
        # Historical WSL2 wall gap. Full same-session Clock/Odom coverage
        # avoids falsely turning Scan-only evidence into a Clock HOLD.
        v=self.healthy()
        v["scan"]=[(i*.318,i*.102) for i in range(42)]
        v["safety_scan"]=[(i*.320,i*.102) for i in range(42)]
        v["clock"]=[(i*.05,i*.05) for i in range(270)]
        v["odom"]=[(i*.1,i*.1) for i in range(140)]
        r=assess_pregoal_samples(v)
        self.assertEqual(r["status"],"PASS_SCOPED_RECEIVED_SCAN_ONLY",r)
        self.assertEqual(r["first_failure"],"NONE")
        self.assertTrue(r["scan_wall_gap_diagnostic_only"])
        self.assertGreater(r["topic_results"]["scan"]["max_wall_gap_ms"],300)
        self.assertEqual(r["clock_coverage"],"FULL_PREG0AL_WINDOW")
        self.assertFalse(r["goal_sent"])

    def test_slow_sim_250ms_receipt_still_checked_by_wall(self):
        v=self.healthy(.25,.10)
        # A 12s preflight yields ~48 scans at 250ms, not 125/31s.
        v["scan"]=v["scan"][:49]
        v["safety_scan"]=v["safety_scan"][:49]
        self.assertEqual(assess_pregoal_samples(v)["status"],
                         "PASS_SCOPED_RECEIVED_SCAN_ONLY")

    def test_missing_scan_or_backward_stamp_holds(self):
        v=self.healthy()
        v["scan"]=v["scan"][:5]
        self.assertEqual(assess_pregoal_samples(v)["status"],"HOLD")
        v=self.healthy()
        v["scan"][20]=(v["scan"][20][0],v["scan"][19][1]-.5)
        self.assertEqual(assess_pregoal_samples(v)["status"],"HOLD")

    def test_sim_stamp_skips_10hz_holds_even_if_wall_fast(self):
        self.assertEqual(assess_pregoal_samples(self.healthy(.11,.205))["status"],"HOLD")

    def test_same_session_readonly_preflight_precedes_owner_tty_and_goal(self):
        from pathlib import Path
        shell=(Path(__file__).resolve().parents[1]/
               "scripts/p2_no_goal_smoke_ci.sh").read_text()
        self.assertIn('AXIA_G07_SCAN_PREFLIGHT_STRICT',shell)
        self.assertIn("p2_g07_scan_wall_pregoal.py",shell)
        self.assertIn("SCAN_WALL_PREG0AL_BLOCKED_NO_GOAL",shell)
        self.assertLess(shell.index("p2_g07_scan_wall_pregoal.py"),
                        shell.index("Simulation-only Moving Goal: type YES-P2-G07-GOAL"))

    def test_first_scan_gap_retains_exact_pair_and_local_clock_rtf_as_diagnostic(self):
        # 10Hz simulated LaserScan, ~0.41 local RTF and ONE delayed wall pair.
        # The original 12s preflight returned prematurely and lost cause data.
        rows=[(i*.249+(.08 if i>=20 else 0.0), i*.102) for i in range(48)]
        safety=[(t+.001,stamp) for t,stamp in rows]
        v={"scan":rows,"safety_scan":safety,
           "clock":[(i*.04,i*.0164) for i in range(310)],
           "odom":[(i*.1,i*.041) for i in range(130)]}
        r=assess_pregoal_samples(v)
        self.assertEqual(r["status"],"PASS_SCOPED_RECEIVED_SCAN_ONLY",r)
        self.assertTrue(r["scan_wall_gap_diagnostic_only"])
        self.assertEqual(r["first_failure"],"NONE")
        self.assertFalse(r["goal_sent"])
        first=r["first_scan_timing_boundary"]
        self.assertEqual(first["topic"],"scan")
        self.assertAlmostEqual(first["gap_ms"],329.,places=2)
        self.assertAlmostEqual(first["header_sim_gap_ms"],102.,places=2)
        self.assertAlmostEqual(first["local_clock_rtf_estimate"],.41,places=2)
        self.assertIn("safety_scan",r["topic_results"])
        self.assertEqual(r["scan_generation_vs_bridge_root_cause"],"UNDETERMINED")

    def test_first_gap_evidence_must_not_hide_sensor_header_period(self):
        v=self.healthy(.10,.205)
        r=assess_pregoal_samples(v)
        self.assertEqual(r["status"],"HOLD")
        self.assertIsNotNone(r["first_scan_timing_boundary"])
        self.assertGreater(r["first_scan_timing_boundary"]["header_sim_gap_ms"],150)

    def test_odom_over_300ms_is_also_a_pre_goal_hard_hold(self):
        v=self.healthy()
        v["odom"]=[(t+(.25 if i>=25 else 0),sim)
                   for i,(t,sim) in enumerate(v["odom"])]
        r=assess_pregoal_samples(v)
        self.assertEqual(r["status"],"HOLD")
        self.assertEqual(r["first_failure"],"SCAN_PREFLIGHT_CLOCK_ODOM_INTERVAL_BREACH")
        self.assertGreater(r["odom_max_wall_gap_ms"],300)

    def test_truncated_clock_buffer_cannot_validate_first_scan_gap_rtf(self):
        v=self.healthy()
        v["clock"]=v["clock"][85:]
        r=assess_pregoal_samples(v)
        self.assertEqual(r["status"],"HOLD")
        self.assertEqual(r["clock_coverage"],"INSUFFICIENT_FOR_FULL_PREG0AL_WINDOW")

    def test_same_process_clock_retention_spans_12s_full_window(self):
        from pathlib import Path
        src=Path(__file__).with_name("p2_g07_scan_wall_pregoal.py").read_text()
        self.assertIn('CLOCK_WINDOW_MAX_SAMPLES=16384',src)
        self.assertIn('maxlen=CLOCK_WINDOW_MAX_SAMPLES',src)
        self.assertIn("clock_coverage",src)

    def test_clock_odom_first_breach_never_hides_scan_pair(self):
        # Real native #44773940465 first found clock334.226/odom335.862,
        # and returned before preserving any simultaneous LaserScan pair.
        v=self.healthy()
        v["scan"]=[(t+(.25 if i>=25 else 0),s)
                   for i,(t,s) in enumerate(v["scan"])]
        v["safety_scan"]=[(t+(.25 if i>=25 else 0),s)
                          for i,(t,s) in enumerate(v["safety_scan"])]
        v["clock"]=[(t+(.35 if i>=40 else 0),s)
                    for i,(t,s) in enumerate(v["clock"])]
        v["odom"]=[(t+(.25 if i>=25 else 0),s)
                   for i,(t,s) in enumerate(v["odom"])]
        r=assess_pregoal_samples(v)
        self.assertEqual(r["status"],"HOLD")
        self.assertIsNotNone(r["first_scan_timing_boundary"])
        self.assertIn("scan",r["topic_results"])
        self.assertIn("safety_scan",r["topic_results"])
        self.assertGreater(r["clock_max_wall_gap_ms"],300)
        self.assertGreater(r["odom_max_wall_gap_ms"],300)
        self.assertEqual(r["first_delivery_violation"]["channel"],"clock")

if __name__=="__main__":
    unittest.main()
