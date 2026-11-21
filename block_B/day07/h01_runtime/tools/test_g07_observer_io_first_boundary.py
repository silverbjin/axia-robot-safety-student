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

    def test_first_gap_heartbeat_not_confused_with_session_global_max(self):
        # Exact prior native #44859905000: main ROS Observer first 335ms
        # gap but independent Python heartbeat remained 20ms in THAT gap.
        p=BoundedObserverIoProbe(max_samples=8)
        for t in (179.413292627,179.749053764):
            ns=int(t*1e9)
            p.record("odom",t,ns,ns,ns,ns,ns,ns,False)
        # A separate unrelated 350ms heartbeat scheduling hiccup occurred
        # OUTSIDE the first ROS timing failure. Never call it process-wide
        # stall proof at the first violation.
        beats=[178.,178.35]+[179.40+i*.020 for i in range(20)]
        d=p.summary(start=179.3,end=179.9,heartbeats=beats)
        self.assertGreater(d["heartbeat_max_gap_ms"],300)
        self.assertGreaterEqual(d["first_violation_heartbeat_count"],14)
        self.assertLess(d["first_violation_heartbeat_max_gap_ms"],40)
        self.assertFalse(d["process_wide_stall_at_first_violation_proven"])
        self.assertEqual(d["release"],"HOLD")

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



    def test_executor_silence_snapshot_is_bounded_read_only_and_not_root_proof(self):
        # Independent heartbeat kept running throughout the actual native
        # 340.896ms seven-topic callback silence in #44867547228.
        # The one-shot CI-only executor stack is a DIAGNOSTIC, never TTL PASS.
        import inspect
        from types import SimpleNamespace
        from p2_g07_observer_io_probe import FirstExecutorSilenceSnapshot
        probe=FirstExecutorSilenceSnapshot(threshold_ms=160)
        spin=SimpleNamespace(ident=314159,name="g07_observer_executor_spin")
        frames={314159:inspect.currentframe()}
        self.assertFalse(probe.capture(now=10.20,last_callback_at=10.,
                           goal_active=False,spin_thread_ident=314159,
                           threads=[spin],frames=frames))
        self.assertFalse(probe.capture(now=10.10,last_callback_at=10.,
                           goal_active=True,spin_thread_ident=314159,
                           threads=[spin],frames=frames))
        self.assertTrue(probe.capture(now=10.20,last_callback_at=10.,
                           goal_active=True,spin_thread_ident=314159,
                           threads=[spin],frames=frames))
        self.assertFalse(probe.capture(now=10.40,last_callback_at=10.,
                           goal_active=True,spin_thread_ident=314159,
                           threads=[spin],frames=frames))
        result=probe.result()
        self.assertEqual(result["status"],"FIRST_EXECUTOR_SILENCE_STACK_CAPTURED_HOLD")
        self.assertGreaterEqual(result["silence_ms"],160)
        self.assertEqual(result["thread_roles"],["executor_spin"])
        self.assertTrue(result["frames_by_role"]["executor_spin"])
        self.assertFalse(result["root_cause_proven"])
        self.assertFalse(result["timing_safety_pass"])
        self.assertEqual(result["release"],"HOLD")
        self.assertNotIn("file_path",str(result))
        self.assertNotIn("local",str(result))

    def test_executor_silence_snapshot_requires_existing_ci_only_io_probe(self):
        from pathlib import Path
        runner=Path(__file__).with_name("p2_g07_ci_moving_goal.py").read_text()
        self.assertIn("FirstExecutorSilenceSnapshot",runner)
        self.assertIn("silence_probe.capture(",runner)
        self.assertIn('"first_executor_silence_snapshot"',runner)
        self.assertIn("if io_probe:",runner)
        self.assertIn("not owner_mode",runner)
        self.assertNotIn("AXIA_G07_EVENTS_EXECUTOR_AB: '1'",runner)


    def test_bounded_multi_wait_candidate_is_ci_only_fail_closed(self):
        from p2_g07_observer_io_probe import select_bounded_executor_wait_candidate
        base={"GITHUB_ACTIONS":"true","AXIA_G07_CI_SIM_GOAL_ALLOWED":"1",
              "AXIA_P0_SIM_ONLY":"1","AXIA_G07_CI_OWNER_OBSERVER_PARITY":"1",
              "AXIA_G07_OBSERVER_IO_PROBE":"1"}
        self.assertFalse(select_bounded_executor_wait_candidate(base,owner_mode=False))
        good={**base,"AXIA_G07_CI_EXECUTOR_WAIT_BOUNDED_AB":"1"}
        self.assertTrue(select_bounded_executor_wait_candidate(good,owner_mode=False))
        for bad,owner in (({**good,"GITHUB_ACTIONS":"false"},False),
                          ({**good,"AXIA_G07_OBSERVER_IO_PROBE":"0"},False),
                          ({**good,"AXIA_G07_EVENTS_EXECUTOR_AB":"1"},False),
                          (good,True)):
            with self.subTest(bad=bad,owner=owner):
                with self.assertRaises(ValueError):
                    select_bounded_executor_wait_candidate(bad,owner_mode=owner)
        with self.assertRaises(ValueError):
            select_bounded_executor_wait_candidate(
                {**base,"AXIA_G07_CI_EXECUTOR_WAIT_BOUNDED_AB":"yes"},
                owner_mode=False)

    def test_bounded_candidate_uses_existing_multi_two_threads_not_events_or_single(self):
        from pathlib import Path
        code=Path(__file__).with_name("p2_g07_ci_moving_goal.py").read_text()
        self.assertIn("select_bounded_executor_wait_candidate",code)
        self.assertIn("executor.spin_once(timeout_sec=.02)",code)
        self.assertIn("MultiThreadedExecutor(num_threads=2 if owner_observer_parity else 3)",code)
        self.assertIn("spin_stop.set()",code)
        self.assertIn("if bounded_wait_candidate:",code)

if __name__=="__main__":
    unittest.main()
