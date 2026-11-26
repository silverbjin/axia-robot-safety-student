'use strict';
// AXIA DAY3 MASTER-FIRST / actual MVP source provenance locked in public student repo.
const pptxgen=require('pptxgenjs');
const pptx=new pptxgen();pptx.layout='LAYOUT_WIDE';
pptx.author='AXIA AI Native Robotics Education';pptx.subject='Complete G07 MVP development integration acceptance debugging workbook';
pptx.title='AXIA DAY3 Master-First Complete MVP Debugging Workbook';pptx.lang='ko-KR';
pptx.theme={headFontFace:'Noto Sans CJK KR',bodyFontFace:'Noto Sans CJK KR',lang:'ko-KR'};
const S=pptx.ShapeType,W=13.333,H=7.5;
const K={navy:'11283F',navy2:'0A1B2C',panel:'1B3852',paper:'F7FAFC',white:'FFFFFF',ink:'1E3548',muted:'62788D',line:'DAE5ED',teal:'008F96',cyan:'66D7D8',green:'159B78',red:'C94255',amber:'C88222',blue:'367DB8',blueLight:'E7F4FA',tealLight:'E4F5F3',redLight:'FBECEF',amberLight:'FFF4DF',light:'EAF0F5',gray:'8096A8'};
const FF='Noto Sans CJK KR',FM='Noto Sans Mono CJK KR';
function box(sl,x,y,w,h,fill=K.white,line=null,rad=.11,opacity=0){sl.addShape(rad?S.roundRect:S.rect,{x,y,w,h,rectRadius:rad,radius:rad,fill:{color:fill,transparency:opacity},line:line?{color:line,width:.7}:{color:fill,transparency:100}})}
function t(sl,st,x,y,w,h,opts={}){sl.addText(String(st),{x,y,w,h,fontFace:opts.mono?FM:FF,fontSize:opts.size||14,color:opts.color||K.ink,bold:opts.bold||false,margin:0,fit:'shrink',valign:opts.valign||'mid',align:opts.align||'left',breakLine:false,...opts})}
function line(sl,x,y,x2,y2,c=K.line,width=1){sl.addShape(S.line,{x,y,w:x2-x,h:y2-y,line:{color:c,width}})}
function arrow(sl,x,y,x2,y2,c=K.teal,width=2){sl.addShape(S.line,{x,y,w:x2-x,h:y2-y,line:{color:c,width,endArrowType:'triangle'}})}
function tag(sl,label,x,y,w,fill=K.teal,color=K.white){box(sl,x,y,w,.32,fill,null,.08);t(sl,label,x+.08,y+.03,w-.16,.22,{size:9.4,color,bold:true,align:'center'})}
function notes(sl,arr){sl.addNotes(arr.join('\n'))}
function frame(section,title,sub='',dark=false){let sl=pptx.addSlide();sl.background={color:dark?K.navy2:K.paper};box(sl,0,0,W,H,dark?K.navy2:K.paper,null,0);
 t(sl,`AXIA / DAY 03    ${section}`,0.62,.29,10.8,.24,{size:10,color:dark?K.cyan:K.teal,bold:true,charSpacing:1});
 t(sl,title,.62,.75,12.15,.62,{size:25.5,color:dark?K.white:K.ink,bold:true});if(sub)t(sl,sub,.65,1.42,12.0,.36,{size:12.4,color:dark?'B9CBD9':K.muted});
 return sl}
