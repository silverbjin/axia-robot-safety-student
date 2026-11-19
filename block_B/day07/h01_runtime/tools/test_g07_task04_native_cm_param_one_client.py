"""Single native CM get_parameters request, never assume loaded YAML equals live node.

Regression #44263077295: first ros2 param get succeeded then the next
independent CLI DDS participant timed out before Goal despite staged READY.
"""
import unittest
from pathlib import Path
from p2_g07_cm_active_param_readback import validate_values

SHELL=(Path(__file__).resolve().parents[1]/"scripts/p2_no_goal_smoke_ci.sh")

class NativeCMParameterReadback(unittest.TestCase):
    def test_all_four_exact_runtime_values(self):
        got={"stop_pub_timeout":(3,5.0),
             "base_shift_correction":(1,False),
             "transform_tolerance":(3,0.2),
             "source_timeout":(3,1.0)}
        self.assertEqual(validate_values(got,require_simple_tf=True)["status"],
                         "ACTIVE_CM_NATIVE_PARAMETER_READBACK_PASS")
        self.assertEqual(validate_values({"stop_pub_timeout":(3,5.0)},
                         require_simple_tf=False)["status"],
                         "ACTIVE_CM_NATIVE_PARAMETER_READBACK_PASS")

    def test_missing_wrong_type_or_wrong_value_fails_closed(self):
        ok={"stop_pub_timeout":(3,5.0),
            "base_shift_correction":(1,False),
            "transform_tolerance":(3,0.2),
            "source_timeout":(3,1.0)}
        for key,bad in (("stop_pub_timeout",(3,1.0)),
                        ("base_shift_correction",(1,True)),
                        ("transform_tolerance",(3,0.6)),
                        ("source_timeout",(3,0.0)),
                        ("source_timeout",(1,True)),
                        ("stop_pub_timeout",(0,5.0))):
            with self.subTest(key=key,bad=bad):
                v={**ok,key:bad}
                self.assertNotEqual(validate_values(v,require_simple_tf=True)["status"],
                                    "ACTIVE_CM_NATIVE_PARAMETER_READBACK_PASS")
        missing={**ok};missing.pop("source_timeout")
        self.assertNotEqual(validate_values(missing,require_simple_tf=True)["status"],
                            "ACTIVE_CM_NATIVE_PARAMETER_READBACK_PASS")

    def test_one_ros_service_request_not_four_ros2_cli_processes(self):
        sh=SHELL.read_text()
        self.assertIn("p2_g07_cm_active_param_readback.py",sh)
        self.assertNotIn("ros2 param get /collision_monitor",sh)
        self.assertIn("AXIA_G07_TASK02_SIMPLE_TF_CANDIDATE",sh)
        self.assertIn("AXIA_G07_CI_MOVING_GOAL_PREG0AL_NATIVE_FIXTURE_BEGIN",sh)

if __name__=="__main__":
    unittest.main()
