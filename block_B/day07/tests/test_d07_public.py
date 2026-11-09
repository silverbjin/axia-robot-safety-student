"""D07 public RED test; data shape stays GREEN before TODO implementations."""
import json
from pathlib import Path
from block_B.day07.route_todo import route_obstacle_status,assess_replan
F=Path(__file__).resolve().parents[1]/"fixtures"/"routes.json"
def test_fixture_schema():
    d=json.loads(F.read_text())
    assert d["schema"]=="axia.d07.avoidance_fixture.v1"
    assert d["source"].startswith("synthetic")
    assert len(d["path_before"])>=3 and len(d["path_detour"])>=3
def test_student_route_detection():
    d=json.loads(F.read_text())
    assert route_obstacle_status(d["path_before"],d["person_xy"])=="BLOCKED"
    assert route_obstacle_status(d["path_detour"],d["person_xy"])=="CLEAR"
def test_student_actual_replanning_claim_boundary():
    d=json.loads(F.read_text())
    r=assess_replan(d["path_before"],d["path_detour"],d["person_xy"])
    assert r["status"]=="REPLAN_EVIDENCED"
    assert r["robot_moved"] is False
    assert r["collision_free_verified"] is False
    assert r["safety_certified"] is False
def test_student_unknown_sensor_has_no_clear_permission():
    assert route_obstacle_status([(0,0),(1,0)],None)=="UNKNOWN"
    assert route_obstacle_status([(0,0),(1,0)],(0.5,0),age_s=1)=="UNKNOWN"
