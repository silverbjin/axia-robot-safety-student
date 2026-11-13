"""Public D05 course docs regression only; no ROS, no student TODO completion."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "day05" / "D05_STUDENT_DEMO_GUIDE_KO.md"
LAB = ROOT / "day05" / "D05_STUDENT_LAB_GUIDE_KO.md"

def test_d05_student_demo_document_exists_and_has_three_learning_results():
    assert DEMO.is_file(), "RED: D05 student demo guide missing"
    text = DEMO.read_text(encoding="utf-8")
    for s in ("D04", "Depth", "1.30", "UNKNOWN", "접근 변화율",
              "NO_GOAL", "SYNTHETIC_COURSE_FIXTURE", "터미널",
              "Ctrl+C", "49", "2.179178", "ROS_GAZEBO_NOT_RUN"):
        assert s in text, f"Demo guide missing: {s}"

def test_d05_lab_stands_alone_and_sets_expected_test_contract():
    assert LAB.is_file()
    text = LAB.read_text(encoding="utf-8")
    for s in ("19:00", "22:00", "measure_person_range", "f001",
              "f002", "f003", "RED", "GREEN", "UNKNOWN",
              "test_f001_median_depth", "test_depth_stamp_mismatch_returns_unknown",
              "D05_STUDENT_DEMO_GUIDE_KO.md", "person_range.csv", "summary.json",
              "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1", "50ms", "Ctrl+C"):
        assert s in text, f"Lab missing: {s}"

def test_existing_student_todo_is_still_not_implemented():
    src = (ROOT / "block_b_todo.py").read_text(encoding="utf-8")
    assert 'raise NotImplementedError("TODO_D04_SELECT_PERSON")' in src
    assert 'raise NotImplementedError("TODO_D05_PERSON_RANGE")' in src


def test_d05_student_real_gazebo_live_guide_is_public_independent():
    """RED until students have a standalone, source-pinned LIVE scene guide."""
    path = ROOT / "day05" / "D05_STUDENT_GAZEBO_LIVE_GUIDE_KO.md"
    assert path.is_file(), "RED: missing student real Gazebo D05 live guide"
    text = path.read_text(encoding="utf-8")
    for term in (
        "AXIA_D05_LIVE=1", "AXIA_D05_SENSOR_ONLY=1",
        "AXIA_D04_STUDENT_DOMAIN_ID=49", "D05_PUBLIC_SENSOR_ONLY_PASS",
        "D05_PRIVATE_DISTANCE_OBSERVER=NOT_RUN",
        "gazebo_live/prepare_scene.py", "/axia/d05/rgbd/depth_image",
        "/yolo/cam0/detections", "D05_STUDENT_LAB_GUIDE_KO.md",
        "1.30m", "UNKNOWN", "Ctrl+C", "WSL2", "Gazebo",
        "강사", "main", "터미널 A", "터미널 B",
    ):
        assert term in text, f"D05 live guide missing contract: {term}"
    assert "gh auth" not in text, "Student guide must not require private GitHub authentication"
