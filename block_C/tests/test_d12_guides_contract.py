"""D12 beginner guides public contracts. Docs only: existing TODO stays intentionally RED."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DAY = ROOT / "day12"
DEMO = DAY / "STUDENT_DEMO_GUIDE_KO.md"
LAB = DAY / "STUDENT_LAB_GUIDE_KO.md"
INDEX = DAY / "README_KO.md"


class D12GuideContract(unittest.TestCase):
    def test_guides_exist_and_approved_objectives(self):
        for p in (DEMO, LAB, INDEX):
            self.assertTrue(p.is_file(), str(p))
            s = p.read_text(encoding="utf-8")
            for term in ("ROS 2", "SYNTHETIC_COURSE_FIXTURE", "INSUFFICIENT_DATA",
                         "WARNING", "인증된 E-Stop", "운영자", "대시보드"):
                self.assertIn(term, s, f"{p}: {term}")

    def test_clone_to_actual_commands_and_logs(self):
        for p in (DEMO, LAB):
            s = p.read_text(encoding="utf-8")
            for term in ("git clone https://github.com/silverbjin/axia-robot-safety-student.git",
                         "block_C/scripts/block_c_once.sh --doctor",
                         "block_C/day12/ros_transport/sample_events.jsonl",
                         "block_C/scripts/block_c_once.sh --ros-l1",
                         "operator_feedback.jsonl", "EXPECTED_RED",
                         "120분", "예상 출력", "미구현"):
                self.assertIn(term, s, f"{p}: {term}")
            self.assertNotIn("torch.save(", s)
            self.assertNotIn("send_goal_async(", s)
            self.assertNotIn("create_publisher(Twist", s)

    def test_readme_has_local_links_and_todo_is_red(self):
        s = INDEX.read_text(encoding="utf-8")
        for name in ("STUDENT_DEMO_GUIDE_KO.md", "STUDENT_LAB_GUIDE_KO.md",
                     "student_event_todo.py", "ros_transport/sample_events.jsonl"):
            self.assertIn(name, s)
        todo = (DAY / "student_event_todo.py").read_text(encoding="utf-8")
        self.assertIn("raise NotImplementedError('D12 TODO not implemented')", todo)
        self.assertFalse((DAY / "D12_SOLUTION_GUIDE_KO.md").exists())

    def test_demo_fixture_data_count_and_non_authority(self):
        lines = (DAY / "ros_transport/sample_events.jsonl").read_text(encoding="utf-8").splitlines()
        data = [json.loads(s) for s in lines if s.strip()]
        self.assertEqual(len(data), 12)
        self.assertEqual({s["level"] for s in data},
                         {"NORMAL", "CAUTION", "WARNING", "INSUFFICIENT_DATA"})
        self.assertTrue(all(s["control_authority"] is False
                            and s["certified_estop"] is False for s in data))


if __name__ == "__main__":
    unittest.main()
