"""Public D07 classroom docs contract; never runs ROS or solves student TODO."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "block_B/day07/D07_STUDENT_3H_CLASSROOM_GUIDE_20261117_KO.md"
TODO = ROOT / "block_B/day07/route_todo.py"


def _guide():
    assert GUIDE.is_file(), "D07_STUDENT_3H_GUIDE_MISSING"
    return GUIDE.read_text(encoding="utf-8")


def test_d07_classroom_schedule_and_outcomes():
    s = _guide()
    for expected in ("19:00", "22:00", "이론 60분", "실습 120분", "LO1", "LO2", "L1", "L8"):
        assert expected in s, expected


def test_d07_classroom_red_green_exit_codes():
    s = _guide()
    for expected in (
        "block_B/day07/tests/test_d07_public.py",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
        "D07_STUDENT_RED_RC",
        "D07_STUDENT_GREEN_RC",
        "set -o pipefail",
        "route_todo.py",
        "NotImplementedError",
    ):
        assert expected in s, expected


def test_d07_classroom_boundaries_and_evidence():
    s = _guide()
    for expected in (
        "ComputePathToPose", "NavigateToPose", "Collision Monitor",
        "UNKNOWN", "NOT_RUN", "SHA", "58", "74", "101",
        "0.35", "0.5", "student", "미검증", "증거",
    ):
        assert expected in s, expected
    assert "YES-P2-G07-GOAL" not in s, "student must not receive owner goal authorization"
    assert "ros2 topic pub /cmd_vel" not in s
    assert "TODO_D07_ROUTE_OBSTACLE" in TODO.read_text(encoding="utf-8")
    assert "TODO_D07_REPLAN_EVIDENCE" in TODO.read_text(encoding="utf-8")


def test_d07_original_topic_contract():
    s = _guide()
    assert "사람을 동적 장애물로 처리하는 회피제어 구조 이해" in s
    assert "사람 회피 로직 및 주행제어 실습" in s
    assert "주행제어 실습의 검증 경계" in s


def test_d07_two_actual_vs_conceptual_pipelines():
    s = _guide()
    for expected in (
        "전체 시스템 아키텍처", "실제 D07 ROS L1 데이터 파이프라인",
        "/axia/d07/test/scan", "/global_costmap/costmap",
        "/compute_path_to_pose", "/cmd_vel_pre_guard",
        "ObstacleLayer", "InflationLayer", "ControllerServer",
        "NavfnPlanner", "동적 장애물의 시간 변화",
    ):
        assert expected in s, expected


def test_d07_code_walkthrough_and_observable_expected_results():
    s = _guide()
    for expected in (
        "코드 해설", "실행 시 예상 결과", "routes.json",
        "route_obstacle_status", "assess_replan",
        "_scan", "_run_stage", "_request_path",
        "nav2_d07_planner.yaml", "test_d07_public.py",
        "1 passed, 3 failed", "4 passed", "0→101→0", "58→74→58",
        "주행제어 판단 워크시트", "실제 주행제어는 미실행",
    ):
        assert expected in s, expected
