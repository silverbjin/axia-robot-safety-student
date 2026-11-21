"""D13 documentation-only regression: published clone-to-demo workflow contracts."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D13 = ROOT / "block_D" / "day13"

class D13GuideContract(unittest.TestCase):
    def test_student_documents_publish_main_clone_and_command_sequence(self):
        for name in ("STUDENT_LAB_GUIDE_KO.md", "STUDENT_DEMO_GUIDE_KO.md"):
            guide = (D13 / name).read_text(encoding="utf-8")
            for token in ("git clone --branch main", "axia-d13-student",
                          "run_lab.py --out /tmp/axia-d13", "Ran 10 tests",
                          "RED_EXPECTED_TODO", "GREEN", "ROS"):
                self.assertIn(token, guide, f"{name}: {token}")
            self.assertGreater(len(guide), 2500)

    def test_eight_fixture_ids_and_sensitive_adapter_boundary(self):
        guide = (D13 / "STUDENT_LAB_GUIDE_KO.md").read_text(encoding="utf-8")
        for name in ("P_same_time_overlap", "N_same_route_different_time",
                     "U_stale_track", "U_future_stamp", "U_low_confidence",
                     "U_frame_mismatch", "U_missing_last_sample", "U_time_jump"):
            self.assertIn(name, guide)
        self.assertIn("map", guide)
        self.assertIn("odom", guide)

    def test_no_private_solution_deployed_and_starter_unmodified(self):
        self.assertEqual(list((ROOT / "block_D").rglob("p3_oracles.py")), [])
        self.assertIn('return "U"', (D13 / "reachability_student.py").read_text())

if __name__ == "__main__":
    unittest.main()
