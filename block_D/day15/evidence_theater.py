"""D15 Evidence Theater: dependency-free ordinal browser presentation of public derived data.

Educational UI only. NO ROS, Gazebo, Action client, cmd_vel or fault injection.
Stage positions are diagrammatic, NOT raw video, timestamps, physical trajectories.
"""
from __future__ import annotations
import json

def immersive_theater_html(data, review, pnu, stages, cases):
    """Render static HTML with an embedded, escaped, immutable evidence snapshot."""
    package={"data":data,"review":review,"pnu":pnu,"stages":stages,"cases":cases,
             "scope":"PUBLIC_DERIVED_AGGREGATE_EDUCATIONAL_L0_NO_NEW_ROS_GAZEBO"}
    payload=(json.dumps(package,ensure_ascii=False,separators=(",",":"))
             .replace("<",r"\u003c").replace(">",r"\u003e")
             .replace("&",r"\u0026"))
    page=r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>AXIA D15 | EVIDENCE THEATER</title>
<style>
:root{color-scheme:dark;--navy:#091426;--pane:#14253b;--edge:#315070;--text:#e6f0ff;--muted:#b8cbe0;--cyan:#5eead4;--amber:#fdba74;--red:#fda4af}
*{box-sizing:border-box}html{font-size:17px}body{margin:0;background:radial-gradient(circle at 4% 2%,#153051 0,#091426 48%);color:var(--text);font-family:"Malgun Gothic","Apple SD Gothic Neo",Arial,sans-serif;line-height:1.55}
main{max-width:1500px;margin:0 auto;padding:18px 26px 35px}
header{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:14px;margin:4px 0 12px}
h1{font-size:clamp(1.4rem,2.5vw,2.1rem);margin:0;letter-spacing:.035em}
h2{font-size:1.2rem;margin:0 0 8px}h3{font-size:1.05rem;margin:0 0 8px}
.subtitle{color:var(--muted);font-size:.85rem}p{margin:4px 0 10px}
.pill{padding:5px 12px;border-radius:999px;border:1px solid #a16207;color:#fde68a;background:#443118;font-size:.84rem;font-weight:700}
.scope{border:2px solid #eab308;background:#332814;color:#fff3c4;border-radius:12px;padding:11px 15px;font-weight:700;margin-bottom:14px;font-size:.92rem}
.layout{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:14px}
.card{background:var(--pane);border:1px solid var(--edge);border-radius:16px;padding:18px;min-width:0;box-shadow:0 12px 32px rgba(0,0,0,.13)}
.sectionTitle{color:var(--cyan);font-size:.81rem;font-weight:800;letter-spacing:.09em;text-transform:uppercase;margin-bottom:9px}
.scene{display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap}
.scene strong{font-size:1.35rem}.muted{color:var(--muted)}small{font-size:.73rem;color:var(--muted)}
.visual{width:100%;height:auto;background:#1b304b;border-radius:12px;display:block}
.meters{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:12px}
.meter{border:1px solid #375775;background:#182c43;border-radius:10px;padding:10px}
.meter strong{display:block;font-size:1.12rem;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.meter span{display:block;color:#b8cbe0;font-size:.75rem}
.rail{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px;margin:12px 0 8px}
.rail button{font-size:.66rem;padding:9px 2px;min-width:0}
button,select,input{font:inherit}
button,select{border:1px solid #718ba4;background:#213a54;color:#f7fbff;border-radius:9px;padding:9px 12px;cursor:pointer}
button:hover,button:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid #5eead4;outline-offset:1px}
button:disabled{opacity:.48;cursor:not-allowed}
button.primary{background:#0f766e;border-color:#6ee7b7;font-weight:800}
button.current{background:#0d9488;border-color:#99f6e4}
.nav{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.nav input[type=range]{flex:1;min-width:100px;accent-color:#2dd4bf}
fieldset{border:1px solid #375775;border-radius:10px;padding:12px;margin:9px 0}
legend{color:#a7f3d0;font-weight:800}
.controls{display:grid;grid-template-columns:1fr auto;gap:9px;align-items:end}
.controls select{max-width:100%;min-width:0}
.reveal{background:#172e44;border:1px dashed #6b8aa8;border-radius:11px;padding:12px;margin-top:12px}
.reveal[hidden]{display:none}
table{width:100%;border-collapse:collapse;table-layout:fixed}th,td{border-bottom:1px solid #35516a;padding:7px 6px;text-align:left;font-size:.83rem;overflow-wrap:anywhere}
th:first-child,td:first-child{width:52%}th{color:#c3daec}
.status{color:#9ff9db;font-size:.9rem;font-weight:700}
.warning{color:#ffd7a8;background:#46311f;border-left:4px solid #fb923c;padding:8px 12px;border-radius:7px;margin:10px 0}
.challenge{margin-top:14px}.challengeRow{display:grid;grid-template-columns:1fr 1fr auto;gap:8px}
.challengeRow select{width:100%}.result{min-height:28px;color:#fcd34d;font-weight:800;margin-top:9px}
.footer{border-top:1px solid #35516a;margin-top:13px;padding-top:12px;font-size:.78rem;color:#c2d3e8}
kbd{border:1px solid #61758f;border-radius:4px;padding:1px 6px}
@media(max-width:930px){main{padding:12px}.layout{grid-template-columns:1fr}.challengeRow{grid-template-columns:1fr 1fr}.challengeRow button{grid-column:1/-1}.rail button{font-size:.58rem}html{font-size:16px}}
@media(max-width:540px){.controls{grid-template-columns:1fr}.meters{grid-template-columns:1fr}.rail{display:flex;overflow-x:auto}.rail button{flex:none;min-width:85px}.challengeRow{grid-template-columns:1fr}}
@media(prefers-reduced-motion:no-preference){#distanceFill{transition:width .42s ease,fill .35s ease}.card{transition:border-color .2s}}
</style></head>
<body><main>
<header><div><div class="subtitle">AXIA · D15 · HUMAN-AWARE SAFETY AMR</div>
<h1>EVIDENCE THEATER — 안전제어 관제실</h1>
<div class="subtitle">학생 예측 → 증거 공개 → 실패 게이트 판정 · 강의용 무인터넷 단일 HTML</div></div>
<span class="pill">RAW HOLD · L0 ONLY</span></header>
<div class="scope" id="riskBoundary">교육용 장면·공개 파생 수치(이전 G07 jrCIgoGl) · 실제 주행 영상 아님 · 합성 G09/P/N/U와 동일 세션 아님 · 이번 ROS/Gazebo/Goal = NOT_RUN · 인증 E-Stop 아님</div>
<div class="layout">
<section class="card" aria-label="개념적 로봇 장면">
<div class="sectionTitle">01 · 로봇·장애물 개념도</div>
<div class="scene"><strong id="stageLabel">CLEAR</strong><span class="pill" id="stageKind">PUBLIC DERIVED</span></div>
<svg class="visual" role="img" aria-label="장애물과 로봇의 거리 도식. 실제 궤적 또는 프레임이 아니다." viewBox="0 0 640 240">
<rect x="12" y="18" width="616" height="198" rx="14" fill="#233c59"/>
<path d="M 22 74 H 618 M 22 161 H 618" stroke="#526d8c" stroke-dasharray="9 13" stroke-width="2"/>
<path d="M 105 117 H 518" stroke="#94a3b8" stroke-width="4" stroke-dasharray="13 10"/>
<rect x="48" y="81" width="86" height="74" rx="18" fill="#0d9488" stroke="#99f6e4" stroke-width="3"/>
<circle cx="80" cy="105" r="10" fill="#99f6e4"/><circle cx="109" cy="105" r="10" fill="#99f6e4"/>
<text x="91" y="139" fill="white" font-size="17" text-anchor="middle" font-weight="bold">AMR</text>
<rect x="514" y="73" width="38" height="88" rx="8" fill="#f97316"/>
<text x="535" y="183" text-anchor="middle" fill="#fed7aa" font-size="15">장애물</text>
<text x="321" y="78" text-anchor="middle" fill="#e2e8f0" font-size="17" id="svgDistance">거리 수치 공개 전</text>
<rect x="157" y="101" width="325" height="23" rx="7" fill="#102238" stroke="#52758f"/>
<rect id="distanceFill" x="157" y="101" width="0" height="23" rx="6" fill="#5eead4"/>
<text x="320" y="143" text-anchor="middle" fill="#e2e8f0" font-size="14">전방 거리 수치의 상대적 비율만 표시</text>
</svg>
<small>화면 도형과 전환은 인과관계 설명용이며 실제 Gazebo 위치·속도·시간을 재생하지 않습니다.</small>
<div class="meters">
<div class="meter"><span>LiDAR 전방 거리 (보고 스냅샷)</span><strong id="distanceValue">예측 후 공개</strong></div>
<div class="meter"><span>최종 속도 명령 (odom 아님)</span><strong id="speedValue">예측 후 공개</strong></div>
</div>
<div class="footer">데이터 경계: Gazebo LiDAR → ROS /scan → Nav2·Collision Monitor / Nav2 제어 → Supervisor → CM → Base Guard → /cmd_vel / 독립 odom·Goal Action</div>
</section>
<section class="card" aria-label="예측하고 증거 확인하기">
<div class="sectionTitle">02 · 학생 선택과 증거 공개</div>
<p class="muted" id="stageDescription">7개 숫자 스냅샷을 차례로 읽습니다.</p>
<div class="rail" id="stageRail" aria-label="7개 교육용 증거 단계"></div>
<nav class="nav"><button id="previous" type="button">◀ 이전</button><input id="slide" type="range" min="0" max="6" step="1" value="0" aria-label="증거 번호"/><button id="next" type="button">다음 ▶</button><span id="idx">1 / 7</span></nav>
<fieldset><legend>학생 예측</legend>
<label for="predict" id="question">어떤 근거를 확인해야 할까요?</label>
<div class="controls"><select id="predict" aria-label="학생의 예측"><option value="">예측 선택</option></select>
<button class="primary" id="reveal" type="button" disabled>증거 공개</button></div>
</fieldset>
<p id="predictionFeedback" aria-live="polite" class="status">예측을 고르면 공개 버튼이 활성화됩니다.</p>
<div class="reveal" id="evidencePanel" hidden>
<h3>공개 파생 증거 / 실제 원본 rosbag 아님</h3><table aria-label="증거 필드"><thead><tr><th>기록 키</th><th>보고된 값</th></tr></thead><tbody id="evidenceFields"></tbody></table>
<p id="explanation" class="warning"></p>
</div>
</section>
</div>
<section class="card challenge" aria-label="5개 합성 수치 반례">
<div class="sectionTitle">03 · FAULT CHALLENGE · 실제 Fault Injector가 아닌 합성 숫자 퀴즈</div>
<p class="muted">원본 fixture를 바꾸지 않습니다. 다섯 개의 교육용 변조 사례 중 하나를 고르고, 먼저 실패할 <b>검증 게이트</b>를 찾아보세요. 시간순 첫 위반 시각은 추정하지 않습니다.</p>
<div class="challengeRow">
<select id="faultCase" aria-label="반례 선택"></select>
<select id="faultGuess" aria-label="실패 게이트 선택"></select>
<button class="primary" id="checkFault" type="button">실패 게이트 판정</button>
</div><div class="result" id="faultResult" aria-live="polite">반례를 선택하고 정답을 예측하세요.</div>
</section>
<section class="card" style="margin-top:14px" aria-label="검증 범위">
<div class="sectionTitle">04 · 증거가 말하는 것과 말하지 않는 것</div>
<p><strong>EDUCATION_NUMERIC_ACCEPTED</strong> = 이전 G07 공개 파생 숫자에 대한 오프라인 L0 계약. 원본: <strong>HOLD_RAW_REVIEW_AND_VISUAL_PENDING</strong>.</p>
<p class="muted">D13 P/N/U·D14 Risk Policy는 합성 교육 사례이며, S04는 별도 실제 Gazebo L2 세션입니다. 현재 G07 jrCIgoGl의 실제 사람 검출 E2E 증거가 아닙니다.</p>
<p class="muted"><strong>first_violation_timestamp</strong> = null · 이유: <strong>NOT_PRESENT_IN_PUBLIC_AGGREGATE_DERIVED_EVIDENCE</strong>. 실제 원본의 최초 타이밍 위반·안전 상태 전이를 재구성할 수 없습니다.</p>
<p class="muted">FORMAL_SAFETY_TIMING_ACCEPTANCE=NOT_CLAIMED · CERTIFIED_ESTOP=false · NO_NEW_ROS_GAZEBO · 소프트웨어 보호 정지 ≠ 인증 E-Stop</p>
<div class="footer">단축키: <kbd>←</kbd> / <kbd>→</kbd> = 장면 변경 (선택 컨트롤에 포커스하지 않았을 때). 네트워크 요청·외부 이미지·자동 재생·가상 타임스탬프가 없습니다.</div>
</section>
<script type="application/json" id="evidence">__PAYLOAD__</script>
<script>
(function () {
'use strict';
const payload=JSON.parse(document.getElementById('evidence').textContent);
const $=id=>document.getElementById(id);
const names=['CLEAR','SLOW','STOP','CANCEL','ODOM_DWELL','SAFETY_TTL','PNU_AND_SCOPE'];
const config=[
{q:'전방 장애물 거리 약 2m. 무엇을 확인할까요?',options:['최종 정지 판정','CLEAR 거리와 이동거리의 종류 구분','인증 E-Stop 상태'],answer:1,reason:'전방거리 2.02m는 장애물까지의 거리이고 odom 누계와 다릅니다.'},
{q:'장애물이 약 0.66m로 접근했습니다. 어떤 명령을 비교할까요?',options:['Supervisor와 최종 Guard 명령','카메라의 실제 사람 ID','Goal SUCCEEDED'],answer:0,reason:'SLOW의 앞단 명령과 최종 명령 크기가 다르며 실제 물리 속도는 별도입니다.'},
{q:'STOP에 도달했다면 어떤 기록이 필요할까요?',options:['/cmd_vel=0 명령만','Goal 성공만','최종 명령 0과 독립 odom 확인'],answer:2,reason:'STOP 명령 자체는 실제 정지 유지시간의 증거가 아닙니다.'},
{q:'Goal 취소를 증명하려면 무엇을 확인할까요?',options:['단순 Cancel ACK','동일 Goal UUID의 최종 CANCELED(5)','새 Goal을 전송'],answer:1,reason:'동일 UUID의 Action terminal CANCELED 상태를 확인해야 합니다.'},
{q:'정지 유지 근거는 어떤 데이터인가요?',options:['odom ZERO dwell 1초 이상','거리 이미지 하나','Nav2 cancel 요청만'],answer:0,reason:'이전 실행의 독립 odom 정지 유지 1.029초가 보고되었습니다.'},
{q:'TTL 검증에서 가장 중요한 원칙은?',options:['Scan 한 값만 PASS면 전체 PASS','모든 기준을 300ms로 통일','5개 채널을 각자의 기준으로 비교'],answer:2,reason:'발행·수신 간격과 Guard age는 별도 경계이며 시간순 첫 위반은 알 수 없습니다.'},
{q:'D13 P/N/U와 이 G07의 관계를 어떻게 설명할까요?',options:['G07 실제 사람 검출 성공','별도의 합성 학습, 원본 HOLD 유지','인증된 E-Stop 동작'],answer:1,reason:'D13/D14 합성, S04 별도 실행, G07 원본 HOLD를 유지해야 합니다.'}
];
let active=0,revealed=false;
function addText(node,text){node.textContent=String(text);}
function staticRender(){
 const stage=payload.stages[active], cfg=config[active];
 revealed=false;
 $('slide').value=String(active);addText($('idx'),(active+1)+' / 7');
 addText($('stageLabel'),stage.id);addText($('stageKind'),stage.kind);
 addText($('stageDescription'),stage.note);addText($('question'),cfg.q);
 $('evidencePanel').hidden=true;$('reveal').disabled=true;
 addText($('predictionFeedback'),'먼저 예측을 선택하세요. 결과값은 아직 숨겨져 있습니다.');
 addText($('distanceValue'),'예측 후 공개');addText($('speedValue'),'예측 후 공개');
 addText($('svgDistance'),'거리 수치 공개 전');
 $('distanceFill').setAttribute('width','0');
 const select=$('predict');select.textContent='';
 const empty=document.createElement('option');empty.value='';empty.textContent='예측 선택';select.appendChild(empty);
 cfg.options.forEach((label,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=label;select.appendChild(o);});
 const rail=$('stageRail');rail.textContent='';
 names.forEach((name,i)=>{const btn=document.createElement('button');btn.type='button';btn.textContent=name;btn.className=i===active?'current':'';btn.setAttribute('aria-current',i===active?'step':'false');btn.addEventListener('click',()=>go(i));rail.appendChild(btn);});
 $('previous').disabled=active===0;$('next').disabled=active===6;
}
function go(n){active=Math.min(6,Math.max(0,n));staticRender();}
function reveal(){
 if(revealed || $('predict').value==='')return;
 const cfg=config[active],choice=Number($('predict').value);
 revealed=true;$('evidencePanel').hidden=false;
 addText($('predictionFeedback'),choice===cfg.answer?'예측이 핵심 검증 관점과 일치합니다.':'다른 선택이었습니다. 실제 근거를 비교해 보세요.');
 addText($('explanation'),cfg.reason);
 const stage=payload.stages[active],body=$('evidenceFields');body.textContent='';
 Object.entries(stage.fields).forEach(([key,value])=>{
  const tr=document.createElement('tr'),a=document.createElement('td'),b=document.createElement('td');
  addText(a,key);addText(b,typeof value==='boolean'?String(value):value===null?'null':String(value));
  tr.appendChild(a);tr.appendChild(b);body.appendChild(tr);
 });
 if(active===5){
   Object.entries(payload.review.threshold_ms).forEach(([key,value])=>{
    const tr=document.createElement('tr'),a=document.createElement('td'),b=document.createElement('td');
    addText(a,key+' / 기준');addText(b,String(value)+' ms');tr.appendChild(a);tr.appendChild(b);body.appendChild(tr);
   });
 }
 const dist={0:payload.data.clear_front_m,1:payload.data.slow_front_m,2:payload.data.stop_front_m}[active];
 if(typeof dist==='number'){
   addText($('distanceValue'),dist.toFixed(3)+' m');
   addText($('svgDistance'),dist.toFixed(3)+' m (파생값)');
   $('distanceFill').setAttribute('width',String(Math.min(325,Math.max(0,325*dist/payload.data.clear_front_m))));
   $('distanceFill').setAttribute('fill',active===0?'#5eead4':active===1?'#fdba74':'#fda4af');
 }else{
   addText($('distanceValue'),'새 거리 측정 없음');
   addText($('svgDistance'),'이 단계는 새 거리 측정 없음');
 }
 let speed=null;
 if(active===1)speed=payload.data.slow_final_vx_mps;
 if(active===2)speed=payload.data.stop_final_vx_mps;
 addText($('speedValue'),speed===null?'별도 새 명령값 없음':speed.toFixed(6)+' m/s');
 $('reveal').disabled=true;
}
$('predict').addEventListener('change',()=>{$('reveal').disabled=$('predict').value==='';});
$('reveal').addEventListener('click',reveal);
$('previous').addEventListener('click',()=>go(active-1));$('next').addEventListener('click',()=>go(active+1));
$('slide').addEventListener('input',e=>go(Number(e.target.value)));
document.addEventListener('keydown',e=>{
 const t=e.target.tagName;
 if(['INPUT','SELECT','TEXTAREA','BUTTON'].includes(t) || e.altKey || e.ctrlKey || e.metaKey)return;
 if(e.key==='ArrowRight'){go(active+1);e.preventDefault();}
 if(e.key==='ArrowLeft'){go(active-1);e.preventDefault();}
});
const gates=[...new Set(payload.cases.map(x=>x.expected_failed_gate))];
function addOption(el,label,value){const o=document.createElement('option');o.value=value;o.textContent=label;el.appendChild(o);}
payload.cases.forEach((c,i)=>addOption($('faultCase'),c.case,String(i)));
addOption($('faultGuess'),'어느 검증 게이트가 실패하나요?','');
gates.forEach(g=>addOption($('faultGuess'),g,g));
function resetChallenge(){addText($('faultResult'),'학생이 실패 게이트를 선택한 후 판정하세요. 합성 수치 변조 / 원본 변경 없음.');$('faultGuess').value='';}
$('faultCase').addEventListener('change',resetChallenge);
$('checkFault').addEventListener('click',()=>{
 const guess=$('faultGuess').value,caseData=payload.cases[Number($('faultCase').value)];
 if(!guess){addText($('faultResult'),'실패 게이트를 먼저 선택하세요.');return;}
 const correct=guess===caseData.expected_failed_gate;
 addText($('faultResult'),(correct?'정답! ':'다시 확인: ')+caseData.case+
  ' / 기대 실패 게이트 = '+caseData.expected_failed_gate+
  ' / detected = '+String(caseData.detected)+' / NOT_ACCEPTED = '+String(caseData.not_accepted)+
  ' / 합성 데이터이며 실제 안전 상태 전이 시각은 알 수 없습니다.');
});
staticRender();resetChallenge();
})();
</script>
</main></body></html>'''
    return page.replace("__PAYLOAD__",payload)
