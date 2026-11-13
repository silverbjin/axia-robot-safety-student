# D05 학생용 Gazebo Live Demo — Waffle RGB-D·움직이는 사람·YOLO

**대상:** WSL2 Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic + WSLg. 공개 학생 저장소만 사용한다.

## 오늘의 학습 목표

1. **Depth 기반 사람-로봇 간 거리 계산 구조 이해:** Waffle의 정렬된 RGB-D 센서, YOLO person Bounding Box, Depth ROI 및 Z-depth 계산의 관계를 설명한다.
2. **접근 위험 수치화 및 거리정보 추출 실습:** Gazebo 사람 Actor의 접근·복귀로 bbox가 변화하는 것을 관찰하고, 별도 Python TODO에서 합성 ROI 중앙값 **1.30m**와 UNKNOWN을 계산한다.

**중요한 경계:** 학생 공개 Live Demo는 **실제 Gazebo RGB-D·YOLO 검출**까지 보여준다. 실행 옵션은 AXIA_D05_LIVE=1, AXIA_D05_SENSOR_ONLY=1이다. 이때 **D05_PRIVATE_DISTANCE_OBSERVER=NOT_RUN**은 정상이며 실시간 거리 토픽 /axia/d05/person_range_status의 VALID 미터값은 제공하지 않는다. 강사용 Observer의 실시간 미터 계산은 비공개이고, 학생의 measure_person_range() TODO도 현재 Live runner와 연결되지 않았다. 학생이 실제 거리 계산까지 완료했다고 발표하면 안 된다.

학생 라이브 장면은 공개 소스 `block_B/day05/gazebo_live/prepare_scene.py`가 기존 D04 Waffle GUI를 재사용하며 생성한다. 거리 원샷을 위해 비공개 Observer나 별도 ROS 패키지를 추가하지 않는다.

## 1. 시스템 데이터 파이프라인과 화면

~~~text
Gazebo Harmonic: 정지 Waffle + 움직이는 visual-only 사람 Actor
    Waffle camera_link 의 단일 registered RGB-D 카메라
        ├── /axia/d05/rgbd/image ──→ yolo_ros
        │                                  ├→ /yolo/cam0/detections
        │                                  └→ /yolo/cam0/debug_image → image_view
        └── /axia/d05/rgbd/depth_image (32FC1, 카메라 깊이 영상)
                ↓ 학생 모드: 실제 ROS 수신/유효성 관찰까지만
                × 거리 Observer 미실행 → live distance_m 없음

별도 학생 Python 합성 실습:
D04 person bbox + Depth ROI [1.0,1.2,1.4,1.6]
                ↓ 학생의 measure_person_range() TODO
                → median 1.30m, invalid면 UNKNOWN
~~~

Gazebo 화면에서는 Actor가 x=2.8→2.0→2.8m로 접근/복귀하고 원래 D04 참고 높이 z=1.0m를 사용한다. RGB-D 카메라를 약 10.3도 상향 배치했다. 사람 Actor는 visual-only이고 로봇을 움직이지 않는다. YOLO bbox 면적만으로 실제 거리나 위험 확률을 판정하지 않는다.

## 2. 터미널 A — 학생 독립 Gazebo Live Demo 실행 (권장)

이 명령은 기존 개인 D04/D05 TODO 작업을 유지하기 위해 별도 독립 폴더를 사용한다. 첫 실행 시 공식 ROS 의존 패키지 설치나 공개 C++ yolo_ros/ONNX/Actor 준비가 발생할 수 있다. 인터넷 연결이 필요할 수 있다. 기존 폴더에 무조건 reset/clean 하지 않는다.

