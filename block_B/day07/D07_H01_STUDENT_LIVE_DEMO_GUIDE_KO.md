# D07-H01 — 훈련생 독립 Gazebo + RViz2 실제 물리 경로 재계획 라이브

**이 문서의 기본 시연은 이제 ROS L1 합성 예제가 아니라 학생 PC에서 직접 실행하는 Gazebo Harmonic 물리 H01입니다.** 강사가 사용한 H01 시연 코드 중 실행에 필요한 허가된 최소 소스를 `block_B/day07/h01_runtime/`에 공개해, 비공개 Instructor 권한·GitHub 토큰 없이 실행합니다. `route_todo.py` 정답과 hidden tests는 공개하지 않습니다.

## A. 학생 PC에서 실제 Gazebo·RViz2를 동시에 실행 (최우선)

**환경:** Windows WSL2 Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic / 공식 Nav2 / WSLg DISPLAY / RViz2 / colcon. 학생은 화면에 **실제 TurtleBot3 Waffle, Gazebo 물리 원통 장애물, RViz2 LaserScan·Global Costmap·공식 Nav2 Path**를 함께 확인합니다. **Before → Intrusion → Restored**: 로봇은 정지, 기존 실행기가 Gazebo 원통 장애물을 이동·제거합니다. Nav2 `ComputePathToPose`는 계획 경로만 계산합니다. `NavigateToPose`, `FollowPath`, `/cmd_vel` 주행 Goal, fault injection, 인증 E-Stop은 수행하지 않습니다. `NO_GOAL`.

**준비(최초 1회, 필요한 경우에만):**

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  git python3-colcon-common-extensions \
  ros-jazzy-nav2-bringup ros-jazzy-nav2-minimal-tb3-sim \
  ros-jazzy-nav2-planner ros-jazzy-nav2-navfn-planner \
  ros-jazzy-turtlebot3-gazebo ros-jazzy-ros-gz \
  ros-jazzy-rviz2 ros-jazzy-xacro
