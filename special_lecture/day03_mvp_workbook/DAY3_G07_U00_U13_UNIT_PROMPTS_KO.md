# AXIA DAY 3 — U00~U13 완전한 단위 실습 프롬프트

> 학생용 워크북과 함께 사용하는 **실행·응답 검수용** 자료입니다. 먼저 [마스터 프롬프트](DAY3_G07_MASTER_PROMPT_EXECUTION_AND_REVIEW_KO.md)를 한 번 읽고 각 단위를 진행합니다.
> 기본 권한은 read-only이며 원본 accepted/runtime과 안전 TTL/Goal 권한을 변경하지 않습니다.

## 공통 사용 규칙

- 현재 코드 SHA·Run ID·읽을 수 있는 파일·시간축을 먼저 제시하세요. AI가 실제로 확인하지 않은 자료는 UNKNOWN/NOT_RUN입니다.
- **모든 단계는 역사적 성공(2/2 L2), 역사적 실패(0/2 L2), 학생 수정본(새 L2/L3 NOT_RUN)을 분리**합니다.
- 수행 가능한 수정은 분리된 교육용 진단 복제본에만 제한하며, 실제 이동/안전 제어에 자동 영향 주지 않습니다.
- 완성된 안전 로직에 결함이 있다고 가정하지 않습니다. 학습용 RED→GREEN은 실습용 별도 복사본에서 수행합니다.

~~~mermaid
flowchart LR
    A["U00 출처"] --> B["U01~05 개발"]
    B --> C["U06~10 통합"]
    C --> D["U11~12 인수"]
    D --> E["U13 Incident Card"]
    E --> F["AI 응답 QA + 인간 승인"]
~~~

## U00 — SHA·증거 출처

- **WORKBOOK:** 52장 신판 워크북 슬라이드 14~15 (A: Result first / B: Complete Unit Prompt)
- **실제 확인 대상:** `DUAL_SOURCE_MANIFEST.json` (경로는 accepted/runtime 기준이며 파일 존재·정확한 파일 수준은 코드 조회로 확인)
- **프롬프트 작성 이유:** 서로 다른 Git SHA와 Run ID를 섞으면 뒤의 원인·인수 판정이 전부 잘못됩니다.

**복사 가능한 전체 단위 프롬프트**

~~~text
당신은 AXIA G07 완성 MVP를 다루는 증거 기반 ROS 2 디버깅 엔지니어입니다.
학생 소스 릴리스 SHA는 96be43164fab3f15025edd59279bcfd50b6232cd입니다.
현재 코드 SHA, Run ID, 실제 접근 가능한 파일과 시간축을 먼저 확인하십시오.
원본 accepted/runtime 불변, 무단 Goal/Fault Injection/TTL 변경 금지,
인증 E-Stop 주장 금지, 신규 L2/L3 검증 전 NOT_RUN, 필요한 경우 HOLD를 지킵니다.
요청: 성공 런타임과 실패 런타임의 정확한 소스 SHA, 전체 릴리스 SHA, 각각의 역사적 L2 Run ID, 현재 worktree SHA를 표로 작성하십시오. 파일을 직접 열어 확인한 필드와 보지 못한 항목을 구분하십시오. 현재 실행 로그가 없으면 UNKNOWN이라고 기입하십시오. 과거 Owner PASS_SCOPED와 자동 HOLD 원본을 모두 표시하십시오.
출력: 확인한 사실, 소스 코드 경로, 아직 모르는 부분, 다음 안전한 읽기 전용 명령,
      실행한 테스트 결과(stdout/stderr/exit code), 검증 수준을 구별하십시오.
~~~

**AI 응답 검수:** 각 숫자가 어느 SHA/Run ID를 근거로 하는지 확인하며 2/2 PASS·0/2 FAIL을 한 실행으로 합치지 않았는지 봅니다.

**다시 질문:**

~~~text
결과표에서 출처가 비어 있는 행만 다시 뽑아주세요. 채우지 못한 필드는 UNKNOWN으로 유지하세요.
~~~

---

## U01 — 네 패키지의 책임

