#!/usr/bin/env python3
"""G07 classroom scenario cards from published measured records. OFFLINE, NO ROS or Goal.

This is not a rosbag replay, sim-time animation, or new acceptance test.
All stage numbers are 2026-11-22 Owner WSL2 RAW report excerpts, except
the separately labeled rejected 2026-11-21 Native L2 values.
"""
import argparse
import json
import math
import sys
from pathlib import Path

SNAPSHOT=Path(__file__).resolve().parents[1]/"scenarios/PROVEN_G07_SCENARIO_SNAPSHOT_20261122.json"
GOOD="f7edb2d126502eeeed58ae014adadc7a2096d41b"
BAD="a04f9a7da8d54bbd9f944d05388792cb706adf28"
REPORT_SHA="c2c4f66c532be2a41855239860b9a9f5d60c4586"

def validate(data):
    errors=[]
    if not isinstance(data,dict):
        return ["NOT_A_RECORD"]
    if data.get("schema")!="axia.day02.scenario_historic_public_snapshot.v1":
        errors.append("SCHEMA_CHANGED")
    if data.get("source_type")!="PUBLIC_REPORT_EXCERPT_NOT_RAW_BAG":
        errors.append("EVIDENCE_TYPE_CHANGED")
    if (data.get("student_source_sha")!=GOOD
        or data.get("public_ci_source_sha")!="64ba0161e66126b4743b4b12a859f4a5349ae58a"
        or data.get("native_l2_run_id")!=44965035965
        or data.get("owner_report_commit")!=REPORT_SHA):
        errors.append("ACCEPTED_PROVENANCE_DRIFT")
    a=data.get("historic_owner",{})
    f=data.get("historical_failed",{})
    lim=data.get("limits",{})
    cl=data.get("claims",{})
    if not all(isinstance(v,dict) for v in (a,f,lim,cl)):
        return errors+["INVALID_SCHEMA_BLOCKS"]
    if (a.get("result")!="PASS_SCOPED"
        or a.get("automatic_verdict")!="HOLD_RAW_REVIEW_AND_VISUAL_PENDING"
        or a.get("independent_gui_content_review") is not False):
        errors.append("OWNER_SCOPE_OVERCLAIM")
    if (f.get("student_source_sha")!=BAD or f.get("public_ci_source_sha")!="8e03ac0a912ca9b81bdddda70212e52e6d804389"
        or f.get("native_l2_run_id")!=44914827138
        or f.get("moving_l2")!="0_OF_2_FAIL" or f.get("owner_l3")!="NOT_RUN"
        or f.get("root_cause")!="UNDETERMINED"):
        errors.append("REJECTED_PROVENANCE_DRIFT")
    if (cl.get("new_ros_gazebo_run") is not False or cl.get("new_goal_sent") is not False
        or cl.get("new_l2_or_l3_acceptance") is not False or cl.get("certified_estop") is not False
        or cl.get("dds_rmw_root_cause")!="UNDETERMINED"):
        errors.append("UNSAFE_NEW_ACCEPTANCE_CLAIM")
    # Preserve exact published measurements. A changed number is not new raw evidence.
    numeric=[
      (a.get("phases",{}).get("CLEAR",{}),"front_m",2.048107),
      (a.get("phases",{}).get("CLEAR",{}),"cm_linear_mps",0.062925),
      (a.get("phases",{}).get("CLEAR",{}),"final_linear_mps",0.037684),
      (a.get("phases",{}).get("SLOW",{}),"front_m",0.674758),
      (a.get("phases",{}).get("SLOW",{}),"cm_linear_mps",0.004810),
      (a.get("phases",{}).get("SLOW",{}),"final_linear_mps",0.003422),
      (a.get("phases",{}).get("STOP",{}),"front_m",0.396788),
      (a.get("phases",{}).get("STOP",{}),"cm_linear_mps",0.0),
      (a.get("phases",{}).get("STOP",{}),"final_linear_mps",0.0),
      (a,"odom_total_m",0.129946523),
      (a,"odom_zero_dwell_sec",1.026194649),
      (a.get("timing_ms",{}),"scan_callback_max",215.082877),
      (a.get("timing_ms",{}),"clock_callback_max",95.138822),
      (a.get("timing_ms",{}),"odom_callback_max",149.593842),
      (a.get("timing_ms",{}),"cm_pre_guard_callback_max",71.460029),
      (a.get("timing_ms",{}),"guard_internal_cm_age_max",49.279328),
      (f.get("cycle1",{}),"scan_callback_max_ms",439.011892),
      (f.get("cycle1",{}),"clock_callback_max_ms",335.393855),
      (f.get("cycle1",{}),"odom_callback_max_ms",374.025229),
      (f.get("cycle2",{}),"first_blocking_odom_ms",362.100229),
      (f.get("cycle2",{}),"cm_pre_guard_max_ms",379.730024),
      (f.get("cycle2",{}),"original_cm_rmw_received_ms",375.941379),
      (f.get("cycle2",{}),"independent_cm_rmw_received_ms",54.116537),
      (f.get("cycle2",{}),"cm_source_interval_ms",53.837048),
    ]
    for block,name,val in numeric:
        got=block.get(name) if isinstance(block,dict) else None
        if type(got) not in (int,float) or not math.isfinite(got) or abs(got-val)>1e-7:
            errors.append("PUBLIC_MEASUREMENT_DRIFT:"+name)
    for key,val in (("scan_callback_ms",300),("clock_callback_ms",300),
                    ("odom_callback_ms",300),("cm_pre_guard_callback_ms",120),
                    ("guard_internal_cm_age_ms",150),("minimum_odom_zero_dwell_sec",1.)):
        if lim.get(key)!=val:errors.append("CONTRACT_CHANGED:"+key)
    if not all((a.get("same_goal_uuid_cancel") is True,a.get("goal_cancel_ack") is True,
        a.get("nav_shutdown_ack") is True,a.get("localization_shutdown_ack") is True,
        a.get("goal_terminal_status")==5,a.get("cm_exit_code")==0,
        a.get("clean_processes")==21,a.get("bag_topic_count")==14,
        a.get("bag_messages")==54641,a.get("contact_count")==0,
        f.get("cycle1",{}).get("goal_sent") is False,
        f.get("cycle2",{}).get("goal_sent") is True)):
        errors.append("SCENARIO_CONTRACT_MISMATCH")
    return errors

