# AXIA D03 v3 — P1 공유형 3시간 학생 실습 가이드

교육: 180분(실습·이론 170분 + 휴식 10분), 24장 슬라이드 대응  
배포: silverbjin/axia-robot-safety-student / D03_v3  
환경: Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic, Nav2, TurtleBot3 Waffle, Python 3.12  
수정할 파일은 **두 개**: block_A/day03/p1_adapter_todo.py 및 block_A/day03/todo_safety.py  
학생은 P1 Supervisor / Fault Injector / Nav2 / Collision Monitor의 안전 제어 코드를 고치지 않는다.

**안전 경계:** 이 패키지는 격리된 시뮬레이터 전용. SW 보호정지는 인증된 HW E-Stop이 아니다. Diagnostics가 OK라고 실제 주행 허가가 생기지 않는다. 실제 로봇 연결·안전 임계값 완화·무단 Goal/Reset/Rearm을 금지한다.

**검증 구분:** CI는 코드·패키지 배포의 ROS-free 검증. 강사 WSL2 ROS 실제 빌드, Gazebo GUI, P1 정상 Goal, Scan Drop과 정지 실측은 각각 별도의 검증이다.

## A. 수업 전 준비 — 180분에 포함하지 않음

강사는 학생 PC에 ROS 2 Jazzy, Gazebo Harmonic, 공식 nav2_bringup, nav2_minimal_tb3_sim, ros_gz_sim, TurtleBot3 Waffle 및 colcon/WSLg를 사전 설치한다. 정상적인 P1 초기자세·TF·AMCL·Nav2 Lifecycle·Goal Owner 실행 절차도 수업 전에 인수해야 한다. **P1이 실제 주행하지 않는 컴퓨터는 Live 단계를 건너뛰고 증거 분석 과제를 진행한다.**

### 터미널 T1 — 학생용 공개 저장소 최초 Clone / 설치

~~~bash
git clone --branch D03_v3 --single-branch \
  https://github.com/silverbjin/axia-robot-safety-student.git \
  "$HOME/axia_d03_v3_student"

cd "$HOME/axia_d03_v3_student"
git branch --show-current
git rev-parse HEAD
test -f block_A/day03/v3/scripts/classroom.sh && echo D03_V3_ENTRYPOINT_FOUND

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install pytest==8.3.5
deactivate

bash block_A/day03/v3/scripts/classroom.sh session
bash block_A/day03/v3/scripts/classroom.sh prepare
~~~

**예상:** D03_v3, D03_V3_ENTRYPOINT_FOUND, SESSION_CREATED(이후 SESSION_REUSED), P1 패키지 4개 colcon 완료, READY P1_D03_V3_SOURCE_BUILD_PREFLIGHT. 이 단계는 Gazebo/Goal/Stop 실제 성공이 아니다.

**반복 오류 방지:** 이미 Clone한 경우 다시 Clone하지 않는다. 현재 저장소의 브랜치와 필수 파일을 먼저 확인한다. 다른 브랜치이거나 기존 수정 파일이 있다면 덮어쓰지 말고 별도의 D03_v3 폴더를 Clone한다. 대화형 터미널에서 set -euo pipefail을 직접 실행하지 말고 자식 Bash 스크립트로 실행한다.

### 터미널 구분과 환경

| 터미널 | 용도 | 유지/종료 |
|---|---|---|
| T1 | Python TODO, pytest, 결과 보고 | 단위시험 동안 |
| T2 | P1 Gazebo·Nav2·Waffle 실행 | Lab 3–4 끝까지 유지 |
| T3 | ROS 토픽 관측·D3 모델·Live 시나리오 | 관측 중 유지 |
| T4(선택) | 학생 Diagnostics Bridge 수동 확인 | Live 이전 종료 |

**새 ROS 터미널을 열 때마다** 아래 환경 설정을 실행한다.

~~~bash
cd "$HOME/axia_d03_v3_student"
source /opt/ros/jazzy/setup.bash
source "$PWD/install/setup.bash"
source "$HOME/axia_d3_v3_classroom/session.env"
echo "ROS_DOMAIN_ID=$ROS_DOMAIN_ID GZ_PARTITION=$GZ_PARTITION"
~~~

ROS 터미널에서는 Python .venv를 비활성화한다. Lab 1·2 Python 테스트에는 .venv를 사용한다.

## B. 24장 / 180분 시간표