- **WORKBOOK:** 52장 신판 워크북 슬라이드 16~17 (A: Result first / B: Complete Unit Prompt)
- **실제 확인 대상:** `ros2_ws/src/{axia_fault_injector,axia_safety_bringup,axia_safety_supervisor,axia_scenario_verifier}` (경로는 accepted/runtime 기준이며 파일 존재·정확한 파일 수준은 코드 조회로 확인)
- **프롬프트 작성 이유:** Node/Topic을 구별해야 이후 오류의 담당 계층을 정확히 지정할 수 있습니다.

**복사 가능한 전체 단위 프롬프트**

~~~text
당신은 AXIA G07 완성 MVP를 다루는 증거 기반 ROS 2 디버깅 엔지니어입니다.
학생 소스 릴리스 SHA는 96be43164fab3f15025edd59279bcfd50b6232cd입니다.
현재 코드 SHA, Run ID, 실제 접근 가능한 파일과 시간축을 먼저 확인하십시오.
원본 accepted/runtime 불변, 무단 Goal/Fault Injection/TTL 변경 금지,
인증 E-Stop 주장 금지, 신규 L2/L3 검증 전 NOT_RUN, 필요한 경우 HOLD를 지킵니다.
요청: 네 ROS 2 패키지 각각의 package.xml과 실제 Python Node/launch를 읽어 패키지→Node→Subscriber/Publisher→처리 함수→출력·검증 결과를 표로 작성하십시오. 실제로 확인하지 못한 연결은 미확인으로 적고 그림만으로 존재한다고 주장하지 마십시오.
출력: 확인한 사실, 소스 코드 경로, 아직 모르는 부분, 다음 안전한 읽기 전용 명령,
      실행한 테스트 결과(stdout/stderr/exit code), 검증 수준을 구별하십시오.
~~~

**AI 응답 검수:** 4개 패키지와 실제 함수/토픽 인용이 일치하는지, 공식 Nav2와 자체 패키지를 혼동하지 않았는지 검토합니다.

**다시 질문:**

~~~text
출처가 없는 Node/Topic만 추려 코드 경로를 붙이거나 '미확인'으로 고쳐주세요.
~~~

---

## U02 — 최초 HEALTH 전이

- **WORKBOOK:** 52장 신판 워크북 슬라이드 18~19 (A: Result first / B: Complete Unit Prompt)
- **실제 확인 대상:** `tools/p2_g07_health_first_boundary.py` (경로는 accepted/runtime 기준이며 파일 존재·정확한 파일 수준은 코드 조회로 확인)
- **프롬프트 작성 이유:** 마지막 타임아웃보다 처음 준비 상태가 막힌 이유가 해결 우선순위를 결정합니다.

**복사 가능한 전체 단위 프롬프트**

~~~text
당신은 AXIA G07 완성 MVP를 다루는 증거 기반 ROS 2 디버깅 엔지니어입니다.
학생 소스 릴리스 SHA는 96be43164fab3f15025edd59279bcfd50b6232cd입니다.
현재 코드 SHA, Run ID, 실제 접근 가능한 파일과 시간축을 먼저 확인하십시오.
원본 accepted/runtime 불변, 무단 Goal/Fault Injection/TTL 변경 금지,
인증 E-Stop 주장 금지, 신규 L2/L3 검증 전 NOT_RUN, 필요한 경우 HOLD를 지킵니다.
요청: HealthFirstBoundary.record/result의 동작을 설명하고 first_readiness_blockers와 first_state_transition을 서로 구분하십시오. 코드에서 진단 release=HOLD인 사실을 확인하십시오. 최초 상태 전이는 반드시 안전 오류가 아니므로 사건·위반으로 단정하지 마십시오. 재현 가능한 기록이 없으면 UNKNOWN.
출력: 확인한 사실, 소스 코드 경로, 아직 모르는 부분, 다음 안전한 읽기 전용 명령,
      실행한 테스트 결과(stdout/stderr/exit code), 검증 수준을 구별하십시오.
~~~

**AI 응답 검수:** first_state_transition과 최초 blocker가 혼합되지 않았는지, 읽기 전용 진단을 PASS로 오해하지 않았는지 확인합니다.

**다시 질문:**

~~~text
최초 sample, 첫 상태 변화, 최종 결과를 서로 다른 칸으로 나눠서 다시 출력해 주세요.
~~~

---

## U03 — RED 반례 설계