```

**터미널 A — 학생 공개 `main`의 라이브 원샷** (복사하여 실행):

```bash
(
  set -Eeuo pipefail
  ROOT="$HOME/axia_d07_h01_student_gui"
  if [[ ! -e "$ROOT" ]]; then
    git clone --single-branch --branch main \
      https://github.com/silverbjin/axia-robot-safety-student.git "$ROOT"
  fi
  test -d "$ROOT/.git"
  cd "$ROOT"
  test "$(git branch --show-current)" = main
  bash -n block_B/day07/run_d07_h01_gazebo_rviz_student_once.sh
  bash block_B/day07/run_d07_h01_gazebo_rviz_student_once.sh --self-check
  bash block_B/day07/run_d07_h01_gazebo_rviz_student_once.sh --doctor
  AXIA_D07_STUDENT_PHASE_HOLD_S=10 \
    bash block_B/day07/run_d07_h01_gazebo_rviz_student_once.sh --run
)
```

- 이미 `$ROOT`가 존재하면 기존 학생 파일을 **삭제하거나 덮어쓰지 않습니다**. 새 코드가 없는 오래된 checkout에서는 변경 내용을 커밋/백업한 후 `git pull --ff-only origin main`으로 갱신합니다.
- `--self-check`는 정적 검사, `--doctor`는 ROS 2 설치 검사만 수행합니다. **`--run`만 실제 Gazebo/RViz·Nav2를 실행합니다.**
- GUI 창을 Ctrl+C로 종료할 때는 **터미널 A에서만** 입력합니다. 시나리오 실행기는 자신이 띄운 프로세스 그룹만 종료합니다. `pkill`·`wsl --shutdown`은 사용하지 않습니다.
- 자동 판단과 화면 관찰은 다릅니다. RViz Path DDS 1구독, 실제 LaserScan 및 Costmap·Planner 경로 3단계, Gazebo scene/info/pose의 실측을 확인하더라도 **학생 화면의 렌더된 로봇·장애물과 경로 변화는 육안으로 별도 확인**해야 합니다.
- 관찰할 로그: `D07_H01_GUI_AFTER_FREE_BASELINE_MARKER` → `D07_H01_GUI_OFFICIAL_PATH_PHASE` (before/intrusion/restored) → `D07_H01_GUI_H01_GEOMETRY_RETURNED_NO_GOAL` → `D07_H01_STUDENT_GAZEBO_RVIZ_L2_PASS`. 마지막 문자열은 **실제 검증을 통과한 경우에만** 출력됩니다.
- 개인 WSL2 GUI는 공개 CI Xvfb와 다르므로 CI 성공만으로 WSLg GPU 렌더링까지 성공했다고 판정하지 않습니다. `AXIA_MVP_DEMO_ACCEPTED=HOLD` 유지.

**터미널 B — 같은 학생 WSL2에서 읽기 전용 토픽 확인** (A의 세 단계 진행 중):

```bash
set +u
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=95
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 topic list -t | grep -E '(/scan|/odom|/global_costmap/costmap|/axia/d07/h01/path_visual|/clock)' || true
ros2 action list -t | grep compute_path_to_pose || true
ros2 topic info /axia/d07/h01/path_visual --verbose
ros2 topic echo /axia/d07/h01/path_visual --field header
# 관측 종료: Ctrl+C
```

동시에 다른 D06/G07 실행기를 같은 Domain에서 시작하지 않습니다. 터미널 B는 `ros2 action send_goal`, `ros2 topic pub`를 하지 않습니다.

**실패 진단:** 학생 원본 증거는 `~/axia_d07_h01_student_evidence/session-*/evidence/` 아래 `launch.log`, `staged_startup.log`, `d07_h01_geometry.log`, `d07_h01_geometry/phase_evidence.jsonl`, `d07_gui_watcher.log`에 남습니다. 창만 뜨고 3D 월드가 비었으면 SceneBroadcaster 및 Gazebo transport topics를 먼저 확인합니다. 실제 ROS 시계/Scan 첫 실패, Nav2 Lifecycle ACK, Costmap 업데이트, RViz Path subscriber의 **첫 위반**을 우선 기록합니다. 현장 동일 오류 무한 재시도 금지.

**검증 범위:** 실제 Gazebo H01이 성공해도 `goal_sent=false`, `robot_moved=false`, 소프트웨어 STOP≠인증된 Hardware E-Stop. 안전 계층 Scan→Supervisor→CM/Guard TTL·정상 종료의 전체 인수는 별도입니다. 전체 AXIA MVP 판정 `AXIA_MVP_DEMO_ACCEPTED=HOLD`.

---

## B. 보조 실습 — 공식 Nav2 L1 합성 Scan (Gazebo가 없는 PC용)

아래 기존 가이드는 **Gazebo 물리 시연이 아니라** 실제 공식 Nav2만 실행하는 보조 실습으로 유지합니다. L1과 물리 H01을 동일시하지 않습니다.

# AXIA Block B D07-H01 — 훈련생용 Nav2 경로 재계획 라이브 시연 가이드

**수업:** 2026-11-17 19:00–22:00 · D07 블록 B  
**공식 기준:** [D07-H01 강사용 라이브 가이드](https://github.com/silverbjin/axia-robot-safety-instructor/blob/main/training/block_B/instructor/D07_H01_INSTRUCTOR_LIVE_DEMO_GUIDE_KO.md)  
**플랫폼:** Ubuntu 24.04 WSL2 / ROS 2 Jazzy / 공식 Nav2 / Gazebo Harmonic(강사 H01만) / RViz2(강사 H01만)

> **필독 — 두 시연은 서로 다른 실행입니다.** 훈련생 독립 실행기는 공개 코드로 **공식 Nav2 PlannerServer와 Costmap의 ROS L1 라이브**를 직접 실행합니다. 이때 입력 LaserScan은 **합성**, Gazebo·RViz2·실제 Waffle 물리 장애물은 **실행하지 않습니다**. 강사가 별도로 시연하는 **H01 L2/L3**는 실제 Gazebo 물리 장애물과 Waffle LaserScan, 공식 Nav2 Costmap, `ComputePathToPose`, RViz2 경로를 관찰하는 **무주행** 장면입니다. 강사의 비공개 저장소/정답 코드를 훈련생에게 배포하거나 접근을 요구하지 않습니다.

## 1. 학습 목표와 검증 수준

- 사람을 **동적 장애물 대체물(proxy)** 로 표현한 후, LaserScan → ObstacleLayer/InflationLayer → Costmap → 공식 Nav2 Planner → `nav_msgs/Path`로 이어지는 데이터 흐름을 구분한다.
- **경로 재계획**과 **실제 장애물 회피 주행**을 구분한다. `ComputePathToPose`는 경로 계산 요청이고 `NavigateToPose`는 실제 로봇 이동 Goal이다.
- 강사 화면에서 Before → Intrusion → Restored를 비교하고, 각각의 **원본 증거/미검증 항목**을 구분해 기록한다.

| 검증 레벨 | 직접 실행하는 주체 | 실측으로 확인하는 것 | 확인되지 않은 것 |
|---|---|---|---|
| **학생 L0** | 학생 Python TODO | `routes.json`과 `route_todo.py`의 RED→GREEN | 실제 ROS·Gazebo |
| **학생 L1 라이브** | **훈련생 독립 실행** | 실제 ROS 2 Jazzy 공식 Nav2 PlannerServer·Costmap, **합성** /axia/d07/test/scan, 공식 `ComputePathToPose` 응답 | 실제 Gazebo·물리 LaserScan·RViz·로봇 이동 |
| **강사 H01 L2** | **강사 원샷** | 실제 Gazebo Waffle·물리 장애물·LaserScan → 공식 Costmap → `ComputePathToPose` → Path | Controller/Follower, 실제 이동·정지·안전 TTL |
| **강사 H01 L3 GUI** | 강사 WSL2/WSLg | Gazebo 3D 화면과 RViz2 Costmap/Path의 실시간 장면 관찰 | 독립적인 자동 픽셀 판정은 `D07_H01_OWNER_GUI_VISUAL_HOLD` |

**전체 안전 인수는 `AXIA_MVP_DEMO_ACCEPTED=HOLD`**. 이 자료는 인증된 하드웨어 E-Stop이나 `NavigateToPose` 이동/회피 성공을 가르치는 실증이 아니다.

## 2. 훈련생 독립 실행 — 공식 Nav2 L1 라이브 (터미널 S)

### 2.1 환경

- ROS 2 Jazzy가 설치된 Ubuntu 24.04 WSL2, Python 3, git, bash, `timeout`.
- 학생 전용 공개 저장소: `silverbjin/axia-robot-safety-student`, `main`.
- 강사용 비공개 GitHub 로그인·Instructor 정답·Gazebo 설치 **불필요**(학생 L1만 실행하는 경우).
- 최초 1회 ROS 공식 Planner 플러그인이 누락된 경우에만 다음 설치를 한다. 기존 설치를 전체 재설치하지 않는다.

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  ros-jazzy-nav2-planner ros-jazzy-nav2-navfn-planner \
  ros-jazzy-nav2-costmap-2d ros-jazzy-nav2-msgs \
  ros-jazzy-tf2-ros ros-jazzy-rclpy ros-jazzy-nav-msgs \
  ros-jazzy-geometry-msgs ros-jazzy-sensor-msgs \
  ros-jazzy-action-msgs ros-jazzy-ros2lifecycle
```

