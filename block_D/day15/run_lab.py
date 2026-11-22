"""D15 no-ROS synthetic *ordinal* replay of published G07 aggregate evidence."""
import argparse
import json
import math
from pathlib import Path
from evidence_review import load_evidence, review_baseline, negative_counterexamples, validate_g09_g10_separation

STAGES=[
    {"id":"CLEAR","kind":"actual_reported_snapshot","note":"CLEAR 오도메트리 구간 이동 후 장애물 접근",
     "fields":["clear_odom_travel_m","clear_front_m"]},
    {"id":"SLOW","kind":"actual_reported_snapshot","note":"Supervisor와 CM/Guard 최종 명령 크기를 비교; 화면 속도 체감과 다름",
     "fields":["slow_front_m","slow_supervised_vx_mps","slow_final_vx_mps"]},
    {"id":"STOP","kind":"actual_reported_snapshot","note":"CM 및 최종 명령 0. 소프트웨어 STOP; 인증 E-Stop 아님",
     "fields":["stop_front_m","stop_final_vx_mps"]},
    {"id":"CANCEL","kind":"derived_action_claim","note":"같은 UUID Nav2 ActionStatus 5 CANCELED; 원본 bag은 비공개",
     "fields":["goal_uuid","goal_cancel_status","exact_goal_uuid_cancelled"]},
    {"id":"ODOM_DWELL","kind":"derived_odom_claim","note":"최종 0속도 이후 독립 odom 정지 유지 1초 초과",
     "fields":["zero_dwell_sec","odom_movement_m"]},
    {"id":"SAFETY_TTL","kind":"aggregated_maxima_no_event_timestamps","note":"단일 Owner 세션 내 관측 최대값; timestamp·반복 안정성 미확보",
     "fields":["scan_gap_max_ms","cm_source_gap_max_ms","cm_observer_gap_max_ms",
               "guard_internal_cm_age_max_ms","guard_status_gap_max_ms"]},
    {"id":"PNU_AND_SCOPE","kind":"separate_educational_evidence","note":"G09 P/N/U 및 S04의 입력은 별도 합성 사례. 실제 jrCIgoGl 사람 검출 아님",
     "fields":["raw_machine_status","visual_content_verified","certified_estop"]},
]


def ordered_snapshots(data):
    return [
        dict(id=s["id"],kind=s["kind"],note=s["note"],
             fields={k:data.get(k) for k in s["fields"]})
        for s in STAGES
    ]


def offline_replay_html(data,review,pnu,stages,cases=None):
    """Offline Evidence Theater; no real-time frames, events or external dependencies.

    Backward-compatible signature is preserved for the original D15 replay tests.
    """
    from evidence_theater import immersive_theater_html
    if cases is None:
        cases=negative_counterexamples(data)
    return immersive_theater_html(data,review,pnu,stages,cases)


def run(out):
    data=load_evidence()
    review=review_baseline(data)
    pnu=validate_g09_g10_separation()
    cases=negative_counterexamples(data)
    stages=ordered_snapshots(data)
    out.mkdir(parents=True,exist_ok=True)
    result={"baseline":review,"pnu_separation":pnu,"snapshots":stages,
            "counterexamples":cases,"evidence_source":"PUBLIC_DERIVED_NUMERIC_NOT_RAW",
            "new_gazebo_or_wsl2_executed":False}
    (out/"d15_evidence_review.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (out/"d15_counterexamples.json").write_text(
        json.dumps(cases,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (out/"d15_offline_replay.html").write_text(
        offline_replay_html(data,review,pnu,stages,cases),encoding="utf-8")
    for step in stages:
        print("D15_STEP={} kind={}".format(step["id"],step["kind"]))
    print("D15_EDUCATION_NUMERIC_GATE="+review["numeric_gate"])
    print("D15_SYNTHETIC_NEGATIVE_DETECTION={}/{}".format(sum(x["detected"] and x["not_accepted"] for x in cases),len(cases)))
    print("D15_G09_G10_SOURCE_SEPARATE="+str(pnu["safe_separation"]))
    print("D15_REPLAY_SCOPE=AGGREGATED_PUBLIC_EVIDENCE_ONLY_NO_NEW_ROS_GAZEBO")
    return 0 if (review["numeric_gate"]=="EDUCATION_NUMERIC_ACCEPTED"
                 and pnu["safe_separation"]
                 and all(x["detected"] and x["not_accepted"] for x in cases)) else 2


if __name__=="__main__":
    ap=argparse.ArgumentParser(description="Read-only AXIA D15 synthetic evidence walkthrough")
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    raise SystemExit(run(args.out))