- **WORKBOOK:** 52장 신판 워크북 슬라이드 20~21 (A: Result first / B: Complete Unit Prompt)
- **실제 확인 대상:** `tools/test_g07_health_first_boundary.py` (경로는 accepted/runtime 기준이며 파일 존재·정확한 파일 수준은 코드 조회로 확인)
- **프롬프트 작성 이유:** 실패를 테스트로 먼저 고정해야 수정이 실제로 문제를 해결했는지 증명할 수 있습니다.

**복사 가능한 전체 단위 프롬프트**

~~~text
당신은 AXIA G07 완성 MVP를 다루는 증거 기반 ROS 2 디버깅 엔지니어입니다.
학생 소스 릴리스 SHA는 96be43164fab3f15025edd59279bcfd50b6232cd입니다.
현재 코드 SHA, Run ID, 실제 접근 가능한 파일과 시간축을 먼저 확인하십시오.
원본 accepted/runtime 불변, 무단 Goal/Fault Injection/TTL 변경 금지,
인증 E-Stop 주장 금지, 신규 L2/L3 검증 전 NOT_RUN, 필요한 경우 HOLD를 지킵니다.
요청: 완성된 기존 코드의 테스트 계약을 먼저 열어 분석하십시오. 별도의 학습용 진단 코드 복제본에 대해서만 최소 반례를 제시하고, 어떤 assert가 왜 RED여야 하는지 설명하십시오. 기존 완성본에 결함이 있다고 가정하거나 안전 런타임에 Fault Injection하지 마십시오. 실행되지 않은 테스트는 NOT_RUN.
출력: 확인한 사실, 소스 코드 경로, 아직 모르는 부분, 다음 안전한 읽기 전용 명령,
      실행한 테스트 결과(stdout/stderr/exit code), 검증 수준을 구별하십시오.
~~~

**AI 응답 검수:** RED의 기대 실패 이유와 실제 stderr·exit code가 같은지 확인합니다. 원본 코드 불변을 점검합니다.

**다시 질문:**

~~~text
성공해야 하는 기존 테스트를 임의로 실패시키지 말고, 교육용 격리 복제본에서의 계약 위반만 제안해 주세요.
~~~

---

## U04 — GREEN 최소 수정

- **WORKBOOK:** 52장 신판 워크북 슬라이드 22~23 (A: Result first / B: Complete Unit Prompt)
- **실제 확인 대상:** `tools/p2_g07_health_first_boundary.py` (경로는 accepted/runtime 기준이며 파일 존재·정확한 파일 수준은 코드 조회로 확인)
- **프롬프트 작성 이유:** RED와 같은 검증 조건을 사용해야 수정 효과가 드러납니다.

**복사 가능한 전체 단위 프롬프트**

~~~text
당신은 AXIA G07 완성 MVP를 다루는 증거 기반 ROS 2 디버깅 엔지니어입니다.
학생 소스 릴리스 SHA는 96be43164fab3f15025edd59279bcfd50b6232cd입니다.
현재 코드 SHA, Run ID, 실제 접근 가능한 파일과 시간축을 먼저 확인하십시오.
원본 accepted/runtime 불변, 무단 Goal/Fault Injection/TTL 변경 금지,
인증 E-Stop 주장 금지, 신규 L2/L3 검증 전 NOT_RUN, 필요한 경우 HOLD를 지킵니다.
요청: 앞서 수집한 RED 반례와 동일한 입력·테스트명으로 GREEN을 확인하십시오. 수정은 학습용 복제본의 진단 모듈에만 제한하고 변경 전후 diff, 실제 실행 명령과 stdout/stderr·exit code를 제시하십시오. 새 안전 동작을 만들거나 TTL을 바꾸지 마십시오.
출력: 확인한 사실, 소스 코드 경로, 아직 모르는 부분, 다음 안전한 읽기 전용 명령,
      실행한 테스트 결과(stdout/stderr/exit code), 검증 수준을 구별하십시오.
~~~

**AI 응답 검수:** 실제 GREEN이 수행됐는지, RED와 동일 조건인지, 새 코드가 실패를 숨기거나 판정을 무조건 PASS로 만들지 않았는지 봅니다.

**다시 질문:**

~~~text
테스트 실행 증거가 없다면 PASS 단정을 취소하고 'NOT_RUN + 필요한 실행 명령'으로 바꿔주세요.
~~~

---

## U05 — REFACTOR·REVIEW·COMMIT

