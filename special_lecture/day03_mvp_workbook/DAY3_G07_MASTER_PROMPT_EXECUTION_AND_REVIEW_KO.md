# AXIA DAY 3 — 완성 G07 MVP 실행형 마스터 프롬프트와 AI 응답 검수 가이드

> 버전 1.0 · 학생용 공개판 · 52장 워크북 U00~U13 대응  
> **사용 방법:** 먼저 2절의 완성 프롬프트를 통째로 AI Agent에 복사합니다. 이후 3절에서 설계 이유를 분석하고, 4절에서 실제 응답을 검수합니다. [U00~U13 단위 프롬프트](DAY3_G07_U00_U13_UNIT_PROMPTS_KO.md)를 순서대로 실습할 수도 있습니다.

## 1. 왜 이 프롬프트를 사용하나요?

완성된 AXIA G07 MVP를 새로 개발하는 수업이 아닙니다. **기존 코드에서 발생하는 개발 → 통합 → 인수 단계의 오류를 AI와 함께 재현·분석·검증하는 수업**입니다. 좋은 프롬프트는 모호한 요청("오류를 고쳐주세요")이 아니라 **현재 SHA, 재현 경계, 입력 증거, 반증, 최소 변경, 검증 수준**을 지정합니다.

**공개 원본 출처:**

| 항목 | 고정 값 |
|---|---|
| 저장소 | https://github.com/silverbjin/axia-robot-safety-student |
| 전체 소스 배포 브랜치 | release/day02-dual-mvp-full-source-build-20261126 |
| 전체 소스 릴리스 SHA | 96be43164fab3f15025edd59279bcfd50b6232cd |
| 성공본 런타임 | special_lecture/day02_mvp_sources/accepted/runtime |
| 실패 이력 런타임 | special_lecture/day02_mvp_sources/failed/runtime |
| 원본 성공 Student SHA | f7edb2d126502eeeed58ae014adadc7a2096d41b |
| 원본 실패 Student SHA | a04f9a7da8d54bbd9f944d05388792cb706adf28 |
| 역사적 성공 Public L2 | Run 44965035965 — 2/2 PASS |
| 역사적 실패 Public L2 | Run 44914827138 — 0/2 FAIL |

두 소스의 ROS 2 패키지 소스 트리는 동일하며, **상위 런타임 도구·검증 계층은 차이**가 있습니다. 단순 diff로 DDS 근본 원인을 확정하지 않습니다. 과거 Owner WSL2는 별도 수치·Lifecycle 검토의 PASS_SCOPED이며, 자동 원본 `HOLD_RAW_REVIEW_AND_VISUAL_PENDING`은 그대로 보존합니다.

## 2. 복사하여 사용하는 완성형 마스터 프롬프트

아래 블록 전체가 **실제로 입력할 프롬프트**입니다. 대괄호 입력란에 실제 실행값을 넣으십시오. Agent가 저장소를 읽지 못한다면 소스 파일·로그를 제공하고 부족한 항목은 UNKNOWN으로 유지하십시오.

~~~text
# AXIA DAY3 — 완성된 G07 MVP에서 개발·통합·인수 오류 해결

[ROLE]
당신은 ROS 2 Jazzy, Gazebo Harmonic, TurtleBot3 Waffle, 공식 Nav2와
Collision Monitor, Safety Supervisor/Base Guard, DDS/RMW, Python 테스트,
GitHub Actions를 이해하는 시니어 ROS 2 디버깅 엔지니어입니다.
목표는 기존 완성 MVP의 기능·안전 계약을 유지하며 실제 오류를
"최초 관측 → 가설/반증 → 최소 수정 → 회귀 검증 → 인수 판정"으로 해결하는 것입니다.
증거 없이 성공 또는 근본 원인을 주장하지 마십시오.

