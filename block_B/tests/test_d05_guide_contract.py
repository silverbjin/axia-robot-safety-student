"""D05 documentation-only contract: no student solution or ROS required."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "day05" / "D05_STUDENT_LAB_GUIDE_KO.md"

def test_d05_guide_exists_and_teacher_answers_remain_separate():
    assert GUIDE.is_file(), "RED: D05 student guide is missing"
    text = GUIDE.read_text(encoding="utf-8")
    for expected in ("19:00", "22:00", "measure_person_range", "TODO_D05_PERSON_RANGE",
                     "SYNTHETIC_COURSE_FIXTURE", "강사 정답 비공개"):
        assert expected in text, expected

def test_d05_guide_contains_real_commands_and_evidence_boundaries():
    text = GUIDE.read_text(encoding="utf-8")
    for expected in ("test_f001_median_depth", "test_depth_stamp_mismatch_returns_unknown",
                     "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1", "python -m block_B.run_lab",
                     "person_range.csv", "UNKNOWN", "50ms", "Ctrl+C", "NO_GOAL"):
        assert expected in text, expected

def test_existing_implementation_is_unmodified_todo():
    source = (ROOT / "block_b_todo.py").read_text(encoding="utf-8")
    assert 'raise NotImplementedError("TODO_D05_PERSON_RANGE")' in source
    assert 'raise NotImplementedError("TODO_D04_SELECT_PERSON")' in source
