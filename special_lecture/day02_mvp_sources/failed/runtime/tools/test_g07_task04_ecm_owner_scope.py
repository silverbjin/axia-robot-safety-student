"""Task04 ROS-free native ECM witness scope; never a moving Goal permission."""
import unittest
from p2_l3_world_overlay import owner_ecm_witness_scope

SHA="a"*40
OWNER={
 "GITHUB_ACTIONS":"false",
 "AXIA_G07_CI_SIM_GOAL_ALLOWED":"0",
 "AXIA_G07_TASK04_OWNER_MOVING_L3":"1",
 "AXIA_G07_TASK04_EXPECTED_STUDENT_SHA":SHA,
 "AXIA_P0_SIM_ONLY":"1",
 "AXIA_P2_G07_PHYSICAL_PREFLIGHT":"1",
 "ROS_DISTRO":"jazzy",
 "ROS_DOMAIN_ID":"86",
 "GZ_PARTITION":"axia_p2_task04_86_123",
}

class ReadOnlyNativeECMWitnessOwnerScope(unittest.TestCase):
    def test_exact_wsl2_sha_sim_scope_allows_read_only_witness(self):
        self.assertTrue(owner_ecm_witness_scope(OWNER,"5.15.153.1-microsoft-standard-WSL2",SHA))
        self.assertTrue(owner_ecm_witness_scope(OWNER,"5.15.153.1-microsoft-standard-WSL2",SHA))

    def test_ci_goal_spoof_and_missing_owner_gates_are_denied(self):
        for key in ("AXIA_G07_TASK04_OWNER_MOVING_L3","AXIA_G07_TASK04_EXPECTED_STUDENT_SHA",
                    "AXIA_P0_SIM_ONLY","AXIA_P2_G07_PHYSICAL_PREFLIGHT",
                    "ROS_DISTRO","ROS_DOMAIN_ID","GZ_PARTITION"):
            wrong=dict(OWNER);wrong.pop(key)
            with self.subTest(key=key):
                self.assertFalse(owner_ecm_witness_scope(wrong,"microsoft-WSL2",SHA))
        for wrong in ({**OWNER,"GITHUB_ACTIONS":"true"},
                      {**OWNER,"AXIA_G07_CI_SIM_GOAL_ALLOWED":"1"},
                      {**OWNER,"AXIA_G07_TASK04_EXPECTED_STUDENT_SHA":"b"*40},
                      {**OWNER,"GZ_PARTITION":"unscoped_1"}):
            with self.subTest(wrong=wrong):
                self.assertFalse(owner_ecm_witness_scope(wrong,"microsoft-WSL2",SHA))
        self.assertFalse(owner_ecm_witness_scope(OWNER,"6.8.0-generic",SHA))
        self.assertFalse(owner_ecm_witness_scope(OWNER,"microsoft-WSL2","b"*40))
        self.assertFalse(owner_ecm_witness_scope(OWNER,"microsoft-WSL2",None))

if __name__=="__main__":
    unittest.main()