[PINNED SOURCE — 원본]
REPO=https://github.com/silverbjin/axia-robot-safety-student
SOURCE_RELEASE_SHA=96be43164fab3f15025edd59279bcfd50b6232cd
ACCEPTED_DIR=special_lecture/day02_mvp_sources/accepted/runtime
FAILED_DIR=special_lecture/day02_mvp_sources/failed/runtime
ACCEPTED_SOURCE_SHA=f7edb2d126502eeeed58ae014adadc7a2096d41b
FAILED_SOURCE_SHA=a04f9a7da8d54bbd9f944d05388792cb706adf28
HISTORIC_L2_ACCEPTED=44965035965 (2/2 PASS)
HISTORIC_L2_FAILED=44914827138 (0/2 FAIL)

[현재 조사할 실행 — 학생이 채움]
CASE=[development | integration | acceptance]
CURRENT_CODE_SHA=[git rev-parse HEAD 실제 값 또는 UNKNOWN]
RUN_ID=[실제 로그 Run ID 또는 UNKNOWN]
LOG_OR_EVIDENCE_PATHS=[실제 파일 경로와 제공 여부 또는 NONE]
OS_ROS_RMW=[실제 확인된 버전 또는 UNKNOWN]
SYMPTOM=[첫 관측 오류 원문]
TIMEBASE=[host monotonic | ROS simulation | RMW system | UNKNOWN]
PERMISSION=[read-only | isolated-training-copy | separately-authorized]
EXECUTION_ENV=[python-only | ROS Jazzy | native Gazebo | Owner WSL2 | UNKNOWN]

[NON-NEGOTIABLE SAFETY]
1. 먼저 읽기 전용으로 조사하십시오. 무단 Moving Goal, Fault Injection,
   ROS/Gazebo 실행, 안전 토픽 발행, 프로세스 전체 종료를 하지 마십시오.
2. accepted/runtime은 불변입니다. 개발 실습의 RED/GREEN은
   별도로 복사한 진단용 Python 모듈과 공개 테스트에서만 진행하십시오.
3. Scan 300ms, Clock 300ms, Odom 300ms, CM 120ms, Guard 150ms
   등 기존 안전 기준을 완화하지 마십시오. 정확한 경계의 부등호와 측정 위치는
   실제 계약/코드에서 확인하십시오.
4. SW STOP != 인증된 물리 E-Stop. CERTIFIED_ESTOP=false입니다.
5. 강사 정답/Hidden Test/원본 Owner rosbag/TAR/개인정보·토큰을 공개하지 마십시오.
6. 과거 CI PASS를 새 소스 또는 Owner L3의 PASS라고 주장하지 마십시오.
7. 실행하지 않은 결과는 NOT_RUN; 증거 부족은 INCONCLUSIVE/HOLD로 남깁니다.
8. main 병합은 사용자의 별도 승인이 없으면 금지합니다.

[STEP 0 — 현재 사실과 코드 접근]
- 원본 SHA, 현재 워크트리 SHA, Run ID, 각 증거의 실제 파일 경로를 표로 쓰십시오.
- 직접 읽은 파일과 열지 못한 파일을 구별하십시오. 파일을 못 읽었다면
  코드 구현을 상상하지 말고 필요한 읽기 전용 명령을 제시하십시오.
- 성공본, 실패본, 학생 수정본은 별도의 실행/검증 행에 기록하십시오.
- ms/s/ns와 ROS simulated header, RMW source/received, host monotonic
  시간축을 구분하십시오. 다른 clock domain의 절대값을 빼지 마십시오.

[STEP 1 — 개발 오류 U01~U05]
- 네 패키지 axia_fault_injector, axia_safety_bringup,
  axia_safety_supervisor, axia_scenario_verifier의 책임을
  실제 파일 → Node → 입력/처리/출력 → 테스트로 연결하십시오.
- tools/p2_g07_health_first_boundary.py를 읽어
  first_readiness_blockers, first_state_transition, release=HOLD 계약을 확인하십시오.
- 최초 관측 사실, 최초 상태 전이, 마지막 예외를 구분하십시오.
- 실제 결함이 이미 해결된 완성본에 있다고 가정하지 마십시오.
  교육용 RED는 격리 복제본의 회귀 테스트에서만 재현하십시오.
- RED → GREEN → REFACTOR → REVIEW → COMMIT 순서를 적용하고
  각 단계의 명령, 파일, stdout/stderr, exit code, diff, Git SHA를 보고하십시오.
