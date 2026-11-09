# AXIA P1 학생용 패키지 — 설치 및 기본 실행 (D03_v3)

**대상:** Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic / Nav2 / TurtleBot3 Waffle  
**공개 저장소:** https://github.com/silverbjin/axia-robot-safety-student/tree/D03_v3  
**목표:** P1 소프트웨어를 직접 설치·빌드하고 Waffle Gazebo 및 ROS 상태 토픽을 확인한 뒤 D03 Diagnostics 실습으로 연결한다.

> 이 문서의 기본 실행은 **NO GOAL / NO 자동 Fault** 시연이다. SW Stop은 인증된 하드웨어 E-Stop이 아니다. 임의의 실제 로봇 연결, 주행 명령, 자동 Reset/Rearm은 금지한다.

## 1. 학생에게 공개한 P1 소프트웨어

| 경로 (ros2_ws/src 아래) | 역할 |
|---|---|
| axia_safety_bringup | 공식 Nav2·Waffle/Gazebo를 재사용하는 P1 Launch |
| axia_safety_supervisor | FSM, Watchdog, Command Gate, Nav2 Goal 권한, Software Stop |
| axia_fault_injector | 시뮬레이션용 LaserScan 장애 주입·상태 관측 |
| axia_scenario_verifier | 시나리오 증거·상태 검증 |
| axia_d3_demo | Gazebo 사람형 프록시, Preview/Live, Observer JSONL |

비공개 Instructor 저장소의 고정 커밋 0be687ee033233fcd53be1190e0b2f9e86730fc9에서 공개 범위로 선정한 런타임 45개 파일을 **Git blob SHA 단위로 대조**했고, 공개 student Bringup 패키징 파일 4개를 더해 전체 49개 파일이다. 출처: [P1_RUNTIME_SOURCE_MANIFEST.json](../../block_A/day03/v3/P1_RUNTIME_SOURCE_MANIFEST.json).

공식 Nav2와 TurtleBot3 소스는 복사하지 않고 **ROS 2 공식 설치본을 재사용**한다. 강사 정답·비공개 Hidden Tests·원본 인수 증거·자격증명은 배포하지 않는다. 학생은 D03 TODO 함수 두 개만 수정한다.

## 2. 준비 환경

