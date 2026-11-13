# D05 학생용 데모 가이드 — 1.30m와 접근 추세를 직접 관찰하기

**수업:** 2026-11-13(금), 19:00–22:00 / 이론 1시간·실습 2시간.
**학습 목표:** (1) Depth 기반 사람-로봇 간 거리 계산 구조 이해 (2) 접근 위험 수치화 및 거리정보 추출 실습.
**검증 범위:** SYNTHETIC_COURSE_FIXTURE / ROS_GAZEBO_NOT_RUN / NO_GOAL / NO_CMD_VEL.

> 교육용 Z-depth는 카메라 광축 방향 깊이다. 로봇 외곽과 사람 사이의 실제 최소 이격거리, 위험 확률 또는 안전인증값이 아니다. UNKNOWN을 CLEAR(안전)로 취급해서는 안 된다.

## 1. D04 → D05 시스템 아키텍처

~~~text
[강사 선행 인수: 실제 Gazebo 단일 registered RGB-D]
 Gazebo RGB-D camera
   ├─ /axia/d05/aligned/image ─→ yolo_ros ─→ /yolo/cam0/detections (bbox)
   └─ /axia/d05/aligned/depth ──────────────────┐
                                                 ↓
                          D05 read-only range observer
                   ROI/valid fraction/median + stamp/age
                                                 ↓
                      /axia/d05/person_range_status
                                  VALID / UNKNOWN
[학생 D05: 별도의 Python 합성 데이터]
 detections.csv + depth_samples.json
    ↓ D04 select_person() TODO → D05 measure_person_range() TODO
    ↓ person_range.csv, summary.json (PYTHON_ONLY)
~~~

학생 필수 D05는 ROS와 Gazebo 없이 Python으로 수행한다. 선택적 **D04 실시간 Gazebo+YOLO GUI**는 기존 [D04 학생 데모 가이드](../day04/D04_GAZEBO_YOLO_GUI_STUDENT_GUIDE_KO.md)에 있다. 해당 GUI는 YOLO bbox를 시각화하지만 D05 aligned Depth 관측기를 실행하지 않는다. 두 데모를 한 화면의 실시간 거리 추정이라고 잘못 설명하지 않는다.

**학생 PC에서 실제 Gazebo RGB-D·YOLO 장면을 직접 관찰하려면** [D05 학생 Gazebo Live Demo 가이드](D05_STUDENT_GAZEBO_LIVE_GUIDE_KO.md)를 따른다. 공개 sensor-only 모드라서 카메라 Depth 토픽과 YOLO bbox를 보여주지만, 이 페이지의 합성 median `1.30m`를 실시간 센서에서 계산해 출력하는 것은 아니다. 기존 D04 GUI 및 학생 TODO 과제와 구분한다.

## 2. 첫 성취 — 1분 만에 1.30m 출력

**터미널 A 하나**, Python 3만 사용한다. 새로운 ROS/Gazebo 터미널이 필요 없다.

~~~bash
python3 - <<'PY'
from statistics import median
roi_m = [1.0, 1.2, 1.4, 1.6]
print(f"D05_STUDENT_DEMO_RANGE_M={median(roi_m):.2f}")
PY
~~~

**예상 출력(합성 픽셀 4개):**

~~~text
D05_STUDENT_DEMO_RANGE_M=1.30
~~~

해설: 4×4 Depth 배열에서 D04 bbox=[1,1,3,3]이 가리키는 2×2 ROI의 유효값 중앙값이다. 이 숫자는 실물 로봇이나 Gazebo 센서에서 측정한 거리가 아니다.

## 3. 접근 변화율로 접근 상황 수치화 — 별도의 합성 변화율

같은 사람의 전방 Z-depth가 1초 동안 2.0m에서 1.5m로 감소했다고 **가정**한다.

~~~bash
python3 - <<'PY'
z0_m, z1_m, dt_s = 2.0, 1.5, 1.0
rate_mps = (z1_m - z0_m) / dt_s
print(f"D05_APPROACH_RATE_MPS={rate_mps:+.2f}")
print("D05_APPROACH_TREND=" + ("APPROACHING" if rate_mps < 0 else "NOT_APPROACHING"))
PY
~~~

**예상 출력:**

~~~text
D05_APPROACH_RATE_MPS=-0.50
D05_APPROACH_TREND=APPROACHING
~~~

음수는 **이 가정에서** 카메라의 Z-depth가 줄었다는 관측이다. 사람 추적 ID, 카메라 움직임, 센서 유효성의 영향은 별도 검증 사항이다. 이 변화율을 충돌 확률, 법정 안전거리, Collision Monitor 정지 임계값으로 사용하지 않는다.

## 4. 무효 Depth 픽셀과 UNKNOWN

~~~bash
python3 - <<'PY'
from math import isfinite
roi_m = [0.0, float("nan"), float("inf"), 0.9]
valid = [v for v in roi_m if isfinite(v) and 0.15 <= v <= 8.0]
print(f"D05_VALID_FRACTION={len(valid)/len(roi_m):.2f}")
if 2 * len(valid) < len(roi_m):
    print("D05_UNKNOWN_REASON=INSUFFICIENT_VALID_DEPTH")
