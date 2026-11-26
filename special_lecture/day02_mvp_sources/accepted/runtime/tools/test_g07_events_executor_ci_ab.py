"""Official Jazzy EventsExecutor backport #1435: CI-only scoped scheduling A/B.

Native G07 #44860872488 2/2 failed WITHOUT a Goal: first scan/odom/clock
300ms boundary despite 99-102ms real header cadence. No safety override.
"""
from pathlib import Path
import unittest
from p2_g07_events_executor_policy import select_events_executor

ROOT=Path(__file__).parent


def ci_env(**overrides):
    e={"AXIA_G07_EVENTS_EXECUTOR_AB":"1",
       "GITHUB_ACTIONS":"true",
       "AXIA_G07_CI_SIM_GOAL_ALLOWED":"1",
       "AXIA_P0_SIM_ONLY":"1",
       "AXIA_G07_OWNER_STARTUP_PARITY":"1"}
    e.update(overrides)
    return e


class JazzyEventsNoNewSafetyComponents(unittest.TestCase):
    def test_default_retains_original_executor_unchanged(self):
        self.assertFalse(select_events_executor({},owner_mode=False))
        self.assertFalse(select_events_executor(ci_env(AXIA_G07_EVENTS_EXECUTOR_AB="0"),owner_mode=False))
        self.assertFalse(select_events_executor(ci_env(AXIA_G07_EVENTS_EXECUTOR_AB=""),owner_mode=False))

    def test_ci_only_opt_in_requires_full_simulation_authority(self):
        self.assertTrue(select_events_executor(ci_env(),owner_mode=False))
        for k,v in (("GITHUB_ACTIONS","false"),
                    ("AXIA_G07_CI_SIM_GOAL_ALLOWED","0"),
                    ("AXIA_P0_SIM_ONLY","0"),
                    ("AXIA_G07_OWNER_STARTUP_PARITY","0")):
            with self.subTest(k=k),self.assertRaisesRegex(ValueError,"G07_EVENTS_EXECUTOR_SCOPE_DENIED"):
                select_events_executor(ci_env(**{k:v}),owner_mode=False)
        with self.assertRaisesRegex(ValueError,"G07_EVENTS_EXECUTOR_SCOPE_DENIED"):
            select_events_executor(ci_env(),owner_mode=True)

    def test_invalid_env_fails_before_goal(self):
        for bad in ("true","EventsExecutor","single","auto","YES"):
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,"G07_EVENTS_EXECUTOR_INVALID_VALUE"):
                select_events_executor(ci_env(AXIA_G07_EVENTS_EXECUTOR_AB=bad),owner_mode=False)

    def test_event_executor_used_by_both_pre_goal_and_one_moving_observer_only(self):
        pre=(ROOT/"p2_g07_scan_wall_pregoal.py").read_text()
        mov=(ROOT/"p2_g07_ci_moving_goal.py").read_text()
        self.assertIn("from rclpy.experimental import EventsExecutor",pre)
        self.assertIn("select_events_executor(os.environ,owner_mode=False)",pre)
        self.assertIn("EventsExecutor()",pre)
        self.assertIn("executor.spin_once(timeout_sec=.04)",pre)
        self.assertIn("from rclpy.experimental import EventsExecutor",mov)
        self.assertIn("events_candidate=select_events_executor(",mov)
        self.assertIn("os.environ,owner_mode=owner_mode)",mov)
        self.assertIn("EventsExecutor()",mov)
        self.assertIn("MultiThreadedExecutor(num_threads=2 if owner_observer_parity else 3)",mov)
        self.assertIn('wait(real_graph_ready,12,"EXCLUSIVE_SUPERVISOR_CM_GUARD_GRAPH")',mov)
        self.assertIn("_task03_exact_goal_terminal(node,obs,goal_uuid)",mov)
        self.assertIn("SCAN_LIMIT_MS=300.0",pre)
        self.assertIn("HEADER_SIM_LIMIT_MS=150.0",pre)
        self.assertNotIn("CM_TTL_SEC =",mov)
        self.assertNotIn("CERTIFIED_ESTOP=true",mov)


if __name__=="__main__":unittest.main()
