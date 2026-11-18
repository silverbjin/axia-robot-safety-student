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