- 안전 로직/기준을 수정하지 않은 증거를 제시하십시오.

[STEP 2 — 통합 오류 U06~U10]
- launch/config와 코드로 Gazebo LiDAR → ros_gz_bridge →
  /scan → Fault Injector → /safety/scan → Supervisor/Collision Monitor →
  Base Guard → 최종 /cmd_vel 및 /odom의 실제 연결을 확인하십시오.
  검증하지 못한 간선은 UNVERIFIED로 표시하십시오.
- tools/p2_g07_scan_rmw_first_pair.py의 source_gap_ms,
  received_gap_ms, observer_gap_ms, header_sim_gap_ms를 확인하십시오.
  모두 "연속 두 메시지 사이 간격"이며, 한 메시지의 송수신 latency와 다릅니다.
  동일 publication sequence, 동일 메시지쌍, timebase 일치가 필요합니다.
- first_state_transition(보고서 별칭 first_safety_transition)과
  first_timing_violation을 독립 항목으로 출력하십시오.
- 메시지 seq/수신 timestamp가 부족하면 INCONCLUSIVE/HOLD로 유지하십시오.
  Publisher stall, DDS 수신, Executor callback 원인을 단정하지 마십시오.
- /scan, /safety/scan, /clock, /odom, CM→Guard 전달, Guard 내부 age를
  각각 조사하십시오. 외부 Observer가 받은 메시지는 Guard가 받았다는 보장이 아닙니다.
- 원인 후보는 최대 세 가지, 각 후보별 반증 관측/필요 계측/비용을 제시하십시오.
- 한 계층을 수정했더라도 다른 안전 계층 타이밍을 검증하지 않았다면
  전체 시연 안정성 UNVERIFIED입니다.

[STEP 3 — 인수 오류 U11~U12]
- 정확한 Nav2 Goal UUID의 terminal, 같은 UUID Cancel ACK,
  CLEAR→SLOW→STOP, odom 0 유지 ≥1s, Scan/Odom/Clock ≤300ms,
  CM 전달 ≤120ms, Guard age ≤150ms, Guard 예상 밖 latch,
  Contact=0, Navigation ACK, Localization ACK, CM exit0, clean shutdown,
  14-topic bag 등 실제 인수 계약 항목을 각각 별도 검증하십시오.
  정확한 비교 부등호 및 모든 계약의 적용 구간은 원본 기준에서 확인하십시오.
- 과거 성공 Run 44965035965, 실패 Run 44914827138, 현재 SHA의 실행을
  분리하십시오. 과거 Owner PASS_SCOPED와 원본 자동 HOLD를 모두 기재하십시오.
- 새 학생 변경 코드의 Native Gazebo L2와 Owner WSL2 L3는
  실제 실행/증거가 없다면 반드시 NOT_RUN으로 유지하십시오.
- CI L0/L1 PASS는 실제 Gazebo L2/Owner L3 인수를 증명하지 않습니다.

[OUTPUT — 아래 순서 고정]
A. 출처 표(SHA, Run ID, 시간축, 실제 접근한 파일, 환경)
B. Mermaid 아키텍처 + 각 구성 블록의 입력/처리/출력/소스 경로
C. 타임라인: first_state_transition, first_timing_violation,
   final_exception, event source/timebase
D. 사실/가설/반증 표(근거 없는 단정 금지)
E. RED/GREEN/REFACTOR/REVIEW/COMMIT 실제 실행 명령·출력·exit code·SHA
F. 안전 계층별 전달 주기 및 TTL 검증 매트릭스
G. 증거 Manifest(경로, 실제 산출한 SHA256, CI Run URL, 검증 수준)
H. L0/L1/L2/L3 결과를 성공본/실패본/현재 코드로 분리한 표
I. PASS_SCOPED/HOLD/INCONCLUSIVE/NOT_RUN 결론 및 미검증 항목
J. 90초 브리핑(증상→첫 경계→원인 후보→최소 수정/반증→검증→인수 판정)

[STOP]
어떤 명령도 실행할 수 없거나 소스/증거가 누락됐다면
"확인한 사실 / 확인하지 못한 사실 / 필요한 다음 읽기 전용 명령"으로
답하십시오. 상상한 테스트 결과로 PASS를 만들지 마십시오.
~~~