### 2.2 훈련생 독립 실행 원샷 (한 번에 복사)

기존 `~/axia_d07_student_lab`이 있으면 **파일을 덮어쓰거나 reset하지 않습니다**. 디렉터리가 없으면 공개 `main`만 내려받습니다. 기존 파일을 수정한 경우에는 자동 병합하지 않고 그 상태를 보존합니다.

```bash
(
  set -Eeuo pipefail
  ROOT="$HOME/axia_d07_student_lab"
  if [[ ! -e "$ROOT" ]]; then
    git clone --single-branch --branch main \
      https://github.com/silverbjin/axia-robot-safety-student.git "$ROOT"
  fi
  test -d "$ROOT/.git"
  cd "$ROOT"
  test "$(git branch --show-current)" = main || {
    echo "D07_STUDENT_WRONG_BRANCH: 기존 실습 브랜치 보존"; exit 3;
  }
  git rev-parse HEAD
  bash -n block_B/day07/run_d07_student_live_once.sh
  bash block_B/day07/run_d07_student_live_once.sh --self-check
  bash block_B/day07/run_d07_student_live_once.sh --doctor
  bash block_B/day07/run_d07_student_live_once.sh --run
)
```

기존 폴더에 **새 가이드가 아직 없을 때만** 훈련생이 변경 파일을 보호한 뒤 `git pull --ff-only origin main`으로 갱신한다. 자동 `reset --hard`, `git clean`, `pkill`, `wsl --shutdown`은 사용하지 않는다. 위 명령은 기존 파일을 강제로 갱신하지 않으므로 학생 TODO를 보존한다.

이 실행기는 공개 Nav2 코드 SHA **`158b7c6032d987177d1e1302bf85fd741120fd9e`**를 임시 체크아웃하고 공식 PlannerServer를 구동한다. `--self-check`는 구문 확인만, `--doctor`는 설치 확인만, **`--run`만 실제 ROS 2를 실행**한다. No Goal / No cmd_vel / No Gazebo 조건을 검사하고 실제 L1 결과가 유효할 때만 성공을 출력한다.

