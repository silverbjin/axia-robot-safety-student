"""Deterministic G02 YAML fixture executor. No ROS, Gazebo or yaml dependency in production."""
from typing import Any
from .fsm import SafetySnapshot, SafetyState, can_move, transition


def validate_fixture(fixture: dict) -> int:
    if not isinstance(fixture, dict) or fixture.get("schema_version") != 1 or fixture.get("gate") != "G02":
        raise ValueError("invalid fixture schema")
    cases = fixture.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases missing")
    seen = set()
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"]:
            raise ValueError("invalid case id")
        if case["id"] in seen:
            raise ValueError("duplicate case id")
        seen.add(case["id"])
        if ("expected_state" not in case or "expected_can_move" not in case
                or type(case["expected_can_move"]) is not bool
                or case["expected_state"] not in {state.value for state in SafetyState}):
            raise ValueError("expected result missing/invalid")
        if not isinstance(case.get("events"), list) or any(not isinstance(e, str) for e in case["events"]):
            raise ValueError("events malformed")
        if "authorize_goal" in case["events"] and not isinstance(case.get("goal_id"), str):
            raise ValueError("goal_id required for authorize_goal")
    return len(cases)


def _snapshot(state: SafetySnapshot) -> dict:
    return {
        "state": state.state.value,
        "reason": state.reason,
        "audit_seq": state.audit_seq,
        "generation": state.generation,
        "startup_epoch": state.startup_epoch,
        "authorized_goal_id": state.authorized_goal_id,
        "can_move": can_move(state),
    }


def run_fixture_case(case: dict) -> tuple[SafetySnapshot, list[dict[str, Any]]]:
    if not isinstance(case, dict) or not isinstance(case.get("events"), list):
        raise ValueError("invalid case")
    state = SafetySnapshot()
    trace = [_snapshot(state)]
    for event in case["events"]:
        if event == "restart":
            # Restart is a process lifecycle operation, not a normal FSM event.
            state = SafetySnapshot()
        elif event == "authorize_goal":
            state = transition(state, event, goal_id=case["goal_id"],
                               generation=state.generation,
                               startup_epoch=state.startup_epoch)
        else:
            state = transition(state, event)
        trace.append(_snapshot(state))
    return state, trace
