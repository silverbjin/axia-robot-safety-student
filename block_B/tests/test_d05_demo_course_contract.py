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
