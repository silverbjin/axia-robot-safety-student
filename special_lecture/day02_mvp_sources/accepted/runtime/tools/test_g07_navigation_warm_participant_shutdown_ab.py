"""G07 issue #163 first Nav2 manager SHUTDOWN ACK missing after real Goal.

Strict actual UDPv4 CI #44698698767:
Navigation manage_nodes sent once but no response in 40.000574s; fresh
/is_active responded in 79.579ms and reported active.  This is NOT a
proved DDS root; Fast-DDS upstream #6630 is one matching hypothesis.
Compare a single request from the ALREADY responsive get_parameters node
against the existing fresh per-manager DDS participant. No retry, extra
Goal, TTL or server modifications; keep Localization stage isolated.
"""
import os
import unittest
from unittest.mock import patch

import p2_g07_ordered_shutdown as s


def env(**kwargs):
    base=dict(ROS_DISTRO="jazzy",AXIA_P0_SIM_ONLY="1",
              GITHUB_ACTIONS="true",AXIA_G07_CI_SIM_GOAL_ALLOWED="1",
              GZ_PARTITION="axia_p2_g07_test")
    base.update(kwargs)
    return base


class WarmNavigationParticipantAB(unittest.TestCase):
    def test_default_both_managers_preserve_isolated_client(self):
        node=object()
        with patch.object(s,"_call_isolated_stage",return_value={"status":"ACK"}) as iso:
            with patch.object(s,"call_native_manage") as used:
                self.assertEqual(s._call_shutdown_stage_for_ab(object(),node,
                    manager="navigation",timeout_sec=40,scope_env=env()),{"status":"ACK"})
                self.assertEqual(s._call_shutdown_stage_for_ab(object(),node,
                    manager="localization",timeout_sec=25,scope_env=env()),{"status":"ACK"})
                self.assertEqual(iso.call_count,2)
                used.assert_not_called()

    def test_ci_opt_in_uses_same_verified_dds_participant_navigation_only(self):
        node=object()
        cfg=env(AXIA_G07_NAV_WARM_PARTICIPANT_CI_AB="1")
        with patch.object(s,"call_native_manage",
                          return_value={"status":"SERVICE_TIMEOUT","request_sent":True}) as direct:
            with patch.object(s,"_call_isolated_stage") as iso:
                result=s._call_shutdown_stage_for_ab(object(),node,
                    manager="navigation",timeout_sec=40,scope_env=cfg)
                self.assertEqual(result["status"],"SERVICE_TIMEOUT")
                direct.assert_called_once_with(node,manager="navigation",
                                               command="shutdown",timeout_sec=40)
                iso.assert_not_called()
        with patch.object(s,"_call_isolated_stage",return_value={"status":"ACK"}) as iso:
            s._call_shutdown_stage_for_ab(object(),node,
                manager="localization",timeout_sec=30,scope_env=cfg)
            iso.assert_called_once()

    def test_owner_and_untrusted_ci_setting_are_never_admitted(self):
        node=object()
        for cfg in (env(GITHUB_ACTIONS="false",AXIA_G07_NAV_WARM_PARTICIPANT_CI_AB="1"),
                    env(AXIA_G07_CI_SIM_GOAL_ALLOWED="0",AXIA_G07_NAV_WARM_PARTICIPANT_CI_AB="1"),
                    env(AXIA_P0_SIM_ONLY="0",AXIA_G07_NAV_WARM_PARTICIPANT_CI_AB="1"),
                    env(AXIA_G07_NAV_WARM_PARTICIPANT_CI_AB="unknown")):
            with self.subTest(cfg=cfg):
                with self.assertRaisesRegex(ValueError,"G07_WARM_NAV_PARTICIPANT"):
                    s._call_shutdown_stage_for_ab(object(),node,manager="navigation",
                         timeout_sec=40,scope_env=cfg)

    def test_bad_manager_no_retry(self):
        with self.assertRaises(ValueError):
            s._call_shutdown_stage_for_ab(object(),object(),
                  manager="bad",timeout_sec=20,scope_env=env())

    def test_run_uses_one_stage_dispatch_before_localization(self):
        from pathlib import Path
        text=Path(s.__file__).read_text()
        self.assertIn('_call_shutdown_stage_for_ab(',text)
        self.assertIn('scope_env=os.environ',text)
        self.assertIn('manager=key',text)
        self.assertIn('navigation_manage_group_probe',text)
        self.assertIn('BLOCKED_LIFECYCLE_',text)


if __name__=="__main__":
    unittest.main()
