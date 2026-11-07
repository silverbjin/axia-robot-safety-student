"""Public contract tests. Synthetic, pure Python; NO ROS/Gazebo acceptance."""
import json
from pathlib import Path

import pytest
from p1_adapter_todo import DiagnosticRecord, diagnose_p1_state

FIXTURES = Path(__file__).resolve().parents[1] / "day03" / "p1_states.jsonl"
REQUIRED = {"state", "scan_fault_code", "stop_is_certified_estop"}


@pytest.mark.parametrize("case", [json.loads(line) for line in FIXTURES.read_text().splitlines()],
                         ids=lambda case: case["case_id"])
def test_fixtures(case):
    result = diagnose_p1_state(json.dumps(case["payload"]),
                               received_mono=case["received_mono"],
                               now_mono=case["now_mono"])
    assert isinstance(result, DiagnosticRecord)
    assert (result.level, result.message) == (case["expected_level"], case["expected_message"])
    assert result.name == "AXIA/P1/SafetySupervisor"
    assert result.hardware_id == "tb3_waffle_sim"
    assert isinstance(result.values, tuple)


def test_no_message_is_stale():
    assert diagnose_p1_state(None, received_mono=None, now_mono=1.0).level == 3


def test_timeout_boundary_is_inclusive():
    payload = {"state": "NORMAL", "stop_is_certified_estop": False,
               "health_diagnostics": dict.fromkeys(("clock_ok", "scan_ok", "graph_ok",
                                                       "cm_lifecycle_ok", "nav2_action_ready"), True)}
    assert diagnose_p1_state(json.dumps(payload), received_mono=1.0,
                             now_mono=2.0).level == 0


@pytest.mark.parametrize("raw", ["not json", "[]", "{}", '{"state":"UNKNOWN"}',
                                       '{"state":"NORMAL","stop_is_certified_estop":true}'])
def test_invalid_payload_fails_closed(raw):
    assert diagnose_p1_state(raw, received_mono=1.0, now_mono=1.1).level == 2


def test_no_sensitive_goal_in_diagnostics():
    payload = {"state": "PROTECTIVE_STOP", "stop_is_certified_estop": False,
               "goal_id": "PRIVATE_SYNTHETIC_GOAL", "scan_fault_code": "STALE_STAMP"}
    record = diagnose_p1_state(json.dumps(payload), received_mono=1.0, now_mono=1.1)
    assert REQUIRED <= {key for key, _ in record.values}
    assert "PRIVATE_SYNTHETIC_GOAL" not in repr(record)


def test_monotonic_reversal_is_invalid():
    assert diagnose_p1_state("{}", received_mono=2.0, now_mono=1.0).level == 2


def test_ros_wrapper_is_readonly():
    source = (FIXTURES.parent / "ros_diagnostics_bridge.py").read_text()
    assert '"/axia/safety/state"' in source
    assert '"/diagnostics"' in source
    for prohibited in ('"/cmd_vel"', '"/navigate_to_pose"', '"/axia/safety/start"',
                       '"/axia/fault/scan_drop"'):
        assert prohibited not in source
