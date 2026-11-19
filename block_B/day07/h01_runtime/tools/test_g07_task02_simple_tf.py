"""One official Nav2 CM Simple TF candidate; public CI simulation only.

No Nav2 fork; positive source_timeout invalid-scan STOP remains authoritative.
Correction is intentionally disabled ONLY in bounded Gazebo teaching candidate.
"""
import copy
import importlib.util
from pathlib import Path
import unittest

POLICY=Path(__file__).resolve().parents[1]/"ros2_ws/src/axia_safety_bringup/launch/axia_p2_launch_policy.py"
spec=importlib.util.spec_from_file_location("axia_p2_launch_policy",POLICY)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def cfg():
    return {"collision_monitor":{"ros__parameters":{
      "transform_tolerance":0.2,"base_shift_correction":True,
      "source_timeout":1.0,"stop_pub_timeout":5.0,
      "cmd_vel_in_topic":"cmd_vel_supervised",
      "cmd_vel_out_topic":"cmd_vel_pre_guard",
      "polygons":["AXIA_StopFront","AXIA_SlowFront"]}}}


def authorized():
    return {"GITHUB_ACTIONS":"true","AXIA_P0_SIM_ONLY":"1",
     "AXIA_G07_CI_SIM_GOAL_ALLOWED":"1",
     "AXIA_G07_OWNER_STARTUP_PARITY":"1",
     "AXIA_P2_G07_PHYSICAL_PREFLIGHT":"1",
     "AXIA_G07_TASK02_SIMPLE_TF_CANDIDATE":"1"}


class OneSimpleTfCandidate(unittest.TestCase):
    def test_exactly_one_official_cm_flag_changes(self):
        x=cfg()
        expected=copy.deepcopy(x)
        expected["collision_monitor"]["ros__parameters"]["base_shift_correction"]=False
        self.assertTrue(module.apply_g07_task02_simple_tf_candidate(x,authorized()))
        self.assertEqual(x,expected)
        cm=x["collision_monitor"]["ros__parameters"]
        self.assertEqual(cm["transform_tolerance"],0.2)
        self.assertEqual(cm["source_timeout"],1.0)
        self.assertEqual(cm["stop_pub_timeout"],5.0)

    def test_unselected_run_keeps_original_advanced_source(self):
        x=cfg()
        self.assertFalse(module.apply_g07_task02_simple_tf_candidate(x,{}))
        self.assertIs(x["collision_monitor"]["ros__parameters"]["base_shift_correction"],True)

    def test_denies_hardware_owner_and_missing_ci_authority(self):
        for key in ("GITHUB_ACTIONS","AXIA_P0_SIM_ONLY",
                    "AXIA_G07_CI_SIM_GOAL_ALLOWED","AXIA_G07_OWNER_STARTUP_PARITY"):
            e=authorized()
            del e[key]
            x=cfg()
            with self.subTest(key=key),self.assertRaises(ValueError):
                module.apply_g07_task02_simple_tf_candidate(x,e)
            self.assertIs(x["collision_monitor"]["ros__parameters"]["base_shift_correction"],True)

    def test_owner_manual_sim_parity_without_ci_goal_spoof(self):
        owner={"GITHUB_ACTIONS":"false","AXIA_P0_SIM_ONLY":"1",
               "AXIA_G07_CI_SIM_GOAL_ALLOWED":"0",
               "AXIA_G07_OWNER_STARTUP_PARITY":"1",
               "AXIA_P2_G07_PHYSICAL_PREFLIGHT":"1",
               "AXIA_P2_G07_RELOCATED_OBSTACLE":"1",
               "AXIA_G07_TASK04_OWNER_MOVING_L3":"1",
               "AXIA_G07_TASK02_SIMPLE_TF_CANDIDATE":"1"}
        x=cfg()
        self.assertTrue(module.apply_g07_task02_simple_tf_candidate(x,owner))
        self.assertIs(x["collision_monitor"]["ros__parameters"]["base_shift_correction"],False)
        for key in ("AXIA_P0_SIM_ONLY", "AXIA_G07_OWNER_STARTUP_PARITY",
                    "AXIA_P2_G07_RELOCATED_OBSTACLE",
                    "AXIA_G07_TASK04_OWNER_MOVING_L3",
                    "AXIA_P2_G07_PHYSICAL_PREFLIGHT"):
            bad=dict(owner);bad.pop(key)
            with self.subTest(key=key),self.assertRaises(ValueError):
                module.apply_g07_task02_simple_tf_candidate(cfg(),bad)
        for update in ({"GITHUB_ACTIONS":"true"},
                       {"AXIA_G07_CI_SIM_GOAL_ALLOWED":"1"}):
            bad={**owner,**update}
            with self.subTest(update=update),self.assertRaises(ValueError):
                module.apply_g07_task02_simple_tf_candidate(cfg(),bad)

    def test_source_timeout_and_polygon_geometry_cannot_be_weakened(self):
        for key,value in (("transform_tolerance",.02),("source_timeout",0.0),
                          ("stop_pub_timeout",2.0),
                          ("base_shift_correction",False),
                          ("polygons",["AXIA_StopFront"])):
            x=cfg()
            x["collision_monitor"]["ros__parameters"][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                module.apply_g07_task02_simple_tf_candidate(x,authorized())

    def test_not_certified_estop_or_general_fast_robot_preset(self):
        x=cfg()
        module.apply_g07_task02_simple_tf_candidate(x,authorized())
        cm=x["collision_monitor"]["ros__parameters"]
        self.assertNotIn("certified_estop",cm)
        self.assertNotIn("full_robot_safety_accepted",cm)


if __name__=="__main__":
    unittest.main()
