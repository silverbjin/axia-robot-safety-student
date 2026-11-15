# AXIA D08 — 학생용 Gazebo + YOLO + RViz2 Live Demo (연구 관측판)

**기준:** ROS 2 Jazzy / Gazebo Harmonic / 공식 Nav2·TurtleBot3 Waffle / Ubuntu 24.04 WSL2 + WSLg. **학습 시간:** D08(2026-11-18) 첫 시간 중 15~20분 관찰, 이후 6개 Python 합성 사례 TDD·통합 설명에 연결한다.

> **학습 목표**: (1) Visionㆍ거리정보 기반 Human-aware Safety 제어 흐름 구성, (2) 사람 인식ㆍ거리계산ㆍ회피제어 통합 실습. 이 Live는 **관측 센서 계층**, 별도 D08 Python 실습은 **판단 계층**이다. 실제 회피제어/Goal은 인수되지 않았으며 자동 실행하지 않는다.

## 1. 기능 범위 — 검증된 코드를 재사용한다

- **Gazebo**: 기존 공개 D04/D05 공식 Waffle 시뮬레이션, 움직이는 사람형 **visual-only** Actor, 정지 Waffle, 등록된 RGB-D 1개. visual-only Actor는 LiDAR가 감지하는 실제 충돌 장애물이라고 주장할 수 없다.
- **YOLO**: 기존 upstream C++ \`yolo_ros\` + 고정된 ONNX 모델, \`/yolo/cam0/debug_image\`의 동적 Bounding Box. \`/yolo/cam0/detections\`은 별도 ROS 메시지 확인.
- **RViz2**: **구독 전용** RobotModel(/robot_description), TF, LaserScan(/scan), Odometry(/odom), D05 등록 RGB(/axia/d05/rgbd/image), Depth(/axia/d05/rgbd/depth_image), YOLO debug 이미지. Fixed Frame=\`odom\`; RViz 파일에 Nav2 Goal/Initial Pose 발행 도구 없음.
- **Python D08**: \`block_B/day08/integration_todo.py\`의 6개 **합성** 사례에만 적용, 라이브 ROS 토픽→\`integrate_case\`는 미연결. 실제 \`distance_m\`·\`/axia/d05/person_range_status\`는 이 **학생 센서 전용** 모드에서 제공하지 않는다.
- **안전 계층**: 실제 공식 Collision Monitor·Guard→\`/cmd_vel\`·Moving Goal·E-Stop 종단은 이번 학생 시연에서 **NO_GOAL / NOT_VERIFIED**. 화면의 교육용 정책을 실제 안전제어로 오인 금지. SW Stop ≠ 인증된 HW E-Stop.

### 데이터 흐름과 모니터링 지점

\`\`\`mermaid
flowchart TD
    G["Gazebo Harmonic Waffle + moving visual-only actor"] --> RGB["registered RGB-D sensor"]
    RGB --> BR["ros_gz_image bridge"]
    BR --> IMG["/axia/d05/rgbd/image  sensor_msgs/Image"]
    BR --> DEP["/axia/d05/rgbd/depth_image  32FC1"]
    IMG --> Y["upstream yolo_ros"]
    Y --> DET["/yolo/cam0/detections"]
    Y --> DBG["/yolo/cam0/debug_image"]
    IMG --> V["RViz2 read-only views"]
    DEP --> V
    DBG --> V
    G --> SC["/scan LaserScan / TF / /odom"]
    SC --> V
    DET -. "연구 후속: 실시간 bbox-Depth 정합/거리(현재 미구현)" .-> ROI["D05 live ROI"]
    P["D04-D07 합성 fixture"] --> L["D08 integrate_case Python L0"]
    ROI -. "현재 연결되지 않음" .-> L
    L --> OUT["6 cases: trace.csv / summary.json"]
\`\`\`

**중요:** RViz2에서 Depth 영상이 보이더라도 bbox-Depth **ROI 거리 계산이 수행됐다는 뜻은 아니다**. \`/scan\`은 실제 LiDAR 관측이지만 이 visual-only Actor의 물리 충돌·제어·정지 성공은 검증하지 않는다. 녹화에는 \`/tf\`와 \`/tf_static\`도 같이 포함해야 프레임 재현에 도움이 된다.

## 2. 단일 WSL2 실행 — 기존 개인 과제·가상환경 보존

학생의 기존 D04~D08 TODO 작업 디렉터리를 수정하지 않고 **별도 공개 시연용 폴더**에 클론한다. 공개 브랜치의 CI 상태를 확인한 뒤 실행한다. 준비 명령을 하나의 Bash 블록으로 실행할 수 있다.

\`\`\`bash
(
  set -Eeuo pipefail
  DEMO="$HOME/axia_d08_student_live"
  BRANCH="feat/d08-live-gazebo-rviz-no-goal-20261115"
  if [[ ! -e "$DEMO" ]]; then
    git clone --branch "$BRANCH" --single-branch \
      https://github.com/silverbjin/axia-robot-safety-student.git "$DEMO"
  else
    [[ -d "$DEMO/.git" ]] || { echo "D08_LIVE_DIRECTORY_NOT_GIT"; exit 2; }
    [[ "$(git -C "$DEMO" branch --show-current)" == "$BRANCH" ]] || {
      echo "D08_LIVE_WRONG_BRANCH"; exit 2; }
    [[ -z "$(git -C "$DEMO" status --porcelain --untracked-files=no)" ]] || {
      echo "D08_LIVE_LOCAL_CHANGES_PRESERVED"; exit 2; }
    git -C "$DEMO" fetch origin "$BRANCH"
    git -C "$DEMO" merge --ff-only FETCH_HEAD
  fi
  cd "$DEMO"
  bash block_B/day08/run_d08_student_live_once.sh --self-check
  bash block_B/day08/run_d08_student_live_once.sh --doctor
  AXIA_D08_DOMAIN_ID=49 AXIA_D08_HOLD_S=300 \
    bash block_B/day08/run_d08_student_live_once.sh --run
)
\`\`\`

\`--self-check\`는 **정적 검사만** 수행한다. \`--doctor\`는 Jazzy/공식 ROS 패키지/RViz 준비 상태를 검사하고 Gazebo는 실행하지 않는다. \`--run\`만 실제 Gazebo·YOLO·RViz2를 시도한다. 실습 플랫폼에 \`rviz2\`가 없으면 \`D08_RVIZ2_NOT_INSTALLED\`로 차단하므로 설치 뒤 재실행한다. WSLg \`DISPLAY\`가 없으면 기존 런처가 차단한다. \`AXIA_D08_HOLD_S=300\`은 시연 관찰용 300초이며 **비동기 백그라운드 데몬을 남기지 않는다.**

### 세 개의 관찰 창

| 화면 | 눈으로 확인할 내용 | 실제 의미 |
|---|---|---|
| **Gazebo Harmonic** | Waffle, 다가왔다 멀어지는 시각용 사람 | 시뮬레이션 장면·Actor 애니메이션 |
| **YOLO image_view** | 움직이는 person bbox·confidence | RGB 이미지에서 검출한 결과 |
| **RViz2 D08 view** | RobotModel, TF, /scan, /odom, D05 RGB/Depth, YOLO debug | **ROS 메시지의 실시간 구독 표시**. Live D05 미터 계산 아님 |

**정상일 때 예상되는 로그 패턴(새로 실행한 실측값 아님):**

\`\`\`text
D08_STUDENT_LIVE_LAUNCH_REQUESTED: Gazebo + moving visual-only person + RGB-D + YOLO + RViz2
D08_STUDENT_LIVE_READONLY: NO_GOAL NO_CMD_VEL NO_PRIVATE_D05_RANGE NO_SAFETY_TTL
D04_STUDENT_GAZEBO_LAUNCHED: GUI startup requested; NOT yet verified
D05_LIVE_VERDICT={"status":"PASS_REAL_GAZEBO_REGISTERED_RGBD_YOLO_MOVING_BBOX_ONLY",...}
D05_PUBLIC_SENSOR_ONLY_PASS REAL_RGBD_YOLO PRIVATE_D05_RANGE_NOT_RUN
\`\`\`

\`LAUNCH_REQUESTED\`는 세 창이 **실제로 나타났다는 증거가 아니다**. 기존 검증기가 ROS RGB/Depth·YOLO 데이터를 확인해야 센서 Live로 판정한다. Gazebo/YOLO/RViz **세 창의 실제 표시**는 학생 WSL2 화면에서 별도로 확인한다. 녹화·스크린샷 1장과 종료 코드·verdict 원본을 같이 남기면 좋다.

## 3. RViz2 표시가 비었을 때 (코드 수정 전 진단)

RViz2 파일: \`block_B/day08/live/d08_student_rgbd_monitor.rviz\`. **D04 기본 설정의 RGB**는 \`/camera/image_raw\`이지만 **D08 관측 모드의 실제 RGB**는 \`/axia/d05/rgbd/image\`다. 새 설정은 이 불일치를 수정한다.

- **Fixed Frame:** \`odom\`; 일부 TF가 미생성일 때 \`map\`을 임의로 사용하지 않는다. Waffle이 정지해 있어도 TF·Odom을 볼 수 있다.
- **LaserScan:** \`/scan\` / Best Effort, 실제 Gazebo 레이저 관측. **visual-only Actor가 점군에 안 보이는 것은 예상 가능한 결과**다.
- **D05 Registered RGB:** \`/axia/d05/rgbd/image\`, \`sensor_msgs/msg/Image\`.
- **D05 Depth 32FC1:** \`/axia/d05/rgbd/depth_image\`, \`sensor_msgs/msg/Image\`; RViz Image의 normalize 기능을 사용. Depth 표시는 **거리 측정 수치**가 아니다.
- **YOLO Debug Image:** \`/yolo/cam0/debug_image\`, person bbox 표시.
- **Object-level DetectionArray:** RViz 기본 Image 플러그인은 \`yolo_msgs/msg/DetectionArray\` 객체의 필드를 표로 표시하지 않는다. **터미널 B**에서 확인한다. RViz의 Path/Collision Monitor 상태는 이번 장면에서 발행 증거가 없어 추가하지 않았다.
- **GPU 부하:** Gazebo+YOLO+RViz 렌더링을 동시에 사용하므로 프레임이 느리면 시각화 패널을 잠시 숨기고 센서 토픽의 실제 wall-time 수신 간격을 먼저 확인한다. 실제 RGB-D 메시지 timestamp가 맞더라도 수신 간격(안전 TTL)은 별도다.

## 4. 터미널 B — 실제 ROS 토픽 읽기 전용 진단

터미널 A에서 세 창이 실행 중일 때, 같은 WSL2 배포판에서 **터미널 B**를 연다.

\`\`\`bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=49
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 topic list | grep -E '^(/scan|/odom|/tf|/axia/d05/rgbd/(image|depth_image)|/yolo/cam0/(detections|debug_image))$'
ros2 topic info /axia/d05/rgbd/depth_image --verbose
ros2 topic echo /axia/d05/rgbd/depth_image --field encoding --once
ros2 topic hz /scan
\`\`\`

**기대 관측:** Depth encoding은 \`32FC1\`이며 \`/scan\`은 실제 구독 Hz가 출력된다. \`ros2 topic hz\`는 종료할 때 B에서 **Ctrl+C**. 메시지 간격과 GUI 프레임율은 WSL2 자원 상황에 따라 달라서 **실측 전 숫자를 약속하지 않는다**. YOLO 검출은 다음으로 타입과 데이터를 확인한다.

\`\`\`bash
ros2 topic info /yolo/cam0/detections --verbose
ros2 topic echo /yolo/cam0/detections --once
\`\`\`

**주의:** \`ros2 topic echo\`로 표시되는 class·score·bbox와 이미지 header stamp를 따로 관찰한다. RGB-D 정합의 \`50ms\` 교육 기준, track freshness \`0.50s\`와 실제 CM→Guard TTL \`150ms\`는 **서로 다른 제약**이다. YOLO가 검출한 person이 반드시 LiDAR 장애물이라는 주장은 하지 않는다.

## 5. 후속 연구 — 1회 rosbag 기록(선택, 관측 전용)

별도 **터미널 C**에서 센서와 관측 메타데이터를 모아 재현 데이터로 보존한다. 연구용으로만 권장하며 실시간 데모 우선 시에는 녹화하지 않아 프레임 지연을 줄인다.

\`\`\`bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=49
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
mkdir -p "$HOME/axia_d08_research"
BAG="$HOME/axia_d08_research/bag_$(date -u +%Y%m%dT%H%M%SZ)_$$"
ros2 bag record -o "$BAG" \
  /scan /odom /tf /tf_static \
  /axia/d05/rgbd/image /axia/d05/rgbd/depth_image \
  /yolo/cam0/detections
# 10~30초 정도 관찰 후 이 터미널에서 Ctrl+C
ros2 bag info "$BAG"
\`\`\`

**제출할 증거:** 자신의 \`git rev-parse HEAD\`, \`live_verdict.json\`, 화면 캡처, 토픽 목록·형식, rosbag 메타데이터/원본 파일 해시. bag에는 영상이 포함되므로 외부 공개 전 개인정보·라이선스·용량을 검토한다.

**후속 연구 순서(이번 실습의 필수 개발이 아님):** (1) 라이브 bbox+Depth 정합을 읽기 전용으로 관측하고 신선도·첫 타이밍 위반 계측, (2) 비충돌 인식 및 위치 TF 연관성 검증, (3) 공개 실제 Gazebo D08 물리 사람 proxy와 **visual-only** Actor 차이를 분석, (4) 독립적인 D07 H01 실제 이동·CM→Guard 종단이 CI/Owner WSL2에서 인수된 뒤에만 경로·정지 모니터링 확장.

## 6. 종료·오류 분리·검증 레벨

- **정상 종료:** 실행 소유자인 터미널 A에서 **Ctrl+C**. 기존 D04 런처가 자신이 시작한 Gazebo·ROS·RViz 자식 프로세스 그룹만 종료한다. \`pkill\`, \`wsl --shutdown\`, 글로벌 ROS 환경 변경 금지.
- **먼저 볼 로그:** \`$HOME/axia_d04_student_evidence/d04-gazebo-*/live_verdict.json\`, 같은 폴더 \`gazebo_nav2.log\`, \`camera_bridge.log\`, \`depth_bridge.log\`, \`yolo_ros.log\`, \`rviz2.log\` (생성된 경우). 최초 실패 데이터 전달·최초 타이밍 위반부터 해석한다.
- **통과 조건:** 세 GUI가 실제 열리고 RGB·Depth·YOLO·RViz 주요 구독 표시, 센서 Live verdict, 종료 시 프로세스 재생성 없음. GUI는 CI 가상 디스플레이 PASS와 사용자 WSLg PASS를 구분한다.
- **기존 검증:** D04 공개 실 Gazebo·YOLO GUI [Run #43166756309](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43166756309); D05 실제 registered RGB-D/움직이는 Actor YOLO [Run #43353480617](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43353480617); D08 별도 near/far 물리 모델·ROS YOLO 영상 재생 [Run #43676658454](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43676658454). **서로 다른 소스 SHA·검증 범위를 하나의 동시 실행 성공으로 합치지 않는다.**
- **이번 D08 변경 신규 검증 목표:** wrapper/RViz config/가이드 공개 CI **L0**. **Gazebo·RViz 동시 GUI L2 및 WSL2 Owner 현장 테스트는 별도**로 남긴다.
