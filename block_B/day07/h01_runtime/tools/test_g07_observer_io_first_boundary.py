"""G07 actual Gazebo first 7-channel timing gap: diagnostic only.
No mock ROS safety pass, no extra publisher/Goal, no TTL change.
"""
import threading
import unittest
from p2_g07_observer_io_probe import BoundedObserverIoProbe


class ObserverIOFirstBoundary(unittest.TestCase):
    def test_exact_native_first_odom_breach_and_correlated_seven_streams(self):
        ledger=BoundedObserverIoProbe(max_samples=64)
        a=264.699048484
        b=265.059473585
        rows={
            "odom": (a,b),
            "scan": (264.717901832,265.060091127),
            "clock": (264.721506471,265.059983585),
            "pre_guard": (264.681983906,265.059718064),
            "supervised": (264.682424551,265.059780488),
            "guard": (264.685620443,265.059857535),
            "supervisor": (264.682526865,265.059918477),
        }
        for kind,(left,right) in rows.items():
            for t in (left,right):
                start=int(t*1e9)
                ledger.record(kind,t,start,start+1000,start+4000,
                              start+9000,start+9000,start+12000,False)
        diag=ledger.summary(start=264.65,end=265.20,heartbeats=[])
        self.assertEqual(diag["first_violation"]["kind"],"odom")
        self.assertAlmostEqual(diag["first_violation"]["gap_ms"],360.425101,places=5)
        self.assertEqual(set(diag["correlated_channels"]),
                         {"odom","scan","clock","pre_guard",
                          "supervised","guard","supervisor"})
        self.assertEqual(diag["release"],"HOLD")
        self.assertFalse(diag["root_cause_proven"])

    def test_flush_and_lock_durations_are_separate_and_same_monotonic_domain(self):
        p=BoundedObserverIoProbe(max_samples=8)
        start=10_000_000_000
        p.record("pre_guard",10.,start,start+10_000_000,
                 start+12_000_000,start+13_000_000,
                 start+193_000_000,start+194_000_000,True)
        x=p.summary(start=9.,end=11.,heartbeats=[9.0,9.02,9.04])
        self.assertAlmostEqual(x["max_lock_wait_ms"],10.0)
        self.assertAlmostEqual(x["max_flush_ms"],180.0)
        self.assertAlmostEqual(x["max_write_ms"],1.0)
        self.assertEqual(x["flush_count"],1)
        self.assertEqual(x["status"],"PROBE_CAPTURED_FIRST_BOUNDARY_UNPROVEN_HOLD")
        self.assertFalse(x["timing_safety_pass"])

    def test_bounded_overflow_and_no_goal_stay_hold(self):
        p=BoundedObserverIoProbe(max_samples=2)
        for i in range(4):
            t=20+i*.05
            ns=int(t*1e9)
            p.record("pre_guard",t,ns,ns,ns,ns,ns,ns,False)
        x=p.summary(start=None,end=None,heartbeats=[])
        self.assertEqual(x["captured"],2)
        self.assertEqual(x["dropped"],2)
        self.assertEqual(x["status"],"PROBE_DROPPED_OR_SCOPE_UNVERIFIED_HOLD")
        self.assertFalse(x["timing_safety_pass"])

    def test_callback_probe_is_only_enabled_by_scoped_ci_with_no_owner_authority(self):
        from pathlib import Path
        runner=Path(__file__).with_name("p2_g07_ci_moving_goal.py").read_text()
        live=Path(__file__).with_name("p2_l3_live_session.py").read_text()
        self.assertIn("AXIA_G07_OBSERVER_IO_PROBE",runner)
        self.assertIn("not owner_mode",runner)
        self.assertIn("GITHUB_ACTIONS",runner)
        self.assertIn("io_probe=io_probe",runner)
        self.assertIn("g07_observer_io_probe_summary.json",runner)
        self.assertIn("self._g07_io_probe",live)
        self.assertIn("time.monotonic_ns()",live)
        self.assertIn("record(kind,t,",live)
        self.assertIn("def io_probe_summary(",live)
        self.assertIn("io_probe=False",live)
        self.assertIn("AXIA_G07_OBSERVER_IO_PROBE",runner)
        self.assertNotIn("CM_TTL_SEC =",runner)
        self.assertNotIn("E_STOP_CERTIFIED=True",live)


if __name__=="__main__":
    unittest.main()