function foot(sl){const n=pptx._slides.length;line(sl,.61,7.08,12.7,7.08,sl.background?.color===K.navy2?'3B5369':K.line,.65);t(sl,'AXIA G07 · 완성 MVP 기반 AI NATIVE DEBUGGING · 교육용 SIM ONLY',.63,7.14,10.5,.18,{size:8.7,color:sl.background?.color===K.navy2?'98B7C7':K.muted});t(sl,`${String(n).padStart(2,'0')} / 52`,11.72,7.135,.94,.18,{size:8.9,color:sl.background?.color===K.navy2?K.white:K.ink,bold:true,align:'right'})}
function card(sl,x,y,w,h,top,bottom,color=K.teal,fill=K.white){box(sl,x,y,w,h,fill,K.line,.13);box(sl,x,y,.06,h,color,null,0);t(sl,top,x+.20,y+.16,w-.38,.29,{size:13.4,color:K.ink,bold:true});t(sl,bottom,x+.20,y+.56,w-.4,h-.68,{size:12.1,color:K.muted,valign:'top'})}
function lines(sl,vals,x,y,w,spacing=.43,color=K.ink,size=13){vals.forEach((v,i)=>{box(sl,x,y+i*spacing+.12,.07,.07,K.teal,null,.04);t(sl,v,x+.20,y+i*spacing,w-.22,.34,{size,color})})}
function term(sl,x,y,w,h,ls,title='WSL2 terminal · expected unless specified'){box(sl,x,y,w,h,'0C2135','284861',.14);box(sl,x,y,w,.35,'1D3C55',null,.10);t(sl,title,x+.18,y+.07,w-.36,.19,{size:9.3,color:'9FE8E0',bold:true});let yy=y+.54;ls.forEach(row=>{let o=typeof row==='string'?{v:row}:row;let col=o.c||((o.v||'').includes('PASS')?K.cyan:(o.v||'').includes('FAIL')?'F6A2A9':'DCECF3');t(sl,o.v,x+.2,yy,w-.4,.30,{size:o.size||12,color:col,mono:true});yy+=.39;})}
function flow(sl,steps,y=2.44,x=.67,w=12){let g=.26,ww=(w-(steps.length-1)*g)/steps.length;steps.forEach((st,i)=>{let xx=x+i*(ww+g);box(sl,xx,y,ww,1.1,K.white,K.line,.13);tag(sl,String(i+1).padStart(2,'0'),xx+.15,y+.13,.43,K.navy);t(sl,st[0],xx+.12,y+.49,ww-.24,.29,{size:12.0,bold:true,align:'center'});t(sl,st[1],xx+.10,y+.81,ww-.20,.18,{size:9.7,color:K.muted,align:'center'});if(i<steps.length-1)arrow(sl,xx+ww+.045,y+.55,xx+ww+g-.05,y+.55,K.teal,1.6)})}
function info(sl,label,msg,x,y,w,h,fill=K.blueLight,col=K.teal){box(sl,x,y,w,h,fill,null,.10);t(sl,label,x+.14,y+.10,w-.26,.24,{size:10,color:col,bold:true});t(sl,msg,x+.14,y+.38,w-.28,h-.48,{size:12.3,color:K.ink,valign:'top'})}
const SRC='special_lecture/day02_mvp_sources/';
const A='accepted/runtime/';
const sha='96be43164fab3f15025edd59279bcfd50b6232cd';
const github='silverbjin/axia-robot-safety-student';
const units=[
{id:'U00',phase:'FOUNDATION',name:'실행 SHA·증거 출처 고정',file:'DUAL_SOURCE_MANIFEST.json',wrong:'성공 로그와 실패 로그를 한 번의 실험처럼 비교',right:'Run ID·소스 SHA·timebase를 먼저 분리해 출처를 고정',steps:['배포 SHA 확인','2개 원본 Run 분리','L0~L3 표기'],why:'근거의 출처가 다르면 원인과 인수 판단이 무너집니다.',expected:'accepted 2/2 PASS · failed 0/2 FAIL (과거 별도 Run)',review:'두 실행의 수치가 섞이지 않았나요?',prompt:'실제 학생 공개 MVP를 기준으로 원본 출처를 검토해 주세요.\n1) 배포 HEAD·각 runtime 소스 SHA·Git Tree SHA를 확인하세요.\n2) Run ID별 L0/L1/L2/L3와 수행 날짜를 분리하세요.\n3) 로그의 시각 기준·단위·증거 파일을 표로 정리하세요.\n4) 증거가 없으면 NOT_RUN, 충돌하면 INCONCLUSIVE로 표시하세요.'},
{id:'U01',phase:'FOUNDATION',name:'코드와 노드 책임 추적',file:'axia_fault_injector/.../fault_injector_node.py',wrong:'패키지명이 비슷하니 모든 안전 판단을 한 노드가 담당',right:'package.xml·node·topic·서비스·Callback을 파일과 연결',steps:['package.xml','Publisher/Subscriber','Fault relay'],why:'문제가 일어난 경계와 수정해야 할 코드 위치를 분리합니다.',expected:'/scan→Fault relay→/safety/scan, fault 기본 비활성',review:'출력 토픽 이름을 실제 SCAN_OUT 정의로 확인했나요?',prompt:'공개 MVP 네 패키지의 책임과 실제 I/O 계약을 추적해 주세요.\n1) package.xml과 실행 노드를 찾으세요.\n2) Publisher·Subscriber·Timer·Service별 메시지 타입을 쓰세요.\n3) 각 연결을 코드 경로/함수와 1:1로 제시하세요.\n4) 확인되지 않은 Nav2 cmd 체인은 UNKNOWN으로 남기세요.'},
{id:'U02',phase:'DEVELOPMENT',name:'최초 HEALTH 상태 전이',file:'tools/p2_g07_health_first_boundary.py',wrong:'마지막 TIMEOUT 메시지가 최초 장애 원인입니다',right:'first_state_transition과 first_readiness_blockers를 우선 조회',steps:['snapshot 획득','blocker 기록','첫 transition'],why:'최종 예외는 최초 안전 상태 변화 이후에 발생할 수 있습니다.',expected:'first_state_transition: from / to / at_host_monotonic',review:'state 변화와 최초 TTL 위반을 동일 사건으로 취급했나요?',prompt:'HealthFirstBoundary.record/result를 읽기 전용으로 분석하세요.\n1) first_sample, first_transition, last_sample의 계약을 설명하세요.\n2) 첫 blocker와 안전 상태 전이의 시점을 별도 필드로 쓰세요.\n3) 마지막 timeout과 최초 원인을 혼동하지 마세요.\n4) 값이 없으면 UNKNOWN으로 표시하고 필요한 원본을 요청하세요.'},
{id:'U03',phase:'DEVELOPMENT',name:'반례부터 작성하는 RED',file:'tools/test_g07_health_first_boundary.py',wrong:'소스가 이상해 보이니 즉시 조건문을 바꿉니다',right:'실패하는 최소 입력을 먼저 만들고 기대 결과를 고정',steps:['입출력 계약','최소 반례','RED stdout'],why:'테스트가 요구사항 때문에 실패해야 수정의 필요성이 증명됩니다.',expected:'교육용 개인 복제본의 타깃 회귀 테스트가 의도된 이유로 FAIL',review:'환경 오류나 import 실패를 RED 성공으로 착각했나요?',prompt:'원본 안전 노드를 수정하지 않고 교육용 진단 모듈 복제본을 검토하세요.\n1) 잘못된 동작의 최소 반례를 설계하세요.\n2) 원본 구현의 정상 계약과 기대 출력을 먼저 고정하세요.\n3) unittest RED 명령·stdout/stderr·exit code를 기록하세요.\n4) 원본 구현은 기준선으로 보존하고 수정 코드는 아직 쓰지 마세요.'},
{id:'U04',phase:'DEVELOPMENT',name:'최소 GREEN 구현',file:'tools/p2_g07_health_first_boundary.py',wrong:'재현 실패를 없애려고 안전 TTL을 늘립니다',right:'복제된 진단 로직의 결함만 수정하고 같은 테스트를 재실행',steps:['RED baseline','국소 수정','GREEN 검증'],why:'시연과 안전제어의 불변 조건을 유지하면서 정확한 수정만 확보합니다.',expected:'동일 반례 GREEN PASS + 관련 회귀 PASS (실습 실행 후 기록)',review:'테스트 기대값이나 TTL을 바꿔 통과시켰나요?',prompt:'앞에서 RED를 확인한 학생 개인 복제본에 한해 GREEN을 진행하세요.\n1) 가장 작은 함수 수정 diff를 제시하세요.\n2) 안전 정책·Goal·원본 runtime에는 손대지 마세요.\n3) 동일 unittest와 관련 회귀를 다시 실행하세요.\n4) 실제 stdout/stderr/exit code를 인용하고 남은 미검증을 쓰세요.'},
{id:'U05',phase:'DEVELOPMENT',name:'REFACTOR·REVIEW·COMMIT',file:'test_g07_health_first_boundary.py + 개인 브랜치',wrong:'테스트 하나가 통과했으니 곧바로 main 병합',right:'부작용 점검·변경 파일 확인·학생 개인 Commit까지',steps:['diff 확인','리뷰 질문','개인 COMMIT'],why:'변경이 안전 경계에 영향을 주지 않았다는 검토와 추적성을 남깁니다.',expected:'커밋 SHA + 변경 파일 + 실행 로그 + 불변 안전 정책',review:'원본 accepted/runtime 소스가 변경되었나요?',prompt:'GREEN 이후의 REFACTOR→REVIEW→COMMIT 체크리스트를 작성하세요.\n1) 중복 제거가 있는지 살피되 동작은 바꾸지 마세요.\n2) 변경된 파일과 무변경 안전 정책을 diff로 입증하세요.\n3) 커밋 전 테스트 결과·명령·exit code를 기록하세요.\n4) 학생 개인 브랜치만 커밋하고 main 병합은 요청하지 마세요.'},
{id:'U06',phase:'INTEGRATION',name:'/scan과 /safety/scan의 연결',file:'axia_fault_injector/fault_policy.py',wrong:'/scan과 /safety/scan은 같은 토픽입니다',right:'원본 LaserScan과 Fault Relay의 토픽을 개별 검증',steps:['SCAN_IN','relay 처리','SCAN_OUT'],why:'센서 발행 정상 여부와 안전 소비자 수신은 별도 질문입니다.',expected:'SCAN_IN=/scan · SCAN_OUT=/safety/scan (코드값 확인)',review:'연결 방향과 메시지 타입/Publisher 수를 검증했나요?',prompt:'현재 SHA에서 LaserScan 전달 경로를 그려 주세요.\n1) fault_policy의 SCAN_IN/SCAN_OUT 상수를 확인하세요.\n2) Injector Subscriber·Publisher의 타입과 QoS를 설명하세요.\n3) Bridge/CM/Supervisor 연결은 launch/config로 확인하세요.\n4) 추측된 실제 배선을 사실처럼 그리지 말고 UNKNOWN을 표기하세요.'},
{id:'U07',phase:'INTEGRATION',name:'Source·RMW·Callback 간격',file:'tools/p2_g07_scan_rmw_first_pair.py',wrong:'Observer 424ms는 DDS가 424ms 느리다는 뜻',right:'source_gap·received_gap·observer_gap은 서로 다른 지표',steps:['source gap','RMW receive gap','Observer gap'],why:'같은 timebase와 publication sequence가 없으면 원인을 판정할 수 없습니다.',expected:'교육용 테스트: source 99ms, received 100ms, observer 424.373ms',review:'실행 시각/시뮬레이션 Header/Host 시각을 섞었나요?',prompt:'first_scan_rmw_pair와 실제 테스트를 기준으로 지표를 구분하세요.\n1) source/receive/observer 간격과 단위를 따로 계산하세요.\n2) 동일 publication seq 및 유효한 timebase를 확인하세요.\n3) Observer 지연만으로 DDS 원인을 단정하지 마세요.\n4) pair가 모자라면 UNVERIFIED_HOLD를 유지하세요.'},
{id:'U08',phase:'INTEGRATION',name:'첫 TTL 위반과 첫 안전 전이',file:'tools/p2_g07_ci_moving_goal_oracle.py',wrong:'STOP 이후의 예외를 첫 타이밍 위반으로 기록',right:'first_timing_violation / first_safety_transition 독립 보고',steps:['delivery ticks','최초 limit breach','상태 transition'],why:'각 사건이 별개 계층에서 기록되며, 발생 순서가 다를 수 있습니다.',expected:'first_delivery_breach / first_pre_latch_delivery_timing 진단 출력',review:'이후 에러를 첫 위반보다 앞선 사건으로 바꿔 적었나요?',prompt:'실제 oracle 및 guard/supervisor 증거에서 사건을 시간순으로 정리하세요.\n1) first_timing_violation과 first_safety_transition을 분리하세요.\n2) Scan300, CM120, Guard150 등 계층별 기준을 적으세요.\n3) 같은 Run/timebase의 값만 계산하세요.\n4) 첫 위반을 놓치면 오류로 표시하고 최종 예외는 별도 기재하세요.'},
{id:'U09',phase:'INTEGRATION',name:'원인 가설과 반증 설계',file:'tools/test_g07_scan_rmw_first_pair.py',wrong:'Publisher가 10Hz이므로 나머지 통신은 모두 정상',right:'source/RMW/Executor 세 가지 후보의 반증 관측 설계',steps:['가설 H1~H3','필요한 관측','반증 판정'],why:'AI가 내놓은 원인 후보를 테스트 가능한 질문으로 바꿉니다.',expected:'H1 source stall / H2 RMW / H3 callback 후보별 증거 매트릭스',review:'근거 없는 확정 원인이나 TTL 완화를 제안했나요?',prompt:'제공된 같은 Run의 로그와 first_pair 결과로 원인 가설을 세우세요.\n1) source stall/RMW 경계/Executor 지연 후보를 제시하세요.\n2) 각 후보를 반박할 수 있는 관측 결과를 작성하세요.\n3) 필요한 읽기전용 최소 계측만 제안하세요.\n4) 입증 불가한 근본 원인은 UNDETERMINED로 유지하세요.'},
{id:'U10',phase:'INTEGRATION',name:'CM→Guard 안전 경계 교차 검토',file:'tools/p2_g07_ci_moving_goal_oracle.py',wrong:'CM Observer가 정상이라 Guard TTL도 통과했습니다',right:'Observer·Guard 내부 receipt·latch를 별도 확인',steps:['CM observer','Guard receipt age','latch / odom'],why:'관측자가 정상이어도 최종 안전 게이트가 오래된 입력을 받을 수 있습니다.',expected:'GUARD_RECEIPT_LAG_CANDIDATE / 증거 미비시 HOLD',review:'CM 120ms와 Guard 150ms를 각각 검사했나요?',prompt:'CM과 Guard의 전송·수신 경계를 분리 검증하세요.\n1) CM publisher/observer/Guard 내부 수신의 증거를 나누세요.\n2) 각 TTL 기준과 실제 측정 timebase를 표시하세요.\n3) 최초 latch와 최초 위반을 교차 비교하세요.\n4) CM 한 곳의 PASS만으로 전체 통합 인수를 주장하지 마세요.'},
{id:'U11',phase:'ACCEPTANCE',name:'UUID·Nav/Loc ACK·CM exit',file:'tools/p2_g07_ordered_shutdown.py',wrong:'Navigation ACK만 있으면 Collision Monitor도 정상 종료',right:'Goal UUID terminal, 두 ACK, CM exit0을 독립 게이트로 확인',steps:['Goal UUID','Nav→Loc ACK','CM exit0'],why:'종료 신호와 실제 프로세스 종료 증거는 다릅니다.',expected:'navigation_ack ≠ cm_clean_process_exit_verified',review:'Goal UUID가 동일하며 shutdown 원본 로그가 있나요?',prompt:'Goal 취소와 종료 시퀀스의 인수 근거를 재구성하세요.\n1) 정확한 Goal UUID와 terminal status를 확인하세요.\n2) Navigation ACK와 Localization ACK를 각각 기록하세요.\n3) CM exit0은 별도 프로세스 로그로 판정하세요.\n4) ACK 누락 또는 exit 미확인 시 scoped HOLD/NOT_RUN을 표시하세요.'},
{id:'U12',phase:'ACCEPTANCE',name:'L0·L1·L2·L3의 증명 범위',file:'DUAL_SOURCE_MANIFEST.json + 공개 CI Run',wrong:'두 패키지 빌드가 성공하면 Owner L3도 PASS',right:'원본 SHA별 실행 환경·엄격 게이트·미검증을 분리',steps:['L0 source','L1 package','L2 Gazebo','L3 Owner'],why:'성공한 테스트의 조건을 넘어 안전성을 주장하지 않기 위해서입니다.',expected:'과거 L2 accepted 2/2 vs failed 0/2 · 신규 학생 수정 L2 NOT_RUN',review:'과거 PASS를 새 학생 SHA의 결과처럼 표시했나요?',prompt:'Evidence Manifest를 코드 SHA·Run ID별로 작성하세요.\n1) L0/L1/L2/L3에서 실제 수행된 명령·환경을 적으세요.\n2) 성공본과 실패본의 역사적 Run을 분리하세요.\n3) 신규 학생 수정 SHA에 없는 실물 시연은 NOT_RUN으로 쓰세요.\n4) 미검증 계층을 밝히고 PASS_SCOPED/HOLD만 정직하게 판정하세요.'},
{id:'U13',phase:'ACCEPTANCE',name:'한 장의 Incident & Acceptance Card',file:'학생 증거 Manifest + 개인 Commit',wrong:'AI가 최종적으로 성공이라고 했습니다',right:'증거·가설·수정·테스트·인수 범위를 직접 발표',steps:['Incident Card','Evidence Manifest','90초 브리핑'],why:'AI Native 개발자의 결과물은 텍스트가 아니라 재현 가능한 판단입니다.',expected:'원인 후보+RED/GREEN 증거+L0~L3 판정+미검증',review:'주장마다 출처 SHA/Run/실행 명령이 연결되나요?',prompt:'모든 결과를 한 장의 Incident & Acceptance Card로 조립하세요.\n1) 원본 SHA·Run ID·첫 위반·첫 전이를 표시하세요.\n2) RED/GREEN 명령·실제 stdout·exit code를 연결하세요.\n3) 테스트 수준과 PASS_SCOPED/HOLD/NOT_RUN을 구분하세요.\n4) 새로운 인수 증거가 없는 결과를 PASS로 쓰지 마세요.\n5) 90초 발표 원고를 작성하고 독립 반례 리뷰를 수행하세요.'}
];
let unitCount=0;
function unitResult(u){let sl=frame(`${u.phase} · ${u.id} / A`,`${u.id} · ${u.name}`,'RESULT FIRST  ·  실제 MVP 소스에서 관측되는 데이터와 흔한 오판을 먼저 비교합니다.');
 tag(sl,'기존 코드',.68,1.96,1.05,K.navy);t(sl,`${A}${u.file}` ,1.88,1.97,10.55,.34,{size:10.8,color:K.muted,mono:true});
 box(sl,.69,2.52,5.84,1.56,K.redLight,null,.13);t(sl,'잘못된 접근',.92,2.75,5.25,.28,{size:15,color:K.red,bold:true});t(sl,u.wrong,.92,3.12,5.13,.70,{size:14,color:K.ink,valign:'top'});
 box(sl,6.77,2.52,5.84,1.56,K.tealLight,null,.13);t(sl,'검증 가능한 접근',7.0,2.75,5.25,.28,{size:15,color:K.teal,bold:true});t(sl,u.right,7.0,3.12,5.1,.70,{size:14,color:K.ink,valign:'top'});
 flow(sl,u.steps.map((x,i)=>[x,['INPUT','PROCESS','OUTPUT'][i]||'EVIDENCE']),4.38,.82,11.7);
 info(sl,'예상 또는 기존 이력의 출력 (SAMPLE / HISTORICAL)',u.expected,.84,5.77,11.66,.83,K.blueLight,K.blue);
 notes(sl,[`[${u.id} RESULT FIRST]`, `원본 참조 ${u.file}`,`오개념: ${u.wrong}`,`적절한 판단: ${u.right}`,`블록: ${u.steps.join(' → ')}`,`강조: ${u.why}`,`검수: ${u.review}`,`기존 원본 MVP를 수정하지 않습니다. 결과는 같은 Run/SHA에서만 계산합니다.`]);foot(sl);unitCount++}
