"""Native S1 #44859276354 cycle1 pre-Goal clock window HOLD,
cycle2 real Gazebo Goal PASS (max flush only1.05ms).
No TTL, QoS, Nav2/CM/Guard, Goal or sensor frequency changes allowed.
"""
from collections import deque
from pathlib import Path
import unittest

import p2_g07_scan_wall_pregoal as pregoal
ROOT=Path(__file__).parent


class ClockCoverageAndPostGoalGraph(unittest.TestCase):
    def test_high_frequency_clock_full_12s_coverage_without_ttl_relaxation(self):
        # Native Gazebo /clock can exceed 4096 callbacks during the same
        # 12s preflight. Earlier fixed deque truncated the first wall seconds.
        self.assertGreaterEqual(pregoal.CLOCK_WINDOW_MAX_SAMPLES,6001)
        clock=deque(maxlen=pregoal.CLOCK_WINDOW_MAX_SAMPLES)
        for i in range(6001):
            t=i*.002
            clock.append((t,t))
        scans=[(i*.1,i*.1) for i in range(121)]
        safety=[(t+.001,stamp) for t,stamp in scans]
        data={"clock":list(clock),"scan":scans,
              "safety_scan":safety,"odom":[(i*.1,i*.1) for i in range(121)]}
        r=pregoal.assess_pregoal_samples(data,window_sec=12.)
        self.assertEqual(r["status"],"PASS_SCOPED_RECEIVED_SCAN_ONLY")
        self.assertEqual(r["clock_coverage"],"FULL_PREG0AL_WINDOW")
        self.assertLess(r["clock_max_wall_gap_ms"],300)

    def test_truncated_clock_history_still_fails_closed_not_false_pass(self):
        data={"clock":[(i*.002,i*.002) for i in range(6001)][-4096:],
              "scan":[(i*.1,i*.1) for i in range(121)],
              "safety_scan":[(i*.1+.001,i*.1) for i in range(121)],
              "odom":[(i*.1,i*.1) for i in range(121)]}
        r=pregoal.assess_pregoal_samples(data,window_sec=12.)
        self.assertEqual(r["status"],"HOLD")
        self.assertEqual(r["first_failure"],"SCAN_PREFLIGHT_CLOCK_RETENTION_INSUFFICIENT")
        self.assertFalse(r["goal_sent"])

    def test_post_goal_does_not_repeat_3_dds_graph_queries(self):
        s=(ROOT/"p2_g07_ci_moving_goal.py").read_text()
        post=s.split("        graph_checks=False",1)[1].split(
                  "        obs.flush_events()",1)[0]
        # All four original call sites use ONLY goal status, goal UUID or
        # Guard/Scan values, never publisher graph metadata.
        self.assertNotIn("obs.snapshot()",post)
        self.assertIn('report["goal_status_at_clear"]=obs.snapshot(include_graph=False)',post)
        self.assertIn('goal_uuid=obs.snapshot(include_graph=False)["goal_uuid"]',post)
        self.assertIn('snap=obs.snapshot(include_graph=False)',post)
        self.assertIn('latest=obs.snapshot(include_graph=False)',post)
        # Exact Goal and stop/cancel ordering remains immutable.
        self.assertIn('_task03_exact_goal_terminal(node,obs,goal_uuid)',s)
        self.assertIn('graph_checks=False',s)
        self.assertIn('AXIA_G07_OBSERVER_IO_PROBE',s)

    def test_original_pre_goal_graph_authority_remains(self):
        s=(ROOT/"p2_g07_ci_moving_goal.py").read_text()
        pre=s.split("        graph_checks=False",1)[0]
        self.assertIn("graph_checks=True",pre)
        self.assertIn('wait(real_graph_ready,12,"EXCLUSIVE_SUPERVISOR_CM_GUARD_GRAPH")',pre)
        self.assertIn("snap=obs.snapshot()",pre)
        self.assertEqual(pregoal.SCAN_LIMIT_MS,300.0)
        self.assertEqual(pregoal.HEADER_SIM_LIMIT_MS,150.0)


if __name__=="__main__":
    unittest.main()
