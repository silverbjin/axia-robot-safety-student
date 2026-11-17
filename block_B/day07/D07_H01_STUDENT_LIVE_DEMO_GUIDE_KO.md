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

## A-2. rqt_graph 아키텍처 분석 — Ctrl+C 전까지 반복되는 실제 물리 시연

이제 `--run`은 **기존 물리 H01의 Before/Intrusion/Restored 세 단계가 실측 PASS한 다음**, Gazebo와 Nav2와 RViz2를 **종료하지 않고** 물체의 위치를 `Free → Intrusion → Lateral(+0.12m) → Restored`로 순환한다. 각 물리 위치에서는 **새 Gazebo set_pose ACK, 실제 /scan·/global_costmap/costmap 신선도, 공식 ComputePathToPose 액션 응답**을 얻어 `/axia/d07/h01/path_visual`에 원본 Path를 새로 게시한다. 이는 학생의 ROS graph 관찰 시간을 확보하는 **교육용 반복**이며 이전 3단계 인수 증거와 별도 로그로 저장한다. 경로가 위치마다 반드시 달라진다고 가정하지 말고, 실제 Path와 Costmap을 비교한다.

- **실행 순서:** 터미널 A에서 `bash .../run_d07_h01_gazebo_rviz_student_once.sh --run` → Gazebo+RViz가 실제 준비되면 터미널 B에서 `rqt_graph` 실행 → 필터를 단계별로 바꾼다 → **종료는 터미널 A에서 Ctrl+C**. 임의의 초·회수만큼 진행했다고 자동 종료되지 않는다. 공개 CI만 동일 런타임을 1회 물리 반복 후 종료해 검증한다.
- **화면 유지:** 기본 각 위치 10초(`AXIA_D07_STUDENT_PHASE_HOLD_S=15`로 단계당 15초 설정 가능). 분석 도중 다른 단계로 넘어가더라도 rqt_graph의 **노드와 토픽 연결 구조 자체는 유지**된다. 창이 닫히면 최초 로그 원인을 확인한다.
- **사전 설치:** `sudo apt-get install -y ros-jazzy-rqt-graph`. 여러 버전이 있다면 `ros2 pkg prefix rqt_graph`로 Jazzy 패키지를 확인한다. `rqt_graph`는 로봇을 조종하지 않는 ROS 그래프 조회 툴이다.

### 터미널 B — rqt_graph 공통 시작 명령 (터미널 A가 실행 중일 때)

```bash
set +u
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=95
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 node list --no-daemon | head -n 50
ros2 topic list -t | grep -E '(/scan|/odom|/clock|/cmd_vel|/costmap|/axia/d07/h01/path_visual)' || true
ros2 run rqt_graph rqt_graph
# rqt_graph 종료는 이 터미널의 Ctrl+C 또는 창 닫기
# 실제 H01 전체 종료는 터미널 A의 Ctrl+C
```

rqt_graph 상단에서 **`Nodes/Topics (all)`** 을 선택하고 새로 고침(Refresh)을 누른다. 첫 번째 텍스트 입력창이 **노드 필터**, 두 번째가 **토픽 필터**다. 기본값 `/`은 전체를 표시한다. **쉼표로 여러 이름 패턴을 나열**하고 앞에 `-`를 붙이면 해당 패턴을 제외할 수 있다(예: `-/rosout,-/parameter_events`). `Hide Debug`를 켜서 노이즈를 줄이되, 단독 퍼블리셔·안전 증거가 안 보일 때는 `Hide Leaf topics`, `Hide Dead sinks`를 **해제**한다. `Actions`와 `tf` 묶음 표시 여부에 따라 다이어그램의 이름·간선 수가 달라진다. 텍스트 입력 후 Enter/Refresh를 누르고 화면이 비면 필터를 `/`로 되돌려 실제 토픽을 확인한다.

### 1단계: 인지·계획 계층 (Perception → Planning)

| rqt_graph 설정 | 입력 |
|---|---|
| 노드 필터 | `/` (ROS 퍼블리셔와 구독자 양 끝을 유지), 이후 필요한 경우 `/planner_server,/global_costmap` |
| 토픽 필터 | `/scan,/safety/scan,/global_costmap/costmap,/axia/d07/h01/path_visual` |
| 표시 | `Nodes/Topics (all)`, `Hide Debug` 켬, `Hide Leaf topics` 해제 |

**해설:** Gazebo Waffle LiDAR → ROS `/scan` (실제 센서) → Nav2 ObstacleLayer·InflationLayer가 갱신하는 `/global_costmap/costmap` → 공식 `/compute_path_to_pose` 액션으로 얻은 Path → 별도 `/axia/d07/h01/path_visual` 게시 → RViz 구독. **Costmap 업데이트와 Planner Path 게시가 동일 ROS 토픽 연결은 아니다.** Costmap은 PlannerServer가 내부적으로 참조하고, Planner 결과는 Action 응답 뒤 시연 노드가 읽기 전용 Path 토픽에 전달한다.

```bash
ros2 topic info /scan --verbose
ros2 topic info /global_costmap/costmap --verbose
ros2 topic info /axia/d07/h01/path_visual --verbose
ros2 action info /compute_path_to_pose
```

**관찰 과제:** Intrusion 때 원통에 대응하는 costmap 표시가 바뀌는지, Lateral에서는 이전과 다른 위치의 장애물이 인식되는지, restored에서 clearing되는지 구분한다. 경로가 같은 52 poses여도 **좌표는 달라질 수 있으므로 개수만으로 우회 여부를 판정하지 않는다**.