function unitPractice(u){let sl=frame(`${u.phase} · ${u.id} / B`,`${u.id} · AI에게 무엇을, 왜 요청할까요?`,'PRACTICE  ·  복사 가능한 프롬프트 전체와 설계 이유·예상 출력·검토 질문');
 box(sl,.70,1.94,7.45,4.87,K.navy2,null,.14);t(sl,'COMPLETE UNIT PROMPT',.99,2.16,6.0,.29,{size:12.2,color:K.cyan,bold:true});line(sl,.97,2.58,7.84,2.58,'365770',.8);
 let p=u.prompt.split('\n');let y=2.77;p.forEach((x,i)=>{t(sl,x,.98,y,6.9,.57,{size:x.length>58?11.4:12.4,color:i===0?'A7F1E8':'E3EDF7',valign:'top'});y+=.61});
 box(sl,8.39,1.94,4.25,1.22,K.white,K.line,.13);t(sl,'WHY · 왜 이 문장이 필요할까요?',8.60,2.13,3.84,.28,{size:12,color:K.teal,bold:true});t(sl,u.why,8.60,2.48,3.80,.47,{size:12,color:K.ink,valign:'top'});
 box(sl,8.39,3.33,4.25,1.47,K.white,K.line,.13);t(sl,'EXPECTED · 무엇이 나올까요?',8.60,3.52,3.84,.28,{size:12,color:K.blue,bold:true});t(sl,u.expected,8.60,3.90,3.79,.78,{size:11.7,color:K.ink,valign:'top'});
 box(sl,8.39,4.99,4.25,1.82,K.white,K.line,.13);t(sl,'REVIEW · 응답에서 검토할 질문',8.60,5.17,3.84,.28,{size:12,color:K.amber,bold:true});t(sl,u.review,8.60,5.55,3.78,.80,{size:12.1,color:K.ink,valign:'top'});t(sl,'확인 불가 = UNKNOWN/INCONCLUSIVE',8.60,6.39,3.83,.22,{size:9.5,color:K.red,bold:true});
 notes(sl,[`[${u.id} PRACTICE]`,`프롬프트 전문:`,u.prompt,`설계 이유: ${u.why}`,`예상 응답: ${u.expected}`,`학생 검수: ${u.review}`,`실행 전: 복제본/원본 읽기전용 범위를 확인합니다.`, `출력·수치를 임의로 생성하거나 PASS를 추정하지 않습니다.`]);foot(sl);unitCount++}

