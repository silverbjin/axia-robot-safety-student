# AXIA D03 v3 — P1 학생 공유형 실습 설계

- 버전/브랜치: D03_v3 (student public repository)
- 설계 기준: AXIA D3 v3 3시간/24장 강의 기획서, P1 Baseline Scenario Acceptance v1
- 런타임: Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic + Nav2 + TurtleBot3 Waffle
- 목적: Diagnostics 해석 → 교육용 Safe Mode 판단 → 실제 시뮬레이션 사건 관측 → 운영자 대응
- 범위: 교육용 Waffle 시뮬레이션. 사람 인식, 실물/인증 E-Stop, 안전 인증 시험 제외

## 1. 최소 개발 범위 확정

| 구분 | 제공 항목 | 학생 수정 여부 |
|---|---|---|
| 공식 TB3/Nav2/Harmonic | 로컬 설치된 기존 공식 패키지 이용, 재구현 없음 | 아니요 |
| P1 런타임 | axia_safety_supervisor, axia_fault_injector, axia_scenario_verifier, P1 launch/config overlay | 아니요 |
| D3 시연 | 기존 axia_d3_demo의 SDF proxy, stage/scene, observer, evidence oracle | 아니요 |
| D03 학생 과제 | block_A/day03/p1_adapter_todo.py, block_A/day03/todo_safety.py | **예, 두 함수만** |
| 학생 실행 도구 | block_A/day03/v3/scripts/classroom.sh → classroom.py | 아니요 |
| 강사 전용 | Reference 정답·비공개 채점·원본 인수 증거·인증정보 | 공개하지 않음 |

P1 ROS 2 소스 45개는 Instructor의 **0be687ee033233fcd53be1190e0b2f9e86730fc9**에서 범위를 선정했다.
학생 저장소 안의 P1_RUNTIME_SOURCE_MANIFEST.json에 각 파일 Git blob SHA를 기록하고 공개 CI에서 byte-for-byte 확인한다.
학생 TODO는 미구현으로 유지하여 정답 누출을 방지한다.

## 2. 시스템 제어와 관측의 분리

~~~
[Nav2 승인된 Goal] → [P1 Safety Supervisor FSM / Command Gate]
  → [Nav2 Collision Monitor] → [Gazebo Waffle]
                         ↑             ↓ raw scan + odom
       [P1 Fault Injector /safety/scan relay]

[P1 /axia/safety/state] → [학생 Diagnostics Adapter + ROS Bridge] → /diagnostics
[P1 state, fault status, diagnostics, odom] → [D3 Observer] → JSONL 증거
[학생 Safe Mode 순수함수] → 판정 후보 (P1 제어 권한 없음)
[교육용 Gazebo proxy] → 인간 형태의 moving geometry (인체 모델 인증 아님)
~~~

실제 P1 정지 판단은 기존 Safety Supervisor의 책임이다. D03 학생 함수는 모니터링과 보수적 모드 **후보**를 반환하며 /cmd_vel, Nav2 Goal, Cancel, Reset/Rearm을 발행할 수 없다.
Gazebo Collision Monitor는 소프트웨어 보호기능이고 인증 하드웨어 E-Stop이 아니다.

## 3. 실습 5개 / 180분 / 24 슬라이드

1. S07–S09 (35–55분): P1 Waffle 실행과 정상 주행 기준선. 학생에게 제공한 P1 런타임의 TF/Nav2 lifecycle/상태를 점검.
2. S10–S12 (55–80분): diagnose_p1_state()를 RED→GREEN 구현. JSON state/health → level 0/1/2/3. Bridge /diagnostics 관측.
3. S13–S15 (80–105분): assess_diagnostic()을 RED→GREEN. SW STOP 우선, stale/invalid fail-closed, recovery latch. 9건 합성 재생.
4. S16–S18 (115–145분): Gazebo proxy를 8단계 이동, GUI에서 직접 확인; 장애물 선행 정지와 센서 고장 원인을 구분.
5. S19–S24 (145–180분): 명시적 P1 Goal Owner 승인 후 기존 scan_drop 한 번, P1 FSM + diagnostic ERROR + odom 정지(1초) + HOLD/END, 원인 분석 보고.

