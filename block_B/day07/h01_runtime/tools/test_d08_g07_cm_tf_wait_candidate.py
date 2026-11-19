"""RED/GREEN: D08-only official Nav2 CM TF 20ms wait candidate.

Real safety still requires G07 120/150ms native and Guard/source TTL gates.
"""
import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"ros2_ws/src/axia_safety_bringup/launch"))
from axia_p2_launch_policy import apply_d08_g07_tf_wait_candidate
from p2_g07_cm_active_param_readback import validate_values

def params():
    return {"collision_monitor":{"ros__parameters":{
        "transform_tolerance":.2,"base_shift_correction":False,
        "source_timeout":1.0,"stop_pub_timeout":5.0,
        "cmd_vel_in_topic":"cmd_vel_supervised",
        "cmd_vel_out_topic":"cmd_vel_pre_guard",
        "polygons":["AXIA_StopFront","AXIA_SlowFront"]}}}

def ci_env():
    return dict(AXIA_D08_G07_CM_TF_WAIT_CANDIDATE="1",
                AXIA_D08_G07_SINGLE_SESSION="1",
                AXIA_G07_TASK02_SIMPLE_TF_CANDIDATE="1",
                AXIA_G07_OWNER_STARTUP_PARITY="1",
                AXIA_P0_SIM_ONLY="1",
                AXIA_P2_G07_PHYSICAL_PREFLIGHT="1",
                GITHUB_ACTIONS="true",
                AXIA_G07_CI_SIM_GOAL_ALLOWED="1")

class TDD(unittest.TestCase):
    def test_scope_bounded_tf_only_without_ttl_relaxation(self):
        p=params()
        self.assertTrue(apply_d08_g07_tf_wait_candidate(p,ci_env()))
        cm=p["collision_monitor"]["ros__parameters"]
        self.assertEqual(cm["transform_tolerance"],.02)
        self.assertEqual(cm["base_shift_correction"],False)
        self.assertEqual(cm["source_timeout"],1.0)
        self.assertEqual(cm["stop_pub_timeout"],5.0)

    def test_non_opt_in_keeps_existing_default(self):
        p=params()
        self.assertFalse(apply_d08_g07_tf_wait_candidate(p,{}))
        self.assertEqual(p["collision_monitor"]["ros__parameters"]["transform_tolerance"],.2)

    def test_no_ci_or_owner_authority_fails_closed(self):
        p=params()
        bad=ci_env()
        bad["AXIA_G07_CI_SIM_GOAL_ALLOWED"]="0"
        with self.assertRaises(ValueError):
            apply_d08_g07_tf_wait_candidate(p,bad)

    def test_native_readback_must_enforce_bounded_candidate(self):
        data={"stop_pub_timeout":(3,5.0),"base_shift_correction":(1,False),
              "transform_tolerance":(3,.02),"source_timeout":(3,1.0)}
        self.assertEqual(validate_values(data,require_simple_tf=True,
              d08_g07_tf_wait=True)["status"],"ACTIVE_CM_NATIVE_PARAMETER_READBACK_PASS")
        data["transform_tolerance"]=(3,.2)
        self.assertNotEqual(validate_values(data,require_simple_tf=True,
              d08_g07_tf_wait=True)["status"],"ACTIVE_CM_NATIVE_PARAMETER_READBACK_PASS")

if __name__=="__main__":
    unittest.main()