// Slide 1: Cover
{let sl=pptx.addSlide();sl.background={color:K.navy2};box(sl,0,0,W,H,K.navy2,null,0);for(let i=0;i<10;i++){line(sl,8.4+i*.4,0,8.4+i*.4,7.5,'1E3D57',.6);line(sl,8.3,1.0+i*.5,13.2,1.0+i*.5,'1E3D57',.6)}
 tag(sl,'G07 · REAL MVP · MASTER FIRST',.72,.67,3.14,K.teal);t(sl,'AI Native 개발의 마지막 단계',.74,1.61,10.8,.58,{size:25,color:K.cyan,bold:true});t(sl,'개발 · 통합 · 인수',.75,2.34,11.72,1.07,{size:43,color:K.white,bold:true});t(sl,'완성된 로봇 MVP의 오류를 프롬프트로 진단하고\n검증 가능한 증거로 해결하는 180분 실습 워크북',.79,3.78,10.8,1.21,{size:20,color:'C9E2EC',valign:'top'});box(sl,.78,6.12,11.75,.54,K.panel,null,.10);t(sl,'ROS 2 Jazzy  /  Gazebo Harmonic  /  TurtleBot3 Waffle  /  Nav2  /  Python L0',1.02,6.25,11.0,.22,{size:12,color:'BDEBE9'});notes(sl,['기존 MVP의 코드를 새로 만들지 않고, 실제 코드·테스트·오류 기록에서 AI Native 프롬프트 설계를 학습합니다.','실제 Gazebo 인수를 새로 수행하지 않았음을 설명합니다.']);foot(sl)}
