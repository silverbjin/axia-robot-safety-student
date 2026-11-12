# D04 학생 독립 실습 — Gazebo Harmonic Waffle + 실시간 YOLO GUI

> **이 문서가 강사의 Gazebo 시연을 학생 PC에서 관찰하기 위한 실습입니다.** 기존 `run_teacher_yolo_demo_once.sh`는 사진 한 장을 CPU로 추론해 CSV를 작성할 뿐 Gazebo GUI를 실행하지 않습니다.

**환경:** Windows 10/11 + WSL2 Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic + WSLg DISPLAY. 첫 실행은 인터넷, ROS 패키지와 C++ yolo_ros 컴파일, ONNX 모델/사람 Actor 다운로드가 필요할 수 있습니다. 공개 소스만 이용하며 `gh auth`나 비공개 강사 저장소는 불필요합니다. 학생이 ROS 2의 Overlay를 독립적으로 빌드합니다.

## 1. 기존 학생 저장소 보존 후 시연 코드 받기

이미 `~/axia-robot-safety-student-d04`가 있다면 재복제·reset하지 않고, 기존 작업 파일을 보존하면서 별도 Git worktree를 만듭니다.

~~~bash
(
  set -Eeuo pipefail
  BASE="$HOME/axia-robot-safety-student-d04"
  DEMO="$HOME/axia_d04_student_gazebo_demo"
  test -d "$BASE/.git"
  git -C "$BASE" fetch origin feature/d04-student-gazebo-yolo-20261112
  if [[ ! -e "$DEMO" ]]; then
    git -C "$BASE" worktree add --detach "$DEMO" FETCH_HEAD
  fi
  cd "$DEMO"
  bash block_B/day04/run_student_gazebo_yolo_once.sh --self-check
  bash block_B/day04/run_student_gazebo_yolo_once.sh --doctor
)
~~~

새로운 PC에서 학생 저장소가 전혀 없다면 다음 최초 설치 명령을 대신 실행합니다.

~~~bash
git clone --single-branch --branch feature/d04-student-gazebo-yolo-20261112 \
  https://github.com/silverbjin/axia-robot-safety-student.git \
  "$HOME/axia_d04_student_gazebo_demo"
~~~

**`--self-check`:** 파일·정적 구문만 확인하며 Gazebo/YOLO는 실행하지 않습니다. **`--doctor`:** WSL2·DISPLAY·ROS 2·공식 패키지 준비를 점검하며 누락될 경우 중단할 수 있습니다. 의존성 설치는 다음 `--run`에서 수행합니다.

### 설치부터 GUI 실행까지 한 번에 처리 (기존 개인 작업 보호)

다음 명령은 기존 `~/axia-robot-safety-student-d04` 저장소의 내용 및 `.venv`를 지우지 않고, 독립된 공개 시연 worktree만 구성합니다. 이미 worktree가 있다면 수정사항이 없을 때 fast-forward로 업데이트하고, 이후 Gazebo와 YOLO GUI를 실행합니다.

~~~bash
(
  set -Eeuo pipefail
  SOURCE="$HOME/axia-robot-safety-student-d04"
  DEMO="$HOME/axia_d04_student_gazebo_demo"
  BRANCH="feature/d04-student-gazebo-yolo-20261112"

  if [[ -d "$DEMO" ]] && git -C "$DEMO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if [[ -n "$(git -C "$DEMO" status --porcelain --untracked-files=no)" ]]; then
      echo "D04_STUDENT_GUI_LOCAL_CHANGES_PRESERVED"; exit 2
    fi
    git -C "$DEMO" fetch origin "$BRANCH"
    git -C "$DEMO" merge --ff-only FETCH_HEAD
  elif [[ -e "$DEMO" ]]; then
    echo "D04_STUDENT_GUI_DIRECTORY_NOT_GIT=$DEMO"; exit 2
  elif git -C "$SOURCE" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "$SOURCE" fetch origin "$BRANCH"
    git -C "$SOURCE" worktree add --detach "$DEMO" FETCH_HEAD
  else
    git clone --single-branch --branch "$BRANCH" \
      https://github.com/silverbjin/axia-robot-safety-student.git "$DEMO"
  fi

  bash "$DEMO/block_B/day04/run_student_gazebo_yolo_once.sh" --run
)
~~~

