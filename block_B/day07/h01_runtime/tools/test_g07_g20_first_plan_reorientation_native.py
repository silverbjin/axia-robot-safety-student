"""Native G20 actual first plan response: same-world #448810 and #448816.

Compare first actual plan before/after 0.62m physical cylinder ACK. This is
GLOBAL PlannerServer output, not controller trajectory or root-cause proof.
Fail-closed labels prevent regressions being masked by downstream SLOW timeout.
"""
import unittest
from p2_g07_g20_nav2_plan_witness import assess_first_plan_change

class FirstPlanChangeNative(unittest.TestCase):
    def test_actual_native_448816_slow_first_reorientation_candidate(self):
        r=assess_first_plan_change(dict(
             phase="PRE_FIXTURE",status="NAV2_GLOBAL_PLAN_GEOMETRY_CANDIDATE_HOLD",
             plan_tangent_yaw_rad=1.168522,plan_points=41,
             robot_map_yaw_rad=.148064,release="HOLD"),dict(
             phase="AFTER_FIXTURE_ACK",status="NAV2_GLOBAL_PLAN_GEOMETRY_CANDIDATE_HOLD",
             plan_tangent_yaw_rad=2.525772,plan_points=66,
             robot_map_yaw_rad=.154047,actual_supervised_vx=.000498,
             obstacle_min_path_distance_m=.711331,release="HOLD"))
        self.assertEqual(r["status"],"AFTER_FIXTURE_GLOBAL_PLAN_REORIENTATION_CANDIDATE_HOLD")
        self.assertGreater(r["plan_tangent_change_abs_rad"],1.3)
        self.assertLess(r["robot_yaw_change_abs_rad"],.01)
        self.assertGreater(r["fixture_global_path_distance_m"],.70)
        self.assertFalse(r["actual_local_controller_replan_proven"])
        self.assertFalse(r["root_cause_proven"])
        self.assertEqual(r["release"],"HOLD")
        self.assertFalse(r["certified_estop"])

    def test_native_448810_slow_observed_without_same_reorientation(self):
        r=assess_first_plan_change(dict(
              phase="PRE_FIXTURE",status="NAV2_GLOBAL_PLAN_GEOMETRY_CANDIDATE_HOLD",
              plan_tangent_yaw_rad=1.201353,plan_points=42,
              robot_map_yaw_rad=.143972,release="HOLD"),dict(
              phase="AFTER_FIXTURE_ACK",status="NAV2_GLOBAL_PLAN_GEOMETRY_CANDIDATE_HOLD",
              plan_tangent_yaw_rad=1.201353,plan_points=42,
              robot_map_yaw_rad=.157174,actual_supervised_vx=.044,
              obstacle_min_path_distance_m=.567462,release="HOLD"))
        self.assertEqual(r["status"],"NO_MAJOR_GLOBAL_PLAN_CHANGE_NOT_ACCEPTANCE_HOLD")
        self.assertEqual(r["release"],"HOLD")

    def test_missing_or_stale_or_unproven_plan_is_no_evidence(self):
        base=dict(phase="PRE_FIXTURE",status="NAV2_GLOBAL_PLAN_GEOMETRY_CANDIDATE_HOLD",
                  plan_tangent_yaw_rad=1.20,plan_points=42,
                  robot_map_yaw_rad=.14,release="HOLD")
        next=dict(phase="AFTER_FIXTURE_ACK",status="NAV2_GLOBAL_PLAN_GEOMETRY_CANDIDATE_HOLD",
                  plan_tangent_yaw_rad=2.52,plan_points=66,
                  robot_map_yaw_rad=.15,release="HOLD")
        for a,b in ((dict(base,plan_tangent_yaw_rad=None),next),
                    (base,dict(next,status="NAV2_PLAN_STALE_HOLD")),
                    (dict(base,release="PASS"),next),
                    (base,dict(next,obstacle_min_path_distance_m=5.0)),
                    (base,dict(next,plan_points=0))):
            self.assertEqual(assess_first_plan_change(a,b)["status"],
                             "FIRST_GLOBAL_PLAN_PAIR_UNVERIFIED_HOLD")
if __name__=="__main__":unittest.main()