- **WORKBOOK:** 52장 신판 워크북 슬라이드 24~25 (A: Result first / B: Complete Unit Prompt)
- **실제 확인 대상:** `git diff / unittest / git status` (경로는 accepted/runtime 기준이며 파일 존재·정확한 파일 수준은 코드 조회로 확인)
- **프롬프트 작성 이유:** 수정 사실뿐 아니라 최소 변경과 회귀를 동료가 재검증할 수 있어야 합니다.

**복사 가능한 전체 단위 프롬프트**

~~~text
당신은 AXIA G07 완성 MVP를 다루는 증거 기반 ROS 2 디버깅 엔지니어입니다.
학생 소스 릴리스 SHA는 96be43164fab3f15025edd59279bcfd50b6232cd입니다.
현재 코드 SHA, Run ID, 실제 접근 가능한 파일과 시간축을 먼저 확인하십시오.
원본 accepted/runtime 불변, 무단 Goal/Fault Injection/TTL 변경 금지,
인증 E-Stop 주장 금지, 신규 L2/L3 검증 전 NOT_RUN, 필요한 경우 HOLD를 지킵니다.
요청: 개인 학습 브랜치의 진단 코드 diff만 REVIEW하십시오. RED→GREEN 결과를 보존하고 REFACTOR 후 같은 테스트 재실행 결과, 파일 범위, git status, 커밋 SHA를 보고하십시오. accepted/runtime이나 main에는 변경하지 마십시오. 수행하지 못한 Git 작업은 NOT_RUN.
출력: 확인한 사실, 소스 코드 경로, 아직 모르는 부분, 다음 안전한 읽기 전용 명령,
      실행한 테스트 결과(stdout/stderr/exit code), 검증 수준을 구별하십시오.
~~~

**AI 응답 검수:** 원본 안전 파일 미변경, 테스트 출력 원본, Git SHA, 리뷰 지적과 조치가 존재하는지 확인합니다.

**다시 질문:**

~~~text
결과에서 '완료'로 표시했지만 명령/commit SHA가 없는 단계를 전부 NOT_RUN으로 고쳐주세요.
~~~

---

## U06 — /scan과 /safety/scan

- **WORKBOOK:** 52장 신판 워크북 슬라이드 26~27 (A: Result first / B: Complete Unit Prompt)
- **실제 확인 대상:** `fault_injector_node.py / launch / configs` (경로는 accepted/runtime 기준이며 파일 존재·정확한 파일 수준은 코드 조회로 확인)
- **프롬프트 작성 이유:** 리레이된 안전 센서 입력과 원본 센서 입력을 혼동하면 잘못된 노드를 수정하게 됩니다.

**복사 가능한 전체 단위 프롬프트**

~~~text
당신은 AXIA G07 완성 MVP를 다루는 증거 기반 ROS 2 디버깅 엔지니어입니다.
학생 소스 릴리스 SHA는 96be43164fab3f15025edd59279bcfd50b6232cd입니다.
현재 코드 SHA, Run ID, 실제 접근 가능한 파일과 시간축을 먼저 확인하십시오.
원본 accepted/runtime 불변, 무단 Goal/Fault Injection/TTL 변경 금지,
인증 E-Stop 주장 금지, 신규 L2/L3 검증 전 NOT_RUN, 필요한 경우 HOLD를 지킵니다.
요청: 실제 Fault Injector가 구독하는 LaserScan 토픽과 발행하는 토픽, QoS, 발행 주체, 서비스를 코드로 찾아 설명하십시오. Gazebo→bridge→/scan→injector→/safety/scan 그래프를 실제 설정과 대조하고 모르는 구간을 UNVERIFIED로 표시하십시오. Default Fault Injection 비활성 계약도 확인하십시오.
출력: 확인한 사실, 소스 코드 경로, 아직 모르는 부분, 다음 안전한 읽기 전용 명령,
      실행한 테스트 결과(stdout/stderr/exit code), 검증 수준을 구별하십시오.
~~~

**AI 응답 검수:** 원본과 릴레이 양쪽을 같은 Publisher로 취급하지 않았는지, launch 확인 없는 임의 연결이 없는지 검토합니다.

**다시 질문:**

~~~text
다이어그램의 각 화살표에 확인한 코드 경로/토픽을 붙이고 확인하지 않은 간선은 점선으로 바꿔주세요.
~~~