## 2. 학생 PC에서 Gazebo+YOLO 시연 (한 번 실행)

~~~bash
(
  set -Eeuo pipefail
  cd "$HOME/axia_d04_student_gazebo_demo"
  bash block_B/day04/run_student_gazebo_yolo_once.sh --run
)
~~~

실행하면 기존 공개 Nav2 시뮬레이터와 공식 ROBOTIS Waffle Pi RGB 카메라를 재사용하고, 시각용 사람 Actor를 만든 다음 C++ `yolo_ros`를 연결합니다. **보여야 할 GUI는 두 개**입니다.

| 창 | 보이는 것 | 실제 주제 |
|---|---|---|
| **Gazebo Harmonic GUI** | 정지한 TurtleBot3 Waffle과 움직이는 사람 | 공식 Gazebo 로봇·카메라 시뮬레이션 |
| **YOLO 미리보기 (`image_view`)** | `/yolo/cam0/debug_image`, 사람 Bounding Box / confidence | `/camera/image_raw` → `yolo_ros` → Detection·Debug |

로봇 모델·TF·레이저를 보고 싶다면 다음 명령으로 RViz2 창을 추가합니다.

~~~bash
cd "$HOME/axia_d04_student_gazebo_demo"
AXIA_D04_STUDENT_RVIZ=1 bash block_B/day04/run_student_gazebo_yolo_once.sh --run
~~~

[학생용 RViz 설정](gazebo_yolo/axia_d04_student.rviz)은 `File → Open Config`로도 선택할 수 있습니다. 너무 느리면 먼저 기본값(RViz 없음)으로 Gazebo와 YOLO 두 창을 확인하세요.

**예상 출력과 의미**

~~~text
D04_STUDENT_GAZEBO_LAUNCHED: GUI startup requested; NOT yet verified
D04_STUDENT_PERSON_DETECTED confidence=<실측>
D04_STUDENT_GAZEBO_YOLO_LIVE_PASS NO_GOAL NO_SAFETY_TTL
D04_STUDENT_GUI_HOLD_STARTED seconds=180
~~~

첫 줄은 **GUI 시작 요청만 성공**한 상태이며, 실제 ROS 관측 통과는 `LIVE_PASS`가 의미합니다. 실제 WSLg 화면이 표시됐는지는 사용자가 직접 확인해야 합니다. `GUI_HOLD`에서는 180초 동안 Gazebo 화면과 YOLO Bounding Box를 관찰할 수 있습니다. 수업이 끝나면 **Ctrl+C**로 자신이 시작한 프로세스만 종료합니다.

## 3. 센서 상태를 추론하는 순서

- **1. 카메라:** `/camera/image_raw`의 이미지 수신이 있는가? 없다면 Gazebo의 Pi 카메라·`ros_gz_image` 브리지부터 점검합니다.
- **2. YOLO 입력/출력:** `/yolo/cam0/detections`의 `yolo_msgs/msg/DetectionArray`와 `/yolo/cam0/debug_image`가 실제로 들어오는가? 카메라 Hz와 YOLO Hz는 다른 값입니다.
- **3. 레이저·TF:** RViz2에서 `/scan` LaserScan, `/tf`·`/tf_static`, `/robot_description` RobotModel, `/odom`을 봅니다. `odom`이 기준 좌표계입니다.
- **4. 사람 Actor:** 카메라에는 사람이 보여도 LiDAR에 반영되지 않을 수 있습니다. 이 Actor는 **visual-only**이며 물리 충돌 장애물이 아닙니다.
- **5. 판정:** 실제 ROS 메시지의 사람이 검출되면 `LIVE_PASS`이나, **SW STOP·Collision Monitor TTL·인증 E-Stop은 수행하지 않았습니다**.

