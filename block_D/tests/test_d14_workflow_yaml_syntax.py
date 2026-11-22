"""D14 public Actions YAML escaped-newline parse regression (docs/CI only)."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
WORKFLOW=ROOT/".github/workflows/block-d-d14-student.yml"
class D14WorkflowSyntax(unittest.TestCase):
    def test_step_has_real_newlines_not_escaped_newline_literal(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn(r"\n        shell:",text,
            "Workflow contains literal escaped newlines, preventing GitHub Actions parsing")
        self.assertIn("      - name: D14 beginner demo and lab docs contract\n"
                      "        shell: bash\n"
                      "        run: python3 -m unittest discover -s block_D/tests "
                      "-p 'test_d14_education_docs.py' -v",text)
    def test_critical_d14_todo_expectations_retained(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("D14_STUDENT_EXPECTED_RED_11=PASS",text)
        self.assertIn("NO_ROS_NO_GAZEBO_NO_GOAL_NO_FAULT=1",text)
if __name__=="__main__":
    unittest.main()
