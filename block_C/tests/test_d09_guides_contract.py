"""D09 student-facing guides: presence, executable contracts, and teacher-answer separation.

Only public documents and safe local commands; no private Instructor checkout.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "day09" / "STUDENT_DEMO_GUIDE_KO.md"
LAB = ROOT / "day09" / "STUDENT_LAB_GUIDE_KO.md"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing D09 guide: {path.name}"
    text = path.read_text(encoding="utf-8")
    assert len(text) > 1200, f"guide too short: {path.name}"
    return text


def test_d09_both_public_guides_exist_and_separate_real_from_synthetic():
    demo, lab = _read(DEMO), _read(LAB)
    for text in (demo, lab):
        assert "SYNTHETIC_COURSE_FIXTURE" in text
        assert "실제" in text and "합성" in text
        assert "인증" in text and "E-Stop" in text
        assert "학습" in text
    assert "ROS 2" in demo and "토픽" in demo
    assert "선택" in demo and "ros2 bag" in demo


def test_d09_commands_match_real_public_student_tree():
    demo, lab = _read(DEMO), _read(LAB)
    for path in ("block_C/scripts/block_c_once.sh",
                 "block_C/fixtures/generator.py",
                 "block_C/fixtures/normal_train.csv"):
        assert Path(path.replace("block_C/", "")).exists() or (ROOT / path.replace("block_C/", "")).exists()
    assert "block_C/scripts/block_c_once.sh --doctor" in demo
    assert "block_C/fixtures/generator.py --check" in lab
    assert "block_C/day09/student_eda_todo.py" in lab
    assert "test_d09_should_build_trace_safe_features" in lab
    assert "EXPECTED_RED" in lab
    assert "INSUFFICIENT_DATA" in lab


def test_d09_training_data_and_quality_contract_are_not_invented():
    demo, lab = _read(DEMO), _read(LAB)
    for marker in ("46", "4,599", "424", "240", "80", "100", "4"):
        assert marker in demo + lab
    assert "10Hz" in demo + lab or "10 Hz" in demo + lab
    assert "trace_id" in lab and "truth_label" in lab


def test_d09_student_guides_do_not_contain_hidden_solution_or_unsafe_control():
    demo, lab = _read(DEMO), _read(LAB)
    for text in (demo, lab):
        assert "def aggregate_trace(" not in text
        assert "def build_features(" not in text
        assert "from eda_pipeline import" not in text
        assert "send_goal_async(" not in text
        assert "create_publisher(" not in text
        assert "git clone" not in text or "axia-robot-safety-instructor" not in text


def test_d09_recording_new_terminal_rebinds_topic_and_reads_bag_metadata():
    demo = _read(DEMO)
    section = demo.split("기록이 가능한 경우에만", 1)[1]
    assert "기록용 터미널" in section
    assert 'read -rp "기록할 토픽 이름' in section
    assert 'ros2 bag info "$BAG"' in section


def test_d09_guides_start_with_safe_fresh_clone_and_repo_root():
    # Training docs must be executable by a learner who has never cloned the repository.
    readme = (ROOT / "day09" / "README_KO.md").read_text(encoding="utf-8")
    for name, content in (("demo", _read(DEMO)), ("lab", _read(LAB)), ("readme", readme)):
        bootstrap = content[:2400]
        assert "git clone https://github.com/silverbjin/axia-robot-safety-student.git" in bootstrap, name
        assert "cd axia-robot-safety-student" in bootstrap, name
        assert "git rev-parse --show-toplevel" in bootstrap, name
        assert "github.com/silverbjin/axia-robot-safety-instructor" not in content
