"""D07 classroom delivery-doc contracts; never runs ROS or student TODO answers."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "block_B/day07"
DEMO = ROOT / "D07_STUDENT_DEMO_GUIDE_20261117_KO.md"
LAB = ROOT / "D07_STUDENT_PRACTICE_GUIDE_20261117_KO.md"


def test_student_demo_exists_and_separates_three_evidence_levels():
    text = DEMO.read_text(encoding="utf-8")
    for phrase in (
        "사람을 동적 장애물로 처리하는 회피제어 구조 이해",
        "사람 회피 로직 및 주행제어 실습",
        "L0", "L1", "L2", "H01", "BLOCKED", "NOT_RUN",
        "0→101→0", "58→74→58", "ComputePathToPose", "NavigateToPose",
        "/global_costmap/costmap", "/odom", "Contact", "실제 주행",
    ):
        assert phrase in text, phrase


def test_student_lab_is_executable_and_contains_red_green_evidence():
    text = LAB.read_text(encoding="utf-8")
    for phrase in (
        "git clone", "docs/d07-3h-classroom-20261114",
        "route_todo.py", "routes.json",
        "test_d07_public.py", "D07_STUDENT_RED_RC",
        "D07_STUDENT_GREEN_RC", "set -o pipefail",
        "1 passed, 3 failed", "4 passed",
        "UNKNOWN", "0.35", "0.5",
        "이론 60분", "실습 120분", "19:00", "22:00",
        "제출", "터미널", "종료",
    ):
        assert phrase in text, phrase


def test_student_documents_have_scope_and_no_owner_motion_commands():
    for file in (DEMO, LAB):
        s = file.read_text(encoding="utf-8")
        for prohibited in ("YES-P2-G07-GOAL", "ros2 topic pub /cmd_vel",
                           "axia-robot-safety-instructor.git",
                           "d07_route_reference.py", "test_d07_route_hidden.py",
                           "AXIA_CLOUD_CI"):
            assert prohibited not in s, (file, prohibited)
        assert "NOT_RUN" in s
        assert "H01" in s
        assert "실제 회피 주행 성공" not in s or "아님" in s


def test_student_docs_reference_existing_independent_readme():
    guide = ROOT / "D07_STUDENT_3H_CLASSROOM_GUIDE_20261117_KO.md"
    assert guide.is_file()
    for file in (DEMO, LAB):
        s = file.read_text(encoding="utf-8")
        assert guide.name in s, file.name
    assert "raise NotImplementedError" in (ROOT / "route_todo.py").read_text()
