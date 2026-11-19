"""D10 student-only educational guide contract, not an answer test."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "day10/STUDENT_DEMO_GUIDE_KO.md"
LAB = ROOT / "day10/STUDENT_LAB_GUIDE_KO.md"
TODO = ROOT / "day10/student_if_todo.py"
DOCS = (DEMO, LAB)

def test_d10_two_goals_and_full_course():
    text = DEMO.read_text(encoding="utf-8")
    assert "Isolation Forest 기반 이상신호 탐지 구조 이해" in text
    assert "정상 패턴 기준 이상탐지 및 조기 경고 검증 실습" in text
    assert "19:00–22:00" in text
    assert "SYNTHETIC_COURSE_FIXTURE" in text

def test_d10_student_lab_is_actionable_and_synthetic():
    text = LAB.read_text(encoding="utf-8")
    for marker in (
        "features_train.csv", "features_valid.csv", "features_test.csv",
        "normal_valid_only", "if_metrics.json", "if_scores_test.csv",
        "D10_STUDENT_DATA_CHECK_PASS", "synthetic_delay_s=1.9",
        "INSUFFICIENT_DATA", "EXPECTED_RED", "NotImplementedError"
    ):
        assert marker in text, marker

def test_d10_student_no_teacher_code_and_no_control():
    code = TODO.read_text(encoding="utf-8")
    assert "raise NotImplementedError" in code
    assert "IsolationForest(" not in code
    for file in DOCS:
        contents = file.read_text(encoding="utf-8")
        assert "from isolation_forest_pipeline import" not in contents
        assert "create_publisher(" not in contents
        assert "send_goal_async(" not in contents
        assert "비인증" in contents or "인증" in contents

def test_d10_manifest_and_fixture_are_immutable():
    manifest = json.loads((ROOT / "fixtures/scenario_manifest.json").read_text(encoding="utf-8"))
    assert manifest["expected_rows"] == {
        "normal_train.csv": 2400, "normal_valid.csv": 800, "test_mixed.csv": 1399
    }
    assert manifest["trace_class_counts"] == {
        "normal_test": 4, "anomaly_test": 6, "quality_test": 4
    }
    assert manifest["seed"] == 2409

def test_d10_students_get_real_input_precondition_not_false_green():
    lab = LAB.read_text(encoding="utf-8")
    assert "D09 학생 과제가 끝나지 않았다면" in lab
    assert "빈" not in lab or "입력" in lab
    assert "공개 테스트는 함수의 반환형만" in lab
