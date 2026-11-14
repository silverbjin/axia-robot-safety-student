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