---

## U07 — RMW·Callback 시각 구분

- **WORKBOOK:** 52장 신판 워크북 슬라이드 28~29 (A: Result first / B: Complete Unit Prompt)
- **실제 확인 대상:** `tools/p2_g07_scan_rmw_first_pair.py` (경로는 accepted/runtime 기준이며 파일 존재·정확한 파일 수준은 코드 조회로 확인)
- **프롬프트 작성 이유:** 서로 다른 수신 위치와 시간축의 숫자를 섞으면 잘못된 병목 원인이 나옵니다.

**복사 가능한 전체 단위 프롬프트**

~~~text
당신은 AXIA G07 완성 MVP를 다루는 증거 기반 ROS 2 디버깅 엔지니어입니다.
학생 소스 릴리스 SHA는 96be43164fab3f15025edd59279bcfd50b6232cd입니다.
현재 코드 SHA, Run ID, 실제 접근 가능한 파일과 시간축을 먼저 확인하십시오.
원본 accepted/runtime 불변, 무단 Goal/Fault Injection/TTL 변경 금지,
인증 E-Stop 주장 금지, 신규 L2/L3 검증 전 NOT_RUN, 필요한 경우 HOLD를 지킵니다.
요청: normalize_scan_message_info와 first_scan_rmw_pair를 실제 코드로 읽고 source_gap_ms, received_gap_ms, observer_gap_ms, header_sim_gap_ms를 정의하십시오. 동일 publication seq의 두 메시지, 일치하는 topic과 header/host 관측 조건을 확인하십시오. 연속 메시지 간격과 단일 메시지의 transit latency를 구별하십시오. RMW 메타데이터 부족이면 HOLD.
출력: 확인한 사실, 소스 코드 경로, 아직 모르는 부분, 다음 안전한 읽기 전용 명령,
      실행한 테스트 결과(stdout/stderr/exit code), 검증 수준을 구별하십시오.
~~~

**AI 응답 검수:** 다른 timebase의 절대 시각을 직접 빼지 않았는지, seq 연속성을 확인했는지, 누락값을 꾸미지 않았는지 봅니다.

**다시 질문:**

~~~text
관측된 네 gap마다 두 원본 timestamp·timebase·seq를 붙여 다시 작성해 주세요.
~~~

---

## U08 — 최초 TTL 위반

- **WORKBOOK:** 52장 신판 워크북 슬라이드 30~31 (A: Result first / B: Complete Unit Prompt)
- **실제 확인 대상:** `tools/p2_g07_ci_moving_goal_oracle.py` (경로는 accepted/runtime 기준이며 파일 존재·정확한 파일 수준은 코드 조회로 확인)
- **프롬프트 작성 이유:** 최대/평균 시간만 보면 로봇이 언제 처음 안전 경계를 넘었는지 놓칩니다.

**복사 가능한 전체 단위 프롬프트**

~~~text
당신은 AXIA G07 완성 MVP를 다루는 증거 기반 ROS 2 디버깅 엔지니어입니다.
학생 소스 릴리스 SHA는 96be43164fab3f15025edd59279bcfd50b6232cd입니다.
현재 코드 SHA, Run ID, 실제 접근 가능한 파일과 시간축을 먼저 확인하십시오.
원본 accepted/runtime 불변, 무단 Goal/Fault Injection/TTL 변경 금지,
인증 E-Stop 주장 금지, 신규 L2/L3 검증 전 NOT_RUN, 필요한 경우 HOLD를 지킵니다.
요청: first_delivery_breach와 first_pre_latch_delivery_timing의 실제 입력 창(start/end), limit, 반환 first_timing_violation을 분석하십시오. first_state_transition과 first_timing_violation, final exception을 각각 분리하고 PRE_GOAL/POST_GOAL 사건을 다른 창으로 다루십시오. 기준 연산자의 > 또는 >=는 실제 구현을 확인하십시오.
출력: 확인한 사실, 소스 코드 경로, 아직 모르는 부분, 다음 안전한 읽기 전용 명령,
      실행한 테스트 결과(stdout/stderr/exit code), 검증 수준을 구별하십시오.
~~~

**AI 응답 검수:** 위반 시점·관측 timestamp·주기·기준이 각각 어떤 단위인지, Run 간 섞임이 없는지 확인합니다.