### 2.3 라이브에서 확인할 실제 출력

**예상 메시지 형식**(개인 WSL2에서 미실행 상태라면 성공 실측으로 보고하지 않는다):

```text
D07_STUDENT_LIVE_STATIC_PASS NAV2_NOT_RUN_GAZEBO_NOT_RUN NO_GOAL
D07_STUDENT_DOCTOR_READY ROS_JAZZY_OFFICIAL_NAV2_PRESENT NAV2_NOT_RUN_GAZEBO_NOT_RUN NO_GOAL
D07_STUDENT_PUBLIC_NAV2_SOURCE_VERIFIED=158b7c6032d987177d1e1302bf85fd741120fd9e
D07_REAL_NAV2_STAGE {"stage": "clear_before", ...}
D07_REAL_NAV2_STAGE {"stage": "person_blocking", ...}
D07_REAL_NAV2_STAGE {"stage": "person_cleared", ...}
D07_NAV2_L1_VERDICT {"status": "PASS_OFFICIAL_NAV2_COSTMAP_REPLAN_L1", "ros_actual": true, "gazebo_actual": false, ...}
D07_STUDENT_NAV2_L1_REAL_PASS lethal=.../.../... path=.../.../... NO_GAZEBO NO_GOAL
```

- `clear_before`: 합성 장애물 없음, 공식 Costmap 위험 셀이 거의 없음.
- `person_blocking`: 합성 LaserScan이 장애물을 표시하고, 실제 Nav2 Costmap lethal cell 증가와 경로 우회가 나타남.
- `person_cleared`: 합성 스캔 clearing 후 Costmap이 복원되는지 확인.
- 수업 참고 실측값은 **lethal 0→101→0, Path 58→74→58**. 로컬 Nav2 버전에 따라 정확한 점 수가 달라질 수 있으므로, 실행기는 값 자체를 강제하지 않고 **장애물 marking/clearing과 경로 우회 조건**으로 판정한다.

**통과 기준:** 실제 `ros_actual=true`, 공식 Costmap publisher/Scan subscriber 확인, 세 `ComputePathToPose` Action 성공, Path 우회 조건 충족, `gazebo_actual=false`, `goal_sent=false`, `navigate_to_pose_sent=false`, `cmd_vel_published=false` 유지.

**원본 증거:** `~/axia_d07_student_live_evidence/session-*/actual_ros_l1/verdict.json`, `actual_ros_l1.stdout.log`, `planner_server.log`, `SHA256SUMS`. 실패 시 `D07_STUDENT_NAV2_L1_BLOCKED` / `D07_STUDENT_LIVE_STATUS=HOLD`이며 이전 성공 결과로 승격하지 않는다.

## 3. 강사 H01 — Gazebo + RViz2 실제 화면 관찰 (별도 세션)

이 부분은 **강사가 강사용 라이브 가이드에 있는 공식 원샷으로 실행**한다. 학생 공개 실행기는 강사 세션이나 물리 월드에 접속하여 장애물을 이동시키지 않는다. 학생은 강사의 스크린 공유/빔 프로젝터로 확인한다.

### 화면에서 찾아볼 세 단계

| 단계 | Gazebo 화면 | RViz2 화면 | 실제 증거의 의미 |
|---|---|---|---|
| **Before** | 정지 Waffle, 경로 부근에 장애물이 침입하지 않은 초기 상태 | LaserScan·Global Costmap·기준 `Path` | 공식 Planner가 생성한 최초 후보 경로 |
| **Intrusion** | 기존 실행기가 **물리 장애물 proxy**를 경로에 이동 | Scan 장애물, lethal Costmap 셀 증가, `Path` 우회 | **실제 Gazebo 물리 센서 입력에 따른 경로 재계획** |
| **Restored** | 물리 장애물 제거 | Scan/costmap clearing, `Path` 복원 | 공식 Costmap의 clearing과 경로 복원 |

강사 기존 고정 증거의 예: 세 단계 Path 각 **52 poses**, Intrusion 신규 lethal **92**, Restored 잔차 **0**, 경로 편차 **0.3659m**. 이는 **이전 강사 원본 실행의 실측값**이며 각 훈련생 L1 실행의 결과가 아니다. Gazebo 창이 있다는 사실만으로 물리 로봇·장애물 로딩이나 Scan 전달을 입증하지 않는다.

