"""G07 G20 physical SLOW fixture: only move existing cylinder while real Goal
still commands steady forward motion. No synthetic LaserScan or cmd_vel.
Grounded in native #44871515361 Cycle2 yaw .1147→1.5198 and reverse vx.
"""
import unittest
from p2_g07_ci_slow_entry import forward_entry

def example():
    s={"mono":100.0,"action_status":2,"supervised_speed":0.07,
       "pre_guard_speed":0.069,"final_speed":0.068,"guard":{"latched":False}}
    for key in ("scan","supervised","pre_guard","final","odom","guard","clock"):
        s[key+"_at"]=99.99
    d={"scan":1.31,"pose":(0.18,0.03,0.10),
       "odom":[dict(t=99.51,vx=.062,wz=.008),
               dict(t=99.73,vx=.064,wz=.011),
               dict(t=99.99,vx=.061,wz=.012)]}
    return s,d

class TestSlowForwardEntry(unittest.TestCase):
    def test_real_forward_steady_before_native_set_pose_can_proceed(self):
        s,d=example()
        r=forward_entry(s,d)
        self.assertTrue(r["forward_entry_proven"])
        self.assertEqual(r["pose"],[0.18,0.03,0.10])
        self.assertLess(r["max_abs_odom_wz"],0.05)
    def test_existing_cycle2_reverse_with_real_front_0_6776_must_hold(self):
        s,d=example()
        s["supervised_speed"]=-.016686975955963135
        d["scan"]=.6776
        d["pose"]=(.1248,.006,.1257)
        self.assertIsNone(forward_entry(s,d))
    def test_rotating_or_nav2_status_not_executing_must_hold(self):
        s,d=example()
        d["odom"][-1]["wz"]=.31
        self.assertIsNone(forward_entry(s,d))
        s,d=example();s["action_status"]=5
        self.assertIsNone(forward_entry(s,d))
    def test_native_cylinder_wiring_must_wait_for_live_forward_not_reposition_synthetic(self):
        from pathlib import Path
        src=(Path(__file__).parent/"p2_g07_ci_moving_goal.py").read_text()
        self.assertIn("from p2_g07_ci_slow_entry import forward_entry",src)
        self.assertIn('slow_entry=wait(lambda s,d: forward_entry(s,d),12,"SLOW_ENTRY_FORWARD")',src)
        self.assertIn('world_anchor,slow_entry["pose"],.62,.07,demo_corridor=True',src)
        self.assertLess(src.index('slow_entry=wait('),src.index('slow_target=obstacle_world_pose('))
        self.assertIn('CI_SLOW_FIXTURE_FORWARD_ENTRY_VERIFIED',src)

    def test_stale_actual_scan_or_guard_latch_or_no_positive_odom_must_hold(self):
        s,d=example();s["scan_at"]=99.5
        self.assertIsNone(forward_entry(s,d))
        s,d=example();s["guard"]["latched"]=True
        self.assertIsNone(forward_entry(s,d))
        s,d=example();d["odom"][-1]["vx"]=-.01
        self.assertIsNone(forward_entry(s,d))

if __name__=="__main__":unittest.main()