**다시 질문:**

~~~text
평균/최댓값 설명 대신 최초 위반 행과 첫 상태변화 행을 시간축별로 분리해 주세요.
~~~

---

## U09 — 가설과 반증

- **WORKBOOK:** 52장 신판 워크북 슬라이드 32~33 (A: Result first / B: Complete Unit Prompt)
- **실제 확인 대상:** `tools/test_g07_scan_rmw_first_pair.py` (경로는 accepted/runtime 기준이며 파일 존재·정확한 파일 수준은 코드 조회로 확인)
- **프롬프트 작성 이유:** 추측을 반증 가능하도록 만들어야 현장 재시도 반복을 줄일 수 있습니다.

**복사 가능한 전체 단위 프롬프트**

~~~text
당신은 AXIA G07 완성 MVP를 다루는 증거 기반 ROS 2 디버깅 엔지니어입니다.
학생 소스 릴리스 SHA는 96be43164fab3f15025edd59279bcfd50b6232cd입니다.
현재 코드 SHA, Run ID, 실제 접근 가능한 파일과 시간축을 먼저 확인하십시오.
원본 accepted/runtime 불변, 무단 Goal/Fault Injection/TTL 변경 금지,
인증 E-Stop 주장 금지, 신규 L2/L3 검증 전 NOT_RUN, 필요한 경우 HOLD를 지킵니다.
요청: 관측된 간격 데이터가 가리킬 수 있는 Publisher, RMW subscriber, Executor/Callback 등 원인 가설을 최대 세 개 제시하십시오. 각각 지지 사실, 반증 가능한 다음 읽기 전용 관측, 원인 미확정 이유를 쓰십시오. 실제 메타데이터가 없으면 DDS 근본 원인을 UNDETERMINED라고 보고하십시오.
출력: 확인한 사실, 소스 코드 경로, 아직 모르는 부분, 다음 안전한 읽기 전용 명령,
      실행한 테스트 결과(stdout/stderr/exit code), 검증 수준을 구별하십시오.
~~~

**AI 응답 검수:** 가설과 관측 사실이 분리되어 있고, '어떤 결과가 나오면 기각'이 구체적인지 확인합니다.

**다시 질문:**

~~~text
근거 없는 근본 원인 단정 문장을 삭제하고 반증 관측이 있는 가설표로 교체해 주세요.
~~~

---

## U10 — CM→Guard 경계

- **WORKBOOK:** 52장 신판 워크북 슬라이드 34~35 (A: Result first / B: Complete Unit Prompt)
- **실제 확인 대상:** `p2_g07_ci_moving_goal_oracle.py / p2_base_guard_node.py` (경로는 accepted/runtime 기준이며 파일 존재·정확한 파일 수준은 코드 조회로 확인)
- **프롬프트 작성 이유:** 한 노드의 정상 수신 주기가 다른 노드의 TTL 만족을 보장하지 않습니다.

**복사 가능한 전체 단위 프롬프트**

~~~text
당신은 AXIA G07 완성 MVP를 다루는 증거 기반 ROS 2 디버깅 엔지니어입니다.
학생 소스 릴리스 SHA는 96be43164fab3f15025edd59279bcfd50b6232cd입니다.
현재 코드 SHA, Run ID, 실제 접근 가능한 파일과 시간축을 먼저 확인하십시오.
원본 accepted/runtime 불변, 무단 Goal/Fault Injection/TTL 변경 금지,
인증 E-Stop 주장 금지, 신규 L2/L3 검증 전 NOT_RUN, 필요한 경우 HOLD를 지킵니다.
요청: CM Publisher 또는 독립 Observer와 Guard 내부 Subscriber의 CM 수신 시간/TTL을 분리하십시오. 실제 Guard 래치·수신 간격과 Observer 시점이 다른 위치임을 보고하고, CM 전달 120ms와 Guard age 150ms의 적용 범위를 각각 확인하십시오. 한 계층 수치가 PASS여도 전체 안전계층 검증은 UNVERIFIED일 수 있습니다.
출력: 확인한 사실, 소스 코드 경로, 아직 모르는 부분, 다음 안전한 읽기 전용 명령,
      실행한 테스트 결과(stdout/stderr/exit code), 검증 수준을 구별하십시오.
~~~

