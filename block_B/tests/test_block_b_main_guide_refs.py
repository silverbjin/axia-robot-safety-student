"""D04-D08 student main-branch teaching entrypoint regression (L0 only).

No ROS/Gazebo launch. Protects against stale deleted release branches in copy-paste guides.
"""
from pathlib import Path

BLOCK = Path(__file__).resolve().parents[1]

def _read(relative: str) -> str:
    return (BLOCK / relative).read_text(encoding="utf-8")


def test_d04_gazebo_guide_uses_main_and_new_isolated_directory():
    guide = _read("day04/D04_GAZEBO_YOLO_GUI_STUDENT_GUIDE_KO.md")
    assert "git -C \"$BASE\" fetch origin main" in guide
    assert "BRANCH=\"main\"" in guide
    assert "git clone --single-branch --branch main" in guide
    assert "axia_d04_student_gazebo_demo_main" in guide
    assert "feature/d04-student-gazebo-yolo-20261112" not in guide
    assert (BLOCK / "day04/run_student_gazebo_yolo_once.sh").is_file()


def test_d04_d05_student_guides_have_no_deleted_course_branch():
    for path in (
        "day04/D04_STUDENT_LAB_GUIDE_KO.md",
        "day05/D05_STUDENT_DEMO_GUIDE_KO.md",
        "day05/D05_STUDENT_LAB_GUIDE_KO.md",
    ):
        text = _read(path)
        assert "feature/d04-student-gazebo-yolo-20261112" not in text, path
        assert "feature/block-b-d05-class-20261112" not in text, path
        assert "blob/fix/d04-course-field-preflight-20261112/" not in text, path
    assert "branch main" in _read("day05/D05_STUDENT_DEMO_GUIDE_KO.md")
    assert "branch main" in _read("day05/D05_STUDENT_LAB_GUIDE_KO.md")


def test_d08_live_guides_and_bootstrap_share_main_contract():
    bootstrap = _read("day08/run_d08_student_live_bootstrap.sh")
    assert 'BRANCH="${AXIA_D08_RELEASE_BRANCH:-main}"' in bootstrap
    assert "axia_d08_student_live_main" in bootstrap
    assert "fix/d08-gazebo-rviz-scene-mesh-20261118" not in bootstrap
    for path in (
        "day08/D08_GAZEBO_RVIZ_LIVE_GUIDE_20261115_KO.md",
        "day08/D08_LIVE_DEMO_GUIDE_OGRE_OWNER_ACCEPTED_20261118_KO.md",
    ):
        text = _read(path)
        assert "axia-robot-safety-student/main/block_B/day08/run_d08_student_live_bootstrap.sh" in text, path
        assert "AXIA_D08_RELEASE_BRANCH=" in text, path
        assert "release/d08-wslg-ogre-owner-accepted-20261118" not in text, path
    assert (BLOCK / "day08/run_d08_student_live_once.sh").is_file()
