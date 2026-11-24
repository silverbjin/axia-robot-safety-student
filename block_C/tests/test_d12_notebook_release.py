"""D12 Notebook distribution contract. Standard library only; no ROS/Gazebo."""
from pathlib import Path
import hashlib
import json
import unittest

BASE = Path(__file__).resolve().parents[1] / "day12" / "notebooks" / "lesson12"
NOTEBOOK = BASE / "lesson12-risk-state-monitoring.ipynb"


def git_blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class D12NotebookRelease(unittest.TestCase):
    def test_required_files_and_public_provenance(self):
        for rel in (
            "lesson12-risk-state-monitoring.ipynb",
            "requirements.txt", "README.md", "student_guide.md",
            "QA_REPORT.md", "assets/event_contract.py",
            "assets/sample_events.jsonl", "assets/run_and_verify.py",
            "outputs/.gitkeep",
        ):
            self.assertTrue((BASE / rel).is_file(), rel)
        self.assertEqual(git_blob_sha(BASE / "assets/sample_events.jsonl"),
                         "07c7c282559870acdce4e44679873b930de7d2b1")
        self.assertEqual(git_blob_sha(BASE / "assets/event_contract.py"),
                         "a00d2230be4d14d810b84db9938d4fac30e79b12")

    def test_complete_executed_notebook_and_embedded_images(self):
        n = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        cells = n["cells"]
        code = [c for c in cells if c["cell_type"] == "code"]
        self.assertEqual(len(cells), 54)
        self.assertEqual(len(code), 11)
        self.assertEqual([c["execution_count"] for c in code], list(range(1, 12)))
        self.assertTrue(all(c["outputs"] for c in code))
        self.assertTrue(all(not any(o["output_type"] == "error" for o in c["outputs"]) for c in code))
        self.assertEqual(sum(bool(c.get("attachments")) for c in cells), 7)
        text = "\n".join("".join(c["source"]) for c in cells)
        for phrase in (
            "SYNTHETIC_COURSE_FIXTURE", "INSUFFICIENT_DATA", "EventGate",
            "DiagnosticArray", "operator_feedback.jsonl", "인증된 E-Stop",
            "NOT_RUN", "sample_events.jsonl",
        ):
            self.assertIn(phrase, text, phrase)

    def test_public_student_privacy_and_documentation(self):
        self.assertFalse((BASE / "instructor_guide.md").exists())
        fixture = [json.loads(line) for line in
                   (BASE / "assets/sample_events.jsonl").read_text(encoding="utf-8").splitlines()
                   if line.strip()]
        self.assertEqual(len(fixture), 12)
        self.assertTrue(all(x["control_authority"] is False and
                            x["certified_estop"] is False for x in fixture))
        docs = (BASE / "student_guide.md").read_text(encoding="utf-8")
        self.assertIn("lesson12-risk-state-monitoring.ipynb", docs)
        self.assertIn("assets", docs)


if __name__ == "__main__":
    unittest.main()
