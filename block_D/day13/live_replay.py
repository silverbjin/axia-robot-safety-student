"""AXIA D13 large-screen TIME × SPACE Live Replay generator (synthetic L0).

This is a read-only educational presentation. It does not replace or modify
the student classifier, G09 oracle, G07 Supervisor, Guard, Nav2, or E-Stop.
No third-party dependencies, network calls, ROS graph or robot control.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from run_lab import evaluate_case, load_cases

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "live_replay_template.html"
HTML_NAME = "axia_d13_live_replay.html"
MANIFEST_NAME = "live_replay_manifest.json"
SCOPE = "OFFLINE_SYNTHETIC_L0_NO_ROBOT_CONTROL"
P_ID = "P_same_time_overlap"
N_ID = "N_same_route_different_time"


def _result(status: str, detail: str) -> dict:
    return {"status": status, "detail": detail}


def fixture_first_issue(case: dict) -> dict:
    """Explain *fixture input* evidence only, never claim student detection.

    The checks below are for the six known synthetic U teaching examples.
    They are not the student P/N/U algorithm and not safety authority.
    """
    rf = case.get("robot_frame")
    hf = case.get("person_frame")
    if not isinstance(rf, str) or not isinstance(hf, str) or not rf or rf != hf:
        return _result("FIXTURE_INPUT_INVALID",
                       "frame 불일치: robot=" + str(rf) + " / person=" + str(hf))
    now = float(case["now_sec"])
    person = case["person"]
    observed = float(person["observed_sec"])
    age = now - observed
    if age < 0:
        return _result("FIXTURE_INPUT_INVALID",
                       "미래 관측: observed=" + format(observed, ".1f")
                       + "s > now=" + format(now, ".1f") + "s")
    if age > 0.5:
        return _result("FIXTURE_INPUT_INVALID",
                       "stale 관측: age=" + format(age, ".1f")
                       + "초 > 0.5초")
    confidence = float(person["confidence"])
    if confidence < 0.5 or not math.isfinite(confidence):
        return _result("FIXTURE_INPUT_INVALID",
                       "낮은 confidence=" + format(confidence, ".2f")
                       + " < 0.50")
    trace = case["robot_trajectory"]
    if len(trace) != 16:
        return _result("FIXTURE_INPUT_INVALID",
                       "경로 시점 누락: 실제 " + str(len(trace)) + "개 / 필요 16개")
    for i, item in enumerate(trace):
        expected_t = now + i * 0.2
        actual_t = float(item["t_sec"])
        if not math.isfinite(actual_t) or abs(actual_t - expected_t) > 1e-6:
            return _result("FIXTURE_INPUT_INVALID",
                           "시간 그리드 오류 index=" + str(i) + ": 예상 "
                           + format(expected_t, ".2f") + "초 / 실제 "
                           + format(actual_t, ".2f") + "초")
    return _result("FIXTURE_INPUT_VALID", "fixture 표본의 주요 시각·프레임·신뢰도 계약 통과")


def build_manifest(cases: list[dict]) -> dict:
    """Preserve the eight original fixtures and separately capture student result."""
    by_id = {case["id"]: case for case in cases}
    if len(by_id) != 8 or P_ID not in by_id or N_ID not in by_id:
        raise ValueError("D13_LIVE_INVALID_8_FIXTURE_SET")
    trajectory = by_id[P_ID]["robot_trajectory"]
    if len(trajectory) != 16:
        raise ValueError("D13_LIVE_INVALID_16_TIMEPOINTS")
    times = [float(p["t_sec"]) for p in trajectory]
    if abs(times[0] - 10.1) > 1e-6 or abs(times[-1] - 13.1) > 1e-6:
        raise ValueError("D13_LIVE_INVALID_TIME_BOUNDARY")
    distribution = {"P": 0, "N": 0, "U": 0}
    items = []
    for case in cases:
        expected = case["expected"]
        if expected not in distribution:
            raise ValueError("D13_LIVE_UNKNOWN_EXPECTED")
        distribution[expected] += 1
        actual = evaluate_case(case)["actual"]
        items.append({
            "id": case["id"],
            "expected": expected,  # Hidden until viewer's reveal action.
            "actual": actual,     # The unmodified *student* classifier output.
            "robot_trajectory": case["robot_trajectory"],
            "person": case["person"],
            "fixture_issue": fixture_first_issue(case),
        })
    if distribution != {"P": 1, "N": 1, "U": 6}:
        raise ValueError("D13_LIVE_DISTRIBUTION_CHANGED")
    return {
        "schema": "axia.block_d.d13.live_replay.v1",
        "scope": SCOPE,
        "no_ros_gazebo_goal": True,
        "learner_algorithm_green": all(c["expected"] == c["actual"] for c in items),
        "learner_verdicts": {c["id"]: c["actual"] for c in items},
        "expected_distribution": distribution,
        "geometry": {
            "time_steps": times,
            "sample_count": len(times),
            "t_first": times[0],
            "t_last": times[-1],
            "dt_sec": 0.2,
            "robot_radius_m": float(trajectory[0]["radius"]),
            "person_radius_m": float(by_id[P_ID]["person"]["radius"]),
        },
        "cases": items,
    }


def render_live_html(manifest: dict) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count("__AXIA_DATA__") != 1:
        raise ValueError("D13_LIVE_TEMPLATE_PLACEHOLDER_INVALID")
    payload = json.dumps(manifest, ensure_ascii=False, separators=(",", ":"))
    # Prevent the embedded JSON from ending the script element.
    payload = (payload.replace("&", "\\u0026").replace("<", "\\u003c")
               .replace(">", "\\u003e").replace("\u2028", "\\u2028")
               .replace("\u2029", "\\u2029"))
    return template.replace("__AXIA_DATA__", payload)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AXIA D13: produce standalone projector-friendly offline Live Replay")
    parser.add_argument("--out", required=True, type=Path,
                        help="Output directory, e.g. /tmp/axia-d13-live")
    args = parser.parse_args()
    cases = load_cases()
    manifest = build_manifest(cases)
    output = args.out.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / HTML_NAME).write_text(render_live_html(manifest), encoding="utf-8")
    (output / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("D13_LIVE_REPLAY_L0_PASS cases=8 timepoints=16 expected=P1_N1_U6")
    print("D13_LIVE_LEARNER_GREEN=" + ("1" if manifest["learner_algorithm_green"] else "0"))
    print("D13_LIVE_HTML=" + str(output / HTML_NAME))
    print("D13_LIVE_MANIFEST=" + str(output / MANIFEST_NAME))
    print("D13_LIVE_SCOPE=" + SCOPE + " NO_ROS_GAZEBO_GOAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
