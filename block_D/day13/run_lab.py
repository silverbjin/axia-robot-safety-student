"""D13 synthetic reachability lab CLI + self-contained SVG/HTML viewer.

Only stdlib / local fixture. No ROS graph, Nav2 Goal, motor or safety authority.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

from reachability_student import classify_time_indexed

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "cases.json"


def load_cases(fixture: Path = FIXTURE) -> list[dict]:
    manifest = json.loads(Path(fixture).read_text(encoding="utf-8"))
    if manifest.get("schema") != "axia.block_d.d13.synthetic.v1":
        raise ValueError("D13_INVALID_FIXTURE_SCHEMA")
    csv_path = Path(fixture).parent / manifest["robot_csv"]
    with csv_path.open(newline="", encoding="utf-8") as fh:
        trace = [{k: float(row[k]) for k in ("t_sec", "x", "y", "radius")}
                 for row in csv.DictReader(fh)]
    cases = []
    for source in manifest["cases"]:
        item = dict(source)
        item["now_sec"] = float(manifest["now_sec"])
        item["robot_trajectory"] = [dict(p) for p in trace]
        if item.get("truncate_last"):
            item["robot_trajectory"] = item["robot_trajectory"][:-1]
        if item.get("time_shift_index") is not None:
            item["robot_trajectory"][int(item["time_shift_index"])]["t_sec"] += .04
        cases.append(item)
    return cases


def evaluate_case(case: dict) -> dict:
    """Pre-check shared frame; frame mismatch is teaching adapter, not G09 oracle."""
    robot_frame, person_frame = case.get("robot_frame"), case.get("person_frame")
    if not (isinstance(robot_frame, str) and robot_frame and robot_frame == person_frame):
        actual = "U"
        explanation = "FRAME_MISMATCH_OR_UNKNOWN"
    else:
        actual = classify_time_indexed(
            case["robot_trajectory"], case["person"], now_sec=case["now_sec"])
        explanation = "TIME_INDEXED_ORACLE"
    return {"id":case["id"],"expected":case["expected"],"actual":actual,
            "pass":actual == case["expected"],"reason":explanation,
            "scope":"SYNTHETIC_OFFLINE_L0_NOT_ROS_OR_GAZEBO"}


def render_html(case: dict, result: dict) -> str:
    """Create read-only co-timed robot/human 2D discs and distance slider."""
    payload = json.dumps({"case":case,"result":result},ensure_ascii=False).replace("<","\\u003c")
    template = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AXIA D13 | 시간 동기 Reachability</title>
<style>
body{font-family:system-ui,sans-serif;max-width:860px;margin:24px auto;padding:0 16px;color:#17212f}
h1{font-size:1.5rem} .panel{border:1px solid #cbd5e1;border-radius:12px;padding:14px;margin:14px 0}
small{color:#475569} svg{width:100%;height:auto;background:#f8fafc;border-radius:8px}
output{font-weight:700}input{width:100%}.r{color:#2563eb}.h{color:#dc2626}
kbd{background:#f1f5f9;padding:3px} .warn{color:#9a3412}
</style></head><body>
<h1>AXIA D13 — 같은 장소와 <em>같은 시각</em>인가?</h1>
<p>합성 fixture의 시간 동기 원형 영역을 비교합니다. ROS·Gazebo·주행 명령을 실행하지 않습니다.</p>
<div class="panel"><strong id="caseId"></strong> | expected <output id="expected"></output>
 | student <output id="verdict"></output><p id="reason"></p></div>
<div class="panel">
<label for="step">예측 시점 <output id="stamp">0</output></label>
<input type="range" id="step" min="0" max="15" step="1" value="0">
<svg id="scene" viewBox="0 0 560 155" role="img" aria-label="로봇과 사람 원형 위치">
<line x1="22" y1="78" x2="530" y2="78" stroke="#94a3b8" stroke-dasharray="4 5"/>
<circle id="robot" r="11" cy="78" fill="#2563eb" fill-opacity=".28" stroke="#1d4ed8" stroke-width="2"/>
<circle id="human" r="14" cy="78" fill="#ef4444" fill-opacity=".25" stroke="#dc2626" stroke-width="2"/>
<text x="25" y="142" fill="#334155">파랑=로봇 점유 반경 / 빨강=사람 예측 점유 반경</text>
</svg>
<p id="metric"></p><small>한 화면의 겹침은 시점별 교육용 계산 예시입니다. P/N/U 및 안전 권한을 대신하지 않습니다.</small>
</div>
<p class="warn">U = 판단 불가. frame mismatch는 CLI의 별도 입력 검증이며 원본 G09가 TF 변환을 수행한다는 뜻이 아닙니다.</p>
<script type="application/json" id="payload">__PAYLOAD__</script>
<script>
const data=JSON.parse(document.getElementById("payload").textContent);
const c=data.case, r=data.result;
document.getElementById("caseId").textContent=c.id;
document.getElementById("expected").textContent=r.expected;
document.getElementById("verdict").textContent=r.actual;
document.getElementById("reason").textContent=r.reason;
const slider=document.getElementById("step");
slider.max=String(c.robot_trajectory.length-1);
function paint(){
 const p=c.robot_trajectory[Number(slider.value)], h=c.person, t=p.t_sec;
 const hx=h.x+h.vx*(t-h.observed_sec), hy=h.y+h.vy*(t-h.observed_sec);
 const scale=150, x0=45, cy=78;
 const rb=document.getElementById("robot"), hu=document.getElementById("human");
 rb.setAttribute("cx",String(x0+p.x*scale)); rb.setAttribute("cy",String(cy-p.y*scale));
 rb.setAttribute("r",String(p.radius*scale));
 hu.setAttribute("cx",String(x0+hx*scale)); hu.setAttribute("cy",String(cy-hy*scale));
 hu.setAttribute("r",String(h.radius*scale));
 const dist=Math.hypot(p.x-hx,p.y-hy);
 document.getElementById("stamp").textContent=t.toFixed(2)+" s";
 document.getElementById("metric").textContent=
  "동시간 거리 "+dist.toFixed(3)+" m / 반경 합 "+(p.radius+h.radius).toFixed(3)+
  " m / 기하학적 겹침 "+(dist<=p.radius+h.radius?"YES":"NO");
}
slider.addEventListener("input",paint);paint();
</script></body></html>'''
    return template.replace("__PAYLOAD__", payload)


def main() -> int:
    ap = argparse.ArgumentParser(description="AXIA D13 synthetic P/N/U worksheet")
    ap.add_argument("--out", type=Path, required=True, help="out folder, e.g. /tmp/axia-d13")
    ap.add_argument("--case", help="run just one fixture ID")
    ap.add_argument("--list", action="store_true", help="list known fixture IDs")
    args = ap.parse_args()
    cases = load_cases()
    if args.list:
        for case in cases:
            print(case["id"])
        return 0
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            ap.error("unknown case ID")
    args.out.mkdir(parents=True,exist_ok=True)
    results = []
    for case in cases:
        result = evaluate_case(case)
        results.append(result)
        (args.out/(case["id"]+".html")).write_text(render_html(case,result),encoding="utf-8")
        print("D13_CASE={} expected={} actual={} status={}".format(
              result["id"],result["expected"],result["actual"],
              "PASS" if result["pass"] else "RED_EXPECTED_TODO"))
    (args.out/"d13_results.json").write_text(
        json.dumps({"scope":"OFFLINE_SYNTHETIC_L0_NOT_ROS",
                    "cases":results,"all_pass":all(x["pass"] for x in results)},
                   ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("D13_REPORT="+str(args.out/"d13_results.json"))
    print("D13_STUDENT_RESULT="+("GREEN" if all(x["pass"] for x in results) else "RED_EXPECTED_TODO"))
    return 0 if all(x["pass"] for x in results) else 2

if __name__ == "__main__":
    raise SystemExit(main())
