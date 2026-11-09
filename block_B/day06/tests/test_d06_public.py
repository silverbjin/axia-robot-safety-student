"""D06 student TDD: TODO intentionally RED, fixture loader itself GREEN."""
import json
from pathlib import Path
from block_B.day06.safety_bubble_todo import classify_range, bubble_policy

FIXTURE=Path(__file__).resolve().parents[1]/"fixtures"/"distances.json"

def test_fixture_shape():
    data=json.loads(FIXTURE.read_text())
    assert data["schema"]=="axia.d06.distance_fixture.v1"
    assert [s["expected"] for s in data["samples"]]==[
        "CLEAR","SLOWDOWN","STOP","STOP","SLOWDOWN","UNKNOWN","UNKNOWN"]

def test_student_all_distance_samples():
    data=json.loads(FIXTURE.read_text())
    for s in data["samples"]:
        assert classify_range(s["distance_m"],valid=s["valid"],age_s=s["age_s"])==s["expected"]

def test_student_policy_response_not_actuator():
    assert bubble_policy(0.30)["status"]=="STOP"
    assert bubble_policy(0.30)["expected_ratio"]==0.0
    assert bubble_policy(0.30)["safety_certified"] is False
    assert bubble_policy(0.30)["control_published"] is False

def test_student_nan_and_stale_are_unknown():
    assert classify_range(float("nan"))=="UNKNOWN"
    assert classify_range(0.65,age_s=1.0)=="UNKNOWN"
