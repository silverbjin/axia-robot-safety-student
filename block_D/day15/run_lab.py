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


def offline_replay_html(data,review,pnu,stages):
    """No fabricated timestamps, no external images/media, no actual raw replay."""
    payload=json.dumps({"data":data,"review":review,"pnu":pnu,"stages":stages},
                       ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")
    template=r'''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AXIA D15 | G07 jrCIgoGl 교육용 증거 Replay</title>
<style>
body{font:15px system-ui,sans-serif;max-width:980px;margin:26px auto;padding:0 14px;color:#17202e;line-height:1.55}
h1{font-size:1.6rem} .warning{border-left:4px solid #c2410c;padding:10px;background:#fff7ed}
.panel{padding:18px;border:1px solid #cbd5e1;border-radius:12px;margin:18px 0}
nav{display:flex;gap:8px;flex-wrap:wrap;align-items:center}button{padding:8px 16px;border-radius:8px;border:1px solid #64748b;background:#f1f5f9;cursor:pointer}
button:focus{outline:2px solid #2563eb}output{font-weight:750}svg{width:100%;height:auto;background:#f8fafc}
table{border-collapse:collapse;width:100%}th,td{padding:8px;border-bottom:1px solid #cbd5e1;text-align:left}
small{color:#475569}.ok{color:#166534}.hold{color:#9a3412}
</style></head><body>
<h1>G07 jrCIgoGl — 증거 분석 Replay</h1>
<div class="warning"><strong>실제 영상/rosbag Replay가 아닙니다.</strong>
기존 공개 파생 수치의 단계별 <em>교육용 재표시</em>입니다. 단계 순서와 스냅샷 값만 제공되며 원본 이벤트 시각·실시간 센서 프레임은 없습니다.
원본 자동 판정은 HOLD이고 실제 GUI 화면 콘텐츠는 미검증입니다.</div>
<div class="panel"><nav>
<button id="previous" type="button">이전 증거</button>
<button id="next" type="button">다음 증거</button>
<label>증거 번호 <input id="slide" type="range" min="0" max="6" step="1" value="0"/></label>
<output id="idx">1 / 7</output></nav>
<h2 id="stage"></h2><p id="note"></p>
<table aria-label="공개 파생 스냅샷 필드"><thead><tr><th>필드</th><th>기록값</th></tr></thead><tbody id="fields"></tbody></table>
<svg viewBox="0 0 720 130" aria-label="CLEAR/SLOW/STOP 전방 장애물 거리의 정적 비교"><line x1="40" y1="70" x2="684" y2="70" stroke="#64748b" stroke-width="3"/>
<circle cx="626" cy="70" r="12" fill="#2563eb"/><circle cx="230" cy="70" r="12" fill="#f59e0b"/><circle cx="156" cy="70" r="12" fill="#dc2626"/>
<text x="585" y="108">CLEAR 2.02m</text><text x="193" y="43">SLOW .66m</text><text x="120" y="108">STOP .38m</text>
</svg><small>거리 도식은 실제 Gazebo 프레임·로봇 궤적이 아닌 근사 비율의 교육 보조입니다.</small></div>
<section class="panel"><h2>별도의 P/N/U 수업 증거</h2><p>G09 P/N/U는 D13 합성 예측, D14는 합성 위험 정책입니다. G07 Owner의 실제 사람 검출 결과가 아닙니다.</p>
<p>기존 S04 실 Gazebo 검증은 별도 #43455456960, 이번 jrCIgoGl 실행이 아닙니다.</p></section>
<section class="panel"><h2>판정 경계</h2><p id="verdict"></p>
<p class="hold">HOLD_RAW_REVIEW_AND_VISUAL_PENDING · FORMAL_SAFETY_TIMING_ACCEPTANCE=NOT_CLAIMED · CERTIFIED_ESTOP=false</p>
<p>과거 다른 CI에서 188.578ms Guard age, 150ms 초과 최초 래치 사례가 있으므로 이 한 회 성공을 전체 안정성 보증으로 사용할 수 없습니다.</p></section>
<script type="application/json" id="evidence">__PAYLOAD__</script>
<script>
const d=JSON.parse(document.getElementById("evidence").textContent);
let at=0;
const $=(x)=>document.getElementById(x);
function draw(){
 const step=d.stages[at];$("idx").textContent=(at+1)+" / "+d.stages.length;
 $("slide").value=String(at);$("stage").textContent=step.id+" — "+step.kind;
 $("note").textContent=step.note;
 const tbody=$("fields");tbody.textContent="";
 for(const [k,v] of Object.entries(step.fields)){
   const tr=document.createElement("tr"),a=document.createElement("td"),b=document.createElement("td");
   a.textContent=k;b.textContent=String(v);tr.append(a,b);tbody.append(tr);
 }
 $("verdict").textContent=d.review.numeric_gate+
   " — 공개 집계자료 L0 계약 판정 (새 Gazebo/WSL2 인수 아님)";
}
$("previous").addEventListener("click",()=>{at=Math.max(0,at-1);draw()});
$("next").addEventListener("click",()=>{at=Math.min(d.stages.length-1,at+1);draw()});
$("slide").addEventListener("input",(e)=>{at=Number(e.target.value);draw()});
draw();
</script></body></html>'''
    return template.replace("__PAYLOAD__",payload)


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
        offline_replay_html(data,review,pnu,stages),encoding="utf-8")
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
