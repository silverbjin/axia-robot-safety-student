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


def test_d06_original_two_course_objectives_and_final_summary():
    """Course promises must be explicit, not merely implicit in safety terms."""
    content = GUIDE.read_text(encoding="utf-8")
    assert "거리 구간별 속도 제한 및 감속ㆍ정지 규칙 이해" in content
    assert "Safety Bubble 기반 안전제어 로직 설계 실습" in content
    assert "수업 전체 정리" in content
    assert "목표 1 달성 증거" in content
    assert "목표 2 달성 증거" in content


def test_d06_student_live_demo_is_independent_from_private_g07():
    """Students own a public no-Goal Gazebo lesson; Owner drives G07 elsewhere."""
    doc=ROOT / "block_B" / "day06" / "D06_STUDENT_LIVE_DEMO_GUIDE_20261116_KO.md"
    assert doc.is_file(), "D06 student LIVE guide must be published on this PR"
    content=doc.read_text(encoding="utf-8")
    for token in (
        "Gazebo", "RViz2", "CLEAR", "SLOWDOWN", "STOP", "UNKNOWN",
        "AXIA_D05_LIVE=1", "AXIA_D05_SENSOR_ONLY=1",
        "NO_GOAL", "NO_CMD_VEL", "E-Stop",
        "YES-P2-G07-GOAL", "공개", "비공개", "강사", "ROS_DOMAIN_ID",
        "실제 ROS", "NOT_RUN", "Ctrl+C",
    ):
        assert token in content,token
    # A student must never clone Instructor's protected source or send a Goal.
    assert "gh repo clone silverbjin/axia-robot-safety-instructor" not in content
    assert "ros2 action send_goal" not in content
    assert "ros2 topic pub /cmd_vel" not in content


def test_d06_lab_sourcing_uses_draft_branch_until_main_merge():
    content=GUIDE.read_text(encoding="utf-8")
    assert "git clone --branch docs/d06-classroom-materials-20261113" in content
    assert "git clone --branch main --single-branch" not in content
    assert "D06_STUDENT_SOURCE_SHA=" in content


def test_d06_green_log_preserves_pytest_exit_code():
    """pytest|tee must not turn a failed test into a false GREEN."""
    content=GUIDE.read_text(encoding="utf-8")
    assert "set -o pipefail" in content
    assert "D06_STUDENT_GREEN_RC=" in content
    assert 'test "$RC" -eq 0' in content
