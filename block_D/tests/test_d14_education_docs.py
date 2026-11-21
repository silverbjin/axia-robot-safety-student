"""D14 교육 가이드: 공개 TODO 및 실제 실행 경로 계약 (ROS-free)."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D14 = ROOT / "block_D" / "day14"

class D14EducationDocsContract(unittest.TestCase):
    def read(self, filename):
        return (D14 / filename).read_text(encoding="utf-8")

    def test_demo_guide_clones_and_runs_without_ros(self):
        s = self.read("STUDENT_DEMO_GUIDE_KO.md")
        for token in ("git clone", "git rev-parse HEAD", "unittest discover",
                      "run_lab.py", "explorer.exe", "RED_EXPECTED_TODO", "NO_ROS_GAZEBO"):
            self.assertIn(token, s)
        self.assertIn("SW STOP", s)
        self.assertIn("E-Stop", s)

    def test_lab_beginner_steps_and_outputs(self):
        s = self.read("STUDENT_LAB_GUIDE_KO.md")
        for token in ("apply_verdict()", "expired_verdict()", "last_rx_mono",
                      "seq", "0.5", "11", "20", "16", "15",
                      "STUDENT_WORKSHEET_KO.md", "runner_rc", "expected", "actual"):
            self.assertIn(token, s)
        self.assertIn("choose_action_intent", s)
        self.assertIn("NOT_IMPLEMENTED", s)

    def test_worksheet_provenance_and_first_violation(self):
        s = self.read("STUDENT_WORKSHEET_KO.md")
        for token in ("SCAN_FAULT", "CM_LOST", "GUARD_LATCH", "FINAL_CMD",
                      "첫", "0.5", "Goal", "SW Stop"):
            self.assertIn(token, s)

    def test_guides_dont_publish_instructor_solution(self):
        for name in ("STUDENT_DEMO_GUIDE_KO.md","STUDENT_LAB_GUIDE_KO.md","STUDENT_WORKSHEET_KO.md"):
            t = self.read(name)
            self.assertNotIn("training/block_D/day14/solution/", t)
            self.assertNotIn("p3_g09_risk_policy.py", t)
            self.assertNotIn("p3_g10_compound.py", t)
            self.assertNotIn("FORMAL_G10_PASS", t)

    def test_fixture_names_are_real(self):
        policy = json.loads((D14/"fixtures/policy_events.json").read_text(encoding="utf-8"))
        g10 = json.loads((D14/"fixtures/g10_events.json").read_text(encoding="utf-8"))
        self.assertEqual(len(policy["cases"]),16)
        self.assertEqual(len(g10["events"]),15)
        events = {e["event"] for e in g10["events"]}
        self.assertTrue({"SCAN_FAULT","CM_LOST","GUARD_LATCH","FINAL_CMD","NO_AUTO_RESUME"} <= events)

if __name__ == "__main__":
    unittest.main()
