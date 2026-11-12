"""Student D08 public RED after scaffold GREEN. Prerequisite D04-D07 TODO."""
import json
from pathlib import Path
from block_B.day08.integration_todo import integrate_case

FIXTURE=Path(__file__).resolve().parents[1]/"fixtures"/"d08_synthetic_cases.json"

def test_d08_synthetic_fixture_contract():
    data=json.loads(FIXTURE.read_text())
    assert data["schema"]=="axia.d08.offline_integration.v1"
    assert data["source"]=="SYNTHETIC_COURSE_FIXTURE"
    assert data["real_person_observed"] is False
    assert data["ros_actual"] is False and data["gazebo_actual"] is False
    assert data["position_source"]=="SYNTHETIC_MAP_PROXY_NOT_CAMERA_TF"
    assert len(data["cases"])==6
    assert [c["case_id"] for c in data["cases"]]==[
        "clear_replan","slow","stop","lost","stale_depth","stale_track"]

def test_d08_integrated_six_scenarios_expected_red_until_todos_complete():
    data=json.loads(FIXTURE.read_text())
    for case in data["cases"]:
        result=integrate_case(case,data["routes"])
        assert {k:result.get(k) for k in case["expected"]}==case["expected"]
        assert result["verified_level"]=="PYTHON_ONLY"
        assert result["source"]=="D08_SYNTHETIC_CLASSROOM"
        for flag in ("control_published","robot_moved","collision_free_verified",
                     "safety_certified","ros_verified","gazebo_verified"):
            assert result[flag] is False

def test_d08_lost_detection_cannot_be_clear_expected_red():
    data=json.loads(FIXTURE.read_text())
    c=next(c for c in data["cases"] if c["case_id"]=="lost")
    r=integrate_case(c,data["routes"])
    assert r["range_status"]=="UNKNOWN"
    assert r["advice"]=="UNKNOWN_REVIEW"
