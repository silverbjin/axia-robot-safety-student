# AXIA D10 — Block B D08 Gazebo + RViz2 + Isolation Forest 실시간 관찰

**실행 범위:** 기존 D08 Waffle·시각용 이동 Actor·RGB-D·YOLO·Scan/TF/Odom을 실제 Gazebo Harmonic과 RViz2에서 계속 실행합니다. 동시에 기존 D10의 **합성 IF 점수**를 D12 교육용 ROS 진단으로 재생하고 RViz2에 읽기 전용 텍스트 Marker로 표시합니다.

**중요:** 실제 로봇의 전류·토크·가속도와 합성 `SYNTHETIC_COURSE_FIXTURE`는 **별개 신호**입니다. 동일 원인/시간축으로 결합되지 않습니다. 합성 WARNING은 **비인증 교육용 경고**이며 Safety Supervisor/FSM/Stop/Nav2/Collision Monitor/Guard TTL/인증 E-Stop을 변경하지 않습니다. Goal 또는 `cmd_vel` 제어를 발행하지 않습니다.

## 1. 시스템 아키텍처

~~~text
[기존 D08 Gazebo Waffle + 이동 시각 Actor]
  ├── /scan   ── RViz2 LaserScan
  ├── /odom, /tf ─ RViz2 RobotModel/TF/Odom
  └── RGB-D → yolo_ros → RViz2 RGB/Depth/YOLO 디스플레이

[고정 D09 합성데이터 4599행/46 Trace]
  ├── mean/std 6개 → Train 정상 240 fit
  ├── Valid 정상 80 → 임계값 95% 분위
  └── Test 100 VALID (+품질4) → 강사 IF 점수 CSV
       ↓ 기존 D12 events.py (104 JSONL; model_id D10_ISOLATION_FOREST)
       ↓ 기존 D12 ros_diagnostic_bridge.py
     /axia/education/diagnostics  (DiagnosticArray)
       ↓ 새 읽기 전용 d10_if_rviz_marker.py
     /axia/education/d10_if_marker
       ↓
     RViz2 Marker: SYNTHETIC IF REPLAY / NO ROBOT CONTROL

※ 위 두 파이프라인은 인과·시간 동기화되지 않습니다.
~~~

기존 D08의 RViz 설정 파일은 변경하지 않습니다. D10이 실행 때 별도 RViz 프로필을 만들어 Marker Display 하나만 추가하며 기존 D08 Waffle/TF/Odom/LaserScan/RGB-D/YOLO 뷰를 보존합니다. RViz 창을 추가로 띄우지 않습니다.

## 2. WSL2 한 블록 실행(강사 PC)

**사전:** Windows WSL2 Ubuntu 24.04, WSLg, ROS Jazzy, Gazebo Harmonic, RViz2, 기존 D08 설치·캐시. 강사 비공개 저장소를 인증 후 로컬에 클론해 둬야 합니다. 다른 D08 인스턴스는 기존 터미널에서 Ctrl+C로 정상 종료하십시오.

~~~bash
(
  set -Eeuo pipefail
  INSTRUCTOR="$HOME/axia_d10_course/axia-robot-safety-instructor"
  STUDENT="$HOME/axia_d10_live_overlay_student"
  BRANCH="feat/d10-gazebo-rviz-synthetic-overlay-20261119"
  test -d "$INSTRUCTOR/.git" || { echo "먼저 강사 비공개 저장소를 인증·클론하십시오: $INSTRUCTOR"; exit 2; }
  if test ! -e "$STUDENT"; then
    git clone --single-branch --branch "$BRANCH" https://github.com/silverbjin/axia-robot-safety-student.git "$STUDENT"
  else
    test -d "$STUDENT/.git"
    test "$(git -C "$STUDENT" branch --show-current)" = "$BRANCH"
    test -z "$(git -C "$STUDENT" status --porcelain)"
    git -C "$STUDENT" pull --ff-only origin "$BRANCH"
  fi
  export AXIA_D10_INSTRUCTOR_ROOT="$INSTRUCTOR"
  export AXIA_D10_DOMAIN_ID=49
  export AXIA_D10_GUI_ENGINE=ogre
  export AXIA_D10_RGBD_RATE_HZ=10
  export AXIA_D10_GUI_HOLD_S=900
  bash "$STUDENT/block_C/day10/live/d10_gazebo_rviz_once.sh" --self-check
  bash "$STUDENT/block_C/day10/live/d10_gazebo_rviz_once.sh" --doctor
  bash "$STUDENT/block_C/day10/live/d10_gazebo_rviz_once.sh" --run
)
~~~

