"""Reproduce actual NO_GOAL positive calibration cleanup failure #44213915956.

A native Contact positive is a sensor proof, not a Nav2 L2 shutdown PASS.
An independently isolated subsequent Goal may proceed only if no leftover
process and the abnormal teardown is exactly a known NO_GOAL localization ACK.
"""
import unittest
from p2_g07_task03_calibration_cleanup import assess_calibration_teardown

class DisposableContactCalibrationCleanup(unittest.TestCase):
    def frame(self):
        return (
            dict(sensor_found=True,report_complete=True,
                 positive_contacts=5382,observed_iterations=22714,
                 missing_iterations=0,source_sha="a"*64),
            dict(status="SMOKE_READY",goal_sent=False,fault_injected=False),
            dict(status="BLOCKED_LIFECYCLE_LOCALIZATION_SERVICE_TIMEOUT",
                 navigation_ack=True,localization_ack=False),
            "P2_L2_GRACEFUL_TEARDOWN\n",3,[],
        )

    def test_exact_no_goal_localization_ack_timeout_allows_only_disposable_sensor_proof(self):
        v=assess_calibration_teardown(*self.frame())
        self.assertEqual(v["status"],"CONTACT_CALIBRATION_PROVEN_DISPOSABLE_ONLY")
        self.assertFalse(v["native_nav2_l2_pass"])
        self.assertFalse(v["moving_goal_accepted"])
        self.assertFalse(v["certified_estop"])
        self.assertTrue(v["world_isolation_required"])

    def test_exact_navigation_shutdown_timeout_disposable_no_goal_zero_leaks_only(self):
        # Real public native Gazebo #44217387168: 5325 actual positive
        # contacts, 32946 ECM frames, no leaked process, but original
        # NO_GOAL Navigation service timed out; moving Goal NOT started.
        args=list(self.frame())
        args[0]["positive_contacts"]=5325
        args[0]["observed_iterations"]=32946
        args[2]={"status":"BLOCKED_LIFECYCLE_NAVIGATION_SERVICE_TIMEOUT",
                 "navigation_ack":False,"localization_ack":False}
        v=assess_calibration_teardown(*args)
        self.assertEqual(v["status"],"CONTACT_CALIBRATION_PROVEN_DISPOSABLE_ONLY")
        self.assertEqual(v["cleanup_stage"],
            "NO_GOAL_NAVIGATION_TIMEOUT_BUT_NO_LEAK_OR_FORCED_KILL")
        self.assertFalse(v["native_nav2_l2_pass"])
        self.assertFalse(v["moving_goal_accepted"])
        args[5]=[9911]
        self.assertNotEqual(assess_calibration_teardown(*args)["status"],
                            "CONTACT_CALIBRATION_PROVEN_DISPOSABLE_ONLY")
        args[5]=[]
        args[1]["goal_sent"]=True
        self.assertNotEqual(assess_calibration_teardown(*args)["status"],
                            "CONTACT_CALIBRATION_PROVEN_DISPOSABLE_ONLY")

    def test_disposable_no_goal_direct_sigint_is_only_sensor_calibration_not_nav2_l2(self):
        # First failure #44218557392: missing Navigation get_parameters
        # during disposal. There is NO Goal and the world will be discarded.
        # Avoid requiring unrelated Nav2 lifecycle management for native
        # S02 sensor calibration. Must still prove real positive contact,
        # no forced SIGKILL, no leaked process, and literal shutdown marker.
        args=list(self.frame())
        args[2]={"status":"DISPOSABLE_NO_GOAL_DIRECT_SIGINT_CONFIRMED",
                 "navigation_ack":False,"localization_ack":False}
        args[4]=0
        v=assess_calibration_teardown(*args)
        self.assertEqual(v["status"],"CONTACT_CALIBRATION_PROVEN_DISPOSABLE_ONLY")
        self.assertEqual(v["cleanup_stage"],"NO_GOAL_DISPOSABLE_DIRECT_SIGINT_NO_NAV2_ACK_CLAIM")
        self.assertFalse(v["native_nav2_l2_pass"])
        self.assertFalse(v["moving_goal_accepted"])
        for problem in ("leak","force","goal","absent_positive"):
            with self.subTest(problem=problem):
                broken=list(args)
                broken[0]=dict(args[0])
                broken[1]=dict(args[1])
                if problem=="leak":broken[5]=[18770]
                if problem=="force":broken[3]="P2_L2_FORCED_SIGKILL"
                if problem=="goal":broken[1]["goal_sent"]=True
                if problem=="absent_positive":broken[0]["positive_contacts"]=0
                self.assertNotEqual(assess_calibration_teardown(*broken)["status"],
                                    "CONTACT_CALIBRATION_PROVEN_DISPOSABLE_ONLY")

    def test_no_goal_direct_sigint_source_is_opt_in_and_never_in_moving_goal(self):
        from pathlib import Path
        runner=(Path(__file__).resolve().parents[1]/"scripts/p2_no_goal_smoke_ci.sh").read_text()
        self.assertIn("AXIA_G07_TASK03_NO_GOAL_DISPOSABLE_NATIVE_POSITIVE_SIGINT",runner)
        self.assertIn("AXIA_G07_TASK03_POSITIVE_ONLY",runner)
        self.assertIn("GITHUB_ACTIONS",runner)
        self.assertIn("AXIA_P0_SIM_ONLY",runner)
        self.assertIn("AXIA_G07_CI_SIM_GOAL_ALLOWED",runner)
        self.assertIn("G07_MOVING_GOAL_ORDERED_SHUTDOWN_ACK_BEFORE_SIGINT",runner)
        self.assertIn("G07_REAL_SHUTDOWN_L2_CM_CLEAN_EXIT_AFTER_NAV2_ACK_PASS",runner)

    def test_no_goal_direct_sigint_emits_distinct_shutdown_json_only_after_graceful_exit(self):
        # Regression: REAL public Gazebo #44220702329 had valid native
        # Contact + graceful rc=0, but proof reader required this absent
        # NO_GOAL-only shutdown JSON. It must never claim Nav2 ACK.
        from pathlib import Path
        runner=(Path(__file__).resolve().parents[1]/"scripts/p2_no_goal_smoke_ci.sh").read_text()
        after_wait=runner.index('wait "$LAUNCH_PID" 2>/dev/null || true')
        after=runner[after_wait:after_wait+1800]
        self.assertIn('task03_disposable_shutdown.marker',after)
        self.assertIn('P2_L2_GRACEFUL_TEARDOWN',after)
        self.assertIn('g07_ordered_shutdown.json',after)
        self.assertIn('DISPOSABLE_NO_GOAL_DIRECT_SIGINT_CONFIRMED',after)
        self.assertIn('"navigation_ack":false',after)
        self.assertIn('"localization_ack":false',after)
        self.assertIn('"goal_sent":false',after)
        self.assertIn('"native_nav2_l2_pass":false',after)

    def test_full_native_nav2_shutdown_ack_is_stronger(self):
        args=list(self.frame())
        args[2]=dict(status="NAV2_LIFECYCLE_SHUTDOWN_ACK",
                    navigation_ack=True,localization_ack=True)
        args[4]=0
        self.assertEqual(assess_calibration_teardown(*args)["status"],
                         "CONTACT_CALIBRATION_PROVEN_DISPOSABLE_ONLY")

    def test_no_goal_early_fail_closed_on_any_leaked_process_or_forced_kill(self):
        for i in ("leak","forced","wrong_error","goal","missing_witness",
                  "different_rc","missing_grace"):
            with self.subTest(case=i):
                args=list(self.frame())
                if i=="leak":args[5]=[9835]
                if i=="forced":args[3]="P2_L2_FORCED_SIGKILL\n"
                if i=="wrong_error":args[2]["status"]="BLOCKED_LIFECYCLE_NAVIGATION_SERVICE_TIMEOUT"
                if i=="goal":args[1]["goal_sent"]=True
                if i=="missing_witness":args[0]["positive_contacts"]=0
                if i=="different_rc":args[4]=124
                if i=="missing_grace":args[3]=""
                self.assertNotEqual(
                    assess_calibration_teardown(*args)["status"],
                    "CONTACT_CALIBRATION_PROVEN_DISPOSABLE_ONLY")
if __name__=="__main__":
    unittest.main()