// Slide 2: mission outcome
{let sl=frame('ORIENTATION','오늘 배울 것은 로봇 코딩이 아니라 오류 해결 능력입니다','완성된 결과부터 시작해서 개발·통합·인수의 프롬프트를 해체해 봅니다.');flow(sl,[['DEV','첫 실패 재현'],['INTEGRATION','노드 경계 검증'],['ACCEPTANCE','증거와 판정']],2.23,.73,11.88);card(sl,.71,4.01,3.73,1.89,'학생 성취 ①','진단 코드 RED→GREEN과 개인 커밋',K.green);card(sl,4.79,4.01,3.73,1.89,'학생 성취 ②','source/RMW/Callback 가설·반증표',K.blue);card(sl,8.86,4.01,3.73,1.89,'학생 성취 ③','한 장의 Incident & Acceptance Card',K.amber);notes(sl,['3일 강의 연결: DAY1 SPEC → DAY2 CODE → DAY3 EVIDENCE/ACCEPTANCE','학생은 개발 오류를 실제 안전 노드에 주입하지 않고 독립 복제된 진단 모듈만 사용합니다.']);foot(sl)}
// Slide 3: verified results
{let sl=frame('PROVENANCE','실제 검증 이력: 성공본 2/2와 실패본 0/2는 다른 실행입니다','과거 공개 CI의 결과를 참조할 뿐, 이번 PPTX 제작 과정의 새로운 Gazebo 결과가 아닙니다.');
 info(sl,'ACCEPTED · HISTORICAL','Native Moving L2 2/2 PASS\nRun #44965035965\n원본 소스 SHA f7edb2d1…',.70,2.02,5.77,2.49,K.tealLight,K.teal);info(sl,'FAILED HISTORY · HISTORICAL','Native Moving L2 0/2 FAIL\nRun #44914827138\n원본 소스 SHA a04f9a7d…',6.78,2.02,5.78,2.49,K.redLight,K.red);
 info(sl,'중요한 차이','네 ROS 2 패키지의 src Git Tree는 동일합니다. 성공/실패의 차이를 곧바로 “ROS 패키지 오류”라고 단정하지 마세요.',.70,4.81,11.87,1.29,K.blueLight,K.blue);notes(sl,['출처: DAY02 DUAL_SOURCE_MANIFEST.json / README_KO.md','두 실행의 Run ID와 커밋을 반드시 분리하여 설명합니다.','기존 Owner PASS_SCOPED와 자동 HOLD_RAW_REVIEW_AND_VISUAL_PENDING를 동시에 보존합니다.']);foot(sl)}
// Slide 4: source and legality
{let sl=frame('PROVENANCE','어떤 코드를 사용하나요?','기존 공개 학생용 저장소에 완성 MVP 전체 소스가 이미 포함되어 있습니다.');
 card(sl,.72,2.03,5.68,2.4,'원본 보존','accepted/runtime/ — 186개 파일\nROS 2 4개 패키지·tools·scripts·configs',K.green);
 card(sl,6.68,2.03,5.68,2.4,'비교 이력 보존','failed/runtime/ — 187개 파일\n동일 src 트리, 런타임 진단·도구 차이',K.red);
 term(sl,.72,4.72,11.65,1.46,[`source branch: release/day02-dual-mvp-full-source-build-20261126`,`release SHA: ${sha}`],'Exact pinned source / not a new runtime test');notes(sl,['Student repository: silverbjin/axia-robot-safety-student','비공개 Instructor 자료와 강사 정답은 이 PPTX의 학생용 소스에 포함하지 않습니다.']);foot(sl)}
// Slide 5: concept master first
{let sl=frame('MASTER FIRST','완성형 프롬프트를 먼저 보고, 왜 필요한지 역분해합니다','문제 정의와 증거가 불충분할수록 AI가 그럴듯한 오답을 제시하기 쉽습니다.');flow(sl,[['BASELINE','SHA/Run 고정'],['FIRST','첫 실패 분리'],['HYPOTHESIS','반증 계획'],['TDD','RED→GREEN'],['ACCEPT','범위 판정']],2.17,.7,11.99);info(sl,'마스터 프롬프트의 출력 계약','타임라인 → 코드 위치 → 반증 → 최소 수정 → 테스트 원문 → Evidence Manifest → L0~L3 판정 → 90초 브리핑',.75,4.47,11.84,1.38);notes(sl,['프롬프트에 역할·소스·검증 범위·금지사항을 넣는 이유를 하나씩 학습합니다.']);foot(sl)}
// Slide 6,7: master excerpt faithful
{let sl=frame('MASTER PROMPT 01','마스터 프롬프트의 전반부: 무엇을 분석할까요?','전문은 별도 MASTER_PROMPT_DAY3_MVP_KO.txt 파일과 학생 리포지토리에 제공합니다.');
 term(sl,.70,2.03,11.9,3.87,[
'ROLE : Jazzy / Gazebo / Nav2 / RMW 개발·통합 디버거',
'SOURCE : accepted/runtime/  +  failed/runtime/',
'PIN : release SHA 96be43164fab…',
'U00 : Run ID, SHA, timebase, evidence 고정',
'U01~05 : 기능 입력/출력, 첫 오류, RED/GREEN, diff',
'U06~10 : /scan, /safety/scan, RMW, Callback, Guard'], 'MASTER / INPUT + ANALYSIS');info(sl,'왜 조건을 먼저 고정할까요?','같은 사건의 로그만 비교하고, AI가 시스템을 임의로 변경하지 못하게 하기 위해서입니다.',.72,6.07,11.86,.69,K.tealLight,K.teal);notes(sl,['마스터 프롬프트 전체는 함께 배포한 텍스트로 복사합니다.','이 화면은 구조 요약이며 전문을 축약했다고 표기합니다.']);foot(sl)}
{let sl=frame('MASTER PROMPT 02','마스터 프롬프트의 후반부: 무엇을 증명할까요?','STOP 원인 확정에는 전송·안전·종료 증거가 모두 필요합니다.');
 term(sl,.70,2.03,11.9,3.78,[
'U11 : 정확 Goal UUID → Nav ACK → Loc ACK → CM exit0',
'U12 : L0/L1/L2/L3 구분 + historical vs new',
'U13 : Incident Card + 90초 기술 보고',
'FORBID : Scan300 / CM120 / Guard150 TTL 완화',
'FORBID : 무단 Goal / Fault Injection / 안전 PASS 조작',
'OUTPUT : FACT / HYPOTHESIS / NOT_RUN / HOLD'], 'MASTER / SAFETY + ACCEPTANCE');info(sl,'AI 답변의 통과 조건','각 주장이 현재 코드 SHA와 원본 증거에서 재현 가능해야 합니다. 불명확하면 INCONCLUSIVE입니다.',.72,6.02,11.86,.77,K.amberLight,K.amber);notes(sl,['출력의 “PASS”는 진짜로 실행된 범위에만 붙입니다.','SW STOP은 인증된 E-Stop이 아닙니다.']);foot(sl)}
// Slide 8 architecture
{let sl=frame('ARCHITECTURE','실제 G07 데이터 흐름: 센서에서 안전 상태까지','굵은 화살표는 센서 데이터 경로, 별도 검증 계층은 읽기 전용 관측을 뜻합니다.');flow(sl,[['Gazebo LiDAR','LaserScan 생성'],['ros_gz_bridge','ROS 변환'],['/scan','Source 토픽'],['Fault Injector','LaserScan relay'],['/safety/scan','Safety 토픽']],2.10,.65,12.0);
 flow(sl,[['Supervisor','상태·신선도'],['Collision Monitor','공간 위험 판단'],['Base Guard','명령 차단'],['TurtleBot3','cmd→odom']],4.03,.85,11.65);
 t(sl,'실제 Cmd 체인·QoS·launch 연결은 각 구현 파일을 읽어 확인합니다. “도식=검증 완료”는 아닙니다.',.86,5.72,11.5,.42,{size:12.5,color:K.red,bold:true});notes(sl,['axia_fault_injector: /scan에서 입력을 받고 SCAN_OUT으로 재발행하는 실제 구현 존재','Collision Monitor/Guard 경로는 구성 및 launch 확인 후 확정합니다.','학생에게 센서 데이터 경로와 제어 명령 경로를 구분하게 합니다.']);foot(sl)}