**AI 응답 검수:** Observer=Guard로 가정했는지, 단일 경계 PASS를 전체 인수로 확대했는지 검토합니다.

**다시 질문:**

~~~text
CM Publisher→Observer와 CM Publisher→Guard를 별개의 관측 경로로 다시 그려주세요.
~~~

---

## U11 — Goal UUID·Shutdown ACK

- **WORKBOOK:** 52장 신판 워크북 슬라이드 36~37 (A: Result first / B: Complete Unit Prompt)
- **실제 확인 대상:** `tools/p2_g07_ordered_shutdown.py / shutdown audit` (경로는 accepted/runtime 기준이며 파일 존재·정확한 파일 수준은 코드 조회로 확인)
- **프롬프트 작성 이유:** 요청 성공과 실제 종료 증거는 다른 계약입니다.

**복사 가능한 전체 단위 프롬프트**

~~~text
당신은 AXIA G07 완성 MVP를 다루는 증거 기반 ROS 2 디버깅 엔지니어입니다.
학생 소스 릴리스 SHA는 96be43164fab3f15025edd59279bcfd50b6232cd입니다.
현재 코드 SHA, Run ID, 실제 접근 가능한 파일과 시간축을 먼저 확인하십시오.
원본 accepted/runtime 불변, 무단 Goal/Fault Injection/TTL 변경 금지,
인증 E-Stop 주장 금지, 신규 L2/L3 검증 전 NOT_RUN, 필요한 경우 HOLD를 지킵니다.
요청: Goal UUID terminal CANCELED(5), 동일 UUID Cancel ACK, /odom ZERO ≥1s, Navigation/Localization 관리 ACK, CM 프로세스 exit0, clean shutdown의 실제 증거를 독립 체크하십시오. Ordered shutdown 코드에서 ACK가 CM exit0 자체를 증명하지 않는다는 점을 명시하십시오. 누락된 항목은 NOT_RUN/INCONCLUSIVE.
출력: 확인한 사실, 소스 코드 경로, 아직 모르는 부분, 다음 안전한 읽기 전용 명령,
      실행한 테스트 결과(stdout/stderr/exit code), 검증 수준을 구별하십시오.
~~~

**AI 응답 검수:** 취소 응답만으로 정지했다고 하지 않았는지, Nav ACK만으로 CM 정상 종료라고 하지 않았는지 봅니다.

**다시 질문:**

~~~text
단계별 '요청/ACK/실제 프로세스 종료/odom' 네 열로 분리해 주세요.
~~~

---

## U12 — L0~L3와 인수 범위

- **WORKBOOK:** 52장 신판 워크북 슬라이드 38~39 (A: Result first / B: Complete Unit Prompt)
- **실제 확인 대상:** `DUAL_SOURCE_MANIFEST.json / Public CI Runs` (경로는 accepted/runtime 기준이며 파일 존재·정확한 파일 수준은 코드 조회로 확인)
- **프롬프트 작성 이유:** 교육용 테스트 PASS는 Owner 실제 Gazebo 인수의 대체물이 아닙니다.

**복사 가능한 전체 단위 프롬프트**

~~~text
당신은 AXIA G07 완성 MVP를 다루는 증거 기반 ROS 2 디버깅 엔지니어입니다.
학생 소스 릴리스 SHA는 96be43164fab3f15025edd59279bcfd50b6232cd입니다.
현재 코드 SHA, Run ID, 실제 접근 가능한 파일과 시간축을 먼저 확인하십시오.
원본 accepted/runtime 불변, 무단 Goal/Fault Injection/TTL 변경 금지,
인증 E-Stop 주장 금지, 신규 L2/L3 검증 전 NOT_RUN, 필요한 경우 HOLD를 지킵니다.
요청: 원본 성공 Public L2 Run 44965035965와 실패 Run 44914827138, 과거 Owner PASS_SCOPED, 현재 학생 변경 SHA의 L0~L3를 서로 다른 행에 작성하십시오. 실제 실행하지 않은 레벨은 NOT_RUN으로 두고 자동 HOLD_RAW_REVIEW_AND_VISUAL_PENDING 기록을 변경하지 마십시오. CI PASS가 검증한 실제 시연 조건을 열로 표시하십시오.
출력: 확인한 사실, 소스 코드 경로, 아직 모르는 부분, 다음 안전한 읽기 전용 명령,
      실행한 테스트 결과(stdout/stderr/exit code), 검증 수준을 구별하십시오.