GUI가 안 뜨거나 YOLO 출력이 없으면 아래 로그를 첫 안전/데이터 경계부터 확인합니다.

~~~bash
OUT="$(ls -dt "$HOME"/axia_d04_student_evidence/d04-gazebo-* | head -n 1)"
echo "$OUT"
tail -n 60 "$OUT/gazebo_nav2.log"
tail -n 60 "$OUT/camera_bridge.log"
tail -n 60 "$OUT/yolo_ros.log"
cat "$OUT/live_verdict.json"
~~~

`/camera/image_raw`가 0프레임이면 YOLO 모델을 변경하기 전에 **Gazebo→브리지**를 분석합니다. 카메라는 수신되고 Detection이 0이면 **브리지→yolo_ros 구독/추론**을 분석합니다. 오래된 종료 후 `Unknown topic`은 정상일 수 있습니다.

## 4. 공개 CI 실제 검증 및 WSL2 최종 검증 경계

**공개 CI 검증 결과(2026-11-12):**

- [ROS 2 Jazzy/Gazebo Harmonic 실제 센서·YOLO PASS](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43166114547): `camera_frames=3`, `scan_frames=3`, `yolo_detection_frames=2`, `yolo_debug_frames=1`, `person_detections=2`, confidence `0.924`, Moving bbox 변화 관측
- [실제 Gazebo/YOLO GUI 창 PASS](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43166756309): Xvfb 상에서 **Gazebo Sim 1000×845** 및 **`/yolo/cam0/debug_image` 400×300** GUI 창 실제 생성. 카메라 40 / scan 23 / detection 12 / person 12, confidence `0.929`, bbox 위치 변화 확인
- [공개 Python/문서·비공개 의존성 배제 계약](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43166945221): **29 passed**. 학생 TODO의 기대 RED는 성공으로 승격하지 않음
- 첫 공개 CI RED는 환경을 source하기 전에 `ros2` 명령을 확인했던 오류였고, Jazzy setup을 먼저 source하도록 수정 후 재인수했다
- 비공개 Instructor/GitHub Actions를 사용하지 않았으며, 공개 브랜치에서만 테스트를 수행했다

**검증 수준:** 공개 CI는 실제 Ubuntu 24.04 Jazzy/Gazebo와 upstream YOLO 메시지 수신, Xvfb 가상 화면에 창 두 개 생성까지 확인했다. **사용자 WSL2 WSLg 화면에서 창이 정상적으로 나타나는지, 사용자가 Bounding Box를 눈으로 확인하는 최종 인수는 아직 수행하지 않았다.** 학생이 성공했다고 보고할 때는 실제 GUI 캡처 1장과 `live_verdict.json`의 데이터를 함께 기록한다.

## 4. 강사 시연과 학생 시연의 범위

강사 시연은 **비공개 P1 안전 계층까지 포함**하고, 학생용은 그 부분을 제외한 **공개 Nav2 Waffle·카메라·yolo_ros 시각화**입니다. 학생이 필요로 하는 실습 성과는 Gazebo의 움직이는 사람과 YOLO Bounding Box를 관찰하는 것입니다. Goal·Fault Injector·`/cmd_vel` 명령·SW Stop·하드웨어 E-Stop은 사용하지 않습니다.

**GitHub Actions 검증 수준:** 공개 CI의 정적 검사는 명령·장면·YAML 구성을 확인합니다. 헤드리스 Gazebo 실동작 검사가 별도 PASS일 경우에도 사용자 WSL2 WSLg 화면의 실제 출현을 자동으로 보장하는 것은 아니므로 **GUI 최종 인수는 현장에서 별도 수행**합니다. CI 결과가 확정되기 전 성공이라고 보고하지 않습니다.