// Slide 9 packages
{let sl=frame('ARCHITECTURE','네 패키지의 책임을 실제 코드와 연결하기','패키지명만 암기하지 않고 입력·처리·출력 관점으로 설명합니다.');const rows=[['axia_fault_injector','LaserScan 입력·Relay·Fault 상태'],['axia_safety_bringup','기존 Nav2/Gazebo Launch 연결'],['axia_safety_supervisor','FSM·Goal·Command Gate·Guard'],['axia_scenario_verifier','시나리오 및 증거 확인']];rows.forEach((r,i)=>card(sl,.76,1.97+i*1.11,11.77,.91,r[0],r[1],[K.teal,K.blue,K.amber,K.green][i]));notes(sl,['소스 경로: accepted/runtime/ros2_ws/src/ 네 패키지','학생이 package.xml과 각 setup.py를 열어 실행 노드 이름을 확인하도록 유도합니다.']);foot(sl)}
// Slide 10 actual code snippet
{let sl=frame('SOURCE CODE','LaserScan Relay: 코드 한 줄과 데이터 파이프라인의 연결','수업에서 “노드가 무엇을 읽고 어디로 전달하는가?”를 실제 코드를 통해 확인합니다.');
 term(sl,.72,2.01,7.50,3.82,[
'FaultInjectorNode(Node):',
'  self._relay = create_publisher(',
'    LaserScan, SCAN_OUT, qos_profile_sensor_data)',
'  create_subscription(',
'    LaserScan, SCAN_IN, self._on_scan, ...)',
'  self._relay.publish(forwarded)'], 'fault_injector_node.py / excerpt',10.5);
 card(sl,8.48,2.01,4.13,1.14,'입력','SCAN_IN = /scan',K.blue);
 card(sl,8.48,3.36,4.13,1.14,'처리','stamp 정책 적용 · 안전 relay',K.teal);
 card(sl,8.48,4.71,4.13,1.14,'출력','SCAN_OUT = /safety/scan',K.green);
 notes(sl,['실제 코드는 self.create_subscription, self.create_publisher 사용','Fault Injection은 기본 비활성이고 물리 로봇 제어용이 아닙니다.','상수값은 해당 SHA의 fault_policy.py를 함께 확인하게 합니다.']);foot(sl)}
// Slide 11 timebase
{let sl=frame('DATA PIPELINE','동일 메시지에서도 시각은 서로 다를 수 있습니다','ROS header.stamp (SIM)·RMW timestamp·host monotonic timestamp를 섞어서 빼면 안 됩니다.');flow(sl,[['Sensor header','ROS sim time'],['RMW source','system ns'],['RMW received','system ns'],['Observer callback','host monotonic']],2.23,.68,12);
 info(sl,'올바른 비교','같은 시간 기준에서 연속 source와 source, received와 received, observer와 observer 사이의 간격을 계산합니다.',.71,4.08,5.74,1.58,K.tealLight,K.teal);
 info(sl,'잘못된 비교','header.sim의 절대 시각에서 host.monotonic의 절대 시각을 빼 “전송 지연”이라고 주장하지 않습니다.',6.73,4.08,5.77,1.58,K.redLight,K.red);
 notes(sl,['MessageInfo의 source_timestamp, received_timestamp, publication_sequence_number 유효성 확인 필요','RMW seq가 없으면 정확한 publication pair는 미입증이며 후보로만 표시합니다.']);foot(sl)}
// Slide 12 real first gap
{let sl=frame('DATA PIPELINE','예제: source 99ms인데 Observer는 424.373ms일 수 있습니다','이 수치는 실제 도구 테스트가 사용하는 교육용 fixture입니다. 특정 새 Gazebo 실행의 실측치가 아닙니다.');
 const st=[['Source gap','99.0 ms',K.green],['RMW recv gap','100.0 ms',K.blue],['Observer gap','424.373 ms',K.red]];st.forEach((v,i)=>{let x=.75+i*4.04;box(sl,x,2.16,3.77,2.2,K.white,K.line,.13);t(sl,v[0],x+.25,2.43,3.19,.34,{size:15,bold:true});t(sl,v[1],x+.24,3.15,3.19,.64,{size:25.5,color:v[2],bold:true});});
 info(sl,'해석','Observer 간격이 300ms를 초과해도 “DDS 전송 지연이 424ms”라는 결론은 성립하지 않습니다. RMW→Callback/Observer 경계의 후속 계측이 필요합니다.',.76,4.79,11.74,1.20,K.amberLight,K.amber);
 notes(sl,['출처: 실제 코드 test_g07_scan_rmw_first_pair.py, test_100ms_source_receive_but_424ms_callback_is_not_publisher_stall','구간별 gap은 메시지 간격입니다. 단일 메시지 지연시간과 동일하지 않습니다.']);foot(sl)}