**주의:** H01의 Waffle은 정지 상태다. `goal_sent=false`, `robot_moved=false`. `ComputePathToPose`는 ***계획 질의***, `NavigateToPose`·`FollowPath`는 ***실제 주행 계층***이다. H01에서 움직이는 것은 장애물이지 로봇이 아니다.

### 선택 — 강사의 **같은 WSL2/ROS 그래프**에서 터미널 B를 읽기 전용으로 사용

**강사가 허락한 공유 실습 PC에서만** 사용할 것. 각 훈련생 노트북의 `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`는 강사 PC의 ROS 그래프에 연결되지 않는다. 각자 노트북에서 아래 명령으로 H01을 관찰했다고 보고하면 안 된다.

```bash
set +u
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=95
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST

ros2 topic list -t | grep -E '(/scan|/global_costmap/costmap|/axia/d07/h01/path_visual|/clock)' || true
ros2 action list -t | grep -E 'compute_path_to_pose' || true
ros2 topic info /axia/d07/h01/path_visual --verbose
ros2 topic echo /axia/d07/h01/path_visual --field header
# 관찰 종료는 이 터미널에서 Ctrl+C
```

이 터미널은 **구독/조회 전용**이다. 학생은 `ros2 action send_goal`, `ros2 topic pub`, `/cmd_vel`, `NavigateToPose`, Gazebo `set_pose`를 실행하지 않는다.

## 4. 기록 및 발표 (5~10분)

개인 제출은 아래 증거를 분리하여 작성한다.

| 항목 | 기록할 것 |
|---|---|
| 독립 L1 | 학생 저장소 `git rev-parse HEAD`, 실행기 고정 공개 SHA, `verdict.json`과 `SHA256SUMS` |
| H01 관찰 | 강사 화면의 Before/Intrusion/Restored 변화, 최초 관측한 Scan/Costmap/Path |
| 검증 구분 | 합성 Scan L1 vs 실제 Gazebo LaserScan H01, Planner 경로 vs 실제 주행 |
| 미검증 | Controller 이동, 최종 속도·Odometry, Sensor→Supervisor→Guard TTL, 실제 GUI 자동 픽셀 판정 |
| 실패 시 | 최초 실패 메시지, 실제 단계, 증거 원본 SHA; 같은 실패를 WSL2에서 무작정 재시도하지 않음 |

과제 코드는 기존 `block_B/day07/route_todo.py`의 **두 TODO**만 구현한다. 정답이나 private 소스를 복사하지 않는다. 관련 수업 실습: [D07 훈련생 실습 가이드](D07_STUDENT_PRACTICE_GUIDE_20261117_KO.md). 훈련생 L1 실행 성공은 학생 TODO GREEN 또는 강사 H01 L2·L3 성공과 별개이다.

## 5. 종료·장애 대응

- 독립 L1 실행기는 자신이 시작한 **공식 PlannerServer**만 종료하고 테스트 증거를 보존한다. 학생은 강사용 Gazebo/RViz 세션의 종료 신호를 보내지 않는다.
- 토픽이 없으면 우선 실행기 stderr/PlannerServer lifecycle 오류 및 정확한 ROS_DOMAIN_ID를 본다. L1의 격리 Domain ID는 실행기가 자체 설정하므로 **별도 터미널에서 강사 H01용 ID=95를 사용해 L1에 연결하지 않는다**.
- 강사 실제 H01의 GUI가 검게 나오거나 로봇이 보이지 않으면 강사에게 알리고, 동일 오류를 현장에서 반복하지 않는다. 공개 CI 검증 원본을 이용해 해설하되 '현장 Live PASS'라고 기록하지 않는다.
- 실제 정지/인증 안전은 별도 검증 대상이다. **SW Stop ≠ 인증된 하드웨어 E-Stop.**
- 공개 증거: 강사 [실제 Gazebo H01 L2 CI #43912555634](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43912555634). Owner GUI는 자동 `VISUAL_HOLD`가 남는다. 학생 독립 L1 CI 결과는 공개 학생 저장소의 `D07 H01 student public live guide and actual Nav2 L1` 워크플로에서 확인한다.

**최종 판정 표기:** 학생 독립 L1이 통과하면 `D07_STUDENT_NAV2_L1_REAL_PASS`; 강사 H01 L2/L3 또는 통합 안전 인수는 자동 승격하지 않는다. 전체 `AXIA_MVP_DEMO_ACCEPTED=HOLD`.
