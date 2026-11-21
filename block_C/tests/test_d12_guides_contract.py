"""D12 beginner guides public contracts. Docs only: existing TODO stays intentionally RED."""
import json
import os
import re
import subprocess
import sys
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


    def test_beginner_lesson_has_scaffolded_explanations_and_real_world_cases(self):
        s = LAB.read_text(encoding="utf-8")
        for key in (
            "초심자를 위한 1분 용어", "왜 필요한가", "코드 한 줄씩 해설",
            "실행 전 예상 출력", "직접 확인", "실무 사례", "스스로 점검",
            "첫 실패 지점", "CLI 기반 미니 대시보드",
            "D12_BEGINNER_TIMELINE_PASS", "D12_FEEDBACK_VALIDATION_PASS",
            "TEST_HOLD", "git rev-parse HEAD",
            "ros_l1/verdict.json", "ROS_DOMAIN_ID",
            "source_timestamp_ns", "monotonic", "Python 3.12",
            "교육용 WARNING", "미구현 설계 시안"):
            self.assertIn(key, s, key)

    def test_sample_first_warning_quality_and_timestamps_are_grounded(self):
        data = [json.loads(line) for line in
                (DAY / "ros_transport/sample_events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()]
        self.assertEqual([e["event_id"] for e in data if e["level"] == "WARNING"][0],
                         "DEMO:TST_N_00:002")
        self.assertEqual([e["event_id"] for e in data if e["level"] == "INSUFFICIENT_DATA"][0],
                         "DEMO:TST_N_00:003")
        self.assertEqual([e["source_timestamp_ns"] for e in data[:4]],
                         [0, 100_000_000, 200_000_000, 300_000_000])
        self.assertTrue(all(e["risk_score"] is None and e["threshold"] is None
                            for e in data if e["level"] == "INSUFFICIENT_DATA"))


    def test_beginner_document_python_examples_execute_and_match_expected(self):
        """Run just the public read-only snippets, never start ROS/robot/control."""
        s = LAB.read_text(encoding="utf-8")
        scenarios = (
            ("### A2-1.", "DEMO:TST_N_00:002 WARNING score= 0.9 quality= None"),
            ("### A4-1.", "D12_BEGINNER_TIMELINE_PASS events=12 first_warning=DEMO:TST_N_00:002"),
            ("### B2-1.", "TEST_HOLD ROS_L1_NOT_MEASURED verdict.json missing"),
        )
        for label, expected in scenarios:
            self.assertIn(label, s)
            after = s.split(label, 1)[1]
            found = re.search(r"~~~bash\s+python3 - <<'PY'\n(.*?)\nPY\n~~~", after, re.S)
            self.assertIsNotNone(found, label)
            code = found.group(1)
            self.assertNotIn("create_publisher(", code)
            self.assertNotIn("send_goal_async(", code)
            with self.subTest(label=label):
                env = dict(os.environ, HOME="/tmp/axia-d12-guide-test-no-evidence")
                p = subprocess.run(
                    [sys.executable, "-c", code], cwd=ROOT.parent, env=env,
                    capture_output=True, text=True, timeout=15, check=False
                )
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertIn(expected, p.stdout)


if __name__ == "__main__":
    unittest.main()