## 3. 프롬프트 구성요소와 설계 이유

| 구성요소 | 왜 넣었나요? | 없으면 생기는 오류 | 대응 Unit |
|---|---|---|---|
| ROLE·목표 | 새 개발이 아닌 기존 코드 디버깅에 집중 | 기능 재구현·MVP 범위 확장 | U00 |
| REPO·SHA·Run ID | 성공/실패/현재 이력 혼합 방지 | 성공본의 PASS를 실패본으로 전용 | U00 |
| 실제 파일 접근 | AI의 함수·노드 경로 환각 방지 | 존재하지 않는 API 해설 | U01 |
| Non-negotiable Safety | TTL 완화·무단 주행·정답 유출 차단 | 통과를 위해 안전값 수정 | 전 Unit |
| 최초 상태 전이 | 안전제어의 첫 변화 관찰 | 마지막 예외만 수정 | U02 |
| RED/반례 | 수정 전 실패 재현 가능성 입증 | 테스트 없이 GREEN 주장 | U03~U05 |
| 노드·Topic 경로 | 실제 인터페이스 오류 탐색 | /scan·/safety/scan 혼동 | U06 |
| RMW 간격과 시간축 | publication/source/receive/callback 원인 계층 분리 | 다른 시간축 빼기 | U07 |
| 첫 TTL 위반 | 평균이 아니라 첫 안전 위반 규명 | 정상 평균으로 TTL 위반 무시 | U08 |
| 가설·반증 | 설명을 실제 검증 실험으로 연결 | DDS 단정 | U09 |
| CM→Guard 수신 차이 | 한 노드 PASS != 전체 안전 PASS | observer를 Guard로 간주 | U10 |
| Goal UUID·ACK·exit0 | 제어 요청/완료/정상 종료 구분 | Cancel ACK만으로 정지 PASS | U11 |
| L0~L3 | CI와 Owner 실제 Gazebo 인수 분리 | Python L0를 L3로 주장 | U12 |
| 출력 계약 | 답변을 증거 기반 보고서로 변환 | 실행 로그/검증 범위 누락 | U13 |

### 파이프라인 설명 다이어그램

~~~mermaid
flowchart LR
  A["Gazebo LiDAR"] --> B["ros_gz_bridge"]
  B --> C["/scan"]
  C --> D["Fault Injector"]
  D --> E["/safety/scan"]
  E --> F["Supervisor / Collision Monitor"]
  F --> G["Base Guard"]
  G --> H["/cmd_vel → Robot → /odom"]
  C -.-> I["출처·시각·수신 간격 증거"]
  E -.-> I
  F -.-> I
  H -.-> I
  I --> J["첫 전이 / 첫 TTL 위반"]
  J --> K["가설·반증·인수"]
~~~

이 그림은 **교육용 논리 개요**입니다. 실제 연결, Topic 이름, QoS는 launch/config·Publisher/Subscriber 구현 코드로 검증해야 합니다.

## 4. AI 응답 필수 검수

아래 질문을 실제 응답에 대조해 각각 **PASS / FAIL / UNVERIFIED**로 기록합니다.

