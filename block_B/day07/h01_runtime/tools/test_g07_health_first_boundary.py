"""RED: actual native Jazzy EventsExecutor #44861540326 Goal NOT sent,
first HEALTH wait blocked; preserve exact missing readiness state, not a generic
CI_MOVING_GOAL_TIMEOUT_HEALTH. Numeric-only, bounded, no extra ROS topics.
"""
import json
import unittest
from pathlib import Path
from p2_g07_health_first_boundary import HealthFirstBoundary

HERE=Path(__file__).parent

class HealthBoundaryContract(unittest.TestCase):
    def sample(self, *, clock=True, scan=1.5, cm=None, guard=False, state="BOOT_SAFE"):
        snap={"clock_advancing":clock,
              "clock_at":10.0 if clock else None,
              "scan_at":10.0 if scan is not None else None,
              "odom_at":10.0,
              "guard_at":10.0}
        data={"scan":scan,
              "guard":{"latched":guard,"reason":"NONE"},
              "supervisor":{"state":state,"health_diagnostics":{
                  "cm_lifecycle_ok":cm,
                  "clock_ok":clock,"scan_ok":scan is not None,
                  "graph_ok":None,"nav2_action_ready":False}}}
        return snap,data

    def test_first_missing_cm_lifecycle_stays_hold_even_with_scan_and_clock(self):
        probe=HealthFirstBoundary(max_samples=8)
        for t in (10.0,10.3,10.6):
            snap,data=self.sample(cm=None)
            probe.record(t,snap,data)
        result=probe.result()
        self.assertEqual(result["status"],"FIRST_HEALTH_READINESS_UNVERIFIED_HOLD")
        self.assertEqual(result["first_readiness_blockers"],["cm_lifecycle_ok_not_true"])
        self.assertEqual(result["first_sample"]["supervisor_state"],"BOOT_SAFE")
        self.assertIsNone(result["first_sample"]["cm_lifecycle_ok"])
        self.assertEqual(result["release"],"HOLD")
        self.assertFalse(result["root_cause_proven"])
        self.assertFalse(result["goal_sent"])
        self.assertFalse(result["certified_estop"])

    def test_clock_and_scan_missing_are_distinct_and_never_pass(self):
        p=HealthFirstBoundary(max_samples=4)
        a,b=self.sample(clock=False,scan=None,cm=True)
        p.record(12.0,a,b)
        r=p.result()
        self.assertEqual(r["first_readiness_blockers"],
                         ["clock_not_advancing","scan_missing"])
        self.assertIsNone(r["first_sample"]["scan_observer_age_ms"])
        self.assertEqual(r["samples"],1)

    def test_first_state_transition_and_last_sample_survive_bounded_history(self):
        p=HealthFirstBoundary(max_samples=2)
        p.record(1.0,*self.sample(cm=None,state="BOOT_SAFE"))
        p.record(1.2,*self.sample(cm=False,state="HEALTH_BAD"))
        p.record(1.4,*self.sample(cm=True,state="NORMAL"))
        r=p.result()
        self.assertEqual(r["first_sample"]["supervisor_state"],"BOOT_SAFE")
        self.assertEqual(r["first_state_transition"]["from"],"BOOT_SAFE")
        self.assertEqual(r["first_state_transition"]["to"],"HEALTH_BAD")
        self.assertEqual(r["samples"],3)
        self.assertEqual(r["dropped_middle_samples"],1)
        self.assertEqual(r["last_sample"]["cm_lifecycle_ok"],True)
        self.assertEqual(r["release"],"HOLD")

    def test_active_goal_or_guard_latch_never_becomes_readiness_pass(self):
        p=HealthFirstBoundary(max_samples=4)
        snap,data=self.sample(cm=True,guard=True)
        p.record(2.,snap,data)
        self.assertIn("guard_latched",p.result()["first_readiness_blockers"])
        self.assertFalse(p.result()["goal_sent"])

    def test_real_runner_captures_first_timeout_before_cleanup(self):
        src=(HERE/"p2_g07_ci_moving_goal.py").read_text()
        self.assertIn("HealthFirstBoundary",src)
        self.assertIn('label=="HEALTH"',src)
        self.assertIn('first_health_boundary.json',src)
        self.assertIn('CI_MOVING_GOAL_TIMEOUT_'+ '"+label',src)
        self.assertIn("probe.record(",src)
        self.assertIn("health_boundary.result()",src)
        self.assertIn("health_first_boundary",src)
        self.assertIn("_task03_exact_goal_terminal",src)

if __name__=="__main__":
    unittest.main()
