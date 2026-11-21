"""G20 read-only official Nav2 PlannerServer /plan provenance and geometry.

Grounded in first native physical SLOW failure #44871515361:
robot yaw .1147rad initially, later 1.5198rad, front 0.6776→1.97m,
supervised speed reversed initially; Goal straight bearing is NOT path.
"""
import math
import unittest
from pathlib import Path
from p2_g07_g20_nav2_plan_witness import PlanWitness

ANCHOR={"map_pose":(-2.0,-.5,0.),"odom_pose":(0.,0.,0.),
        "world_pose":(-2.0,-.5,0.),
        "relative_motion_source":"ros_odom",
        "world_pose_source":"validated_official_nav2_world_spawn",
        "map_pose_source":"tf_map_base_link"}

class G20Nav2PlanWitness(unittest.TestCase):
    def test_no_actual_path_never_conflates_goal_bearing_with_local_plan(self):
        witness=PlanWitness()
        value=witness.summarize(ANCHOR,(.125,.006,.1147),
                 fixture_world_xy=(-1.194325,-.41848),
                 at_monotonic=50.,phase="AFTER_FIXTURE_ACK",
                 front_m=.6776,supervised_vx=-.016686975955963135)
        self.assertEqual(value["status"],"NAV2_PLAN_NOT_OBSERVED_HOLD")
        self.assertEqual(value["release"],"HOLD")
        self.assertFalse(value["root_cause_proven"])
        self.assertFalse(value["nav2_local_trajectory_proven"])
        self.assertFalse(value["certified_estop"])

    def test_actual_planner_path_tangent_can_differ_from_goal_straight_bearing(self):
        witness=PlanWitness()
        # Synthetic geometry for L0 math, NOT proof this was the native path.
        points=[(-2.,-.5),(-1.8,-.5),(-1.5,-.5),(-1.5,-.3),
                (-1.6,.0),(-1.7,.7)]
        self.assertTrue(witness.observe("map",points,stamp_ns=123,at_monotonic=50.))
        value=witness.summarize(ANCHOR,(.125,.006,.1147),
                 fixture_world_xy=(-1.194325,-.41848),
                 at_monotonic=50.5,phase="AFTER_FIXTURE_ACK",
                 front_m=.6776,supervised_vx=-.016686975955963135)
        self.assertEqual(value["status"],"NAV2_GLOBAL_PLAN_GEOMETRY_CANDIDATE_HOLD")
        self.assertEqual(value["nearest_plan_segment_index"],0)
        self.assertLess(abs(value["plan_tangent_yaw_rad"]),0.1)
        self.assertGreater(value["straight_goal_bearing_rad"],1.2)
        self.assertLess(value["obstacle_min_path_distance_m"],.31)
        self.assertGreater(value["obstacle_min_path_distance_m"],.20)
        self.assertFalse(value["nav2_local_trajectory_proven"])
        self.assertFalse(value["goal_straight_as_plan_proven"])
        self.assertEqual(value["release"],"HOLD")

    def test_stale_plan_and_wrong_frame_cannot_be_promoted(self):
        witness=PlanWitness()
        self.assertFalse(witness.observe("odom",[(0,0),(1,0)],at_monotonic=50.))
        self.assertTrue(witness.observe("map",[(-2.,-.5),(-1.7,.7)],at_monotonic=50.))
        r=witness.summarize(ANCHOR,(.125,.006,.1147),
                            at_monotonic=70.,phase="PRE_FIXTURE")
        self.assertEqual(r["status"],"NAV2_PLAN_STALE_HOLD")
        self.assertFalse(r["root_cause_proven"])

    def test_invalid_anchor_and_invalid_path_fail_closed(self):
        witness=PlanWitness()
        self.assertFalse(witness.observe("map",[(0,0),(math.nan,0)],
                                          at_monotonic=50.))
        self.assertFalse(witness.observe("map",[(0,0)]*3000,
                                          at_monotonic=50.))
        self.assertTrue(witness.observe("map",[(-2.,-.5),(-1.7,.7)],
                                        at_monotonic=50.))
        r=witness.summarize({},(.125,.006,.1147),
                            at_monotonic=50.1,phase="PRE_FIXTURE")
        self.assertEqual(r["status"],"FRAME_ANCHOR_UNVERIFIED_HOLD")
        self.assertFalse(r["root_cause_proven"])

    def test_runtime_is_ci_only_readonly_and_original_slow_oracle_unchanged(self):
        src=(Path(__file__).parent/"p2_g07_ci_moving_goal.py").read_text()
        self.assertIn("AXIA_G07_G20_NAV2_PLAN_READONLY_PROBE",src)
        self.assertIn('create_subscription(NavPath,"/plan"',src)
        self.assertIn("GITHUB_ACTIONS",src)
        self.assertIn("AXIA_P0_SIM_ONLY",src)
        self.assertIn('g20_capture_plan("PRE_FIXTURE")',src)
        self.assertIn('g20_capture_plan("AFTER_FIXTURE_ACK")',src)
        self.assertIn('g20_capture_plan("SLOW_OBSERVATION_FAILED")',src)
        self.assertIn('rows["slow"]=wait(phase("slow"),35,"SLOW")',src)
        self.assertIn('world_anchor,obs.data().get("pose"),.62,.07,demo_corridor=True',src)
        self.assertNotIn("forward_entry(",src)

if __name__=="__main__":
    unittest.main()
