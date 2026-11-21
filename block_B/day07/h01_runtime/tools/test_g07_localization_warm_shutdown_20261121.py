"""G07 actual #44904732397: Navigation ACK but Localization SHUTDOWN timeout.

RED→GREEN regression for a ONE-request, same-existing-rclpy-participant
Localization client pre-created before Navigation SHUTDOWN. No retry, fabricated
ACK, goal, TTL or official LifecycleManager change. Scope is opt-in only.
"""
import inspect
import unittest
from unittest.mock import Mock,patch

import p2_g07_ordered_shutdown as s

def ci_env(**kw):
    out={"ROS_DISTRO":"jazzy","GITHUB_ACTIONS":"true",
         "AXIA_G07_CI_SIM_GOAL_ALLOWED":"1","AXIA_P0_SIM_ONLY":"1",
         "GZ_PARTITION":"axia_p2_actual_g07",
         "AXIA_G07_NAV_WARM_PARTICIPANT_CI_AB":"1",
         "AXIA_G07_LOCALIZATION_WARM_PARTICIPANT_AB":"1"}
    out.update(kw)
    return out

class LocalizationSameParticipantShutdown(unittest.TestCase):
    def test_ci_one_genuine_localization_ack_on_precreated_endpoint(self):
        node=Mock()
        kind=object()
        cfg=ci_env()
        client=s.prepare_localization_shutdown_client(
            node,kind=kind,scope_env=cfg)
        node.create_client.assert_called_once_with(
            kind,"/lifecycle_manager_localization/manage_nodes")
        self.assertIs(client,node.create_client.return_value)
        with patch.object(s,"_call_isolated_stage") as isolated,patch.object(
                s,"call_native_manage",return_value={"status":"ACK","request_sent":True}) as call:
            result=s._call_shutdown_stage_for_ab(
                object(),node,manager="localization",
                timeout_sec=30,scope_env=cfg,prewarmed_client=client)
        self.assertEqual(result["status"],"ACK")
        call.assert_called_once_with(node,manager="localization",
                                     command="shutdown",timeout_sec=30,
                                     prewarmed_client=client)
        isolated.assert_not_called()

    def test_disabled_loc_optin_stays_isolated_and_never_retries(self):
        cfg=ci_env(AXIA_G07_LOCALIZATION_WARM_PARTICIPANT_AB="0")
        node=Mock()
        self.assertIsNone(s.prepare_localization_shutdown_client(
            node,kind=object(),scope_env=cfg))
        node.create_client.assert_not_called()
        with patch.object(s,"_call_isolated_stage",
                return_value={"status":"SERVICE_TIMEOUT","request_sent":True}) as old,patch.object(
                s,"call_native_manage") as direct:
            result=s._call_shutdown_stage_for_ab(
                object(),node,manager="localization",
                timeout_sec=30,scope_env=cfg)
        self.assertEqual(result["status"],"SERVICE_TIMEOUT")
        old.assert_called_once()
        direct.assert_not_called()
        self.assertEqual(s.shutdown_stage_budget("localization",60),30)

    def test_bad_authority_never_creates_new_or_preemptive_endpoint(self):
        for override in (
            {"GITHUB_ACTIONS":"false"},
            {"AXIA_G07_CI_SIM_GOAL_ALLOWED":"0"},
            {"AXIA_P0_SIM_ONLY":"0"},
            {"AXIA_G07_NAV_WARM_PARTICIPANT_CI_AB":"0"},
            {"AXIA_G07_NAV_WARM_PARTICIPANT_CI_AB":"1",
             "AXIA_G07_NAV_WARM_PARTICIPANT_OWNER":"1"},
        ):
            with self.subTest(override=override):
                node=Mock()
                with self.assertRaisesRegex(ValueError,"G07_LOCALIZATION_WARM"):
                    s.prepare_localization_shutdown_client(
                        node,kind=object(),scope_env=ci_env(**override))
                node.create_client.assert_not_called()

    def test_one_loc_client_custody_precedes_navigation_and_cleanup(self):
        code=inspect.getsource(s.run)
        self.assertIn("loc_shutdown_client = prepare_localization_shutdown_client(",code)
        self.assertLess(code.index("loc_shutdown_client = prepare_localization_shutdown_client("),
                        code.index("response = call("))
        self.assertIn('loc_shutdown_client if key=="localization" else None',code)
        self.assertIn("node.destroy_client(loc_shutdown_client)",code)
        self.assertIn('if ack["status"]!="ACK":',code)
        self.assertIn('BLOCKED_LIFECYCLE_',code)
        self.assertIn("deadline = monotonic() + limit",code)

if __name__=="__main__":unittest.main()