| 시간 | 슬라이드 | 수행 |
|---|---|---|
| 0–15분 | S01–S03 | 사고 가설과 증거 종류 구분 |
| 15–35분 | S04–S06 | P1 제어 경로·Diagnostics 관측 경로·Safe Mode |
| 35–55분 | S07–S09 | P1 Gazebo Waffle 기동, 상태 기준선 관측 |
| 55–80분 | S10–S12 | Lab 1: Diagnostics Adapter TDD |
| 80–105분 | S13–S15 | Lab 2: Safe Mode 후보 TDD |
| 105–115분 | — | 휴식 10분 |
| 115–145분 | S16–S18 | Lab 3: Gazebo 인간형 프록시 이동 |
| 145–170분 | S19–S22 | Lab 4: Scan Drop / P1 보호정지 |
| 170–180분 | S23–S24 | Lab 5: 원인 분석과 HOLD/END 보고 |

## C. S01–S06 — 문제 인식과 데이터 흐름 (0–35분)

**사건:** 물류 로봇이 주행 중 사람형 장애물이 접근하고 LiDAR Scan 스트림이 끊겼다. 로봇이 멈춘 원인을 현장 대응자가 로그로 밝혀야 한다.

**제어 경로:** 공식 Nav2 → P1 Safety Supervisor / Command Gate → 공식 Collision Monitor → Gazebo Waffle.

**관측 경로:** P1 /axia/safety/state JSON → 학생 구현 Diagnostics Adapter → ROS Bridge → /diagnostics. P1 상태 + Fault status + odom + diagnostics → D3 Observer JSONL.

**학생 작성:** 최초 원인 가설 2개, 검증할 ROS 토픽 4개, 운영자 확인 항목 1개.

| 관측 | 의미 | 주행 허가? |
|---|---|---|
| NORMAL + OK(0) | 정상 상태 후보 | Diagnostics만으로는 불가 |
| LIMITED + WARN(1) | 제한 상태 관측 | P1 실제 게이트 확인 |
| PROTECTIVE_STOP + ERROR(2) | 보호정지 발생 | 불가 |
| Diagnostic STALE(3) | 수신 정보 신선도 초과 | 보수적 안전 후보 |
| SW_STOP_LATCHED + WARN(1) | 수동 SW 정지 래치 | **WARN이라도 주행 불가** |
| RECOVERY_REQUIRED | 과거 보호정지 복구 필요 | 자동 재주행 불가 |

**토의:** LaserScan stamp 불량과 Diagnostics STALE의 차이는 무엇인가? 진단 수준은 주행 명령의 권한을 대체할 수 있는가?

## D. S07–S09 — Lab 0: P1 시뮬레이터와 사고 전 기준선 (35–55분)

T2: Gazebo를 실행하고 유지한다.

~~~bash
cd "$HOME/axia_d03_v3_student"
bash block_A/day03/v3/scripts/classroom.sh preflight
bash block_A/day03/v3/scripts/classroom.sh launch
~~~

- preflight는 Jazzy/Nav2/Harmonic 및 P1 필수 패키지를 검사하며 Goal/Fault를 발행하지 않는다.
- launch는 시뮬레이터 확인 문구 YES-D3-SIM 이후 기존 P1 Launch를 실행한다.
- **예상:** Gazebo에서 TurtleBot3 Waffle이 보이고 /clock, /scan, /odom 및 P1 상태를 조회할 수 있다. 실제 GUI 출력이 없으면 PASS가 아니다.

T3: 읽기 전용 관측.

~~~bash
cd "$HOME/axia_d03_v3_student"
source /opt/ros/jazzy/setup.bash
source "$PWD/install/setup.bash"
source "$HOME/axia_d3_v3_classroom/session.env"

ros2 topic type /axia/safety/state
ros2 topic type /odom
ros2 topic type /scan
ros2 topic echo /axia/safety/state --once
ros2 topic echo /odom --once
ros2 lifecycle nodes
~~~

**예상 출력 형식(실측값 아님):**

~~~text
std_msgs/msg/String
nav_msgs/msg/Odometry
sensor_msgs/msg/LaserScan
data: '{"state":"BOOT_SAFE", ...}'  # 실제 상태는 초기화 단계에 따라 다름
twist: ...                          # 실제 linear.x와 angular.z 값 기록
~~~

**기준선 조건:** P1 Goal Owner의 검증된 시작/목표 승인, TF(map→odom→base), AMCL, Nav2 active, P1 NORMAL, 실제 odom 이동. Launch가 성공했다는 이유만으로 이 조건이 충족된 것은 아니다. 초기 자세나 검증된 Goal 좌표를 강사 승인 없이 새로 만들어 사용하지 않는다.

