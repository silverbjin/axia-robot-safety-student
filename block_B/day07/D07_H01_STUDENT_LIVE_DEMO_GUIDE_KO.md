# D07-H01 — 훈련생 독립 Gazebo + RViz2 실제 물리 경로 재계획 라이브

**이 문서의 기본 시연은 이제 ROS L1 합성 예제가 아니라 학생 PC에서 직접 실행하는 Gazebo Harmonic 물리 H01입니다.** 강사가 사용한 H01 시연 코드 중 실행에 필요한 허가된 최소 소스를 `block_B/day07/h01_runtime/`에 공개해, 비공개 Instructor 권한·GitHub 토큰 없이 실행합니다. `route_todo.py` 정답과 hidden tests는 공개하지 않습니다.

## A. 학생 PC에서 실제 Gazebo·RViz2를 동시에 실행 (최우선)

**환경:** Windows WSL2 Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic / 공식 Nav2 / WSLg DISPLAY / RViz2 / colcon. 학생은 화면에 **실제 Waffle(TurtleBot3), Gazebo 물리 원통 장애물, RViz2 LaserScan·Global Costmap·공식 Nav2 Path**를 함께 확인합니다. **Before → Intrusion → Restored**: 로봇은 정지, 기존 실행기가 Gazebo 원통 장애물을 이동·제거합니다. Nav2 `ComputePathToPose`는 계획 경로만 계산합니다. `NavigateToPose`, `FollowPath`, `/cmd_vel` 주행 Goal, fault injection, 인증 E-Stop은 수행하지 않습니다. `NO_GOAL`.

**준비(최초 1회, 필요한 경우에만):** 공식 Jazzy Nav2의 현대 Gazebo(Harmonic) 배포 패키지를 사용하며, 이전 Gazebo Classic 전용 `turtlebot3_gazebo` 패키지는 이 H01의 필수 의존성이 아닙니다.

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  git python3-colcon-common-extensions \
  ros-jazzy-navigation2 ros-jazzy-nav2-bringup \
  ros-jazzy-nav2-minimal-tb3-sim ros-jazzy-ros-gz \
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

## A-2. 연속 라이브 시연: rqt_graph로 실제 ROS 아키텍처 분석

이제 터미널 A의 `--run`은 **처음 검증된 Before → Intrusion → Restored가 끝나도 종료되지 않습니다.** 같은 Gazebo Harmonic·정지 Waffle·공식 Nav2·RViz2 프로세스를 유지한 채 이미 실제 검증된 원통 위치 **주행 경로 안(Intrusion) ↔ 경로 밖(Restored)** 사이를 번갈아 이동하고, 매번 **실제 /scan → Costmap 갱신 후 공식 `ComputePathToPose`**로 새로운 `nav_msgs/Path`를 받습니다. 세 상태(Before/Intrusion/Restored)가 반복되므로 rqt_graph를 켜고 화면을 분석할 시간이 있습니다.

- **기본값:** `AXIA_D07_H01_CLASSROOM_MAX_CYCLES=0` = 무제한 반복. 시연 종료는 **실행 중인 터미널 A에서 `Ctrl+C`**, 원통을 원위치로 복귀시키고 실행기가 소유한 Gazebo·Nav2·RViz 프로세스만 종료합니다.
- **수업용 선택:** `AXIA_D07_STUDENT_PHASE_HOLD_S=10`은 각 공식 Path를 10초간 화면에 유지합니다(5~15초). 원하는 경우 실행 전에 `export AXIA_D07_STUDENT_PHASE_HOLD_S=15`로 조정하십시오. **안전 TTL 값과 무관**합니다.
- **공개 CI 검증용:** `AXIA_D07_H01_CLASSROOM_MAX_CYCLES=2`는 *같은* Gazebo 세션에서 두 번의 실제 원통 왕복과 공식 경로 6개를 검증하고 자동 종료합니다. 학생은 기본값 0을 사용해 `Ctrl+C`로 종료합니다.
- 성공 단계별 메시지는 `D07_H01_CLASSROOM_LOOP_READY`, `D07_H01_CLASSROOM_REAL_PLAN`, `D07_H01_CLASSROOM_CYCLE_PASS`이며, 반복 단계는 `classroom_replan_cycles.jsonl`에 누적됩니다. 실제 시연이 아직 실행되지 않았거나 새 장애물이 Costmap에 반영되지 않으면 반복 성공이라고 보고하지 않습니다.

