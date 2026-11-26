"""Promote real UDPv4 native 2-cycle #44705873381 warm DDS shutdown A/B
to *genuine* WSL2 Owner simulation authorization, NEVER spoof CI authority.

Actual public run used opt-in CI-only mode with CM120/Guard150 etc unchanged.
Owner must use its own TTY-guarded one-shot and identical one-request path.
"""
import unittest
from unittest.mock import patch

import p2_g07_ordered_shutdown as shutdown


def owner_env(**extra):
    e={"ROS_DISTRO":"jazzy",
       "GZ_PARTITION":"axia_p2_owner_scope",
       "GITHUB_ACTIONS":"false",
       "AXIA_P0_SIM_ONLY":"1",
       "AXIA_P2_G07_PHYSICAL_PREFLIGHT":"1",
       "AXIA_G07_OWNER_STARTUP_PARITY":"1",
       "AXIA_G07_TASK04_OWNER_MOVING_L3":"1",
       "AXIA_G07_CI_SIM_GOAL_ALLOWED":"0",
       "AXIA_G07_NAV_WARM_PARTICIPANT_OWNER":"1"}
    e.update(extra)
    return e


class OwnerWarmDDSAuthority(unittest.TestCase):
    def test_real_owner_only_single_navigation_request_after_param_ack(self):
        token=object()
        with patch.object(shutdown,"call_native_manage",
                          return_value={"status":"ACK","request_sent":True}) as one:
            with patch.object(shutdown,"_call_isolated_stage") as iso:
                v=shutdown._call_shutdown_stage_for_ab(object(),token,
                      manager="navigation",timeout_sec=40,scope_env=owner_env())
                self.assertEqual(v["status"],"ACK")
                one.assert_called_once_with(token,manager="navigation",
                                             command="shutdown",timeout_sec=40)
                iso.assert_not_called()

    def test_owner_localization_stays_separate_per_manager(self):
        with patch.object(shutdown,"_call_isolated_stage",
                          return_value={"status":"ACK"}) as iso:
            with patch.object(shutdown,"call_native_manage") as direct:
                shutdown._call_shutdown_stage_for_ab(object(),object(),
                      manager="localization",timeout_sec=30,scope_env=owner_env())
                iso.assert_called_once()
                direct.assert_not_called()

    def test_no_owner_ci_authority_spoof_or_missing_real_scope(self):
        variants=[
            {"GITHUB_ACTIONS":"true"},
            {"AXIA_G07_CI_SIM_GOAL_ALLOWED":"1"},
            {"AXIA_G07_TASK04_OWNER_MOVING_L3":"0"},
            {"AXIA_G07_OWNER_STARTUP_PARITY":"0"},
            {"AXIA_P2_G07_PHYSICAL_PREFLIGHT":"0"},
            {"AXIA_P0_SIM_ONLY":"0"},
            {"GZ_PARTITION":"not_axia"},
            {"ROS_DISTRO":"humble"},
            {"AXIA_G07_NAV_WARM_PARTICIPANT_CI_AB":"1"},
            {"AXIA_G07_NAV_WARM_PARTICIPANT_OWNER":"yes"}
        ]
        for kw in variants:
            with self.subTest(kw=kw):
                with self.assertRaisesRegex(ValueError,
                                           "G07_WARM_NAV_PARTICIPANT"):
                    shutdown._call_shutdown_stage_for_ab(object(),object(),
                         manager="navigation",timeout_sec=40,
                         scope_env=owner_env(**kw))

    def test_default_owner_stays_previous_isolated_behavior(self):
        with patch.object(shutdown,"_call_isolated_stage",
                          return_value={"status":"ACK"}) as isolated:
            shutdown._call_shutdown_stage_for_ab(object(),object(),
                 manager="navigation",timeout_sec=40,scope_env=owner_env(
                     AXIA_G07_NAV_WARM_PARTICIPANT_OWNER="0"))
            isolated.assert_called_once()

    def test_no_broad_safety_modification(self):
        from pathlib import Path
        s=Path(shutdown.__file__).read_text()
        self.assertNotIn("retry_shutdown",s)
        self.assertNotIn("AXIA_G07_CI_SIM_GOAL_ALLOWED=1",s)
        self.assertIn("navigation_manage_group_probe",s)
        self.assertIn('AXIA_G07_NAV_WARM_PARTICIPANT_OWNER',s)


if __name__=="__main__":
    unittest.main()
