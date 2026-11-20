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

    def test_wsl2_318ms_scan_102ms_sim_blocks_goal(self):
        v=self.healthy()
        v["scan"]=[(i*.318,i*.102) for i in range(50)]
        v["safety_scan"]=[(i*.320,i*.102) for i in range(50)]
        r=assess_pregoal_samples(v)
        self.assertEqual(r["status"],"HOLD")
        self.assertEqual(r["first_failure"],"SCAN_PREFLIGHT_300MS_OR_HEADER_PERIOD_BREACH")
        self.assertFalse(r["goal_sent"])

    def test_slow_sim_250ms_receipt_still_checked_by_wall(self):
        self.assertEqual(assess_pregoal_samples(self.healthy(.25,.10))["status"],
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

if __name__=="__main__":
    unittest.main()
