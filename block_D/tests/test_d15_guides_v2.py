"""D15 38-slide beginner/demo documentation release contract (no ROS runtime)."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
DAY = ROOT / "block_D" / "day15"

class D15DetailedGuideContract(unittest.TestCase):
    def test_student_demo_exists_and_replays_seven_steps(self):
        p = DAY / "STUDENT_DEMO_GUIDE_KO.md"
        self.assertTrue(p.is_file(), "D15 beginner demo guide missing")
        s = p.read_text(encoding="utf-8")
        for token in ("git clone --branch main", "run_lab.py", "explorer.exe",
                      "d15_evidence_review.json", "d15_counterexamples.json",
                      "CLEAR", "SLOW", "STOP", "CANCEL", "ODOM_DWELL",
                      "SAFETY_TTL", "PNU_AND_SCOPE", "first_violation_timestamp",
                      "HOLD_RAW_REVIEW_AND_VISUAL_PENDING", "NOT_RUN"):
            with self.subTest(token=token):
                self.assertIn(token, s)
    def test_student_lab_has_beginner_stepwise_details(self):
        s = (DAY / "STUDENT_LAB_GUIDE_KO.md").read_text(encoding="utf-8")
        for token in ("## 9. 38장", "입력 → 처리 → 출력", "d15_offline_replay.html",
                      "git rev-parse HEAD", "D15_SYNTHETIC_NEGATIVE_DETECTION=5/5",
                      "SCAN_301MS", "GUARD_151MS", "NO_ROS_GAZEBO",
                      "SW Stop"):
            with self.subTest(token=token):
                self.assertIn(token, s)
    def test_no_instructor_solution_leak_and_scope_protected(self):
        s = (DAY / "STUDENT_DEMO_GUIDE_KO.md").read_text(encoding="utf-8")
        for forbidden in ("training/block_D/day15/INSTRUCTOR_ANSWER_KEY_KO.md", "BEGIN PRIVATE KEY"):
            self.assertNotIn(forbidden, s)
        self.assertIn("학생용 공개", s)
        self.assertNotIn("G11_FORMAL_ACCEPTED=true", s)

if __name__ == "__main__":
    unittest.main()