앞의 0–35분은 도입, 아키텍처, 안전 경계; 105–115분은 휴식.

## 4. 학생 실행기 계약

- 진입점: bash block_A/day03/v3/scripts/classroom.sh {session|prepare|preflight|route|launch|preview|remove-proxy|bridge|live|verify|new-evidence|status}
- 스크립트는 **자식 프로세스로만 실행**: 상위 대화형 셸을 set -e로 종료시키지 않음
- 기존 작업 디렉터리와 기존 브랜치를 지우거나 강제 reset하지 않음. 학생 저장소는 D03_v3만 별도 Clone
- session은 최초 1회 생성 후 재사용, 환경변수를 격리된 홈 폴더의 0600 파일에 저장
- route는 world 식별자, 경로 거리 0.3–3.0m, 좌표 [-15,15]의 형식·범위를 검사하나 충돌 없는 경로는 보증하지 않음
- prepare는 **빌드/패키지 확인만** 수행, Goal/Fault는 호출하지 않음
- launch는 Gazebo 실행 승인(YES-D3-SIM)만, Goal은 보내지 않음
- preview는 인간형 프록시만 움직임(YES-D3-PREVIEW), Fault 없음
- live는 학생 mapper 공개 GREEN, P1 state / odom, 실제 world 서비스, 깨끗한 새 증거, Goal Owner의 **선행 승인된 정상 주행**이 없으면 차단
- live에서는 시뮬레이션 승인(YES-D3-SIM)과 fault 승인(YES-D3-FAULT)을 **각각** 입력받음
- live는 별도 ROS Bridge와 observer를 구동한 뒤 기존 d3_scene으로 proxy 이동·scan_drop 호출. P1 goal/start/reset/rearm은 호출하지 않음
- 증거는 학생 개인 홈 폴더에만 남고 재시연 때 new-evidence로 분리; Fault/Stop은 자동 해제하지 않음
- verify는 교육용 이벤트 순서만 확인. 불충분하거나 역순이면 INCONCLUSIVE/INVALID_EVIDENCE

## 5. 테스트-인수 게이트

| 단계 | 확인 | 수준 |
|---|---|---|
| RED | 새 배포 파일 없을 때 public CI 실패 | 실제 실행 로그 |
| GREEN | manifest 45개 blob, 세션·경로·보호·쉘 파싱·문서·기존 TODO 보존 | GitHub Actions ROS-free |
| REFACTOR | 소스 SHA 고정, 래퍼 1곳, 코드 경로 분리, 새 evidence 정책 | 코드 정적 검토 |
| REVIEW | 학습 경로·비공개 정답 미포함·Fault 승인 독립성 확인 | GitHub 변경사항 검토 |
| COMMIT | 공개 Student의 D03_v3 브랜치만 | main 병합 금지 |

**ROS-free CI와 실기 시험은 별개**다. ROS2 실제 colcon 빌드, TF/Nav2 정상 주행, Gazebo 프록시의 GUI 이동, Fault→Supervisor→진단→odom 관측은 강사 WSL2에서 별도 실행해야만 PASS 가능하다.
일부 학생 PC가 준비되지 않은 경우 기존 합성 9사례를 사용해 문제 분석을 이어갈 수 있지만 Gazebo 실기 검증으로 대체하지 않는다.

## 6. 품질 기준

- 안전 파라미터 완화/우회, 자동 Start/Reset/Rearm, 무단 Goal 발행 금지.
- 기존 P1 Goal Owner를 통한 **운영자 승인**을 전제. 좌표는 강사 검증 전 고정값 제공 금지.
- 사람형 모델은 가상의 collision geometry이지 실제 인체 안전 검출/충돌 회피 성능이 아님.
- UI/CLI 성공을 실제 주행 검증으로 보고하지 않음.
- 결과물은 24장 강의 흐름, 코드 TODO 2개, 테스트 출력, 증거 JSONL, 현장 문제해결 보고서.
