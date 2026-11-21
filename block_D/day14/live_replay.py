"""AXIA D14 offline classroom Safety Control Room generator.

Read-only projector/quiz view of the *existing* D14 synthetic fixture and
*unchanged student* policy replay.  No hardware, ROS, Gazebo, goal, fault, stop,
reset, rearm, or certified E-Stop is commanded. The SLOW/AVOID/STOP cards are
teaching prompts, not a new choose_action_intent() implementation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_lab import load_cases, load_g10_events, replay

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "live_replay_template.html"
HTML_NAME = "axia_d14_safety_control_room.html"
MANIFEST_NAME = "d14_live_manifest.json"
SCOPE = "OFFLINE_SYNTHETIC_L0_NO_ROBOT_CONTROL"

# Deliberately static conceptual exercises; NEVER call them executable policy.
INTENT_CARDS = [
    {
        "id": "approaching_person",
        "name": "손님이 복도로 접근합니다",
        "scene": "센서와 위치 추정이 신선하고, 충돌 영역 밖에 여유 공간이 있습니다.",
        "choice": "SLOW",
        "owner": "Collision Monitor slowdown 또는 Nav2 속도 제한을 별도로 설계·검증",
        "why": "접근 위험을 지켜보며 속도를 낮출 수 있지만 P/U/보호 Latch가 생기면 이 판단은 철회해야 합니다.",
    },
    {
        "id": "cart_blocked_alternate",
        "name": "이동식 카트가 통로를 막았습니다",
        "scene": "Costmap과 위치 추정이 정상이고 사용 가능한 대체 통로가 확인됩니다.",
        "choice": "AVOID",
        "owner": "Nav2 Planner/Controller/Costmap에서 실제 경로 재계획·실행을 별도 검증",
        "why": "경로 재계획은 보호 정지를 해제할 수 없으며, 안전 센서가 고장이라면 주행을 지속하지 않습니다.",
    },
    {
        "id": "scan_fault",
        "name": "주행 중 Scan이 사라졌습니다",
        "scene": "관측 신뢰성이 무너지고 CM Lost/Guard Latch 위험이 생길 수 있습니다.",
        "choice": "STOP",
        "owner": "실제 CM/Guard/Supervisor의 보호 정지·odom·Goal 검증은 이 L0에 포함되지 않음",
        "why": "안전한 감속·회피를 판단할 근거가 없으므로 보호 정지 의도를 우선합니다.",
    },
    {
        "id": "risk_p_after_cart",
        "name": "우회로는 있지만 새로운 P와 Guard 보호 조건이 나타났습니다",
        "scene": "대체 경로는 있으나 예측 위험 P가 있고 보호 제한이 유지되고 있습니다.",
        "choice": "STOP",
        "owner": "보호 제한이 회피 명령보다 우선; 안전 권한 없는 재출발 금지",
        "why": "우회 가능하다는 사실과 지금 움직일 권한이 있다는 것은 별개입니다.",
    },
]


def build_manifest(cases: list[dict] | None = None, g10: list[dict] | None = None) -> dict:
    """Snapshot real student replay() results separately from fixture expectations."""
    cases = load_cases() if cases is None else cases
    g10 = load_g10_events() if g10 is None else g10
    if len(cases) != 16 or len({c["id"] for c in cases}) != 16:
        raise ValueError("D14_LIVE_REQUIRE_EXACT_16_POLICY_CASES")
    if len(g10) != 15 or len({e["event"] for e in g10}) != 15:
        raise ValueError("D14_LIVE_REQUIRE_EXACT_15_G10_EVENTS")
    required = ["SCAN_FAULT", "CM_LOST", "GUARD_LATCH", "FINAL_CMD",
                "ODOM_STOP_DWELL", "RESET_REJECTED_ACTIVE_FAULT", "NO_AUTO_RESUME"]
    ordered = [e["event"] for e in g10]
    if any(x not in ordered for x in required) or g10[-1]["event"] != "NO_AUTO_RESUME":
        raise ValueError("D14_LIVE_G10_EVENTS_CHANGED")
    if any(float(g10[i]["t_sec"]) > float(g10[i+1]["t_sec"]) for i in range(14)):
        raise ValueError("D14_LIVE_G10_ORDER_INVALID")
    data = [
        {
            "id": c["id"],
            "description": c["description"],
            "steps": c["steps"],
            "expected_last_action": c["expected_last_action"],
            "expected_limited": c["expected_limited"],
            "result": replay(c),  # unchanged student implementation, not fabricated GREEN
        }
        for c in cases
    ]
    return {
        "schema": "axia.block_d.d14.control_room.v1",
        "scope": SCOPE,
        "no_ros_gazebo_goal": True,
        "no_control_or_actuation": True,
        "student_policy_green": all(i["result"]["pass"] for i in data),
        "student_policy_pass_count": sum(i["result"]["pass"] for i in data),
        "intent_implementation": "NOT_IMPLEMENTED",
        "intent_evidence": "CONCEPTUAL_WORKSHEET_ONLY_NOT_PYTHON_OR_ROBOT_CONTROL",
        "policy_cases": data,
        "g10_events": g10,
        "intent_cards": INTENT_CARDS,
    }


def render_live_html(manifest: dict) -> str:
    """Single-file, offline HTML with safely embedded JSON. No external assets."""
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count("__AXIA_DATA__") != 1:
        raise ValueError("D14_LIVE_TEMPLATE_DATA_PLACEHOLDER_INVALID")
    if not manifest.get("no_ros_gazebo_goal") or not manifest.get("no_control_or_actuation"):
        raise ValueError("D14_LIVE_INVALID_SAFETY_SCOPE")
    payload = json.dumps(manifest, ensure_ascii=False, separators=(",", ":"))
    # Do not let an untrusted fixture label close the embedded JSON script.
    payload = (payload.replace("&", "\\u0026")
               .replace("<", "\\u003c").replace(">", "\\u003e")
               .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))
    return template.replace("__AXIA_DATA__", payload)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AXIA D14 interactive offline Safety Control Room (synthetic L0)")
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    args = parser.parse_args()
    manifest = build_manifest()
    out = args.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / HTML_NAME).write_text(render_live_html(manifest), encoding="utf-8")
    (out / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("D14_LIVE_GENERATOR_L0_PASS cases=16 g10_events=15 intent=WORKSHEET_ONLY")
    print("D14_LIVE_STUDENT_GREEN=" + ("1" if manifest["student_policy_green"] else "0"))
    print("D14_LIVE_STUDENT_CASES_PASSED=" + str(manifest["student_policy_pass_count"]))
    print("D14_LIVE_HTML=" + str(out / HTML_NAME))
    print("D14_LIVE_MANIFEST=" + str(out / MANIFEST_NAME))
    print("D14_LIVE_SCOPE=" + SCOPE + " NO_ROS_GAZEBO_GOAL")
    return 0  # generator success is NEVER evidence of student policy success


if __name__ == "__main__":
    raise SystemExit(main())