~~~bash
(
  set -Eeuo pipefail
  REPO="$HOME/axia_d05_student_gazebo_live"
  SHA="1c03c9bfb4b41e2726a7c1d2f47d65496bdaa474"

  if [[ ! -e "$REPO" ]]; then
    git clone --quiet --no-checkout \
      https://github.com/silverbjin/axia-robot-safety-student.git "$REPO"
    git -C "$REPO" fetch --quiet --depth 1 origin "$SHA"
    git -C "$REPO" checkout --quiet --detach "$SHA"
  fi

  test -d "$REPO/.git"
  test "$(git -C "$REPO" rev-parse HEAD)" = "$SHA" || {
    echo "D05_STUDENT_SOURCE_SHA_MISMATCH"; exit 2; }
  test -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" || {
    echo "D05_STUDENT_LOCAL_CHANGES_PRESERVED"; exit 2; }

  cd "$REPO"
  AXIA_D05_LIVE=1 bash block_B/day04/run_student_gazebo_yolo_once.sh --self-check

  AXIA_D05_LIVE=1 AXIA_D05_SENSOR_ONLY=1 \
  AXIA_D04_STUDENT_GUI=1 AXIA_D04_STUDENT_DOMAIN_ID=49 \
  AXIA_D04_STUDENT_GUI_HOLD_S=180 \
    bash block_B/day04/run_student_gazebo_yolo_once.sh --run
)
~~~

**예상 로그:**

~~~text
D04_STUDENT_GAZEBO_STATIC_PASS GAZEBO_NOT_RUN YOLO_NOT_RUN
D04_STUDENT_GAZEBO_LAUNCHED: GUI startup requested; NOT yet verified
D05_LIVE_VERDICT={"status":"PASS_REAL_GAZEBO_REGISTERED_RGBD_YOLO_MOVING_BBOX_ONLY",...}
D05_PUBLIC_SENSOR_ONLY_PASS REAL_RGBD_YOLO PRIVATE_D05_RANGE_NOT_RUN
D04_STUDENT_GUI_HOLD_STARTED seconds=180; press Ctrl+C when finished
D04_STUDENT_EXIT_CODE=0
~~~

GUI 두 개(실제 Gazebo와 YOLO image_view)의 생성 및 표시를 학생이 직접 확인한다. 위 예상 로그의 숫자와 ROS 프레임 수는 실행마다 다르다. self-check만 통과한 상태는 **Gazebo NOT_RUN**이며 LIVE_PASS가 아니다.

**학습 관찰:** Gazebo의 정지 Waffle/접근하는 사람, YOLO의 person·confidence·Bounding Box 변화, 그리고 RGB/Depth가 실제 센서에서 나오는 경로를 말로 설명한다.

## 3. 터미널 B — 라이브 센서 토픽 모니터링 (선택)

터미널 A가 실행 중일 때 **새 WSL2 터미널 B**를 연다. 실행 로그와 거리 계산 코드를 혼동하지 않고 실제 RGB·Depth·Detection의 발행자를 본다.

~~~bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID="$(printenv AXIA_D04_STUDENT_DOMAIN_ID 2>/dev/null || printf 49)"
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST

ros2 topic list | grep -E '/axia/d05/rgbd/(image|depth_image)|/yolo/cam0/detections'
ros2 topic info /axia/d05/rgbd/depth_image --verbose
ros2 topic info /yolo/cam0/detections --verbose
~~~

**예상 이름과 타입:** /axia/d05/rgbd/image · /axia/d05/rgbd/depth_image = sensor_msgs/msg/Image, /yolo/cam0/detections = yolo_msgs/msg/DetectionArray.

다음은 Depth Image의 **encoding만** 확인한다. 원본 이미지 전체 배열을 터미널에 쏟아내지 않는다.

~~~bash
ros2 topic echo /axia/d05/rgbd/depth_image \
  --once --field encoding --qos-reliability best_effort
~~~

**예상:** 32FC1. 이것은 깊이 픽셀 자료형의 증거이지 사람 거리가 몇 미터인지 나타내는 출력이 아니다. 메시지가 없으면 먼저 ROS_DOMAIN_ID 일치와 Depth 브리지 수신을 검사한다. 필요하면 YOLO 토픽 구독과 실제 Gazebo actor 시야를 확인한다.

