"""G07 G20 physical SLOW fixture: only move existing cylinder while real Goal
still commands steady forward motion. No synthetic LaserScan or cmd_vel.
Grounded in native #44871515361 Cycle2 yaw .1147→1.5198 and reverse vx.
"""
import unittest
from pathlib import Path
from p2_g07_ci_slow_entry import forward_entry, diagnose_forward_entry

ANCHOR={"map_pose":(-2.0,-0.5,0.),"odom_pose":(0.,0.,0.),
        "world_pose":(-2.0,-0.5,0.),
        "relative_motion_source":"ros_odom",
        "map_pose_source":"tf_map_base_link",
        "world_pose_source":"validated_official_nav2_world_spawn"}

def example():
    s={"mono":100.0,"action_status":2,"supervised_speed":0.07,
       "pre_guard_speed":0.069,"final_speed":0.068,"guard":{"latched":False}}
    for key in ("scan","supervised","pre_guard","final","odom","guard","clock"):
        s[key+"_at"]=99.99
    d={"scan":1.31,"pose":(0.18,0.03,1.32),
       "odom":[dict(t=99.51,vx=.062,wz=.008),
               dict(t=99.73,vx=.064,wz=.011),
               dict(t=99.99,vx=.061,wz=.012)]}
    return s,d

class TestSlowForwardEntry(unittest.TestCase):
    def test_real_northeast_goal_heading_aligns_before_slow_set_pose(self):
        # Goal (-2,-.5)->(-1.7,.7) ~=76deg, real native yaw .1147
        # immediately after physical SLOW then 1.5198 at +35sec.
        s,d=example()
        d["pose"]=(.125,.006,.1147)
        self.assertIsNone(forward_entry(s,d,ANCHOR))
        self.assertEqual(diagnose_forward_entry(s,d,ANCHOR)["first_blocker"],
                         "GOAL_HEADING_NOT_ALIGNED")
        d["pose"]=(.1898,.1405,1.5198)
        self.assertIsNotNone(forward_entry(s,d,ANCHOR))
        self.assertEqual(diagnose_forward_entry(s,d,ANCHOR)["first_blocker"],
                         "ENTRY_CONDITIONS_SATISFIED_BUT_WAIT_UNVERIFIED")

    def test_missing_verified_map_odom_anchor_fails_closed(self):
        s,d=example()
        self.assertIsNone(forward_entry(s,d,None))
        self.assertEqual(diagnose_forward_entry(s,d,None)["first_blocker"],
                         "FRAME_ANCHOR_INVALID")

    def test_real_forward_steady_before_native_set_pose_can_proceed(self):
        s,d=example()
        r=forward_entry(s,d,ANCHOR)
        self.assertTrue(r["forward_entry_proven"])
        self.assertEqual(r["pose"],[0.18,0.03,1.32])
        self.assertLess(r["max_abs_odom_wz"],0.05)
    def test_existing_cycle2_reverse_with_real_front_0_6776_must_hold(self):
        s,d=example()
        s["supervised_speed"]=-.016686975955963135
        d["scan"]=.6776
        d["pose"]=(.1248,.006,.1257)
        self.assertIsNone(forward_entry(s,d,ANCHOR))
    def test_rotating_or_nav2_status_not_executing_must_hold(self):
        s,d=example()
        d["odom"][-1]["wz"]=.31
        self.assertIsNone(forward_entry(s,d,ANCHOR))
        s,d=example();s["action_status"]=5
        self.assertIsNone(forward_entry(s,d,ANCHOR))
    def test_actual_native_clear_velocity_00376_reports_precise_forward_blocker(self):
        # First new native #44876802910 CLEAR at 0.03762598m/s < extra
        # entry threshold .05: expose the exact blocker, not a generic SLOW.
        s,d=example()
        s.update(supervised_speed=.037625983357429504,
                 pre_guard_speed=.037625983357429504,
                 final_speed=.037625983357429504)
        r=diagnose_forward_entry(s,d,ANCHOR)
        # Existing production CLEAR phase admits supervised vx > .03.
        # A new pre-fixture .05 limit rejected actual native CLEAR .037626.
        self.assertEqual(r["first_blocker"],"ENTRY_CONDITIONS_SATISFIED_BUT_WAIT_UNVERIFIED")
        self.assertIsNotNone(forward_entry(s,d,ANCHOR))
        self.assertAlmostEqual(r["supervised_vx"],.037626,places=5)
        self.assertEqual(r["release"],"HOLD")
        self.assertFalse(r["entry_proven"])
        self.assertNotIn("goal_uuid",r)

    def test_actual_native_end_velocity_0018827_remains_blocked(self):
        s,d=example()
        s.update(supervised_speed=.018827,pre_guard_speed=.018827,
                 final_speed=.018827)
        self.assertIsNone(forward_entry(s,d,ANCHOR))
        self.assertEqual(diagnose_forward_entry(s,d,ANCHOR)["first_blocker"],
                         "SUPERVISED_FORWARD_BELOW_ENTRY_GATE")

    def test_real_turn_and_stale_scan_have_distinct_first_blocker(self):
        s,d=example()
        d["odom"][-1]["wz"]=.31
        self.assertEqual(diagnose_forward_entry(s,d,ANCHOR)["first_blocker"],
                         "ODOM_YAW_RATE_NOT_STABLE")
        s,d=example()
        s["scan_at"]=99.5
        self.assertEqual(diagnose_forward_entry(s,d,ANCHOR)["first_blocker"],
                         "STALE_OR_MISSING_SCAN")

    def test_runtime_failure_must_emit_bounded_first_blocker_before_error(self):
        src=(Path(__file__).parent/"p2_g07_ci_moving_goal.py").read_text()
        self.assertIn("AXIA_G07_G20_FIRST_FORWARD_ENTRY_BLOCKER",src)
        self.assertIn("diagnose_forward_entry",src)
        self.assertIn("CI_MOVING_GOAL_TIMEOUT_SLOW_ENTRY_FORWARD",src)

    def test_rejected_goal_bearing_gate_not_enabled_in_original_moving_runtime(self):
        # Native #44878195833 L2 FAIL despite L0; Goal straight bearing
        # is not the actual Nav2 local plan tangent. Revert the unproven gate.
        src=(Path(__file__).parent/"p2_g07_ci_moving_goal.py").read_text()
        self.assertNotIn("SLOW_ENTRY_FORWARD",src)
        self.assertNotIn("from p2_g07_ci_slow_entry import",src)
        self.assertIn('world_anchor,obs.data().get("pose"),.62,.07,demo_corridor=True',src)
        self.assertIn("CI_MOVING_GOAL_TIMEOUT_SLOW",src)

    def test_stale_actual_scan_or_guard_latch_or_no_positive_odom_must_hold(self):
        s,d=example();s["scan_at"]=99.5
        self.assertIsNone(forward_entry(s,d,ANCHOR))
        s,d=example();s["guard"]["latched"]=True
        self.assertIsNone(forward_entry(s,d,ANCHOR))
        s,d=example();d["odom"][-1]["vx"]=-.01
        self.assertIsNone(forward_entry(s,d,ANCHOR))

if __name__=="__main__":unittest.main()