// Slide 13 safe setup
{let sl=frame('GETTING STARTED','완성 소스를 원본 그대로 준비하고 검증합니다','학생 실습에서는 실제 주행 Goal을 자동 실행하지 않습니다.');
 term(sl,.75,2.00,11.83,3.42,[
'git clone --single-branch --branch release/day02-dual-mvp-full-source-build-20261126 \\',
'  https://github.com/silverbjin/axia-robot-safety-student.git axia-day03-mvp',
'cd axia-day03-mvp',
`git checkout --detach ${sha}`,
'python3 special_lecture/day02_mvp_sources/scripts/verify_dual_source.py'], 'WSL2 Ubuntu 24.04 / NO ROS RUN',10.2);
 info(sl,'예상 결과 (실제 학생 실행 전)','DUAL_G07_SOURCE_CUSTODY_L0_PASS. 실패 시 git status/HEAD·SHA를 점검하세요. 기존 경로를 삭제·덮어쓰지 않습니다.',.74,5.64,11.87,1.06,K.tealLight,K.teal);
 notes(sl,['Source: DAY2 README build_dual_mvp.sh','학생 환경에서 실제 CLI를 실행했다고 주장하지 않습니다.','이미 디렉터리가 존재할 경우 새 디렉터리 이름을 선택하도록 안내합니다.']);foot(sl)}
// 14*2 unit slides = 28, current 13 -> 41.
units.forEach(u=>{unitResult(u);unitPractice(u)});
// Slide 42 Dev capstone
{let sl=frame('MISSION D / WRAP','개발 단계 성취: RED→GREEN은 증거로 연결됩니다','완성 MVP의 안전 노드는 원본 유지 · 개인 복제본의 진단 모듈만 학습용 변경');flow(sl,[['RED','잘못된 계약 재현'],['GREEN','최소 수정'],['REFACTOR','동작 유지'],['REVIEW','부작용 확인'],['COMMIT','학생 SHA']],2.22,.65,12.0);
 info(sl,'학생 제출','코드 diff / RED stdout+exit / GREEN stdout+exit / 정책 불변 증거 / 학생 개인 Commit SHA',.75,4.47,11.72,1.23,K.tealLight,K.teal);notes(sl,['실제 학생 실행 출력은 수업에서 획득','정답 코드와 Hidden Test는 강사 비공개 저장소에서만 관리']);foot(sl)}
// Slide43 integration
{let sl=frame('MISSION I / WRAP','통합 단계 성취: 어느 경계가 먼저 깨졌는지 설명할 수 있습니다','데이터 전달의 주기와 안전 상태의 첫 변화는 다른 계측입니다.');
 flow(sl,[['Publisher','source interval'],['RMW','received interval'],['Callback','observer gap'],['Supervisor','first transition'],['Guard','age / latch']],2.16,.67,12);
 info(sl,'학생 제출','각 경계: 입력→처리→출력 / 같은 Run·시계 / 최초 위반 / 후보 가설 / 반증 가능 계측',.74,4.63,11.8,1.26,K.blueLight,K.blue);
 notes(sl,['CM Observer와 Guard 내부 receipt 비교는 독립 증거 필요','Scan 300ms, CM 120ms, Guard 150ms 안전 정책 불변']);foot(sl)}
// Slide44 acceptance
{let sl=frame('MISSION A / WRAP','인수 단계 성취: 무엇을 PASS라고 부를 수 있나요?','과거 성공본의 증거와 학생 수정 코드의 신규 인수는 별도입니다.');
 flow(sl,[['Goal UUID','terminal status'],['Navigation','ACK'],['Localization','ACK'],['Collision Monitor','exit0'],['Odom/TTL','안전 증거']],2.16,.68,12);
 info(sl,'결론의 엄격성','새 학생 수정 코드: 직접 실험하지 않았다면 L2/L3 = NOT_RUN. 한 계층만 통과했으면 전체 시연 안정성은 미검증입니다.',.74,4.63,11.8,1.27,K.amberLight,K.amber);notes(sl,['SW Stop not certified E-Stop','Nav ACK를 CM exit0 증명으로 대체하지 않습니다.']);foot(sl)}
// Slide45 evidence provenance
{let sl=frame('ACCEPTANCE / EVIDENCE','실제 과거 CI와 신규 학습 코드의 증거를 나눕니다','Run ID마다 헤더·결과·원본 SHA를 유지해야 결과를 신뢰할 수 있습니다.');
 const row=[['SOURCE','SHA','RUN / LEVEL','VERDICT'],['accepted','f7edb2d1…','#44965035965 / L2','2/2 PASS'],['failed','a04f9a7d…','#44914827138 / L2','0/2 FAIL'],['student edit','학생 commit','신규 L0 직접 실행','결과 기입'],['student edit','학생 commit','신규 L2/L3','NOT_RUN']];row.forEach((r,i)=>{let y=2.09+i*.73;box(sl,.75,y,11.78,.65,i===0?K.navy:(i%2?K.white:K.light),i===0?null:K.line,.05);const w=[1.78,2.20,4.30,2.7],xx=[.96,2.78,5.09,9.4];r.forEach((v,j)=>t(sl,v,xx[j],y+.14,w[j],.31,{size:i===0?12.2:11.7,color:i===0?K.white:K.ink,bold:i===0||j===3}))});notes(sl,['역사적 Native 2/2 성공과 0/2 실패는 실제 공개 CI에서 완료된 기록입니다.','학생 재현은 새 테스트·새 SHA가 있어야 새로운 PASS가 됩니다.']);foot(sl)}
// Slide46 workflow paper
{let sl=frame('ACCEPTANCE / EVIDENCE','AC → TEST → EVIDENCE → RESULT는 항상 연결되어야 합니다','요구사항만 적거나 CI 체크만 첨부하면 인수 범위가 모호해집니다.');flow(sl,[['Acceptance Criteria','무엇을 증명?'],['Test','어떤 명령?'],['Evidence','어느 Run·SHA?'],['Result','무엇이 PASS?']],2.26,.71,11.95);
 info(sl,'정확한 결과 문장 예시','“학생 개인 브랜치의 진단 모듈 L0 회귀를 실행했고, 해당 테스트 3개가 PASS했습니다. 신규 Moving L2/Owner L3는 NOT_RUN입니다.”',.73,4.50,11.88,1.35,K.tealLight,K.teal);notes(sl,['실제 실행하지 않은 테스트 숫자는 예시로만 전달하고 인수 증거처럼 쓰지 않습니다.']);foot(sl)}
// Slide47 verdict card
{let sl=frame('STUDENT OUTPUT','한 장의 Incident & Acceptance Card를 완성하세요','실습 종료 시 결과를 증거와 함께 짧게 발표합니다.');
 box(sl,.74,1.98,11.87,4.72,K.white,K.line,.12);tag(sl,'INCIDENT',.98,2.24,1.13,K.navy);t(sl,'최초 상태 전이: ________    최초 timing 위반: ________',2.27,2.23,9.8,.36,{size:15,bold:true});line(sl,1.0,2.83,12.30,2.83,K.line);
 t(sl,'SOURCE / SHA / RUN',1.02,3.02,4,.27,{size:12,bold:true,color:K.teal});t(sl,'DEV / INTEGRATION / ACCEPTANCE',6.1,3.02,5.9,.27,{size:12,bold:true,color:K.blue});
 t(sl,'원본: __________________________\n학생 커밋: _____________________\n증거 파일: _____________________',1.04,3.41,5.15,1.28,{size:13.6,color:K.ink,valign:'top'});
 t(sl,'RED→GREEN: ______________________\n가설·반증: _______________________\n검증 L0/L1/L2/L3: _______________',6.10,3.41,5.77,1.28,{size:13.6,color:K.ink,valign:'top'});
 box(sl,1.01,5.30,11.30,.92,K.amberLight,null,.10);t(sl,'최종 판정  PASS_SCOPED / HOLD / INCONCLUSIVE / NOT_RUN',1.26,5.56,10.80,.34,{size:16,bold:true,color:K.amber});notes(sl,['워크시트는 학생이 직접 채웁니다.','미검증 항목을 적절하게 HOLD로 남기는 것도 성공적인 판단입니다.']);foot(sl)}