## E. S10–S12 — Lab 1: ROS Diagnostics Adapter (55–80분)

T1은 Python 전용으로 사용한다.

~~~bash
cd "$HOME/axia_d03_v3_student"
source .venv/bin/activate

bash block_A/day03/scripts/run_lab.sh inspect
bash block_A/day03/scripts/run_lab.sh red
~~~

**예상:** INSPECT_OK, 최초 TODO 기준 EXPECTED_RED_CONFIRMED, 원본 pytest 종료 코드 1(기존 기준 22 failed, 8 passed). 의도된 RED이며 아직 정답 PASS가 아니다.

수정 파일은 block_A/day03/p1_adapter_todo.py, 함수 diagnose_p1_state().

| 조건 | level / message | 설명 |
|---|---|---|
| NORMAL + 필수 health 모두 True | OK(0) / NORMAL | 건강한 관측 후보 |
| NORMAL + health 중 False | ERROR(2) / HEALTH_BAD | 명시적 고장 |
| NORMAL + health 누락·None | WARN(1) / HEALTH_UNKNOWN | 모르는 정보는 OK 금지 |
| PROTECTIVE_STOP | ERROR(2) / PROTECTIVE_STOP | P1 보호정지 |
| P1 상태 미수신 또는 수신 시간 초과 | STALE(3) / STATE_MESSAGE_STALE | Bridge 입력 신선도 |
| 손상 JSON·가짜 인증 플래그 | ERROR(2) / INVALID_STATE_MESSAGE | Fail closed |

**구현 힌트:** monotonic time, time age == timeout 경계 포함, Goal ID/원본 JSON/비밀번호를 values에 싣지 않는다.

~~~bash
PYTHONPATH=block_A/day03 python3 -m pytest -q \
  block_A/tests/test_d03_adapter_public.py
~~~

**예상:** Adapter 계약을 구현한 뒤 해당 공개 테스트만 GREEN.

T4 선택 ROS 실습(실제 P1이 동작하고 Adapter가 완성된 경우):

~~~bash
cd "$HOME/axia_d03_v3_student"
source /opt/ros/jazzy/setup.bash
source "$PWD/install/setup.bash"
source "$HOME/axia_d3_v3_classroom/session.env"
PYTHONPATH=block_A/day03 /usr/bin/python3 \
  block_A/day03/ros_diagnostics_bridge.py
~~~

T3에서 ros2 topic echo /diagnostics --once를 확인한다. Bridge가 메시지를 아직 받지 못했다면 초기 STALE가 가능하다. **Bridge는 읽기/진단 발행만 하며 제어 권한이 없다.**

## F. S13–S15 — Lab 2: 단계적 Safe Mode 후보 (80–105분)

수정 파일은 block_A/day03/todo_safety.py, 함수 assess_diagnostic().

우선순위: SW_STOP_LATCHED > 입력 시간/형식 오류 > ERROR/STALE > 이전 보호정지 래치 > WARN > OK.

**중요:** ERROR → OK → OK의 예상 상태는 PROTECTIVE_STOP → RECOVERY_REQUIRED → RECOVERY_REQUIRED. 정상 진단 재수신 후 자동 재주행을 허용하지 않는다.

~~~bash
cd "$HOME/axia_d03_v3_student"
source .venv/bin/activate

PYTHONPATH=block_A/day03 python3 -m pytest -q \
  block_A/tests/test_safety_public.py

bash block_A/day03/scripts/run_lab.sh green
bash block_A/day03/scripts/run_lab.sh run
deactivate
~~~

**예상(정답 구현 시):**

~~~text
30 passed
D03_REPLAY_RESULT cases=9 failures=0
ROS_VERIFIED=NOT_RUN GAZEBO_VERIFIED=NOT_RUN
~~~

이는 Python/합성 사례에서만 유효한 PASS이다.

## 휴식 105–115분

T2 Gazebo는 종료하지 않는다. T4에서 Bridge를 실행했다면 Live가 자체적으로 Bridge를 실행하기 전에 Ctrl+C로 종료한다. 중복 Bridge를 남기지 않는다.

## G. S16–S18 — Lab 3: 인간형 프록시 생성·이동 (115–145분)

T3에서 실제 Gazebo World 이름을 조회한다.

~~~bash
cd "$HOME/axia_d03_v3_student"
source /opt/ros/jazzy/setup.bash
source "$PWD/install/setup.bash"
source "$HOME/axia_d3_v3_classroom/session.env"
gz service -l | grep '/world/.*/set_pose'
~~~