def timeline(data,case):
    a=data["historic_owner"]; f=data["historical_failed"]; lim=data["limits"]
    lines=[
        "HISTORICAL_EVIDENCE_REPLAY_NO_ROS_NO_GOAL",
        "NEW_L2_L3_NOT_RUN  CERTIFIED_ESTOP=false",
        "실측 수치의 순서별 해설입니다. 정확한 물리 재생·동영상·새 Gazebo 실행이 아닙니다.",
    ]
    if case in ("success","compare"):
        lines += ["", "[ACCEPTED G07 / HISTORIC OWNER L3 RAW PASS_SCOPED]",
                  "S01 준비: Gazebo Waffle→/scan→Fault Injector→/safety/scan; Nav2 Goal 권한 별도",
                  "S02 CLEAR: 전방 %.6fm / CM %.6fm/s / Guard 최종 %.6fm/s" %
                  tuple(a["phases"]["CLEAR"][v] for v in ("front_m","cm_linear_mps","final_linear_mps")),
                  "S03 SLOW:  전방 %.6fm / CM %.6fm/s / Guard 최종 %.6fm/s" %
                  tuple(a["phases"]["SLOW"][v] for v in ("front_m","cm_linear_mps","final_linear_mps")),
                  "S04 STOP:  전방 %.6fm / CM %.6fm/s / Guard 최종 %.6fm/s" %
                  tuple(a["phases"]["STOP"][v] for v in ("front_m","cm_linear_mps","final_linear_mps")),
                  "S05 CANCEL/ODOM: 동일 UUID Goal terminal=CANCELED(5), 실제 누적 이동 %.6fm, ZERO dwell %.6fs (기준 ≥%.1fs)" %
                  (a["odom_total_m"],a["odom_zero_dwell_sec"],lim["minimum_odom_zero_dwell_sec"]),
                  "S06 SHUTDOWN: Nav ACK=%s / Localization ACK=%s / CM exit=%s / 21 프로세스 정상 종료" %
                  (a["nav_shutdown_ack"],a["localization_shutdown_ack"],a["cm_exit_code"]),
                  "타이밍: scan %.3f<300ms; CM→preGuard %.3f<120ms; Guard 내부 CM age %.3f<150ms" %
                  (a["timing_ms"]["scan_callback_max"],a["timing_ms"]["cm_pre_guard_callback_max"],a["timing_ms"]["guard_internal_cm_age_max"]),
                  "Contact=0은 이번 세션 충돌 미발생 증거이지 Positive contact calibration을 증명하지 않습니다.",
                  "원본 자동 HOLD_RAW_REVIEW_AND_VISUAL_PENDING 보존; 별도 원본 수치/Lifecycle 사후 PASS_SCOPED",
                  "GUI 창 존재만 확인, 독립적인 화면 콘텐츠 판독은 NOT_PROVIDED",
                  ]
    if case in ("failed","compare"):
        one=f["cycle1"]; two=f["cycle2"]
        lines += ["", "[REJECTED G07 / HISTORIC PUBLIC NATIVE MOVING L2 0/2 FAIL]",
                  "F01 Cycle1 PRE_GOAL: /scan %.3fms >300, /clock %.3fms >300, /odom %.3fms >300; Goal 발행 없음" %
                  (one["scan_callback_max_ms"],one["clock_callback_max_ms"],one["odom_callback_max_ms"]),
                  "F02 Cycle2 POST_GOAL: 첫 FSM BOOT_SAFE→NORMAL, 최초 blocking /odom %.3fms >300" % two["first_blocking_odom_ms"],
                  "F03 명령 전달: /cmd_vel_pre_guard %.3fms >120ms" % two["cm_pre_guard_max_ms"],
                  "F04 전달 경계: CM source %.3fms / 독립 수신 %.3fms / 기존 Subscriber RMW 수신 %.3fms" %
                  (two["cm_source_interval_ms"],two["independent_cm_rmw_received_ms"],two["original_cm_rmw_received_ms"]),
                  "분석 판정: SOURCE와 실제 기존 수신 간격 차이 관측; DDS/Executor/OS 근본 원인 UNDETERMINED",
                  "미검증: 실패 소스 Owner L3 NOT_RUN; 새 소스 Native 2/2 PASS 전까지 HOLD",
                  ]
    if case=="compare":
        lines += ["", "비교 경고: Student SHA와 Public CI 환경이 모두 달라서 성공본·실패본 차이만으로 인과성을 증명할 수 없습니다."]
    lines += ["", "출처 ① "+data["owner_report_ref"],"출처 ② "+f["report_ref"]]
    return lines

