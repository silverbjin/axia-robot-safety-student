"""Task04 Owner numerical verdict cannot be promoted to L3 by CI evidence."""
import unittest
from p2_g07_task04_moving_review import authorized_scenario_result

class OwnerVerdictScope(unittest.TestCase):
    def test_ci_public_l2_candidate_stays_ci(self):
        self.assertEqual(authorized_scenario_result(
          {"status":"CI_GAZEBO_MOVING_GOAL_CANDIDATE"}),"ci")
    def test_owner_numerical_candidate_requires_shared_oracle(self):
        self.assertEqual(authorized_scenario_result({
          "status":"NUMERICAL_CANDIDATE",
          "shared_execution_mode":"owner",
          "common_g07_ci_oracle_status":"CI_GAZEBO_MOVING_GOAL_CANDIDATE"}),"owner")
        for bogus in (
          {"status":"NUMERICAL_CANDIDATE","shared_execution_mode":"owner"},
          {"status":"NUMERICAL_CANDIDATE","shared_execution_mode":"ci",
           "common_g07_ci_oracle_status":"CI_GAZEBO_MOVING_GOAL_CANDIDATE"},
          {"status":"CI_GAZEBO_MOVING_GOAL_CANDIDATE","shared_execution_mode":"owner"},
          {"status":"TASK04_OWNER_MOVING_L3_PASS"},
          {"status":"HOLD"}):
            with self.subTest(bogus=bogus):
                self.assertIsNone(authorized_scenario_result(bogus))
if __name__=="__main__":
    unittest.main()
