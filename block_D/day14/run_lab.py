"""AXIA D14 synthetic event replay and offline HTML policy diagram.

Zero external dependencies. No ROS node, no actual Supervisor state transition,
no Nav2 goal, no cmd_vel or fault injection.
"""
from __future__ import annotations
import argparse
import html
import json
from pathlib import Path

from risk_policy_student import RiskState, apply_verdict, expired_verdict

HERE=Path(__file__).resolve().parent
POLICY=HERE/"fixtures"/"policy_events.json"
G10=HERE/"fixtures"/"g10_events.json"
SCOPE="SYNTHETIC_ROS_L1_NO_MOTION"


def load_cases(path=POLICY):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema")!="axia.block_d.d14.policy_events.v1":
        raise ValueError("D14_INVALID_POLICY_FIXTURE_SCHEMA")
    if len(data.get("cases",[]))<10:
        raise ValueError("D14_INCOMPLETE_POLICY_FIXTURES")
    return data["cases"]


def load_g10_events(path=G10):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema")!="axia.block_d.d14.g10_educational_events.v1":
        raise ValueError("D14_INVALID_G10_FIXTURE_SCHEMA")
    events=data["events"]
    if len(events)!=15:
        raise ValueError("D14_G10_FIXTURE_15_EVENTS_REQUIRED")
    return events


def replay(case):
    """Returns educational policy-only snapshots, not actual Supervisor states."""
    state=RiskState()
    trace=[]
    for e in case["steps"]:
        kind=e["kind"]
        when=e["mono"]
        if kind=="verdict":
            payload={
                "seq":e["seq"],"verdict":e["verdict"],
                "scope":e.get("scope",SCOPE),
                "gate_accepted":e.get("gate_accepted",False),
                "goal_sent":False,"certified_estop":False,
            }
            state,action=apply_verdict(
                state,payload,now_mono=when,
                unique_source=e.get("unique_source",True),
                owned_goal=e.get("owned_goal",True),
                healthy=e.get("healthy",True))
            receipt_stale=expired_verdict(state,now_mono=when)
        elif kind=="tick":
            receipt_stale=expired_verdict(state,now_mono=when)
            action=("RECEIPT_EXPIRED_REQUEST_LIMIT" if receipt_stale else "RECEIPT_FRESH_NO_CHANGE")
        else:
            raise ValueError("D14_UNKNOWN_EVENT_TYPE")
        limited_request=state.limited_by_risk or receipt_stale
        trace.append({
            "mono":when,"kind":kind,"verdict":e.get("verdict","TICK"),
            "action":action,"limited_request":limited_request,
            "last_seq":state.last_seq,"ever_received":state.ever_received,
            "receipt_expired":receipt_stale,
            "policy_indicator":"LIMITED_REQUEST" if limited_request else "NORMAL_POLICY",
        })
    last=trace[-1]
    return {
        "case_id":case["id"],"expected_last_action":case["expected_last_action"],
        "expected_limited":case["expected_limited"],
        "actual_last_action":last["action"],"actual_limited":last["limited_request"],
        "pass":last["action"]==case["expected_last_action"] and
                last["limited_request"]==case["expected_limited"],
        "trace":trace,
        "verification":"OFFLINE_SYNTHETIC_L0_NOT_REAL_SUPERVISOR_OR_GAZEBO",
    }


