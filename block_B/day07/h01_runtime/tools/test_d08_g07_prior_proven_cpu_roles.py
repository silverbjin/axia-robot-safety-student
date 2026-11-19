"""RED: reuse prior real G07 Cycle36 isolated CM/Gazebo physical server roles.

Actual L2 #43863443121 passed <=120ms CM with CM cores {1,2},
official gz server core {3}, and separate GUI/observer core0.
No ROS or OS affinity changes in these tests.
"""
import unittest
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from d08_g07_prior_proven_cpu_roles import choose_cpu_roles, match_roles, validate_scope

class TestG07PriorProvenCPUSeparation(unittest.TestCase):
    def test_reuse_exact_prior_successful_four_core_partition(self):
        cm,gz=choose_cpu_roles({0,1,2,3})
        self.assertEqual(cm,{1,2})
        self.assertEqual(gz,{3})
        self.assertTrue(cm.isdisjoint(gz))
    def test_eight_core_partition_and_cgroups(self):
        self.assertEqual(choose_cpu_roles(set(range(8))),({1,6},{2,3,4,5,7}))
        self.assertEqual(choose_cpu_roles({24,25,26,27}),({25,26},{27}))
        with self.assertRaises(ValueError):
            choose_cpu_roles({0,1,2})
    def test_exact_one_owned_cm_and_native_gz_server(self):
        records=[
            (42,40,["/opt/ros/jazzy/lib/nav2_collision_monitor/collision_monitor","--ros-args"],1000),
            (43,40,["gz sim -r -s /tmp/nav2_ABC123.sdf"],1000),
            (44,40,["gz","sim","-g"],1000),
            (45,99,["/opt/ros/jazzy/lib/nav2_collision_monitor/collision_monitor"],1000),
            (46,40,["gz sim -r -s /tmp/nav2_ABC123.sdf"],999),
        ]
        self.assertEqual(match_roles(records,40,1000),(42,43))
        with self.assertRaises(ValueError):
            match_roles(records+[(47,40,["gz sim -r -s /tmp/nav2_OTHER.sdf"],1000)],40,1000)
    def test_no_goal_authorization_or_wsl2_ci_spoof(self):
        env={"GITHUB_ACTIONS":"true","AXIA_P0_SIM_ONLY":"1",
          "AXIA_P2_G07_PHYSICAL_PREFLIGHT":"1",
          "AXIA_G07_TASK04_CI_GUI_MOVING":"1",
          "AXIA_G07_CI_SIM_GOAL_ALLOWED":"1",
          "AXIA_D08_G07_SINGLE_SESSION":"1",
          "AXIA_G07_OWNER_STARTUP_PARITY":"1",
          "AXIA_D08_G07_CPU_ROLE_C36":"1"}
        self.assertTrue(validate_scope(env))
        for k in ("GITHUB_ACTIONS","AXIA_G07_CI_SIM_GOAL_ALLOWED",
                  "AXIA_D08_G07_SINGLE_SESSION"):
            bad=dict(env);bad[k]="0"
            with self.assertRaises(ValueError):
                validate_scope(bad)
if __name__=="__main__":unittest.main()