### 터미널 B — rqt_graph 실행 (A가 종료되지 않은 상태)

한 번만 설치합니다. **rqt_graph는 실제 ROS 2 DDS 노드·토픽 그래프를 읽는 도구이며 Gazebo transport의 원시 /world 토픽을 표시하지 않습니다.**

```bash
sudo apt-get install -y ros-jazzy-rqt-graph
set +u
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=95
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 run rqt_graph rqt_graph
# B의 Ctrl+C는 그래프 창만 닫는다. H01 자체 종료는 A의 Ctrl+C.
```

rqt_graph 상단에서 먼저 **Nodes/Topics (all)** 또는 **Nodes/Topics (active)**를 선택하고 **Refresh(새로고침)** 버튼을 누릅니다. 뷰 우측 또는 상단의 두 필터는 **Node filter(노드/네임스페이스 필터)**와 **Topic filter(토픽 필터)**입니다. 두 입력 칸의 기본 `/`는 전체를 의미하며, 필터는 **쉼표(,)로 여러 이름 또는 정규식 패턴을 묶을 수 있고**, `.*`는 임의 문자열, `-`로 시작하는 토큰은 제외 패턴입니다. 아래 텍스트는 명령어가 아니라 해당 **GUI 필터 입력 칸에 그대로 붙여 넣는 값**입니다. 입력 뒤 Enter(또는 포커스 이동)→Refresh를 눌러 적용하세요. rqt_graph의 실제 필터 코드는 [rqt_graph dotcode.py](https://github.com/ros-visualization/rqt_graph/blob/rolling/src/rqt_graph/dotcode.py)의 쉼표/정규식 include·exclude 규칙을 사용합니다.

기본 **Hide Debug**를 켜서 `/rosout`·`/parameter_events`를 감추고, 특정 토픽이 안 보이면 **Hide leaf topics / Hide dead sinks**를 순서대로 해제하세요. 토픽에는 publisher만 있거나 subscriber만 있을 수 있어 **숨겨졌다는 이유로 미발행·고장을 단정하지 않습니다**. `Group Actions`를 켜거나 꺼서 액션 그룹 표시를 비교하세요. `ComputePathToPose` 액션 서비스 통신은 일반 Topic만으로 모두 설명되지 않으므로 CLI `ros2 action info`도 같이 확인합니다.

### 관찰 1 — 인지와 계획 계층: Gazebo Waffle LaserScan → Costmap → 경로

**Node filter 입력:**
```text
/ros_gz_bridge,/planner_server,.*global_costmap.*,.*axia_d07_h01_classroom_planner_no_goal.*,.*rviz.*
```

**Topic filter 입력:**
```text
/scan,/global_costmap/costmap,/axia/d07/h01/path_visual,/compute_path_to_pose/.*
```

<text>**관찰·해설:** Gazebo Harmonic의 물리 LiDAR는 `ros_gz_bridge`를 통해 ROS `/scan`을 발행하고, 공식 Nav2 `global_costmap`의 ObstacleLayer가 이를 사용합니다. 경로 계획 요청은 `/compute_path_to_pose` 액션으로 `planner_server`에 전달됩니다. `/axia/d07/h01/path_visual`은 **공식 액션의 실제 결과 Path를 RViz로 전달하는 표시용 토픽**이지 직접 로봇을 제어하는 명령이 아닙니다. 장애물 진입·제거를 반복할 때 `Path`의 메시지 타임스탬프와 장면이 변하는지 확인합니다. `rqt_graph`는 데이터 연결을 보여주지만 그 메시지의 숫자 값이나 장애물 회피의 충돌 안전성을 보증하지 않습니다.</text>

### 관찰 2 — 내비게이션과 제어 계층: Planner/Controller/Smoother → 안전 명령 체인

**Node filter 입력:**
```text
/planner_server,/bt_navigator,/controller_server,/velocity_smoother,/axia_safety_supervisor,/collision_monitor,/axia_base_command_guard,/ros_gz_bridge
```

**Topic filter 입력:**
```text
/cmd_vel_smoothed,/cmd_vel_supervised,/cmd_vel_pre_guard,/cmd_vel,/odom,/compute_path_to_pose/.*
```

**관찰·해설:** Nav2 `planner_server`는 **경로를 계산**합니다. 일반적인 주행 구조에서는 `bt_navigator`와 `controller_server`가 `NavigateToPose`/FollowPath 관련 행위를 수행하고, `velocity_smoother` 출력 `/cmd_vel_smoothed`가 Supervisor로 전달됩니다. 다음 `/cmd_vel_supervised` → `collision_monitor` → `/cmd_vel_pre_guard` → `axia_base_command_guard` → `/cmd_vel`은 **안전 제어가 실제 주행 명령보다 뒤에 놓이는 배선 구조**입니다. 단, H01은 `NavigateToPose`를 호출하지 않으며 `goal_sent=false`, `robot_moved=false`입니다. rqt_graph에서 `/cmd_vel` 화살표가 보이더라도 **실제 속도 발생·안전 성능 PASS 증거가 아닙니다**. 일부 노드가 Action/Service 위주라 토픽 그래프에서 고립되어 보일 수 있습니다.

### 관찰 3 — 안전과 물리 증거 계층: Scan TTL 관측 대상·Guard·실제 시뮬레이션

**Node filter 입력:**
```text
/ros_gz_bridge,/axia_safety_supervisor,/collision_monitor,/axia_base_command_guard,/axia_p2_readonly_observer,.*axia_d07_h01_classroom_planner_no_goal.*
```

**Topic filter 입력:**
```text
/clock,/odom,/scan,/safety/scan,/cmd_vel_supervised,/cmd_vel_pre_guard,/cmd_vel,/axia/p2/base_guard
```

**관찰·해설:** `/clock`은 시뮬레이션 시간, `/odom`은 실제 로봇 오도메트리, `/scan`과 `/safety/scan`은 원본/안전 계층 입력을 각각 살펴볼 단서입니다. `axia_safety_supervisor`, `collision_monitor`, `axia_base_command_guard` 사이의 배선은 실제 코드의 안전 흐름을 이해하는 데 필요합니다. **표시된 노드/토픽 존재만으로 Scan→Supervisor→CM→Guard의 TTL 또는 인증된 E-Stop을 검증한 것은 아닙니다.** 실제 움직임은 없는 무주행 H01이므로 모터 안전 시험과 혼동하지 마세요. Gazebo의 **원통 `set_pose` 서비스 및 `/world/default/pose/info`는 ROS DDS 밖의 Gazebo transport**이므로 rqt_graph에 직접 나타나지 않습니다.

### 터미널 C — 세 단계의 원본 DDS / Gazebo transport 확인

다른 창에서 **읽기 전용**으로 실행합니다. 값이 나타나지 않으면 A의 준비 상태, 동일 `ROS_DOMAIN_ID`와 실제 토픽 광고를 먼저 확인하고 임의 토픽 발행은 하지 않습니다.

```bash
set +u; source /opt/ros/jazzy/setup.bash; set -u
export ROS_DOMAIN_ID=95 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 node list | grep -E 'planner_server|global_costmap|collision_monitor|axia_'
ros2 topic list -t | grep -E 'scan|costmap|path_visual|cmd_vel|odom|clock|base_guard'
ros2 topic info /scan --verbose
ros2 topic info /global_costmap/costmap --verbose
ros2 topic info /axia/d07/h01/path_visual --verbose
ros2 action info /compute_path_to_pose
timeout 8s ros2 topic hz /scan || true
gz topic -l | grep -E '/world/default/(pose|scene)|/axia_p2_g07/contacts' || true
```

**실습 과제:** 한 번의 Intrusion 전후에 `/scan`, `/global_costmap/costmap`, `/axia/d07/h01/path_visual`의 토픽을 찾아 각각 발행 노드와 구독 노드를 설명하고, 경로 변경이 왜 **로봇 이동 성공과 다른지** 발표합니다. 다음 반복에서는 rqt_graph 노드/토픽 필터를 1→2→3 순서로 바꿔 데이터 흐름을 추적합니다. 화면과 근거 파일 `classroom_replan_cycles.jsonl`을 함께 남기세요. 중간에 종료하려면 터미널 A에서 **Ctrl+C**.

**안전·검증 경계:** rqt_graph는 ROS 그래프 관찰용이고 Gazebo transport service ACK/실제 물리 Contact/타이밍 검증용 도구가 아닙니다. `/cmd_vel`·`NavigateToPose` 송신 금지, SW 정지와 인증 E-Stop 혼동 금지, `AXIA_MVP_DEMO_ACCEPTED=HOLD` 유지. 공개 CI는 Xvfb의 rqt_graph 창 존재와 실제 토픽만 확인하고 **학생 WSLg에서 필터를 실제 클릭한 화면은 육안 인수 대상**입니다.

---

## 학생 L0/L1/L2/L3 증거 분리 계약

훈련생 독립 실행의 **우선순위는 물리 H01 Gazebo/RViz**입니다. `ROS_DOMAIN_ID=95`는 동일한 학생 WSL2의 읽기 전용 터미널과 공유하되 서로 다른 PC에서 같은 토픽이 자동으로 발견된다고 가정하지 않습니다.

| 구분 | 실제 실행 | 합격 또는 미검증 범위 |
|---|---|---|
| L0 | 학생 TODO 테스트 | 실제 Gazebo/ROS 미실행 |
| L1 | 공식 Nav2, **합성** LaserScan | `D07_STUDENT_NAV2_L1_REAL_PASS`는 *Gazebo 물리 시연 성공이 아님* |
| L2 | **훈련생 독립 실행**, 실제 Gazebo Harmonic·Waffle·LaserScan·공식 Nav2 경로·RViz2 | `goal_sent=false`, 세 단계 실측과 창을 같은 세션에서 검증 |
| L3 | 학생 WSL2/WSLg 화면 육안 인수 | 공개 CI의 Xvfb 렌더러와 다름. `VISUAL_HOLD` 상태로 남겨 학생 자신의 실제 화면을 확인 |

H01의 `ComputePathToPose`는 경로 *계산*일 뿐 `NavigateToPose`는 보내지 않습니다. 학생 시연은 정지한 Waffle의 물리 장애물 이동·경로 재계획만 확인하며 실제 주행/충돌회피를 인수하지 않습니다. 안전 스캔 TTL·Supervisor·Collision Monitor·Guard의 통합 증거가 없으면 `AXIA_MVP_DEMO_ACCEPTED=HOLD`를 유지합니다.

## B. 대체 수업 — Gazebo가 없는 PC의 공식 Nav2 L1

이 부분은 **실제 Gazebo/RViz2 H01을 대체하여 동등한 성공이라고 보고하는 시연이 아닙니다.** 수업 장비의 Gazebo·WSLg가 준비되지 않은 경우에만, 공식 ROS 2 Jazzy Nav2 PlannerServer와 Costmap을 실제 실행하고 **합성 LaserScan**으로 경로 재계획 알고리즘을 설명합니다.

```bash
cd "$HOME/axia_d07_student_lab"
bash block_B/day07/run_d07_student_live_once.sh --self-check
bash block_B/day07/run_d07_student_live_once.sh --doctor
bash block_B/day07/run_d07_student_live_once.sh --run
```

학생용 별도 합성 L1 설명은 [기존 D07 학생 데모 가이드](D07_STUDENT_DEMO_GUIDE_20261117_KO.md)와 [실습 TODO 가이드](D07_STUDENT_PRACTICE_GUIDE_20261117_KO.md)를 따릅니다. 합성 L1 공개 CI [#44036198722](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44036198722)는 **Costmap 0→101→0, Path 58→74→58, 실제 Planner와 합성 Scan**을 확인했습니다. 실제 Gazebo H01에서는 물리 Scan과 공식 Path, RViz 표시를 별도로 측정하며 과거 L1 숫자를 재사용하지 않습니다.

## C. 검증 보고와 인수 한계

학생에게 공개한 물리 H01의 실제 검증은 학생 저장소 공개 GitHub Actions `D07 H01 student REAL physical Gazebo Waffle Nav2 Path RViz2 NO-GOAL`의 동일 SHA 실행에서 판단합니다. Xvfb의 창 생성과 ROS L2 메시지 검증은 **WSL2/WSLg 실제 픽셀 표시**를 보증하지 않습니다. 학생 화면을 한 번 관찰하고 창·Waffle·원통 장애물·Path를 기록한 뒤 본인 결과를 별도로 판정합니다. 로봇 주행, 충돌 접촉 안전성, Scan→Supervisor→CM/Guard TTL, 인증 E-Stop은 해당 시연의 인수 범위를 벗어납니다.

`AXIA_MVP_DEMO_ACCEPTED=HOLD`