- Windows 11 WSL2 Ubuntu 24.04 또는 네이티브 Ubuntu 24.04.
- ROS 2 Jazzy와 ROS apt 저장소 구성. 아직 없으면 [ROS 2 Jazzy 공식 deb 설치 절차](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)를 먼저 따른다.
- Gazebo Harmonic은 Jazzy의 ros-jazzy-ros-gz를 통해 설치한다. 기존 Fortress·Ionic과 혼합하지 않는다. [Gazebo/ROS 공식 호환성](https://gazebosim.org/docs/harmonic/ros2_integration/).
- WSL2 사용자는 WSLg GUI가 표시 가능한 환경을 준비한다. 기존 CI의 Headless PASS는 학생 WSLg 창 표시를 보증하지 않는다.

**T1: Ubuntu 버전 및 ROS 환경 확인**

~~~bash
cat /etc/os-release | grep -E '^(ID|VERSION_ID)='
test -f /opt/ros/jazzy/setup.bash && echo JAZZY_FOUND || echo JAZZY_MISSING
~~~

예상: ID=ubuntu, VERSION_ID="24.04". JAZZY_MISSING이면 ROS 공식 설치를 먼저 완료한다.

## 3. 최초 설치: Clone → 의존성 → 빌드

**T1: 공개 저장소 Clone (최초 1회)**

~~~bash
git clone --branch D03_v3 --single-branch \
  https://github.com/silverbjin/axia-robot-safety-student.git \
  "$HOME/axia_d03_v3_student"

cd "$HOME/axia_d03_v3_student"
git branch --show-current
git rev-parse HEAD
test -f scripts/p1_d03_v3_student_setup.sh && echo P1_SETUP_FOUND
~~~

예상: D03_v3, Git 커밋 SHA, P1_SETUP_FOUND. **기존 Checkout이 있으면 재Clone/강제 reset하지 않는다.** 학생의 이전 실습 수정 파일을 삭제하지 않는다.

**T1: 공식 apt 의존성 설치 (선택, 기존에 설치돼 있다면 생략)**

~~~bash
cd "$HOME/axia_d03_v3_student"
bash scripts/p1_d03_v3_student_setup.sh --install-deps
~~~

실행 시에만 sudo apt-get update/install을 수행한다. ROS apt 소스는 임의로 생성하거나 변경하지 않는다. 설치 대상은 ROS 2 Jazzy ros-base, Nav2 bringup, minimal TB3 simulation, ros_gz, ROS CLI/message 패키지, colcon, Python venv/pytest다. 공식 소스 미등록으로 Unable to locate package가 발생하면 ROS 설치 문서의 apt source 단계를 확인한다.

예상: [INSTALLED] ROS 2 Jazzy / Nav2 / Gazebo Harmonic / Waffle dependencies.

**T1: 격리 세션 생성·5개 P1/D3 패키지 실제 빌드**

~~~bash
cd "$HOME/axia_d03_v3_student"
bash scripts/p1_d03_v3_student_setup.sh --prepare
bash scripts/p1_d03_v3_student_setup.sh --check
~~~

기존 classroom.sh를 재사용한다. ~/axia_d3_v3_classroom/session.env에 ROS_DOMAIN_ID/GZ_PARTITION을 안전하게 저장하고, 5개 패키지의 colcon build/ROS 인덱스/공식 Nav2 확인을 수행한다. 실행 도중 Goal/Fault를 발행하지 않는다.

예상 출력 **예시(학생 PC 미실측)**:

~~~text
[D03_V3] [SESSION_CREATED] .../axia_d3_v3_classroom/session.env
Summary: 5 packages finished [...]
[D03_V3] [READY] P1_D03_V3_SOURCE_BUILD_PREFLIGHT (NO GOAL, GUI OR FAULT RUN)
[READY] P1_D03_V3_STUDENT_BUILD_BASIC_PREFLIGHT
[SCOPE] Gazebo GUI NOT_RUN; Nav2 Goal NOT_RUN; Fault NOT_RUN; E-Stop NOT_CERTIFIED
~~~

실습 중에는 session.env를 삭제하거나 새로 만들지 않는다. 각 터미널이 **동일한** ROS_DOMAIN_ID/GZ_PARTITION을 사용해야 한다.

## 4. 기본 실행 — Gazebo TurtleBot3 Waffle

**T2: 새 터미널에서 Gazebo GUI 실행 (계속 유지)**

~~~bash
cd "$HOME/axia_d03_v3_student"
bash block_A/day03/v3/scripts/classroom.sh launch
~~~

확인 프롬프트에 **YES-D3-SIM**을 직접 입력한다. Gazebo Waffle 시뮬레이션은 시작되지만 자동 Goal·Fault·Reset은 발생하지 않는다. P1 Launch의 autostart=false에서 Nav2 Lifecycle을 별도로 준비할 수 있다. Gazebo GUI에 Waffle이 실제 보이지 않으면 GUI_NOT_VERIFIED.

**T3: 새 터미널에서 ROS 환경 설정 (매 터미널마다 실행)**

~~~bash
cd "$HOME/axia_d03_v3_student"
source /opt/ros/jazzy/setup.bash
source "$PWD/install/setup.bash"
source "$HOME/axia_d3_v3_classroom/session.env"

echo "ROS_DOMAIN_ID=$ROS_DOMAIN_ID GZ_PARTITION=$GZ_PARTITION"
ros2 pkg prefix axia_safety_supervisor
ros2 pkg prefix axia_fault_injector
ros2 pkg prefix axia_d3_demo

ros2 topic type /axia/safety/state
ros2 topic type /axia/fault/status
ros2 topic type /scan
ros2 topic type /odom

timeout 20 ros2 topic echo /axia/safety/state --once --full-length
timeout 20 ros2 topic echo /odom --once
timeout 20 ros2 topic echo /scan --once --field header --qos-reliability best_effort
gz service -l | grep -E '^/world/[^/]+/(set_pose|create)$'
~~~

**기대 타입:** /axia/safety/state = std_msgs/msg/String; /axia/fault/status = std_msgs/msg/String; /scan = sensor_msgs/msg/LaserScan; /odom = nav_msgs/msg/Odometry. 상태는 BOOT_SAFE 등 초기화 단계에 따라 달라진다. /odom의 0속도는 자동 Goal이 없는 기본 실행에서 정상일 수 있다.

**기본 실행 판정:** Waffle GUI 실제 표시 + 센서 메시지 수신 + P1 상태 토픽 확인이 각각 필요하다. Nav2 Goal 주행은 이 절차의 범위가 아니며, 기본 실행 통과만으로 P1 G00 인수나 장애 대응 시연을 완료했다고 주장하지 않는다.

## 5. 선택: 사람형 모델 Preview (Goal과 Fault 없음)

먼저 Gazebo에서 실제 World와 사람형 모델의 이동 경로를 확인한다. 시작/끝 거리 0.3–3.0m 제한은 충돌 없는 경로를 보증하지 않는다.

~~~bash
cd "$HOME/axia_d03_v3_student"
source /opt/ros/jazzy/setup.bash
source "$PWD/install/setup.bash"
source "$HOME/axia_d3_v3_classroom/session.env"

read -r -p "WORLD 이름: " WORLD
read -r -p "START_X START_Y END_X END_Y: " SX SY EX EY

bash block_A/day03/v3/scripts/classroom.sh route \
  "$WORLD" "$SX" "$SY" "$EX" "$EY"

bash block_A/day03/v3/scripts/classroom.sh preview
# YES-D3-PREVIEW 승인, Gazebo GUI에서 8단계 이동 실제 확인

bash block_A/day03/v3/scripts/classroom.sh remove-proxy
# YES-D3-REMOVE 승인, 모델 제거
~~~

예상: PREVIEW_MOVE 1/8 ~ 8/8, PREVIEW_MOVED. **터미널 성공 출력은 GUI 실제 가시성 검증을 대신하지 않는다.** 기존 route.env가 있다면 자동 덮어쓰기하지 않는다.

## 6. D03 학생 코드 작성 및 Diagnostics 확인

학생이 구현하는 파일은 block_A/day03/p1_adapter_todo.py의 diagnose_p1_state(), block_A/day03/todo_safety.py의 assess_diagnostic()뿐이다. P1 Supervisor, Fault Injector, 공식 Nav2/Collision Monitor의 안전 로직을 수정하지 않는다.

**T1: Python 전용 환경**

~~~bash
cd "$HOME/axia_d03_v3_student"
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install pytest==8.3.5

bash block_A/day03/scripts/run_lab.sh inspect
bash block_A/day03/scripts/run_lab.sh red

# 두 함수 구현 후:
bash block_A/day03/scripts/run_lab.sh green
bash block_A/day03/scripts/run_lab.sh run

deactivate
~~~

초기 TODO RED는 의도된 출발점이다. **구현 완료 후 공개 30개 PASS와 합성 9사례 failures=0**은 과제 목표이지 이 배포본에서 이미 달성한 학생 성과는 아니다.

**T4: 학생 Adapter 완료 후 읽기 전용 Diagnostics Bridge**

~~~bash
cd "$HOME/axia_d03_v3_student"
source /opt/ros/jazzy/setup.bash
source "$PWD/install/setup.bash"
source "$HOME/axia_d3_v3_classroom/session.env"
bash block_A/day03/v3/scripts/classroom.sh bridge
~~~

별도의 T3에서 ros2 topic echo /diagnostics --once 를 실행해 DiagnosticArray가 들어오는지 확인한다. Diagnostics는 관측 결과이며 주행 허가 명령이 아니다. 전체 주행·LiDAR 장애·HOLD/END 실습은 [D03 v3 학생 실습 가이드](../../block_A/day03/v3/README_D03_V3_LAB_KO.md)의 추가 게이트를 따른다.

## 7. 오류 대응

| 증상 | 원인·조치 |
|---|---|
| ROS apt Unable to locate package | ROS 2 Jazzy 공식 apt 저장소 설정·update 확인 |
| classroom.sh No such file or directory | 이전 D03 브랜치 또는 잘못된 실행 폴더. git branch --show-current 확인 |
| ros2 pkg prefix에서 P1 미발견 | --prepare 빌드, source install/setup.bash 확인 |
| gz: command not found | ros-jazzy-ros-gz 설치 상태 확인. Jazzy/Harmonic 외 배포판과 혼용 금지 |
| Gazebo 창이 열리지 않음 | WSLg DISPLAY/WAYLAND_DISPLAY, GPU/창 로그 확인. Headless CI와 구분 |
| Gazebo 창만 뜨고 로봇이 움직이지 않음 | 정상일 수 있음. 이 기본 실행은 NO GOAL이고 autostart=false |
| /scan 메시지 없음 | ROS_DOMAIN_ID·GZ_PARTITION·QoS best_effort·/clock 확인 |
| /diagnostics 없음 | 학생 TODO GREEN, Bridge 실행, P1 상태 토픽·도메인 확인 |
| 기존 route.env와 다른 좌표 | 모델 이동 경로가 변경되었으므로 강사 검토 후 백업·새 세션에서 실행 |
| 인수 실패 / INCONCLUSIVE | 결과를 기록한다. 안전 기준 완화 또는 자동 Reset/Rearm 금지 |

## 8. 검증 수준 / 인수 / 종료

| 검증 | 공개 증거 | 학생 PC에서 해야 할 확인 |
|---|---|---|
| 원본 45개 blob SHA | 매니페스트 + 배포 CI | Git SHA 기록 |
| 실제 Jazzy colcon 빌드(5 packages) | [Actions #42573704529](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/42573704529) | --prepare 실제 실행 |
| Headless Gazebo Waffle 센서·P1 상태 | 같은 Actions | T2/T3에서 실제 메시지 |
| Headless 프록시 create/set_pose 3/3 | 같은 Actions | 선택 Preview GUI 확인 |
| 무주행 SW_STOP_LATCHED + 0 Twist | 같은 Actions | 주행 중 정지 검증과 구별 |
| WSL2 GUI 및 Nav2 Goal 후 이동 | CI 미검증 | 실제 WSL2 인수 필요 |
| LiDAR Scan Drop → PROTECTIVE_STOP → odom 정지 | CI 미검증 | 강사 승인 Live 필요 |
| 인증된 E-Stop | NOT_VERIFIED | 이 교육 범위가 아님 |

종료 순서: Preview 모델 제거 → 선택 Bridge Ctrl+C → Gazebo 실행 T2 Ctrl+C → 실제 명령/로그/Exit Code/Git SHA 기록. Software Stop과 인증된 E-Stop을 혼동하지 않는다.

## 9. 공식 문서

- [ROS 2 Jazzy Ubuntu 24.04 deb 설치](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
- [Gazebo Harmonic과 ROS 연동](https://gazebosim.org/docs/harmonic/ros2_integration/)
- [Gazebo Harmonic Ubuntu 설치](https://gazebosim.org/docs/harmonic/install_ubuntu/)
