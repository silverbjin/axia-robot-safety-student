# D05 학생 실습 — YOLO Bounding Box → 정렬 Depth ROI → 사람 거리

- **2026-11-13(금) 19:00–22:00:** 이론 1시간, 실습 2시간
- **학습 목표:** D04 bbox로 정렬된 Depth ROI를 선택하고, 유효 픽셀 median을 미터(m)로 계산하며 invalid/stale를 UNKNOWN으로 처리
- **실습 범위:** SYNTHETIC_COURSE_FIXTURE / Python 3.12+ / pytest 8.3.5 / ROS·Gazebo·GPU 불필요 / NO_GOAL / NO_CMD_VEL
- **강사 정답 비공개:** 학생은 block_B/block_b_todo.py의 기존 measure_person_range() TODO를 직접 구현한다. 강사 정답과 hidden tests는 학생 공개 저장소에 넣지 않는다.

## 0. 먼저 결과를 눈으로 확인

어제 D04의 bbox=(1,1,3,3)은 4×4 영상에서 반열린 구간 [1,3)×[1,3)의 2×2 ROI이다. 오늘의 합성 Depth는 ROI 네 값이 **[1.0,1.2,1.4,1.6] m**, median은 **1.30m**다. 반면 Depth가 끊기거나 invalid 픽셀이 많으면 **UNKNOWN**이어야 한다. 마지막 정상 측정값을 재사용하지 않는다.

~~~text
YOLO: person, bbox=[1,1,3,3]
       ↓ 정렬이 확인된 aligned RGB ↔ Depth
Depth ROI: [1.0,1.2,1.4,1.6]
       ↓ 4/4 valid, median
f001 = 1.30m (교육용 합성값)
~~~ 

**현업 연결:** 서비스로봇이 사람 거리 알림을 만들기 전에 센서의 입력 품질, 정렬, 수신 시간과 무효값을 검증해야 한다. UNKNOWN은 CLEAR/안전의 증거가 아니다.

### 공식 참고

- ROS Image header.stamp/optical frame: https://github.com/ros2/common_interfaces/blob/rolling/sensor_msgs/msg/Image.msg
- 32FC1/16UC1 인코딩: https://github.com/ros2/common_interfaces/blob/rolling/sensor_msgs/include/sensor_msgs/image_encodings.hpp
- RGB/Depth 동기화: https://github.com/ros2/message_filters/blob/rolling/doc/index.rst
- 실제 카메라 정렬 사례(RealSense align_depth.enable): https://github.com/realsenseai/realsense-ros

**중요:** 동일 크기·동일 timestamp만으로는 정렬이 증명되지 않는다. 이번 입력의 aligned_to_rgb=true는 합성 fixture의 전제이며 실제 센서 교정을 대신하지 않는다. 실제 드라이버에 따라 Depth 단위도 확인해야 한다.

## 1. 환경 준비 — 20:00–20:15 (터미널 1개)

D04 select_person()을 이미 완성했다면 **기존 checkout과 개인 수정을 보존**한다. reset/clean 금지. 새 학생 PC에서 처음 설치할 때만 다음 원샷을 실행한다. 최초 clone에는 D04/D05 TODO가 모두 남아 있으므로 D04 과제를 먼저 마쳐야 전체 GREEN이다.

~~~bash
(
  set -Eeuo pipefail
  DIR="$HOME/axia-robot-safety-student-d04"
  if [[ ! -e "$DIR" ]]; then
    git clone --single-branch --branch feature/block-b-d05-class-20261112 \
      https://github.com/silverbjin/axia-robot-safety-student.git "$DIR"
  fi
  test -f "$DIR/block_B/block_b_todo.py" || { echo "D05_REPO_PATH_CHECK_REQUIRED=$DIR"; exit 2; }
  if [[ ! -x "$DIR/.venv/bin/python" ]]; then python3 -m venv "$DIR/.venv"; fi
  "$DIR/.venv/bin/python" -m pip install --disable-pip-version-check 'pytest==8.3.5'
  cd "$DIR"
  echo "D05_REPO_SHA=$(git rev-parse HEAD)"
  bash block_B/day04/run_student_fixture_once.sh --fixture
)
~~~ 

**예상:** pytest fixture **4 passed**, D04_FIXTURE_ISOLATED_PASS, D04_FIXTURE_SCOPE=SYNTHETIC_COURSE_FIXTURE. 아직 거리 계산/Gazebo 검증이 아니다. D04 Gazebo GUI가 실행 중이라면 해당 터미널에서 **Ctrl+C**로 종료한다. 학생 필수 실습은 터미널 1개만 쓴다.

## 2. RED — 20:15–20:30

기존 학생 block_B/block_b_todo.py를 열어 measure_person_range()의 TODO_D05_PERSON_RANGE를 확인한다. 이미 본인이 구현했다면 일부러 코드를 초기화하지 않는다.

~~~bash
cd "$HOME/axia-robot-safety-student-d04"
mkdir -p "$HOME/axia_d05_student_logs"
set -o pipefail
set +e
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q \
  block_B/tests/test_block_b_public.py \
  -k 'f001_median_depth or depth_stamp_mismatch_returns_unknown' \
  2>&1 | tee "$HOME/axia_d05_student_logs/d05_red.txt"
D05_RED_RC=$?
set -e
echo "D05_RED_RC=$D05_RED_RC"
~~~ 

**미완성 TODO일 때 예상:** NotImplementedError: TODO_D05_PERSON_RANGE, pytest exit 1. 이 실패는 **의도된 학생 RED**이지 GREEN/실기 PASS가 아니다. ROS 소싱으로 불필요한 pytest 플러그인 오류가 났던 D04 경험을 반영해 이 호출에만 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1을 쓴다.

