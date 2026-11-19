"""S75/n7 Owner Guard read-only telemetry: fail before running another WSL2 Goal."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "ros2_ws/src/axia_safety_supervisor/axia_safety_supervisor/p2_base_guard_node.py"


def load_evidence_scope():
    tree = ast.parse(GUARD.read_text())
    found = [n for n in tree.body if isinstance(n, ast.FunctionDef)
             and n.name == "_task04_timing_evidence_enabled"]
    assert len(found) == 1, "OWNER_GUARD_TIMING_SCOPE_HELPER_MISSING"
    ns = {}
    exec(compile(ast.Module(body=found, type_ignores=[]), str(GUARD), "exec"), ns)
    return ns[found[0].name]


class OwnerN7GuardTelemetryRegression(unittest.TestCase):
    def test_ci_formal_preserved_and_interactive_owner_enabled(self):
        allowed = load_evidence_scope()
        self.assertTrue(allowed({"GITHUB_ACTIONS": "true", "AXIA_P0_SIM_ONLY": "1",
                                 "AXIA_G07_TASK03_FORMAL_CI": "1"}))
        self.assertTrue(allowed({"AXIA_P0_SIM_ONLY": "1",
                                 "AXIA_G07_TASK04_OWNER_MOVING_L3": "1",
                                 "AXIA_G07_OWNER_STARTUP_PARITY": "1"}))
        for invalid in (
            {}, {"AXIA_P0_SIM_ONLY": "1"},
            {"GITHUB_ACTIONS": "true", "AXIA_P0_SIM_ONLY": "1",
             "AXIA_G07_TASK04_OWNER_MOVING_L3": "1",
             "AXIA_G07_OWNER_STARTUP_PARITY": "1"},
            {"AXIA_P0_SIM_ONLY": "1", "AXIA_G07_TASK04_OWNER_MOVING_L3": "1"},
            {"AXIA_G07_TASK04_OWNER_MOVING_L3": "1",
             "AXIA_G07_OWNER_STARTUP_PARITY": "1"},
            {"GITHUB_ACTIONS": "true", "AXIA_G07_TASK03_FORMAL_CI": "1"},
        ):
            with self.subTest(invalid=invalid):
                self.assertFalse(allowed(invalid))

    def test_owner_numeric_report_preserves_unmodified_wallclock_gap(self):
        # Owner small diagnostics must retain the raw RMW 2.964s jump as
        # evidence, not silently present only the normalized 38ms envelope.
        src=(ROOT/"tools/p2_g07_task04_moving_review.py").read_text()
        for key in ('"source_raw_gap_max_ms"', '"clock_step_pairs"',
                    '"clock_step_evidence"', '"host_external_clock_verified"'):
            self.assertIn('cm.get('+key+')',src)

    def test_owner_numeric_review_is_scoped_to_actual_timing_oracle(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        from p2_g07_task04_moving_review import accepted_cm_scope
        self.assertTrue(accepted_cm_scope(
            "TASK02_PUBLIC_L2_NUMERICAL_CANDIDATE", "ci"))
        self.assertTrue(accepted_cm_scope(
            "TASK02_OWNER_NATIVE_NUMERICAL_CANDIDATE", "owner"))
        self.assertTrue(accepted_cm_scope(
            "TASK02_OWNER_MONOTONIC_CLOCK_STEP_NUMERICAL_CANDIDATE", "owner"))
        for status,scope in (
            ("TASK02_OWNER_NATIVE_NUMERICAL_CANDIDATE", "ci"),
            ("TASK02_PUBLIC_L2_NUMERICAL_CANDIDATE", "owner"),
            ("TASK02_ACTUAL_GOAL_OR_GUARD_UNVERIFIED_HOLD", "owner"),
            ("TASK02_CM120_SOURCE_OR_OBSERVER_FIRST_VIOLATION_HOLD", "owner"),
            ("TASK02_CLOCK_STEP_WITHOUT_DUAL_RMW_PROOF_HOLD", "owner"),
        ):
            self.assertFalse(accepted_cm_scope(status, scope))


if __name__ == "__main__":
    unittest.main()
