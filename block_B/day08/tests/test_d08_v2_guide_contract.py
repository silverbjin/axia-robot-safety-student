"""D08 V2 public documentation contract: no private teacher source, no ROS claims."""
from pathlib import Path

DAY = Path(__file__).resolve().parents[1]
DEMO = DAY / "D08_STUDENT_DEMO_GUIDE_V2_20261115_KO.md"
LAB = DAY / "D08_STUDENT_PRACTICE_GUIDE_V2_20261115_KO.md"

def test_d08_v2_guides_present_and_two_original_objectives():
    assert DEMO.is_file() and LAB.is_file()
    docs = DEMO.read_text(encoding="utf-8") + LAB.read_text(encoding="utf-8")
    for goal in (
        "Visionㆍ거리정보 기반 Human-aware Safety 제어 흐름 구성",
        "사람 인식ㆍ거리계산ㆍ회피제어 통합 실습",
    ):
        assert goal in docs

def test_d08_v2_demo_has_data_pipeline_and_scope_labels():
    text = DEMO.read_text(encoding="utf-8")
    for term in ("select_person", "measure_person_range", "bubble_policy",
                 "assess_replan", "integrate_case", "NO-GOAL", "PYTHON_ONLY",
                 "Collision Monitor", "UNKNOWN_REVIEW"):
        assert term in text

def test_d08_v2_lab_matches_real_student_commands_and_six_cases():
    text = LAB.read_text(encoding="utf-8")
    for term in ("test_d08_public.py", "run_lab", "submission_zip",
                 "trace.csv", "summary.json", "pytest.txt", "SHA256SUMS",
                 "clear_replan", "stale_depth", "stale_track",
                 "D08_PYTHON_FIXTURE_REPLAY_PASS", "D08_ZIP_HASH_VERIFY_PASS"):
        assert term in text

def test_d08_v2_student_docs_never_expose_private_code_or_claim_real_safety():
    docs = DEMO.read_text(encoding="utf-8") + LAB.read_text(encoding="utf-8")
    forbidden = ("from d08_integration_reference import", "import d08_integration_reference",
                 "from d06_bubble_reference import", "safety_certified=True",
                 "robot_moved=True", "collision_free_verified=True")
    assert not any(term in docs for term in forbidden)
    assert "SW Stop" in docs
    assert "E-Stop" in docs