def render_html(cases,results,g10):
    """Static SVG policy transition and step timeline with no remote assets."""
    rows=[]
    for case,result in zip(cases,results):
        safeid=html.escape(case["id"])
        actions=" / ".join(html.escape(s["action"]) for s in result["trace"])
        note=html.escape(case["description"])
        rows.append(f'<tr><td>{safeid}</td><td>{note}</td><td>{actions}</td><td>{result["expected_limited"]}</td><td>{result["actual_limited"]}</td></tr>')
    g10rows=[]
    for e in g10:
        g10rows.append('<tr><td>{:.2f}</td><td>{}</td></tr>'.format(
            e["t_sec"], html.escape(e["event"])))
    template='''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AXIA D14 위험정책·복합 장애 — L0</title><style>
body{font-family:system-ui,sans-serif;max-width:1080px;margin:24px auto;padding:0 18px;color:#152238}
svg{width:100%;max-width:850px;height:auto;border:1px solid #ddd;border-radius:12px}
table{border-collapse:collapse;width:100%;font-size:.88rem}td,th{border:1px solid #cbd5e1;padding:7px;text-align:left}tr:nth-child(even){background:#f1f5f9}
section{margin:24px 0}.note{color:#9a3412}
</style></head><body>
<h1>D14 — 위험정책 요청은 어떻게 유지되는가?</h1>
<p class="note">SYNTHETIC L0. 이 그림은 기존 Supervisor의 실제 NORMAL/LIMITED 상태나 Nav2 Goal 수행 증거가 아닙니다.</p>
<svg viewBox="0 0 850 270" role="img" aria-label="NORMAL 정책 상태에서 LIMITED 요청으로 전환, N만으로는 복귀 불가">
<rect x="55" y="70" width="220" height="100" rx="16" fill="#e0f2fe" stroke="#0369a1" stroke-width="3"/>
<text x="165" y="110" text-anchor="middle" fill="#075985" font-size="20">NORMAL_POLICY</text>
<text x="165" y="135" text-anchor="middle" fill="#075985" font-size="13">N (fresh, no previous risk)</text>
<rect x="545" y="70" width="245" height="100" rx="16" fill="#ffedd5" stroke="#c2410c" stroke-width="3"/>
<text x="667" y="110" text-anchor="middle" fill="#9a3412" font-size="20">LIMITED_REQUEST</text>
<text x="667" y="135" text-anchor="middle" fill="#9a3412" font-size="13">P / U / stale / untrusted</text>
<path d="M275,115 L543,115" stroke="#334155" stroke-width="3"/>
<polygon points="542,115 527,107 527,123" fill="#334155"/>
<text x="405" y="100" text-anchor="middle" font-size="14">유효한 위험 입력</text>
<path d="M666,170 Q665,230 595,228 Q545,225 565,169" fill="none" stroke="#c2410c" stroke-width="3"/>
<text x="680" y="242" text-anchor="middle" font-size="14">N / 중복만으로 해제 금지</text>
<text x="425" y="266" text-anchor="middle" font-size="12" fill="#475569">Owner reset/rearm는 본 실습에서 실행하지 않음</text>
</svg>
<section><h2>합성 P/N/U 및 이상 전송의 최종 정책 요청</h2>
<table><thead><tr><th>사례</th><th>설명</th><th>정책 action</th><th>기대 limited</th><th>실제 limited</th></tr></thead><tbody>__POLICY_ROWS__</tbody></table></section>
<section><h2>G10 — 합성 복합 장애 이벤트 시간 순서</h2>
<p>SCAN_FAULT → CM_LOST → GUARD_LATCH → 최종 ZERO → Goal CANCELED → Owner 승인된 Reset/Rearm. 실제 Fault 주입 아님.</p>
<table><thead><tr><th>t(s)</th><th>이벤트</th></tr></thead><tbody>__G10_ROWS__</tbody></table></section>
<p class="note">SW 정지는 인증 E-Stop이 아닙니다. P/N/U 결과는 제어 명령이 아니며 별도 /cmd_vel 발행자는 없습니다.</p>
</body></html>'''
    return template.replace("__POLICY_ROWS__","\n".join(rows)).replace("__G10_ROWS__","\n".join(g10rows))


def main():
    parser=argparse.ArgumentParser(description="D14 synthetic PNU -> LIMITED policy replay")
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--case")
    args=parser.parse_args()
    cases=load_cases()
    if args.case:
        cases=[x for x in cases if x["id"]==args.case]
        if not cases:
            parser.error("unknown D14 case")
    results=[replay(x) for x in cases]
    g10=load_g10_events()
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"d14_policy_results.json").write_text(
        json.dumps({"scope":"SYNTHETIC_POLICY_L0_NO_MOTION","cases":results,
                    "all_pass":all(x["pass"] for x in results)},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (args.out/"d14_policy_timeline.html").write_text(
        render_html(cases,results,g10),encoding="utf-8")
    for x in results:
        print("D14_CASE={} expected={} actual={} limited={} status={}".format(
            x["case_id"],x["expected_last_action"],x["actual_last_action"],
            x["actual_limited"],"PASS" if x["pass"] else "RED_EXPECTED_TODO"))
    print("D14_G10_SYNTHETIC_EVENT_COUNT="+str(len(g10)))
    ok=all(x["pass"] for x in results)
    print("D14_STUDENT_RESULT="+("GREEN" if ok else "RED_EXPECTED_TODO"))
    print("D14_REPORT="+str(args.out/"d14_policy_results.json"))
    return 0 if ok else 2

if __name__=="__main__":
    raise SystemExit(main())
