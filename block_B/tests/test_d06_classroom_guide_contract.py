"""D06 classroom guide source-only contract; NO ROS or Gazebo execution."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "block_B" / "day06" / "D06_STUDENT_3H_CLASSROOM_GUIDE_20261116_KO.md"
TODO = ROOT / "block_B" / "day06" / "safety_bubble_todo.py"
LAB = ROOT / "block_B" / "day06" / "D06_LAB_KO.md"


def test_d06_classroom_guide_exists_and_has_timeboxes():
    content = GUIDE.read_text(encoding="utf-8")
    for token in ("2026-11-16", "19:00–22:00", "20:25–20:45", "21:25–21:40", "21:50–22:00", "L1", "L8"):
        assert token in content, token


def test_d06_guide_has_public_tdd_expectations_and_safety_scope():
    content = GUIDE.read_text(encoding="utf-8")
    for token in ("TODO_D06_CLASSIFY_RANGE", "TODO_D06_BUBBLE_POLICY", "1 passed, 3 failed", "4 passed", "/axia/d06/test/cmd_out", "UNKNOWN", "NOT_RUN", "LaserScan", "/cmd_vel", "E-Stop", "Ctrl+C", "RED", "GREEN"):
        assert token in content, token
    assert "safety_certified=False" in content
    assert "control_published=False" in content


def test_existing_student_todo_is_intentionally_red_and_not_replaced():
    assert LAB.is_file()
    src = TODO.read_text(encoding="utf-8")
    assert 'raise NotImplementedError("TODO_D06_CLASSIFY_RANGE")' in src
    assert 'raise NotImplementedError("TODO_D06_BUBBLE_POLICY")' in src
    assert "create_publisher" not in src