// Slide48 pitfall
{let sl=frame('COMMON FAILURES','AI 응답에서 반드시 걸러야 하는 다섯 가지 오답','기술적으로 그럴듯해도 원본 증거가 없으면 채택하지 않습니다.');
 const xs=['마지막 예외 = 최초 원인','서로 다른 Run의 숫자를 합산','received gap = DDS 지연','CI PASS = WSL2 PASS','Software STOP = 인증 E-Stop'];xs.forEach((v,i)=>{box(sl,.78,1.98+i*.89,11.70,.74,i%2?K.white:K.redLight,K.line,.10);tag(sl,String(i+1).padStart(2,'0'),1.0,2.16+i*.89,.45,K.red);t(sl,v,1.64,2.11+i*.89,9.97,.37,{size:15.1,bold:true})});notes(sl,['학생에게 틀린 문장 5개를 실제 코드·증거를 사용해 반박하도록 합니다.']);foot(sl)}
// Slide49 timings
{let sl=frame('COURSE TIMELINE','180분 운영표: 실습은 실제 완성 코드에서 시작합니다','실시간 Gazebo 재시연은 필수가 아니며, 기존 증거의 해석과 코드 검증에 집중합니다.');
 const rows=[['00–15','실제 2/2 vs 0/2 결과 먼저'],['15–40','소스 SHA·네 패키지·Graph'],['40–75','MISSION D: 개발 오류·RED/GREEN'],['75–85','휴식 · 증거 점검'],['85–130','MISSION I: RMW·Callback·Guard'],['130–165','MISSION A: UUID·ACK·L0~L3'],['165–180','Incident Card · 90초 발표']];rows.forEach((r,i)=>{let y=1.99+i*.64;box(sl,.78,y,11.74,.57,i%2?K.white:K.light,K.line,.07);tag(sl,r[0],.98,y+.11,1.24,K.navy);t(sl,r[1],2.45,y+.10,9.60,.32,{size:13.3,bold:i===2||i===4||i===5})});notes(sl,['시간표는 기존 DAY 3 개정 기획 v3.0에 맞춰 고정했습니다.']);foot(sl)}
// Slide50 sheet
{let sl=frame('STUDENT CHECKLIST','학생 제출 전 확인할 7개의 질문','체크하지 못한 항목은 마지막 보고서에 미검증으로 표시합니다.');let arr=['현재 코드의 정확한 HEAD·Run ID가 있나요?','각 블록의 입력·처리·출력이 소스와 맞나요?','first_safety_transition과 first_timing_violation을 분리했나요?','AI의 가설을 반박할 수 있는 데이터를 제시했나요?','RED/GREEN 명령·stdout·exit code를 보존했나요?','CM/Guard/Scan/Odom의 별도 타이밍 경계를 확인했나요?','새 코드는 L2/L3를 실행하지 않았다면 NOT_RUN인가요?'];arr.forEach((v,i)=>{t(sl,`□ ${v}`,1.0,1.99+i*.63,11.41,.41,{size:15.2,bold:i===2||i===6})});notes(sl,['교사는 체크리스트로 개인 발표 후 피드백을 수행합니다.']);foot(sl)}
// Slide51 definitions
{let sl=frame('GLOSSARY','초심자를 위한 핵심 용어 모음','서로 다른 개념을 같은 의미로 쓰지 않는 것만으로도 많은 오류를 막을 수 있습니다.');const rows=[['Publisher / Subscriber','보내는 노드 / 메시지를 받는 노드'],['RMW / DDS','ROS 2 미들웨어 인터페이스 / 메시지 전달 체계'],['Callback / Executor','도착 이벤트 처리 함수 / 실행 관리자'],['Message age / TTL','마지막 유효 입력의 나이 / 허용 유효 시간'],['Run ID / SHA','실험 증거 식별자 / 소스 코드 식별자'],['INCONCLUSIVE / NOT_RUN','증거 불충분 / 아예 실행하지 않음']];rows.forEach((r,i)=>{let y=2.02+i*.73;box(sl,.77,y,11.77,.63,i%2?K.white:K.light,K.line,.05);t(sl,r[0],.96,y+.13,4.1,.29,{size:13.6,color:K.teal,bold:true});t(sl,r[1],5.05,y+.12,7.1,.33,{size:12.9})});notes(sl,['Timebase: ROS simulation header와 host monotonic 시각을 직접 뺄셈하지 않습니다.']);foot(sl)}
// Slide52 final
{let sl=pptx.addSlide();sl.background={color:K.navy2};box(sl,0,0,W,H,K.navy2,null,0);tag(sl,'DAY 03 · MISSION COMPLETE',.83,.82,3.55,K.teal);t(sl,'AI가 코드를 제안했습니다.',.84,1.68,11.65,.62,{size:29,color:K.white,bold:true});t(sl,'우리는 증거로 검증합니다.',.84,2.59,11.65,.87,{size:41,color:K.cyan,bold:true});t(sl,'실제 소스 · 최초 실패 · 반증 가능한 가설 · RED→GREEN · 명확한 인수 범위',.86,4.17,11.7,.58,{size:18.6,color:'C9E0EC'});box(sl,.84,5.50,11.55,.60,K.panel,null,.10);t(sl,'SPEC → CODE → EVIDENCE → ACCEPTANCE',1.14,5.62,10.9,.34,{size:19,color:K.white,bold:true,align:'center'});notes(sl,['요약: 실패를 포장하지 않고, 어디까지 입증했는지를 정확히 설명하는 개발자','기존 완성 MVP 증거는 보존하며 학생의 신규 결과는 별도 Run/SHA로 기록합니다.']);foot(sl)}

if (pptx._slides.length!==52)throw new Error('BAD_SLIDE_COUNT='+pptx._slides.length);
const output=process.argv[2]||'/mnt/data/AXIA_DAY3_MVP_MASTER_FIRST_WORKBOOK_52_KO.pptx';
pptx.writeFile({fileName:output}).then(()=>console.log('PPTX_WRITTEN='+output+' SLIDES='+pptx._slides.length+' UNIT_FACES='+unitCount)).catch(e=>{console.error(e);process.exit(1)});