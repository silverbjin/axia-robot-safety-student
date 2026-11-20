"""FV17z53O regression: Owner guard timer evidence must exist without CI authority.

Actual field Owner G07 moved/canceled safely, but Guard tick had no
cm_age_sec/supervisor_age_sec/guard_ever_moved, so reviewer held for missing
evidence. Here we test only the evidence *selection*, not Guard policy itself.
"""
import sys
from pathlib import Path
import unittest

R=Path(__file__).resolve().parent
PKG=R.parent/"ros2_ws"/"src"/"axia_safety_supervisor"
sys.path.insert(0,str(PKG))
from axia_safety_supervisor.p2_guard_evidence_mode import internal_timing_evidence_enabled

class GuardEvidenceParity(unittest.TestCase):
    def test_actual_owner_wsl2_profile_collects_guard_timing(self):
        env={"AXIA_G07_TASK04_OWNER_MOVING_L3":"1",
             "AXIA_G07_OWNER_STARTUP_PARITY":"1","AXIA_P0_SIM_ONLY":"1",
             "AXIA_G07_CI_SIM_GOAL_ALLOWED":"0"}
        self.assertTrue(internal_timing_evidence_enabled(env))
        self.assertFalse(internal_timing_evidence_enabled(
            {**env,"AXIA_P0_SIM_ONLY":"0"}))
        self.assertFalse(internal_timing_evidence_enabled(
            {**env,"AXIA_G07_OWNER_STARTUP_PARITY":"0"}))
    def test_existing_public_ci_mode_still_collects_guard_timing(self):
        env={"GITHUB_ACTIONS":"true","AXIA_P0_SIM_ONLY":"1",
             "AXIA_G07_TASK03_FORMAL_CI":"1"}
        self.assertTrue(internal_timing_evidence_enabled(env))
        self.assertFalse(internal_timing_evidence_enabled(
            {**env,"AXIA_G07_TASK03_FORMAL_CI":"0"}))
    def test_default_and_normal_legacy_p2_do_not_add_fields(self):
        self.assertFalse(internal_timing_evidence_enabled({}))
        self.assertFalse(internal_timing_evidence_enabled(
            {"GITHUB_ACTIONS":"true","AXIA_P0_SIM_ONLY":"1"}))
    def test_guard_only_calls_pure_evidence_flag_at_publish(self):
        src=(PKG/"axia_safety_supervisor"/"p2_base_guard_node.py").read_text()
        self.assertIn("internal_timing_evidence_enabled(os.environ)",src)
        for field in ("'cm_age_sec'","'supervisor_age_sec'","'guard_ever_moved'"):
            self.assertIn(field,src)
        self.assertIn("self._policy.step(tick_mono)",src)
        self.assertIn("self._status.publish(status)",src)

if __name__=="__main__":unittest.main()