PY
~~~

**예상 출력:**

~~~text
D05_VALID_FRACTION=0.25
D05_UNKNOWN_REASON=INSUFFICIENT_VALID_DEPTH
~~~

해설: 유효 픽셀 1/4=25%이므로 교육 계약의 최소 50%에 못 미친다. 하나의 0.9m만 가지고 정상 거리라고 선언하지 않는다. 위 짧은 코드는 개념 데모이며, 실제 학생 함수는 timestamp/bbox/영상 형식까지 검사해야 한다.

## 5. 본 실습 연결: 기존 학생 TODO는 그대로

학생 작업 저장소를 reset/clean 하지 않는다. 전날 구현한 D04 select_person()을 보존한다. 아직 작업 공간이 없다면 독립 공개 브랜치를 새 위치에 복제한다.

~~~bash
# 최초 설치 시에만
git clone --single-branch --branch feature/block-b-d05-class-20261112 \
  https://github.com/silverbjin/axia-robot-safety-student.git \
  "$HOME/axia_d05_student_course"
~~~

기존 D04 과제를 해결한 학생은 자신의 **기존 checkout**을 그대로 사용한다. 이 경우 터미널에서 먼저 AXIA_D05_STUDENT_REPO 환경변수에 기존 실제 저장소 경로를 지정한다. 복제본과 원본 사이에 TODO를 자동 복사/덮어쓰기 하지 않는다.

~~~bash
# 본인이 실제로 실습할 저장소로 이동한다.
REPO="${AXIA_D05_STUDENT_REPO:-$HOME/axia_d05_student_course}"
cd "$REPO"
bash block_B/day04/run_student_fixture_once.sh --fixture
~~~

**예상:** 4 passed, D04_FIXTURE_ISOLATED_PASS (입력 fixture의 무결성 확인만 의미).

D05 구현 전에는 아래 테스트가 **의도적으로 RED**다.

~~~bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q \
  block_B/tests/test_block_b_public.py \
  -k 'f001_median_depth or depth_stamp_mismatch_returns_unknown'
~~~

**RED 예상:** NotImplementedError: TODO_D05_PERSON_RANGE. 기존 D04 및 D05 두 함수를 완성한 후에는 위 두 테스트 GREEN을 확인하고 전체 재생을 실행한다.

~~~bash
OUT="results/d05_student_$(date +%Y%m%d_%H%M%S)_$$"
.venv/bin/python -m block_B.run_lab --out "$OUT"
cat "$OUT/person_range.csv"
cat "$OUT/summary.json"
~~~

**학생 구현 완료 후 예상 출력(합성 데이터):**

~~~text
PYTHON_SYNTHETIC_ONLY: 3 frames; output=results/d05_student_...
frame_id,person_found,distance_m,range_valid
f001,True,1.3,True
f002,False,,False
f003,True,,False
~~~

CSV에는 UNKNOWN 문자열 컬럼이 없다. distance_m 비어 있음 + range_valid=False가 관측 불가 상태에 대응한다. summary.json에는 source=SYNTHETIC_COURSE_FIXTURE, ros_verified=false, gazebo_verified=false가 기록된다.

## 6. 실제 공개 CI 증거는 강사 화면으로 비교

기존 [D05 실제 Gazebo+YOLO L2 공개 Actions #42646086413](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/42646086413)에는 실제 bbox=[253,15,387,445], YOLO confidence≈0.9005, valid 46267/57620, median **2.179178m**가 기록되어 있다.

Depth 브리지만 중단했을 때 RGB와 YOLO는 계속 수신되고 D05 Observer는 VALID→UNKNOWN, distance_m=null, reason=STALE_INPUT이 되었다. **이것은 선행 CI 실측(49 Python passed)**이지 학생 PC에서 이번 데모로 Gazebo를 실행한 결과가 아니다. 강사 WSL2 기능 인수도 과거 별도 증거에 있으며 모든 프로세스의 CLEAN 종료 인증은 아님.

## 7. 터미널 종료 및 진단

- 필수 Python 데모/pytest/replay는 자체 종료한다. 새 터미널 불필요.
- 선택적 D04 Gazebo GUI를 켰다면 **자신이 실행한 터미널에서 Ctrl+C**를 누른다. 일괄 pkill, WSL2 강제 종료 금지.
- **LAB_BLOCKED: Output directory must not exist**면 기존 결과를 삭제하지 말고 새 --out 경로를 선택한다.
- 학생 질문: 1.30m는 무엇의 거리인가? 50ms와 51ms가 다른 이유는? 무효 75%일 때 왜 UNKNOWN인가? −0.50m/s는 위험 확률인가?

**안전 경계:** 교육용 관측 지표일 뿐 실제 보호 정지/Goal/Collision Monitor/인증된 HW E-Stop 검증은 수행하지 않는다. SW Stop은 인증된 E-Stop이 아니다.