**학생 Live에서는 다음 거리 토픽을 제공하지 않는다.** 토픽이 없어도 정상 범위 제한이다.

~~~bash
ros2 topic list | grep /axia/d05/person_range_status || \
  echo "D05_STUDENT_NO_LIVE_RANGE_OBSERVER_EXPECTED"
~~~

강사용 Observer의 실제 미터값을 표시하려면 비공개 강사 실행을 별도로 해야 하며, 그것은 학생 독립 Live Demo의 기능에 포함되지 않는다.

### 터미널 A를 조용하게 운용하는 추가 옵션

위 §2의 실행을 **이미 하고 있다면 중복 실행하지 않는다.** 이전 실행을 종료한 다음, 동일한 독립 데모 폴더에서 아래 명령으로 시작하면 A에는 시작/종료 메시지만 보이고 실행 로그는 파일에 저장된다. 터미널 B의 ROS 모니터링은 위 명령 그대로 사용한다.

~~~bash
(
  set -Eeuo pipefail
  REPO="$HOME/axia_d05_student_gazebo_live"
  test -f "$REPO/block_B/day04/run_student_gazebo_yolo_once.sh"

  LOGDIR="$HOME/axia_d05_student_live_logs"
  mkdir -p "$LOGDIR"
  LOG="$(mktemp "$LOGDIR/owner_$(date +%Y%m%d_%H%M%S)_XXXXXX.log")"
  printf '%s\n' "$LOG" > "$LOGDIR/latest.logpath"
  echo "[D05 STUDENT A] Gazebo/YOLO 실행 — 로그: $LOG"

  set +e
  (
    cd "$REPO"
    AXIA_D05_LIVE=1 AXIA_D05_SENSOR_ONLY=1 \
    AXIA_D04_STUDENT_GUI=1 AXIA_D04_STUDENT_DOMAIN_ID=49 \
    AXIA_D04_STUDENT_GUI_HOLD_S=180 \
      bash block_B/day04/run_student_gazebo_yolo_once.sh --run
  ) > "$LOG" 2>&1
  RC=$?
  set -e
  echo "[D05 STUDENT A] 종료 코드=$RC (모든 노드 CLEAN 종료를 뜻하지 않음)"
  exit "$RC"
)
~~~

추가 로그 보기: tail -n 50 "$(cat "$HOME/axia_d05_student_live_logs/latest.logpath")". 이 옵션에서도 실행기를 백그라운드에 방치하지 않고 **터미널 A가 소유한 GUI/ROS 프로세스를 정리**한다. 터미널 B Ctrl+C는 구독만 종료한다. 전체 시연을 중단하려면 터미널 A에서 Ctrl+C.

## 4. Live 영상과 실제 미터값 계산의 차이 (학생 TODO 연계)

**Live의 Bounding Box는 거리값이 아니다.** 학생이 미터 단위 값을 직접 출력하는 실습은 합성 fixture를 이용해 구현하는 기존 공개 TODO이다. 별도 Python에서 바로 중앙값 원리를 먼저 확인한다.

~~~bash
python3 - <<'PY'
from statistics import median
pixels_m = [1.0, 1.2, 1.4, 1.6]
print(f"D05_STUDENT_SYNTHETIC_MEDIAN={median(pixels_m):.2f}m")
PY
~~~

**예상 출력:** D05_STUDENT_SYNTHETIC_MEDIAN=1.30m. 이 숫자는 실제 Gazebo 센서 실측이 **아니고 합성 ROI 값**이다. [D05_STUDENT_LAB_GUIDE_KO.md](D05_STUDENT_LAB_GUIDE_KO.md)를 따라 기존 개인 작업 폴더의 block_B/block_b_todo.py::measure_person_range() 함수를 직접 작성하여 RED→GREEN으로 검증한다. `invalid`와 timestamp 불일치에서는 UNKNOWN을 반환해야 하며, UNKNOWN은 안전(CLEAR)과 다르다.

