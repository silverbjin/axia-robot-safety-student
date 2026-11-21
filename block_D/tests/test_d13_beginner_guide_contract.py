"""Beginner D13 textbook docs-only acceptance: novice can repeat steps safely."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
D13 = ROOT / "block_D" / "day13"
GUIDE = D13 / "STUDENT_LAB_GUIDE_KO.md"
SHEET = D13 / "STUDENT_WORKSHEET_KO.md"

class D13BeginnerGuide(unittest.TestCase):
    def test_concepts_and_function_walkthrough(self):
        g = GUIDE.read_text(encoding="utf-8")
        for concept in ("초심자 용어 사전", "CSV", "JSON", "dict", "list",
                        "load_cases()", "evaluate_case()", "classify_time_indexed()",
                        "render_html()", "main()", "키워드 전용 인수"):
            self.assertIn(concept, g, concept)
        self.assertGreater(len(g), 12500)

    def test_copy_paste_commands_and_failover(self):
        g = GUIDE.read_text(encoding="utf-8")
        for token in ("git clone --branch main", "python3 -m unittest discover",
                      "echo \"student_tests_rc=$?\"", "Ctrl+O", "Ctrl+X",
                      "RED_EXPECTED_TODO", "D13_STUDENT_RESULT=GREEN",
                      "11.54", "HTML_BROWSER_NOT_RUN", "git diff --name-only"):
            self.assertIn(token, g, token)

    def test_worksheet_has_scaffold_without_answer_source(self):
        w = SHEET.read_text(encoding="utf-8")
        for token in ("체크포인트", "예상 출력", "관측시각",
                      "내가 수정한 부분", "최초 RED", "최종 GREEN"):
            self.assertIn(token, w, token)
        self.assertNotIn("def classify_time_indexed(", w)
        self.assertIn('return "U"', (D13 / "reachability_student.py").read_text())
        self.assertEqual(list((ROOT / "block_D").rglob("p3_oracles.py")), [])

if __name__ == "__main__":
    unittest.main()
