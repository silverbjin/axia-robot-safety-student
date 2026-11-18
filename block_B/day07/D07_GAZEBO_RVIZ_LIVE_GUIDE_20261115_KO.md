# Block B D07 — Gazebo Harmonic + RViz2 학생 라이브 관찰 가이드 (2026-11-15)

> **교육용 관찰판 1단계: 실제 Gazebo Waffle 센서/TF/Odom + RViz2, NO_GOAL.**  
> ROS 2 Jazzy / Gazebo Harmonic / Ubuntu 24.04 WSL2 WSLg. 2026-11-17 D07 원래 두 학습 목표의 **동기 유발 라이브 데모**를 추가한다.  
> 기존 D04/D05/D08의 실제 ROS·Gazebo 학생 실행기를 재사용하지만 **H01 물리 장애물의 공식 Nav2 경로 재계획이 이 모드에 연결됐다는 주장은 하지 않는다**. 학생용 TODO·강사 비공개 정답은 그대로 둔다.

## 1. 기존 main과 현재 모드의 차이

- **D07 main**: 공식 ROS PlannerServer/Costmap L1 실습은 성공(기존 lethal 0→101→0, Path 58→74→58), 하지만 이는 Gazebo 물리 장면이 아닌 별도 synthetic LaserScan 계획 시험.
- **D07-H01 Draft**: 실제 물리 장애물과 LiDAR를 공식 Costmap/Nav2 Planner로 연결한 **no-moving-Goal Gate 1**, [공개 실제 Gazebo #43673228520](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43673228520) **L2 범위 한정 PASS**. intrude 0→102→0 lethal, official detour 0.3849m, obstacle clearance 0.3933m, restored path delta 0.0443m. 그러나 Contact-free 실제 이동과 CM→Guard 150ms TTL, H01 Goal/Owner L3는 미인수.
- **이 새 학생 관찰판**: 기존 D04/D05 Waffle + Gazebo GUI, 시각용 사람 Actor(visual-only), 실제 /scan·/odom·/tf 센서, RViz2 표시를 일괄 실행한다. **시각용 Actor는 LiDAR 물리 충돌체가 아니며** 이 모드에는 H01 공식 PlannerServer/Costmap/Path 제공이 없다. 학생용 첫 10~15분 몰입용 관찰판이다. 실제 회피 주행은 **NOT_RUN / BLOCKED**.

| 화면 | 눈으로 볼 것 | 무엇을 증명하는가 |
|---|---|---|
| Gazebo Harmonic | 정지 Waffle, 움직이는 visual-only 사람 Actor, RGB-D 장면 | 동적 시각 장면. 사람이 /scan 장애물이라는 의미 **아님** |
| RViz2 (D07 preset) | 실제 /scan, /tf, /odom, Grid | ROS 센서·좌표계 시각화. 현재 로봇은 stationary/no Goal |
| 기존 YOLO view | 사람 Bounding Box(동작하는 경우) | RGB 영상 사람 인식. Nav2 연결 증거 **아님** |
| RViz2의 H01 Costmap·Path | 기본 Disabled | **H01 별도 동일 세션의 실제 공식 Planner·Path 시각화 연계가 되기 전에는 활성화 금지** |

## 2. 운영 절차 — 학생/강사 WSL2 한 번에 다운로드·실행

현재 작업물은 별도 공개 Draft 브랜치에서 개발하고 공개 CI를 먼저 검증한다. **CI GREEN SHA가 확정된 뒤에만** 아래 `SHA`에 해당 공개 40자리 커밋을 입력한다. `main` 자동 병합이나 근거 없는 latest 브랜치 다운로드를 하지 않는다. 새 전용 디렉터리 `~/axia_d07_live_demo`를 사용하므로 기존 D04~D08 학생 작업을 변경하지 않는다.

**터미널 A — Owner 학생 GUI 실행** (기존 ROS/Gazebo 세션이 없는 별도 수업 도메인):

```bash
(
  set -Eeuo pipefail
  SHA="<PUBLIC_CI_GREEN_SHA_40_HEX>"
  SCRIPT="$(mktemp --suffix=.sh)"
  trap 'rm -f -- "$SCRIPT"' EXIT

  curl -fL --retry 3 --max-time 90 -sS \
    "https://raw.githubusercontent.com/silverbjin/axia-robot-safety-student/$SHA/block_B/day07/run_d07_student_live_bootstrap.sh" \
    -o "$SCRIPT"
  bash -n "$SCRIPT"
  bash "$SCRIPT" --self-check
  AXIA_D07_PUBLIC_SHA="$SHA" AXIA_D07_DOMAIN_ID=51 \
    AXIA_D07_HOLD_S=300 bash "$SCRIPT" --run
)
```

`<PUBLIC_CI_GREEN_SHA_40_HEX>`는 **예시 치환 지점**이고 실제 Git SHA가 아니다. 실제 값은 최종 공개 CI PASS와 PR에서만 확정하여 배포한다. `AXIA_D07_HOLD_S`는 화면을 유지하는 초 단위 수업 옵션이다. `Ctrl+C`로 종료하면 기존 D04 실행 소유자가 **자신의 자식 프로세스 그룹만** 정리한다. `wsl --shutdown`, 전역 `pkill` 사용 금지.

**정적 확인과 실제 실행은 서로 다름:**

```text
D07_BOOTSTRAP_STATIC_PASS GAZEBO_NOT_RUN RVIZ_NOT_RUN NO_GOAL
D07_RVIZ_STATIC_PASS GAZEBO_NOT_RUN RVIZ_NOT_RUN NO_GOAL
D07_STUDENT_NO_GOAL NO_CMD_VEL CERTIFIED_ESTOP_FALSE
D07_STUDENT_GAZEBO_RVIZ_LAUNCH_REQUESTED ...
D07_SENSOR_ONLY_LIVE_EXPECT_VERDICT_FROM_D04_D05_NOT_YET_VERIFIED
```

마지막 두 줄은 **실행 요청 및 검증 대기 메시지**다. 성공 판정은 기존 D04/D05 검증기의 실제 `D05_PUBLIC_SENSOR_ONLY_PASS`와 Gazebo/RViz2/YOLO 창의 실제 표시, 정상 종료 코드에 근거한다. 이 새 D07 모드의 실제 WSL2 GUI PASS는 수행하지 않았으면 **NOT_RUN**이다.

**실행 전 진단만 필요한 경우** 같은 공개 SHA로 다운로드한 스크립트에 `AXIA_D07_PUBLIC_SHA="$SHA" bash "$SCRIPT" --doctor`를 적용한다. `--doctor`는 ROS 패키지 확인만 하고 Gazebo 실행을 요구하지 않는다. `D07_RVIZ2_REQUIRED`라면 `sudo apt-get install ros-jazzy-rviz2` 후 다시 확인한다. 외부 셸에서 `set -u` 후 직접 ROS setup을 source하지 않으며, 런처 내부에서 `set +u; source; set -u`를 사용한다.

## 3. 터미널 B — RViz2와 실제 ROS 토픽 읽기 전용 관찰

A의 스크립트가 지정한 `ROS_DOMAIN_ID=51`과 동일하게 관찰한다. B에서만 다음을 실행한다.

```bash
set +u
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=51
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 topic list | grep -E '^/(clock|scan|odom|tf|tf_static)$' || true
ros2 topic info /scan --verbose
ros2 topic hz /scan
# 종료: B에서 Ctrl+C, A의 Gazebo는 유지
```

**RViz2 관찰 포인트:** Fixed Frame=`odom`, LaserScan `/scan`, TF `/tf`, Odometry `/odom`, Waffle RobotModel은 mesh 리소스 문제를 대비하여 기본 OFF다. 토픽이 있다고 TF 연결까지 성공했다고 보고하지 말고 RViz Status를 확인한다. CPU/WSLg 부담이 크면 YOLO/RViz 두 창을 동시에 강제로 재실행하는 대신 화면 유지 시간을 줄인다.

## 4. D07 본래 목표를 충족시키는 H01 물리 Planner 라이브 연구 모드 — **설계 단계**

이번 1단계에서 **가장 중요한 미구현 항목**이다. 이것을 구현해야 `/global_costmap/costmap`과 공식 `nav_msgs/Path`가 **같은 Gazebo 물리 장애물에 의해 실시간으로 변하는 모습**을 RViz2에서 볼 수 있다.

```text
Gazebo physics-enabled human proxy → real Waffle /scan
  → official ObstacleLayer / InflationLayer
  → /global_costmap/costmap (nav_msgs/OccupancyGrid)
  → PlannerServer /compute_path_to_pose (ComputePathToPose)
  → [신규 검증용 read-only Path relay]
  → /axia/d07/h01/path_visual (nav_msgs/Path)
  → RViz2 Costmap + Path overlay
```

**기존 H01 Gate 1 실제 CI 범위 한정 성공을 재사용**하되, private Instructor H01 실행기에는 `GITHUB_ACTIONS` 전용 no-Goal 게이트, headless Gazebo 실행, Path 결과 JSON 기록만 있고 RViz2/Path 시각화 토픽은 아직 없다. 단순히 CI용 안전 게이트를 제거해 학생에게 실행시키는 접근은 금지한다.

필요한 최소 추가 작업:
1. Instructor H01 실행기와 분리된 **시뮬레이션 전용 read-only GUI 실행 권한** 검증: Goal/Guard/CM 변경 없이 실제 Waffle + 물리 인체 proxy의 no-Goal 장면만 실행. 위조된 `GITHUB_ACTIONS=true` 금지.
2. 기존 `ComputePathToPose` 실제 결과만 `/axia/d07/h01/path_visual`에 복사하는 **시각화 전용 Path relay**. TF map→odom, RViz `Fixed Frame=map` 및 신선한 Costmap stamp를 검증한다. 없는 토픽에 Path가 있다고 주장하거나 합성 경로를 실제로 표시하지 않는다.
3. **공개 CI RED→GREEN → 실제 Jazzy/Gazebo L2 no-Goal/Path 시각화 검증 → 강사 Owner WSL2 GUI 1회**. 실제 주행 Controller/Contact-free/150ms TTL 인수는 여전히 별도 Gate 2~5. 학생은 선택적으로 **같은 DDS 도메인의 RViz 구독**만 사용할 수 있다.
4. 연구용 별도 파일에는 Costmap, scan, TF, Path, Goal 금지, stamps/주기를 기록하고 rosbag SQLite 원본과 SHA256으로 후속 분석 근거를 남긴다.

**추가 연구:** LaserScan과 Costmap 위치·TF·시간 정합, Planner 경로가 동적 장애물과 상호작용하는 시각적 패턴, 물리 obstacle과 visual-only actor 차이, ROS topic age vs 실제 CM→Guard TTL 인과 관계. 현재 연구 화면은 센서 Live일 뿐 STOP/E-Stop이나 실제 회피 주행 성공을 증명하지 않는다.

## 5. 선택적 연구용 bag — 실제 샘플만 기록

터미널 C에서 필요할 때만 다음을 실행한다. 실시간 GUI 성능이 우선이면 기록을 생략한다.

```bash
set +u
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=51
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
OUT="$HOME/axia_d07_research/bag_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$(dirname "$OUT")"
ros2 bag record -o "$OUT" /clock /scan /odom /tf /tf_static
# 15~30초 뒤 이 터미널에서 Ctrl+C
ros2 bag info "$OUT"
sha256sum "$OUT"/*.db3
```

H01 Live 경로가 나중에 인수되면 동일 세션에서 `/global_costmap/costmap`과 실제 publish된 `/axia/d07/h01/path_visual`을 수집 목록에 추가한다. 현재 없는 토픽을 가짜로 게시하지 않는다.

## 6. 테스트·인수 표시

| 기준 | 현재 허용 판정 |
|---|---|
| 새로운 D07 RViz 설정·실행기·bootstrap·학생 가이드 계약 | 공개 **L0 static** CI 후에만 PASS 가능 |
| 기존 D08/D04/D05 Gazebo/RGB-D/YOLO/RViz2 학생 런처 | 과거 실제 Owner/공개 CI 센서 라이브 성공 근거 재사용 |
| 이번 **D07 새 GUI 설정**의 Gazebo+RViz2 화면 표시 | **NOT_RUN** (수업 WSL2 또는 별도 Xvfb 필요) |
| 이번 D07의 **동일 Gazebo 물리 장애물→Costmap→Planner→Path RViz** | **NOT_RUN / BLOCKED** (H01 계층 분리된 추가 연결 필요) |
| 실제 D07-H01 robot moving Goal·Controller·contact-free·안전 TTL | **NOT_RUN / BLOCKED** |

학생은 자신의 `route_todo.py`를 유지하고 강사 정답을 다운로드하지 않는다. **SW STOP은 인증된 하드웨어 E-Stop이 아니다.** 공개 CI/학생/Instructor `main` 병합은 별도 승인 전 진행하지 않는다.
