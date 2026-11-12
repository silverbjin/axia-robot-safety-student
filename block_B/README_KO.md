# AXIA Block B — D04 사람 검출 / D05 거리 측정 (학생용)

- **D05 11/13 실습 시작:** [D05 RGB-D ROI median·UNKNOWN 학생 가이드](day05/D05_STUDENT_LAB_GUIDE_KO.md) — D04 개인 작업물 보존, 학생 TODO 독립 수행. 기존 ROS/Gazebo 안전제어와 별개.

**상태:** 합성 CSV/Depth 교육 실습. 실제 ROS 2 / Gazebo / 로봇 주행 안전 인증이 아닙니다.

- 필요: Python 3.12+, pytest 8.3.5 (필수 경로에 torch, GPU, 카메라, ROS 없음)
- 입력: `fixtures/detections.csv`, `fixtures/depth_samples.json`, `fixtures/scenario_manifest.json`, `fixtures/SHA256SUMS`
- TODO: `block_b_todo.py`의 `select_person`, `measure_person_range` 두 함수만 작성
- 정상 센서 유효성 판단: bbox/image bounds, confidence, 단위 m, 0/NaN/Inf 필터, 최소 ROI 유효 비율 50%, 영상/Depth stamp 차이 0.05s 이하(교육용 예시값)

## D04 Gazebo GUI 실시간 YOLO 시연 — 사진 1장 실습과 별개

[Gazebo 학생 시연 가이드](day04/D04_GAZEBO_YOLO_GUI_STUDENT_GUIDE_KO.md)를 먼저 확인한다. 이전 `run_teacher_yolo_demo_once.sh`는 실제 YOLO26n 모델로 사진 한 장만 추론하므로 Gazebo가 열리지 않는다. **학생이 강사의 시연과 같이 로봇과 움직이는 사람 및 실시간 Bounding Box를 관찰하려면** WSL2 Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic에서 새 학생 GUI 실행기 `block_B/day04/run_student_gazebo_yolo_once.sh --run`을 사용한다. 학생 GUI용 공개 브랜치에서 제공되며 **비공개 강사 저장소·정답은 필요 없다**.

Gazebo 및 YOLO 프리뷰 화면이 실제 표시됐는지 학생 PC에서 관찰하고, `D04_STUDENT_GAZEBO_YOLO_LIVE_PASS`의 실제 메시지 수신 여부와 구분한다. 시각용 사람은 충돌 장애물이 아니고, Goal/안전 정지/인증 E-Stop은 검증하지 않는다.

## 시작 명령 (저장소 최상위에서, 터미널 하나)

**ROS 2 Jazzy를 이미 source한 WSL2**에서는 pytest가 `launch_testing`을 자동 검색하여 `No module named 'yaml'`로 시작 단계에서 실패할 수 있습니다. D04 학생 실습에는 ROS 2용 pytest 플러그인이 필요하지 않으므로 **학생용 실행기**를 사용합니다.

~~~bash
# 1) 필수 합성 CSV / checksum 검사: 4 passed 예상
bash block_B/day04/run_student_fixture_once.sh --fixture

# 2) 구현 전 D04의 의도적인 RED: TODO_D04_SELECT_PERSON 확인
bash block_B/day04/run_student_fixture_once.sh --red

# 3) select_person() 학생 구현 후에만 GREEN 검사
bash block_B/day04/run_student_fixture_once.sh --green
~~~

`--red`는 내부 pytest에서 `TODO_D04_SELECT_PERSON`이 실제로 발생했을 때 `D04_STUDENT_TODO_EXPECTED_RED rc=1`을 표시하고 **스크립트 자체는 0을 반환**합니다. 이것은 GREEN이 아닙니다. `--green`은 학생의 TODO가 미완성이라면 **실패해야 정상**입니다.

학생 실행기는 저장소의 `.venv`를 선택·필요시 생성하고 `pytest==8.3.5`만 준비합니다. 외부 플러그인 자동 탐색은 해당 명령에서만 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`로 차단하며 ROS 설치를 변경하지 않습니다. 이미 내려받은 폴더와 `.venv`를 삭제하지 마세요.

**D04와 D05를 모두 완료한 이후에만** 다음 전체 검증과 합성 데이터 재생을 실행합니다.

~~~bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q block_B/tests
.venv/bin/python -m block_B.run_lab --out results/d04_d05_run1
cat results/d04_d05_run1/person_range.csv
~~~

`--out` 경로는 **새 디렉터리**여야 합니다. 같은 경로 재실행은 `LAB_BLOCKED`로 차단됩니다. `results/`는 제출 자료로만 이용하며 Git에 올리지 않습니다. D04만 끝난 시점에 D05 실패로 전체 RED가 나오는 것은 예견된 상태입니다.

### 예상 결과(실제 로봇 출력 아님)

- `f001`: 사람이 감지되고 거리 중앙값 약 `1.30m`
- `f002`: 사람 confidence가 임계값 미달 → `person_found=False`
- `f003`: ROI 깊이 데이터의 유효 비율 미달 → `distance_m` 비어 있음

데이터에 써 있는 프레임 4×4는 **합성 배열**입니다. 실제 YOLO 추론 영상·거리센서 정밀도 증거가 아닙니다.

## 안전·제출

- 본 실습은 `/cmd_vel`을 발행하지 않고 Goal/Fault도 실행하지 않습니다.
- `None`(미확인 거리)을 안전하다고 간주하지 마십시오. 위험 응답은 D06에서 별도 학습합니다.
- SW Stop은 인증된 HW E-Stop이 아닙니다.
- 제출: 두 TODO 함수, 공개 pytest 결과, 실행 결과 CSV, Git SHA와 CI 링크, 미검증 항목.
- 수업 종료: `.venv/bin/python`을 직접 사용하므로 `deactivate`가 필요 없습니다. 가상환경을 수동 활성화했다면 종료 시 `deactivate`; 새 터미널은 불필요합니다.