접근 변화율 수치화는 같은 사람의 두 **유효한 거리 샘플** 사이에서만 의미가 있으며, f001과 임의의 다른 프레임을 같은 사람이라고 가정해서 위험 확률을 만들지 않는다. 학생 TODO를 현재 Live ROS Depth에 연결하는 별도 어댑터는 **이번 문서에서 구현하지 않았다**.

## 5. 공개 CI 근거와 미검증 사항

- 이미 성공한 공개 통합 실제 Gazebo CI: https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43353480617 — 실제 ROS 2 Jazzy/Gazebo Harmonic RGB-D/YOLO/Xvfb GUI, 등록된 RGB-D 쌍 13개, person 2건, bbox 면적 변화 약 16.7%; private 거리 Observer는 NOT_RUN.
- 이 가이드 게시용 공개 Python CI는 **문서 계약·기존 코드 보존**만 검증한다. 신규 사용자 WSL2 Gazebo/GUI 실행은 NOT_RUN.
- 기존 강사 WSL2에서는 2.860311–3.025961m 실제 Z-depth가 관측됐으나 이는 **강사 비공개 Observer**의 별도 선행 증거이다.
- 안전 경계: NO_GOAL / NO_CMD_VEL / NO_ESTOP. 인증된 E-Stop과 소프트웨어 정지는 다르며 이번 교육용 Actor는 실제 충돌 장애물이 아니다.

## 6. 오류 확인 및 종료

| 현상 | 가장 먼저 확인 | 판단 |
|---|---|---|
| self-check만 성공 | GAZEBO_NOT_RUN 표기 | 실제 Live 미실행 |
| Gazebo GUI가 안 보임 | WSLg DISPLAY, AXIA_D04_STUDENT_GUI=1 | GUI 미인수 |
| Depth 토픽이 없음 | camera_link RGB-D → ros_gz_image bridge, Domain 49 | 센서 전달 미검증 |
| YOLO person이 없음 | RGB 입력, Actor 시야, yolo_ros 로그 | 검출 미검증 |
| D05_PRIVATE_DISTANCE_OBSERVER=NOT_RUN | 학생 sensor-only인지 확인 | **정상 범위 제한** |
| person bbox가 움직이지만 미터값이 없음 | 학생 TODO↔ROS adapter 미구현 | **예정된 기능 아님** |
| 실행 코드 0이 아닌 종료 | 증거 폴더/최초 입력 실패/타이밍 위반 확인 | PASS 금지 |

기존 실행 증거는 고유 폴더 ~/axia_d04_student_evidence/d04-gazebo-*에 저장된다. 최신 폴더의 실제 결과를 확인한다.

~~~bash
OUT="$(ls -dt "$HOME"/axia_d04_student_evidence/d04-gazebo-* | head -n1)"
cat "$OUT/live_verdict.json"
tail -n 60 "$OUT/gazebo_nav2.log"
tail -n 60 "$OUT/camera_bridge.log"
tail -n 60 "$OUT/yolo_ros.log"
~~~

**수업 종료:** 터미널 A의 소유 실행기에서 Ctrl+C로 Gazebo·YOLO를 정리하고, B에서 Ctrl+C로 구독을 닫는다. 전역 pkill, WSL2 강제 종료, 학생 개인 TODO 디렉터리 삭제는 하지 않는다. 최초 RGB/Depth/YOLO 데이터 경계와 50ms/0.5s 시각 제약을 왜곡하지 않는다.

**학생 제출 체크:** Gazebo에서 Waffle와 접근하는 사람, YOLO bbox 화면 캡처 / 실제 Depth 토픽 이름·타입 확인 / 합성 ROI 1.30m 계산과 UNKNOWN 원인 설명 / 실측·합성·미검증 기능을 구분한 한 문장 결론.

**마지막 확인:** 이 D05 Live는 기존 원본 D04 GUI 실행기를 재사용한 **학생용 공개 시연**이다. 학생 정답·강사 비공개 소스는 포함하지 않는다.