## 3. GREEN — 20:30–21:10

**수정 파일은 1개:** block_B/block_b_todo.py의 measure_person_range() 함수. 기존 D04 select_person(), run_lab.py, fixtures, SHA256SUMS를 수정하지 않는다.

구현 계약(정답 코드는 제공하지 않음):

1. 유한·비음수 RGB/Depth timestamp를 검사한다. **최대 skew 50ms(0.05s, 경계 포함)**; 51ms는 None.
2. bbox는 이미지 안의 정수 x1,y1,x2,y2와 image_width/image_height. 빈 ROI/이미지 밖은 ValueError.
3. Depth는 RGB에 정렬된 동일 크기의 직사각형 2D 배열로 가정한다. ragged grid·치수 불일치는 ValueError.
4. ROI의 0/NaN/Inf, 비숫자, 0.15m 미만, 8.0m 초과는 버린다.
5. **유효 픽셀 수×2 ≥ ROI 픽셀 수**이면 유효 픽셀 median을 미터로 반환한다. 부족하면 None.
6. None은 거리 미확인 **UNKNOWN**으로 해석하며 0m·안전·최근 수치로 바꾸지 않는다.

~~~bash
cd "$HOME/axia-robot-safety-student-d04"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q \
  block_B/tests/test_block_b_public.py \
  -k 'f001_median_depth or depth_stamp_mismatch_returns_unknown'
~~~ 

**예상:** 선택한 두 공개 테스트 PASS (직접 구현 완료 시). 실제 출력과 테스트 수를 기록한다.

## 4. 반례·경계 — 21:10–21:35

| 조건 | 결과 |
|---|---|
| 정상 4개 ROI [1.0,1.2,1.4,1.6] | median=1.3m |
| ROI valid < 50% | None → UNKNOWN |
| 정확히 50% valid | median 허용 |
| RGB↔Depth 50ms | 허용 |
| RGB↔Depth 51ms | None → UNKNOWN |
| bbox 빈 영역/음수/이미지 밖 | ValueError |
| Depth ragged grid | ValueError |
| 0/NaN/Inf/범위 외 | 픽셀 제외 |

~~~bash
cd "$HOME/axia-robot-safety-student-d04"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q \
  block_B/tests/test_block_b_public.py -k 'depth or roi or ragged'
~~~ 

**예상:** D05 범위의 선택 계약 테스트가 PASS. 이 테스트는 학생 Python 구현만 시험하며 ROS 센서 주기/TTL이나 로봇 안전 정지를 검증하지 않는다.

## 5. 전체 GREEN·결과 CSV — 21:35–21:50

D04와 D05의 두 학생 TODO가 모두 완료된 뒤 다음 명령을 실행한다. 각 실행은 **새로운 출력 디렉터리**를 사용한다.

~~~bash
cd "$HOME/axia-robot-safety-student-d04"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q \
  block_B/tests 2>&1 | tee "$HOME/axia_d05_student_logs/d05_green.txt"

OUT="results/d04_d05_$(date +%Y%m%d_%H%M%S)_$$"
.venv/bin/python -m block_B.run_lab --out "$OUT"
cat "$OUT/person_range.csv"
cat "$OUT/summary.json"
git rev-parse HEAD
~~~ 

**기대 출력 예시(합성 데이터, 현재 학생 실행 결과는 아님):**

~~~text
PYTHON_SYNTHETIC_ONLY: 3 frames; output=results/d04_d05_...
frame_id,person_found,distance_m,range_valid
f001,True,1.3,True
f002,False,,False
f003,True,,False
~~~ 

CSV에는 UNKNOWN이라는 컬럼 자체가 없다. **range_valid=False + 비어 있는 distance_m**가 UNKNOWN에 대응한다. summary.json은 source=SYNTHETIC_COURSE_FIXTURE, verified_level=PYTHON_ONLY, ros_verified=false, gazebo_verified=false여야 한다. 기존 --out 디렉터리 존재 시 LAB_BLOCKED는 데이터 덮어쓰기를 방지하는 정상 동작이다.

## 6. 실제 Gazebo 사례 비교·종료 — 21:50–22:00

과거 공개 GitHub Actions 실제 Gazebo 인수: https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/42646086413

- Gazebo 실제 person bbox=[253,15,387,445], confidence≈0.9005, **median 2.179178m**, 유효 Depth 46267/57620(80.30%).
- Depth bridge를 끄자 RGB·YOLO는 계속 수신되지만 D05 거리 관측은 **VALID → UNKNOWN, distance_m=null, STALE_INPUT**.
- 이 결과는 학생의 1.30m **합성 fixture와 다른 실측 데이터**. 2026-11-10 강사 WSL2 관측 기능 인수도 별도 기록이 있지만 전체 프로세스 완전 정상 종료 인증은 아니다.
- 거리 관측 성공은 Nav2 Goal, Collision Monitor Stop, 인증된 E-Stop 성공을 의미하지 않는다.

**제출물:** 본인 수정 block_B/block_b_todo.py, d05_red.txt(시작이 TODO였을 경우), d05_green.txt, person_range.csv, summary.json, Git SHA, 50ms/51ms와 invalid/UNKNOWN 반례 설명.

**종료:** pytest/run_lab은 자동 종료한다. 별도로 D04 Gazebo 프로세스가 있다면 소유 터미널에서 Ctrl+C. 수동으로 .venv를 source한 경우에만 deactivate. reset/clean, wsl --shutdown, 전역 pkill은 사용하지 않는다. GitHub 공개 CI의 문서·fixture PASS를 **학생 본인의 TODO GREEN이나 실제 ROS/Gazebo 실행 PASS로 승격하지 않는다.**