강사가 GUI에서 로봇과 벽에 접촉하지 않는 시작/끝 좌표를 확인한다. 범위 검사(좌표 ±15m, 이동 거리 0.3–3.0m)는 충돌 없는 경로를 보증하지 않는다.

~~~bash
# 아래 WORLD와 좌표를 실제 Gazebo에서 확인한 값으로 교체한다
bash block_A/day03/v3/scripts/classroom.sh route \
  '<WORLD>' '<SX>' '<SY>' '<EX>' '<EY>'

bash block_A/day03/v3/scripts/classroom.sh preview
~~~

**예상:** ROUTE_SAVED, YES-D3-PREVIEW 승인, PREVIEW Proxy created, PREVIEW_MOVE 1/8 … 8/8, SCENARIO PREVIEW_MOVED.

**GUI 합격 조건:** 학생 눈으로 인간형 모델 생성과 시간에 따른 이동을 확인하고 캡처. 터미널 성공과 Gazebo GUI 실제 이동은 별개다.

Preview 종료 후 동일 이름 중복 생성을 방지한다.

~~~bash
bash block_A/day03/v3/scripts/classroom.sh remove-proxy
# 승인: YES-D3-REMOVE
~~~

**현장 문제:** 장애물이 먼저 안전 정지를 유발하고 후에 Scan Fault가 실행됐다면, 센서 장애가 정지 원인이었다고 주장하지 않는다. 기존 Collision Monitor 설정을 끄거나 완화하지 않는다.

## H. S19–S22 — Lab 4: 정상 주행 중 LiDAR Scan Drop (145–170분)

다음 5개가 모두 충족되어야 Live를 시작한다.

1. TF/AMCL/Nav2 lifecycle/초기 위치 정상. **P1 Goal Owner의 기존 승인된 절차로만** Goal이 시작됨.
2. P1 NORMAL + 최근 /odom 선속 절댓값 0.05m/s 이상.
3. Preview 모델 제거 완료, 실제 world set_pose/create 서비스 있음.
4. 학생 두 함수 공개 30건 GREEN. Fault Injector 상태 NORMAL + enabled true.
5. 시뮬레이션만을 위한 ROS_DOMAIN_ID/GZ_PARTITION이 각 터미널에서 일치.

T3 상태·Fault 확인(읽기 전용):

~~~bash
ros2 topic echo /axia/safety/state --once
ros2 topic echo /axia/fault/status --once
ros2 topic echo /odom --once
ros2 service type /axia/fault/scan_drop
~~~

**예상:** P1 NORMAL, fault NORMAL/enabled true, 실제 odom 이동, std_srvs/srv/Trigger. 불일치하면 BLOCKED, 임의 호출 금지.

T3 Live 실행:

~~~bash
cd "$HOME/axia_d03_v3_student"
bash block_A/day03/v3/scripts/classroom.sh live
~~~

실행자가 별도로 입력: YES-D3-SIM → YES-D3-FAULT → 모델을 GUI에서 확인한 후 YES-VISIBLE → 보호정지 확인 후 HOLD 또는 END.

**기대 순서 (성공 보장 아닌 예상)**

~~~text
[WAIT] P1 must already be NORMAL and odom must indicate movement
[GAZEBO] Spawned proxy ...
[MOVE] 1/8 ...
[FAULT] Existing P1 scan_drop service accepted
[WAIT] Observing fault_status + PROTECTIVE_STOP + ERROR diagnostic + odom stop...
[RESULT] DEMO_OBSERVED (education-only, not E-Stop certification)
~~~

학생 Live는 ROS Diagnostics Bridge를 학생 구현으로 실행하고 D3 Observer로 JSONL을 수집한다. P1 Goal/Start/Reset/Rearm을 발행하지 않는다.

**Live 실패:** BLOCKED_NO_LIVE_MOTION, BLOCKED_FAULT_DISABLED, BLOCKED_P1_STOPPED_BEFORE_FAULT, INCONCLUSIVE_STOP_OR_DIAGNOSTICS 등은 각각 현장 분석의 자료이며 임의 성공 처리 금지.

~~~bash
bash block_A/day03/v3/scripts/classroom.sh verify
bash block_A/day03/v3/scripts/classroom.sh status
~~~

재시연할 때는 P1 Fault/Stop의 **기존 승인된 수동 복구**가 먼저 필요하다. 아래 명령은 기존 fault를 해제하지 않고 새 증거 파일만 준비한다.

