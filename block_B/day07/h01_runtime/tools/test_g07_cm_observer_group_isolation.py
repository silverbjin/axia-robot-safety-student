"""Owner 1ibYCGPg: 124.069ms CM Observer callback gap while DDS Received
interval was 41.902ms. No change to any CM/Guard/Goal publisher or TTL.

ROS2 defaults to a single MutuallyExclusiveCallbackGroup per node; two
MultiThreadedExecutor workers cannot concurrently dispatch all callbacks
of that one default group. Scope ONLY existing read-only pre_guard and
supervised subscriptions onto distinct exclusive groups (opt-in) so
busy /clock/scan/guard callbacks on default group cannot block both.
"""
import unittest
from pathlib import Path
from p2_g07_observer_cb_group_policy import scoped_cm_groups

ROOT=Path(__file__).parent
OBSERVER=ROOT/"p2_l3_live_session.py"
RUNNER=ROOT/"p2_g07_ci_moving_goal.py"

class TestCMIsolatedObserverGroups(unittest.TestCase):
    def test_disabled_default_is_exactly_original(self):
        calls=[]
        self.assertEqual(scoped_cm_groups({
            "AXIA_G07_OWNER_STARTUP_PARITY":"1",
            "AXIA_G07_CM_OBSERVER_GROUPS":"0"},lambda:calls.append(object())),(None,None))
        self.assertEqual(calls,[])

    def test_enabled_creates_two_distinct_groups_once_without_ros(self):
        calls=[]
        def factory():
            group=object();calls.append(group);return group
        groups=scoped_cm_groups({
            "AXIA_G07_OWNER_STARTUP_PARITY":"1",
            "AXIA_G07_CM_OBSERVER_GROUPS":"1"},factory)
        self.assertEqual(len(calls),2)
        self.assertIs(groups[0],calls[0])
        self.assertIs(groups[1],calls[1])
        self.assertIsNot(groups[0],groups[1])

    def test_nonparity_or_bad_value_cannot_opt_in(self):
        for env in ({
              "AXIA_G07_OWNER_STARTUP_PARITY":"0",
              "AXIA_G07_CM_OBSERVER_GROUPS":"1"},
              {"AXIA_G07_CM_OBSERVER_GROUPS":"1"},
              {"AXIA_G07_OWNER_STARTUP_PARITY":"1",
               "AXIA_G07_CM_OBSERVER_GROUPS":"yes"}):
            with self.subTest(env=env),self.assertRaisesRegex(ValueError,"G07_CM_OBSERVER"):
                scoped_cm_groups(env,object)

    def test_exact_existing_twist_subscriptions_grouped_other_subs_untouched(self):
        s=OBSERVER.read_text()
        self.assertIn("from rclpy.callback_groups import MutuallyExclusiveCallbackGroup",s)
        self.assertIn("scoped_cm_groups(os.environ,MutuallyExclusiveCallbackGroup)",s)
        # Official Jazzy callback groups need a strong Node/Observer lifetime
        # reference; constructor locals can be GC'd after __init__ returns.
        self.assertIn("self._g07_cm_observer_callback_groups=(cm_group,supervised_group)",s)
        self.assertIn("callback_group=cm_group",s)
        self.assertIn("callback_group=supervised_group",s)
        self.assertIn("'/cmd_vel_pre_guard'",s)
        self.assertIn("'/cmd_vel_supervised'",s)
        self.assertIn("def sub(cls,topic,fn,qos,callback_group=None)",s)
        self.assertIn("node.create_subscription(cls,topic,fn,qos,callback_group=callback_group)",s)
        self.assertIn("sub(Clock,'/clock',self._clock,qos_profile_sensor_data)",s)
        self.assertIn("sub(LaserScan,'/safety/scan',self._scan,qos_profile_sensor_data)",s)

    def test_original_cancel_goal_and_safety_limits_unchanged(self):
        s=RUNNER.read_text()
        self.assertIn('_task03_exact_goal_terminal(node,obs,goal_uuid)',s)
        self.assertIn('stop_dwell=wait(dwell,3.5,"ODOM_STOP_DWELL")',s)
        self.assertIn("max_cm_interval_sec",s)
        self.assertNotIn("AXIA_G07_CM_OBSERVER_GROUPS",s)

if __name__=="__main__":unittest.main()
