"""Task04 regression: observer graph discovery must not authorize Goal before /odom.

The 2026-11-18 native GUI L2 failure #44250223189 had an unnamed
AssertionError before any Goal, after clock/scan/graph readiness. The sole
bare assert inside the moving runner's active try was missing Observer pose.
No synthetic odom or TTL extension is allowed.
"""
import unittest
import p2_g07_ci_moving_goal as moving

class NativeFirstOdomBeforeGoal(unittest.TestCase):
    def setUp(self):
        self.snap={"mono":10.20,"odom_at":10.10}
        self.data={"pose":(-2.0,-0.5,0.0),
                   "odom":[{"t":10.0,"vx":0.0,"wz":0.0},
                           {"t":10.10,"vx":0.0,"wz":0.0}]}

    def test_two_real_fresh_odom_samples_admit_pose(self):
        self.assertEqual(moving._pre_goal_odom_pose(self.snap,self.data),
                         (-2.0,-0.5,0.0))

    def test_graph_and_scan_without_odom_never_admit_goal(self):
        for value in (None,[],[{"t":10.10}]):
            with self.subTest(odom=value):
                candidate={**self.data,"odom":value}
                if value is None:candidate["pose"]=None
                self.assertIsNone(moving._pre_goal_odom_pose(self.snap,candidate))

    def test_stale_odom_missing_timestamp_and_gap_fail_closed(self):
        for snap in ({**self.snap,"odom_at":9.85},
                     {**self.snap,"odom_at":None},
                     {**self.snap,"odom_at":10.25}):
            with self.subTest(snap=snap):
                self.assertIsNone(moving._pre_goal_odom_pose(snap,self.data))
        late={**self.data,"odom":[{"t":9.0},{"t":10.10}]}
        self.assertIsNone(moving._pre_goal_odom_pose(self.snap,late))

if __name__ == "__main__":
    unittest.main()
