"""D13 beginner-guide educational evidence contract; documentation-only, no ROS."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "block_D" / "day13" / "STUDENT_LAB_GUIDE_KO.md"
WORKSHEET = ROOT / "block_D" / "day13" / "STUDENT_WORKSHEET_KO.md"

class D13BeginnerGuideContract(unittest.TestCase):
    def test_student_can_execute_scaffold_and_read_actual_source(self):
        text = GUIDE.read_text(encoding="utf-8")
        required = [
            "초심자", "git clone --branch main", "python3 --version",
            "csv.DictReader", "json.load", "math.hypot",
            "load_cases()", "evaluate_case()", "classify_time_indexed()",
            "render_html()", "main()", "python3 - <<'PY'",
            "Ran 10 tests", "FAILED (failures=2)", "runner_rc=2",
            "D13_STUDENT_RESULT=GREEN", "STUDENT_WORKSHEET_KO.md",
        ]
        for token in required:
            self.assertIn(token, text, token)

    def test_meaningful_both_topics_and_graded_beginner_worksheet(self):
        guide = GUIDE.read_text(encoding="utf-8")
        sheet = WORKSHEET.read_text(encoding="utf-8")
        for word in ("Reachability", "공간예측", "16개", "0.35", "map",
                     "odom", "동일 시각", "HTML", "NOT_RUN", "인증 E-Stop"):
            self.assertIn(word, guide, word)
        for token in ("활동 A", "활동 B", "활동 C", "활동 D", "활동 E",
                      "예상 출력", "최초 RED", "U_", "학습 성찰"):
            self.assertIn(token, sheet, token)

if __name__ == "__main__":
    unittest.main()