스크립트는 D08의 실제 `D05_PUBLIC_SENSOR_ONLY_PASS`를 확인한 후에만 D12 합성 재생을 시작합니다. 출력은 별도의 `~/axia_d10_live_evidence/d10-*`에 보존하며 기존 원본과 저장소를 삭제/덮어쓰지 않습니다. 오류 발생 시 `d08_session.log`의 첫 안전 상태 전이/첫 센서 타이밍 위반부터 확인합니다.

**예상 로그 패턴(실제 새 WSL2 실행 출력 아님):**

~~~text
D10_RVIZ_MARKER_STATIC_OK ROS_NOT_RUN GAZEBO_NOT_RUN NO_CONTROL
D10_LIVE_STATIC_PASS NO_ROS_NO_GAZEBO_NO_CONTROL
D10_LIVE_DOCTOR_STATIC_PASS student=<SHA>
C05_EVENTS_JSONL_PASS count=104 ... ros_actual=false
D10_RVIZ_OVERLAY_STATIC_READY ...
D05_PUBLIC_SENSOR_ONLY_PASS REAL_RGBD_YOLO PRIVATE_D05_RANGE_NOT_RUN
D10_LIVE_REPLAY_STARTED source=SYNTHETIC_COURSE_FIXTURE domain=49
D10_LIVE_RVIZ_MARKER_TOPIC=/axia/education/d10_if_marker
~~~

창·PID·로그만으로 실제 화면 PASS를 선언하지 않습니다. Gazebo Waffle/Actor 움직임, RViz RobotModel·TF·LaserScan·RGB-D·YOLO 및 Synthetic IF 텍스트를 직접 관찰해 인수합니다.

## 3. 별도 터미널 — ROS 토픽 탐색

~~~bash
set +u; source /opt/ros/jazzy/setup.bash; set -u
export ROS_DOMAIN_ID=49
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 topic list -t | grep -E '(^/scan|^/odom|^/tf|^/axia/education|^/yolo/cam0)'
ros2 topic info /axia/education/diagnostics -v
ros2 topic info /axia/education/d10_if_marker -v
ros2 topic echo /axia/education/d10_if_marker --once --field text
~~~

가상·물리 데이터를 구분하세요. 텍스트에 나타나는 `TST_A_00/W5`의 합성 Timestamp **5.9초**와 이상 주입 **4.0초**의 차이는 **1.9초 합성 윈도우 지연**입니다. 이것은 현재 시뮬레이터의 센서 시간·네트워크 지연·Safety TTL과 무관합니다.

## 4. RViz에서 반드시 볼 것

| RViz2 Display | Topic | 증거 |
|---|---|---|
| RobotModel/TF/Odometry | /robot_description, /tf, /odom | D08 Waffle 실제 시뮬레이션 데이터 |
| LaserScan | /scan | Waffle LiDAR, Actor의 LiDAR 충돌체를 의미하지 않음 |
| RGB / Depth / YOLO | /axia/d05/rgbd/image, /axia/d05/rgbd/depth_image, /yolo/cam0/debug_image | 실제 Gazebo RGB-D/YOLO |
| D10 Marker | /axia/education/d10_if_marker | IF 합성 진단 텍스트 **NO ROBOT CONTROL** |

실습 질문: ① 실제 센서가 무엇이며 합성 모델점수가 무엇인가? ② IF는 어떤 Train/Valid/Test 경계를 지키는가? ③ TP1/FP2/FN17/TN80에서 왜 안전성·조기예지를 주장할 수 없는가? ④ 첫 WARNING은 합성 시각인가 DDS 수신 시각인가?

## 5. 범위·검증·종료

- 재사용 근거: Block B D08의 Gazebo/WSLg Ogre1 GUI와 RViz2 교육용 센서 시연, 기존 Block C D12 ROS DDS L1 및 C03 IF Python L0.
- 새 통합: 기존 D08 런처의 **선택적 RViz 설정 파일 override 한 줄** 및 두 교육 전용 어댑터만 신규 작성. 기본 D08 실행은 변경하지 않음.
- 공개 CI는 **Python/쉘 L0 계약만 검증**합니다. 새 동시 실행의 실제 Gazebo·RViz2 화면, ROS D12→Marker 전달 주기, WSL2 리소스·Scan/Odom/Clock 전송 안전 TTL은 **미검증**. 기존 D08 최초 500ms Scan 지연 분석을 건너뛰어 전체 시연 안정성 PASS를 선언하지 않습니다.
- 종료는 실행 터미널 **Ctrl+C**. 다른 WSL2 세션 종료, 전역 pkill, 명령 주행, 인증 E-Stop 조작을 하지 않습니다.