~~~bash
bash block_A/day03/v3/scripts/classroom.sh new-evidence
~~~

## I. S23–S24 — Lab 5: 운영자 대응·근본원인 분석 (170–180분)

| 항목 | 요구 증거 | 미확인 시 |
|---|---|---|
| 프록시 생성·이동 | Gazebo 화면 + PREVIEW_MOVE 8단계 | NOT_VERIFIED |
| P1 주행 | NORMAL + odom 실제 이동 | BLOCKED |
| Fault | 서비스 응답과 fault_status DROP_SCAN | NOT_OBSERVED |
| Diagnostics | AXIA/P1/SafetySupervisor ERROR(2) | NOT_OBSERVED |
| Supervisor | P1 PROTECTIVE_STOP | NOT_OBSERVED |
| 정지 | odom 선속 <0.03m/s, 각속 <0.05rad/s를 최소 1초 | NOT_OBSERVED |
| 인과 | Scan Fault 이전 정지 여부 확인 | INCONCLUSIVE |
| 운영자 | HOLD / END 기록, 재가동 승인 보류 | INCONCLUSIVE |

**보고서 3문장:** ① 최초 사건과 추정 원인 ② 로그로 확인된 사실과 미확인 ③ HOLD 또는 END 결정과 수동 복구 요건.

**제출:** 학생 수정 Python 2개, 실제 명령·Exit Code·테스트 출력, 개인 Git SHA, Gazebo 증거(실행했다면), JSONL/로그 중 필요한 부분, REPORT_D03_V3_KO.md를 복사해 작성한 분석 보고서.

## J. 장애 대응 테이블

| 증상 | 원인 후보 | 조치 |
|---|---|---|
| classroom.sh not found | D03 이전 브랜치/잘못된 CWD | Git 브랜치·경로·파일 존재 확인 후 별도 Clone |
| 터미널이 코드 127로 종료됨 | 대화형 셸에서 set -e 적용 | 자식 Bash 스크립트로만 실행 |
| ROS package missing | 공식 Jazzy/Nav2/TB3 설치 누락 | 패키지 조회, ROS 없는 PC는 합성 Lab 진행 |
| GUI만 뜨고 주행 없음 | P1 AMCL/TF/Nav2 Lifecycle/Goal 미준비 | P1 Owner의 기준선 검증, 임의 Goal 금지 |
| TODO_NOT_IMPLEMENTED | 학생 함수 미완성 | 공개 테스트로 RED→GREEN |
| /diagnostics 없음 | Bridge 미시작, 도메인 불일치 | 학생 Bridge/세션 환경과 Green 확인 |
| WORLD set_pose 없음 | 실제 World 이름 다름 | gz service -l 확인 |
| 모델 안 보임 | 카메라/모델 좌표 오류 | GUI 위치 확인, 위험 경로 금지 |
| BLOCKED_NO_LIVE_MOTION | P1 NORMAL·odom 주행 미충족 | P1의 실제 주행 절차 먼저 검증 |
| STOP_PRECEDED_SCAN_FAULT | Collision Monitor 등 정지 선행 | 인과 INCONCLUSIVE, 원본 기록 보존 |
| 재실험 evidence exists | 기존 실행 증거 파일 있음 | new-evidence, P1 별도 수동 복구 |
| Python ROS import 실패 | 활성 .venv 등 PATH 충돌 | deactivate 및 시스템 Python으로 ROS 실행 |

## K. 실습 종료와 검증 수준

- Python 공개 테스트 30개 GREEN / 9사례 재생: 실제 결과 기입.
- 공개 CI 패키지 무결성: 저장소 CI URL과 HEAD SHA 기록.
- ROS 2 Jazzy 실제 빌드와 ROS Bridge: 시행한 경우에만 PASS.
- Gazebo GUI·P1 Goal·Fault·실제 정지: 실제 실행한 경우에만 PASS, 아니면 NOT_RUN.
- 인증 하드웨어 E-Stop: **NOT_VERIFIED**.

종료 순서: Live 종료 → Fault/Stop 상태 보존 및 운영자 기록 → T4 Bridge 중복 프로세스 종료 → T2 Gazebo Ctrl+C → T1 코드·로그·Git SHA 제출. 자동 재주행 금지.

관련 문서: DESIGN_D03_V3_KO.md, REPORT_D03_V3_KO.md, P1_RUNTIME_SOURCE_MANIFEST.json.