| 검수 ID | 무엇을 확인할까요? | PASS 증거 |
|---|---|---|
| Q01 | 실제 파일과 함수 서명을 확인했나요? | SHA 고정 소스 경로/함수 |
| Q02 | 성공본·실패본·학생 수정본을 분리했나요? | 코드 SHA와 Run ID별 별도 표 |
| Q03 | 첫 상태 전이와 첫 타이밍 위반이 분리됐나요? | first_state_transition / first_timing_violation |
| Q04 | 마지막 예외를 최초 원인이라고 단정하지 않았나요? | 원본의 시간순 사건 |
| Q05 | ms, s, ns 및 시간축 변환이 올바른가요? | 각 값의 단위/timebase |
| Q06 | source_gap_ms, received_gap_ms, observer_gap_ms를 구별했나요? | 같은 메시지 pair/seq |
| Q07 | /scan과 /safety/scan의 발행/구독이 맞나요? | 실제 Node 코드와 launch |
| Q08 | CM Observer와 Guard 내부 수신을 혼동하지 않았나요? | 두 수신 위치 증거 |
| Q09 | 근본 원인은 사실과 가설을 분리했나요? | 각 가설의 반증 조건 |
| Q10 | RED와 GREEN을 같은 테스트·같은 조건에서 수행했나요? | 테스트 이름, 출력, exit code |
| Q11 | 안전 TTL·Goal 승인·SW STOP 의미를 유지했나요? | diff, 설정 변경 없음 |
| Q12 | 수정 후 다른 안전 계층의 타이밍을 점검했나요? | 계층별 PASS/HOLD/UNVERIFIED |
| Q13 | exact Goal UUID, Odom ZERO, Nav/Loc ACK, CM exit0을 각각 확인했나요? | 독립 기록 |
| Q14 | L0/L1/L2/L3가 검증 범위에 맞나요? | 실제 CI/Gazebo/Owner 증거 |
| Q15 | 인증 E-Stop으로 잘못 표현하거나 비밀자료를 유출하지 않았나요? | CERTIFIED_ESTOP=false |
| Q16 | 없는 증거는 NOT_RUN/INCONCLUSIVE/HOLD로 두었나요? | 보수적 최종 판정 |

**거부 기준:** Q01, Q02, Q05, Q09, Q11, Q14, Q15, Q16에서 FAIL이 하나라도 있으면 AI 답변을 그대로 적용하거나 인수 PASS로 사용하지 마십시오. 미검증 항목은 PASS를 추정하지 말고 별도로 표시하십시오.

### 역사적 수치와 예상 결과를 구분하세요

- **실제 실패본의 과거 Run 44914827138:** PRE_GOAL scan gap 439.011892ms, clock 335.393855ms, odom 374.025229ms. 이후 별도 cycle의 최초 blocking odom 362.100229ms. *각 cycle을 합쳐 하나의 타임라인으로 만들지 않습니다.*
- **실제 성공본의 과거 Owner 실행:** CLEAR 전방 2.048107m → SLOW 0.674758m → STOP 0.396788m, odom ZERO 유지 1.026194649초. **과거 결과를 신규 테스트 출력으로 사용하지 않습니다.**
- **학생 변경 코드:** 새 L2/L3 실제 실행 전에는 NOT_RUN입니다. 과거 수치에 맞게 테스트 출력을 창작하지 않습니다.

## 5. 잘못된 응답에 대한 교정 프롬프트

### A. AI가 "Fast DDS 근본 원인입니다"라고 단정할 때

~~~text
관측 사실과 추정을 구분해 다시 작성해 주세요.
현재 Run ID와 SHA에서 직접 확인된 동일 message pair의 source_gap_ms,
received_gap_ms, observer_gap_ms, publication seq 증거를 제시하세요.
없으면 UNKNOWN으로 남기고 DDS/Publisher/Executor 가설 각각에 대해
반증할 관측을 제시하세요. 원인 확정 또는 안전 TTL 완화는 금지합니다.
~~~

### B. 실행하지 않은 테스트를 PASS라 할 때

~~~text
실제 실행한 명령, 원본 stdout/stderr, exit code, Git SHA만 제시하세요.
실행 환경이나 도구가 없으면 NOT_RUN으로 정정하세요.
RED를 재현하려면 원본 accepted/runtime이 아닌 격리된 교육용 복사본을 쓰세요.
~~~

### C. CI 성공을 WSL2 L3 성공이라고 주장할 때

~~~text
성공본/실패본/학생 수정본을 서로 다른 행으로 분리하고,
L0/L1/L2/L3와 코드 SHA, Run ID를 각각 표시하세요.
Goal UUID terminal, odom ZERO, Nav ACK, Loc ACK, CM exit0을 별개로 평가하세요.
증거가 없다면 NOT_RUN, 근거 불충분은 INCONCLUSIVE, 전체 신규 인수는 HOLD입니다.
~~~

## 6. 학생 실습 절차

1. 52장 신판 워크북의 **U00~U13(슬라이드 14~41)**을 열고 이 문서 2절의 전체 프롬프트를 먼저 확인합니다.
2. 학생용 소스를 고정 SHA로 복제하고 출처 검사를 실행합니다.