~~~

**AI 응답 검수:** 기존 PASS를 새 SHA의 PASS로 전이하지 않았는지, Owner 화면 콘텐츠 독립 검수 한계를 남겼는지 검토합니다.

**다시 질문:**

~~~text
각 PASS 오른쪽에 정확한 source SHA/Run ID/검증조건을 붙이고 없는 것은 NOT_RUN으로 정정해 주세요.
~~~

---

## U13 — Incident Card·90초 설명

- **WORKBOOK:** 52장 신판 워크북 슬라이드 40~41 (A: Result first / B: Complete Unit Prompt)
- **실제 확인 대상:** `WORKBOOK / Evidence Manifest` (경로는 accepted/runtime 기준이며 파일 존재·정확한 파일 수준은 코드 조회로 확인)
- **프롬프트 작성 이유:** 분석이 끝난 뒤 누가 보더라도 재현 가능한 결론과 인수 범위를 전달해야 합니다.

**복사 가능한 전체 단위 프롬프트**

~~~text
당신은 AXIA G07 완성 MVP를 다루는 증거 기반 ROS 2 디버깅 엔지니어입니다.
학생 소스 릴리스 SHA는 96be43164fab3f15025edd59279bcfd50b6232cd입니다.
현재 코드 SHA, Run ID, 실제 접근 가능한 파일과 시간축을 먼저 확인하십시오.
원본 accepted/runtime 불변, 무단 Goal/Fault Injection/TTL 변경 금지,
인증 E-Stop 주장 금지, 신규 L2/L3 검증 전 NOT_RUN, 필요한 경우 HOLD를 지킵니다.
요청: 앞선 U00~U12 결과를 한 장의 Incident & Acceptance Card로 조립하십시오. 사건·첫 상태 전이·첫 TTL 위반·근거·반증·수정 내용·실제 RED/GREEN·미검증 안전 경계·현재 HOLD 판정 및 증거 링크를 포함하고, 90초 발표 스크립트를 작성하십시오. 누락 데이터는 UNKNOWN이며 CERTIFIED_ESTOP=false입니다.
출력: 확인한 사실, 소스 코드 경로, 아직 모르는 부분, 다음 안전한 읽기 전용 명령,
      실행한 테스트 결과(stdout/stderr/exit code), 검증 수준을 구별하십시오.
~~~

**AI 응답 검수:** 본문과 증거 Manifest의 SHA·Run·수치·판정 일치, 근본 원인 과장, 현장 신규 인수 주장 여부를 검토합니다.

**다시 질문:**

~~~text
근거 없는 결론을 지우고 '관측 사실/남은 반증/다음 게이트'로 마무리 문단을 다시 작성해 주세요.
~~~

---

## 통합 미션 수행 순서

**개발:** U00→U05에서 출처·첫 상태 전이·별도 진단 복제본의 RED/GREEN 및 Git diff를 확인합니다.  
**통합:** U06→U10에서 publisher/relay/subscriber 경로와 RMW/Callback/TLL 경계를 재구성합니다.  
**인수:** U11→U13에서 Goal UUID·Lifecycle·CM exit0·L0~L3를 분리하고 최종 Incident Card를 작성합니다.

## 학생 최종 검토 항목

| 단계 | 필수 제출 증거 | 누락 시 |
|---|---|---|
| 개발 | 입력 파일 SHA, 실제 RED/GREEN 명령 및 stdout/exit | NOT_RUN / HOLD |
| 통합 | 코드 기반 Node/Topic 그래프, first_state_transition과 first_timing_violation, 동일 seq/timebase 비교 | INCONCLUSIVE |
| 인수 | 역사적/현재 SHA·Run 분리, L0/L1/L2/L3, Goal UUID, Nav/Loc ACK, CM exit0, Odom ZERO | HOLD |
| 공통 | 안전 기준 불변, 비공개 정답 제외, CERTIFIED_ESTOP=false | 공개 불가 / 미인수 |

**주의:** 이 문서는 프롬프트와 검수법을 제공하는 교육 자료입니다. 새 Gazebo L2/Owner WSL2 L3는 수행하지 않았으며 NOT_RUN입니다. 실제 실행 증거를 만들어내지 마십시오.