def result_record(data,case,lines):
    return {"schema":"axia.day02.scenario_display.v1","case":case,
      "verification_level":"HISTORIC_EVIDENCE_REPLAY_L0_ONLY",
      "stage_count":6 if case=="success" else 4 if case=="failed" else 10,
      "accepted_source_sha":data["student_source_sha"],
      "failed_source_sha":data["historical_failed"]["student_source_sha"],
      "accepted_owner_scope":"PASS_SCOPED",
      "failed_case_status":"0_OF_2_FAIL",
      "new_ros_gazebo_run":False,"new_l2_l3_acceptance":False,
      "certified_estop":False,"narration":lines}

def main():
    p=argparse.ArgumentParser(description="G07 historical observations; no Gazebo, no ROS or Goal")
    p.add_argument("--case",choices=("success","failed","compare"),default="success")
    p.add_argument("--json-out",type=Path,help="Optional JSON report; refuses overwrite")
    args=p.parse_args()
    try:
        data=json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        errors=validate(data)
        if errors:
            print("G07_SCENARIO_UNVERIFIED_HOLD "+";".join(errors),file=sys.stderr)
            return 3
        lines=timeline(data,args.case)
        print("\n".join(lines))
        if args.json_out:
            dest=args.json_out.expanduser()
            dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open("x",encoding="utf-8") as fh:
                json.dump(result_record(data,args.case,lines),fh,ensure_ascii=False,indent=2)
                fh.write("\n")
        return 0
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print("G07_SCENARIO_EVIDENCE_UNAVAILABLE_HOLD "+type(exc).__name__,file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
