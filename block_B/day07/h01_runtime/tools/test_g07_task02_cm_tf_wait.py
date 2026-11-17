"""RED->GREEN public-only Task02: preserve advanced TF geometry; cap wait.

No ROS, no new Goal, no changing official Nav2 sources or safety TTL.
"""
import copy
import importlib.util
from pathlib import Path
import unittest

POLICY=Path(__file__).resolve().parents[1]/"ros2_ws/src/axia_safety_bringup/launch/axia_p2_launch_policy.py"
spec=importlib.util.spec_from_file_location("axia_p2_launch_policy",POLICY)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def config():
    return {
        "collision_monitor":{"ros__parameters":{
            "transform_tolerance":0.2,
            "base_shift_correction":True,
            "source_timeout":1.0,
            "stop_pub_timeout":5.0,
            "cmd_vel_in_topic":"cmd_vel_supervised",
            "cmd_vel_out_topic":"cmd_vel_pre_guard",
            "polygons":["AXIA_StopFront","AXIA_SlowFront"]}},
        "controller_server":{"ros__parameters":{"xy_goal_tolerance":0.1}},
    }


def authorized():
    return dict(GITHUB_ACTIONS="true",AXIA_P0_SIM_ONLY="1",
        AXIA_G07_CI_SIM_GOAL_ALLOWED="1",AXIA_G07_OWNER_STARTUP_PARITY="1",
        AXIA_G07_TASK02_TF_WAIT_CANDIDATE="1")


class OneMinimalTfWaitCandidate(unittest.TestCase):
    def test_only_expected_cm_tf_tolerance_changes(self):
        p=config()
        before=copy.deepcopy(p)
        self.assertIs(module.apply_g07_task02_tf_wait_candidate(p,authorized()),True)
        before["collision_monitor"]["ros__parameters"]["transform_tolerance"]=0.02
        self.assertEqual(p,before)
        cm=p["collision_monitor"]["ros__parameters"]
        self.assertIs(cm["base_shift_correction"],True)
        self.assertEqual(cm["source_timeout"],1.0)
        self.assertEqual(cm["stop_pub_timeout"],5.0)

    def test_not_opted_in_preserves_official_value(self):
        p=config()
        self.assertIs(module.apply_g07_task02_tf_wait_candidate(p,{}),False)
        self.assertEqual(p["collision_monitor"]["ros__parameters"]["transform_tolerance"],0.2)

    def test_scoped_only_public_sim_and_exact_owner(self):
        for removed in ("GITHUB_ACTIONS","AXIA_P0_SIM_ONLY","AXIA_G07_CI_SIM_GOAL_ALLOWED","AXIA_G07_OWNER_STARTUP_PARITY"):
            e=authorized()
            e.pop(removed)
            p=config()
            with self.subTest(removed=removed),self.assertRaises(ValueError):
                module.apply_g07_task02_tf_wait_candidate(p,e)
            self.assertEqual(p["collision_monitor"]["ros__parameters"]["transform_tolerance"],0.2)

    def test_never_relax_safety_params_or_accept_unknown_official_tf_value(self):
        for key,value in (("transform_tolerance",0.3),("base_shift_correction",False),
                          ("source_timeout",0.0),("stop_pub_timeout",2.0)):
            p=config()
            p["collision_monitor"]["ros__parameters"][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                module.apply_g07_task02_tf_wait_candidate(p,authorized())

    def test_candidate_is_not_runtime_or_e_stop_release(self):
        p=config()
        module.apply_g07_task02_tf_wait_candidate(p,authorized())
        self.assertNotIn("certified_estop",p["collision_monitor"]["ros__parameters"])
        self.assertNotIn("axia_task02_release_pass",p["collision_monitor"]["ros__parameters"])


if __name__=="__main__":
    unittest.main()