~~~bash
git clone --single-branch --branch release/day02-dual-mvp-full-source-build-20261126 \
  https://github.com/silverbjin/axia-robot-safety-student.git ~/axia-day03-mvp
cd ~/axia-day03-mvp
git checkout --detach 96be43164fab3f15025edd59279bcfd50b6232cd
git rev-parse HEAD
python3 special_lecture/day02_mvp_sources/scripts/verify_dual_source.py
~~~

3. `CASE=development`로 U01~U05 개발 오류를 분석합니다. RED→GREEN을 수행한다면 **별도 학습용 복제본**의 진단 코드에만 적용합니다.
4. `CASE=integration`으로 U06~U10을 검토하며 Scan/RMW/Callback의 실측 증거를 분리합니다.
5. `CASE=acceptance`로 U11~U13 역사적 증거와 현재 미검증을 분리하고 Incident Card를 작성합니다.
6. 이 문서 Q01~Q16으로 AI 응답을 사람이 다시 검토한 뒤 90초 기술 브리핑을 수행합니다.

**주의:** 위 명령은 원본 소스 출처 L0를 검사할 뿐 새 ROS 노드·Gazebo·Goal을 실행하지 않습니다. 클론 디렉터리가 이미 있다면 새 경로를 사용하고 원본을 덮어쓰지 마십시오.

## 7. 증거 제출 템플릿

~~~markdown
# DAY 3 — Incident & Acceptance Card
- CASE:
- Student Git SHA:
- Source SHA / actual Run ID:
- Evidence paths / timestamp timebase:
- Prompt version:
- first_state_transition: UNKNOWN / source:
- first_timing_violation: UNKNOWN / source:
- final_exception: UNKNOWN / source:
- 사실 / 가설 / 반증:
- RED (명령/exit/stdout/SHA): NOT_RUN
- GREEN (명령/exit/stdout/SHA): NOT_RUN
- REFACTOR / REVIEW / COMMIT: NOT_RUN
- source_gap_ms: UNKNOWN
- received_gap_ms: UNKNOWN
- observer_gap_ms: UNKNOWN
- 안전 계층 타이밍 및 미검증 범위:
- 기존 성공 Run 44965035965: HISTORICAL 2/2 PASS, current test 아님
- 기존 실패 Run 44914827138: HISTORICAL 0/2 FAIL, current test 아님
- 현재 변경 SHA L0: NOT_RUN / L1: NOT_RUN / L2: NOT_RUN / L3: NOT_RUN
- Owner L3 과거 PASS_SCOPED / 원본 자동 HOLD 보존
- AI 응답 QA: Q01~Q16 (PASS/FAIL/UNVERIFIED)
- 전체 신규 인수: HOLD
- CERTIFIED_ESTOP=false
- 90초 브리핑: 증상 → 첫 경계 → 반증 → 수정/검증 → 미검증 → 판정
~~~

## 8. 근거 문서·검증 범위

- [실제 원본 마스터 프롬프트](MASTER_PROMPT_DAY3_MVP_KO.txt) — 이번 실행형 프롬프트의 기준 초안.
- [신판 워크북 슬라이드 목차](WORKBOOK_SLIDE_INDEX_KO.md) — Unit과 강의 장표의 연결.
- [DAY 3 상세 기획](DAY3_MVP_WORKBOOK_PLAN_KO.md).
- [완성·실패 MVP 전체 소스 안내](../day02_mvp_sources/README_KO.md).
- 실제 파일: `tools/p2_g07_health_first_boundary.py`, `tools/p2_g07_scan_rmw_first_pair.py`, `tools/p2_g07_ci_moving_goal_oracle.py`, `tools/p2_g07_ordered_shutdown.py`.
- [과거 성공 Public L2](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44965035965) 및 [실패 Public L2](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44914827138).

**이번 문서는 교육용 프롬프트와 응답 검수 기준을 제공할 뿐, 새 실물 Gazebo L2·Owner WSL2 L3를 실행하지 않았습니다. 신규 L2/L3=NOT_RUN.**