### 2단계: 네비게이션·제어 계층 (Navigation → Control)

| rqt_graph 설정 | 입력 |
|---|---|
| 노드 필터 | `/`, 필요한 노드만 강조할 때 `/planner_server,/controller_server,/collision_monitor` |
| 토픽 필터 | `/compute_path_to_pose,/plan,/cmd_vel_supervised,/cmd_vel_pre_guard,/cmd_vel,/odom` |
| 표시 | `Nodes/Topics (all)`; Action 연결을 보려면 `Actions` 묶음 켬/끔 비교 |

**해설:** `ComputePathToPose`는 **계획 요청과 응답**이며 `NavigateToPose`는 경로 추종을 실제로 개시할 수 있는 **이동 Goal**이다. 이 시연에서는 이동 Goal을 보내지 않아 `controller_server`·`collision_monitor`·`base_guard` 노드가 존재하더라도 **주행 제어 성공의 증거가 아니다**. `/cmd_vel_supervised` → `/cmd_vel_pre_guard` → `/cmd_vel`은 안전 출력 체인의 *배선*이며 실제 속도·모터 명령 활성화로 오해하지 않는다. 표시가 안 되는 Action은 `ros2 action list -t`·`ros2 action info /compute_path_to_pose`로 교차 검증한다.

```bash
ros2 action list -t
ros2 node list | grep -E 'planner|controller|collision_monitor|guard|supervisor' || true
ros2 topic info /cmd_vel --verbose
ros2 topic info /odom --verbose
```

**관찰 과제:** Planner Path가 수차례 갱신되어도 로봇의 `/odom` 위치와 `/cmd_vel`을 별도로 확인해야 한다. `rqt_graph`의 간선은 데이터 통신 관계이지 명령 발행 빈도나 로봇 이동량을 보증하지 않는다.

### 3단계: 안전·물리 증거 계층 (Safety → Physics)

| rqt_graph 설정 | 입력 |
|---|---|
| 노드 필터 | `/`, 비교용 `/collision_monitor,/p2_base_guard` 등은 실제 `ros2 node list` 출력에 따라 선택 |
| 토픽 필터 | `/safety/scan,/axia/safety/state,/axia/p2/base_guard,/cmd_vel_supervised,/cmd_vel_pre_guard,/cmd_vel,/odom,/clock` |
| 표시 | `Nodes/Topics (all)`, `Hide Debug` 켬, **`Hide Leaf topics` 해제**, `tf`는 필요할 때만 표시 |

**해설:** Supervisor의 `/axia/safety/state`, Collision Monitor 출력 `/cmd_vel_pre_guard`, Base Guard 최종 `/cmd_vel`, Gazebo/ROS `/odom`·`/clock`을 각기 독립적인 증거로 해석한다. 무주행 H01에서는 **SW Stop ≠ 인증된 E-Stop**, 이 그래프만으로 150ms CM TTL·300ms Scan TTL이나 비상정지 지연을 판정할 수 없다.

**Gazebo 물리 세계는 별개의 Transport 그래프다.** `/world/default/set_pose`, `/world/default/scene/info`, `/world/default/pose/info` 등 Gazebo native 서비스·토픽은 ROS 2 `rqt_graph`에 직접 나타나지 않을 수 있다. 다음 CLI로 **같은 `GZ_PARTITION`**을 설정하여 Gazebo 측을 따로 확인한다. (`/world/default/set_pose`는 관찰하지 호출하지 않는다.)

```bash
# 같은 학생 WSL2의 실제 시연 환경과 GZ_PARTITION을 맞춘 경우에만
gz topic -l | grep -E '/world/default/(scene|pose)/info|/clock' || true
gz service -l | grep '/world/default/set_pose' || true
ros2 topic info /axia/p2/base_guard --verbose
ros2 topic info /clock --verbose
```

**필터로 숨긴 노드는 종료된 것이 아니다.** rqt_graph의 필터링은 화면 편집일 뿐 ROS Safety Supervisor·Nav2·CM의 실행 설정이나 TTL을 바꾸지 않는다. `/rosout`·`/parameter_events` 노이즈를 제외하고 다시 전체 그래프로 돌아가 토픽 연결·미연결을 비교한다.

### 수업 증거·안전 범위

학생 시연 `~/axia_d07_h01_student_evidence/session-*/evidence/d07_h01_geometry/teaching_cycle_evidence.jsonl`에 반복마다 `cycle`, `stage`, 실제 native pose ACK, LaserScan/Costmap stamps, 공식 Path 좌표 개수, RViz 구독 수, `goal_sent=false`가 기록된다. 정상 수업 종료는 **터미널 A Ctrl+C**, 종료 후 실측 로그·원본 해시를 보존한다. CI는 테스트용으로만 정확히 1회 반복 후 종료하지만, WSL2 실행에는 반복 횟수 제한이 없다.

제출물은 **계층별 필터 화면 3장**, 세 장면의 토픽 및 노드/Action 관계 해설, 순환 장애물 위치에 따른 실제 Path 변화/불변 원인, `/cmd_vel` 무주행과 `/odom` 증거, 미검증 안전 TTL 목록이다. rqt_graph 창이 뜬 것만으로 WSLg GUI 픽셀 검증이나 AXIA MVP 전체 인수를 선언하지 않는다. `AXIA_MVP_DEMO_ACCEPTED=HOLD`.

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
