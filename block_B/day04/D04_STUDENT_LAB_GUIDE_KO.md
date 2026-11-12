# AXIA D04 — 학생용 실습 가이드: YOLO 사람 검출 결과를 검증하는 개발자

> **대상:** 2026-11-12 D04 (19:00–22:00, 이론 60분 + 실습 120분)  
> **실습 범위:** 필수 = Python 3.12+, pytest 8.3.5, **합성 CSV**. 선택 = 강사와 동일한 Python YOLO 코드로 **실제 이미지 1장 CPU 추론**(Ultralytics·공식 모델·공식 샘플 사진은 학생 PC에서 준비). ROS 2/Gazebo 불필요.  
> **관련 교안:** D04 v5 32장, 특히 11–16장(데이터 경계), 22–31장(실습·코드·검증).
> **주의:** 필수 `select_person()`은 합성 데이터 실습이다. 선택형 이미지 YOLO 실행은 **동일한 강사용 Python 코드**를 별도로 실행하는 것이며, 실제 Gazebo/ROS Detection과 자동 연결되지 않는다.

## 0. 실습 시작 전: 강사 YOLO 환경 오류와 학생 과제는 별개 (2026-11-12 보완)

강사 선택형 이미지 데모에서 `No module named 'ultralytics'` 또는 `can't open file '/home/.../training/block_B/instructor/yolo_single_image_demo.py'`가 나오더라도 **이 학생 실습은 진행할 수 있다**. 해당 스크립트는 비공개 강사 저장소의 Python/`.pt` 이미지 추론 데모로, 기존 학생 TODO 코드와는 별도였다. 이제 **같은 추론 스크립트를 `block_B/day04/yolo_single_image_demo.py`에 공개**했다. 필수 CSV 실습에는 Ultralytics·PyTorch·Gazebo·ROS·모델 가중치가 필요 없고, **선택형 실제 이미지 추론**을 할 때만 학생용 가상환경에 Ultralytics와 공식 모델·샘플 사진을 준비한다.

독립 학생 저장소가 **이미 있다면 그대로 재사용하고, 없다면 최초 1회 clone**한 뒤 저장소 루트에서 명령을 실행한다. `~/`에서 바로 `python3 training/...`을 실행하지 않는다. 아래는 새 터미널 하나에서 수행할 최소 진단이다.

~~~bash
(
  set -Eeuo pipefail
  DIR="$HOME/axia-robot-safety-student-d04"
  BRANCH="feature/block-b-d04-shared-yolo-demo-20261112"

  if [[ -d "$DIR/.git" ]]; then
    # 기존 실습·.venv·개인 작업물을 삭제하거나 reset하지 않는다.
    [[ "$(git -C "$DIR" branch --show-current)" == "$BRANCH" ]] || {
      echo "D04_STUDENT_BRANCH_CHECK_REQUIRED"; exit 2; }
    [[ -z "$(git -C "$DIR" status --porcelain --untracked-files=no)" ]] || {
      echo "D04_STUDENT_LOCAL_CHANGES_PRESERVED: 직접 확인 후 병합"; exit 2; }
    git -C "$DIR" fetch origin "$BRANCH"
    git -C "$DIR" merge --ff-only FETCH_HEAD
  elif [[ ! -e "$DIR" ]]; then
    git clone --single-branch --branch "$BRANCH" \
      https://github.com/silverbjin/axia-robot-safety-student.git "$DIR"
  else
    echo "D04_STUDENT_DIRECTORY_EXISTS_NOT_GIT=$DIR"; exit 2
  fi

  bash "$DIR/block_B/day04/run_student_fixture_once.sh" --fixture
)
~~~

**이미 clone한 학생 저장소를 보존하는 절차입니다.** 새 폴더를 만들거나 기존 `.venv`를 삭제하지 않습니다.

**기대 출력:** `4 passed`와 `D04_FIXTURE_ISOLATED_PASS PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. 기존 `~/axia-robot-safety-student-d04`가 있다면 재-clone하지 않고 공개 브랜치를 **fast-forward만** 수행한다. 개인의 수정이 감지되면 자동 병합을 중지하며 삭제·reset하지 않는다. 이 검사 PASS는 **합성 fixture 무결성만** 의미한다.

**이번 WSL2 오류의 최초 원인:** ROS 2 Jazzy를 source한 터미널의 `launch_testing` pytest11 플러그인이 자동 검색됐고, 학생용 `.venv`에는 그 플러그인에 필요한 `PyYAML`이 없어 `ModuleNotFoundError: No module named 'yaml'`이 났다. **fixture 코드가 실행되기 전의 테스트 환경 오류**다. `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`은 이 학생용 pytest 호출에서만 외부 플러그인 자동 검색을 끄는 최소 수정이며, 전역 ROS 설치나 학생 가상환경에 불필요한 ROS 의존성을 추가하지 않는다.

**이미 설치된 `.venv`에서 직접 확인할 때** (새 스크립트 없이도 가능): `cd ~/axia-robot-safety-student-d04 && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q block_B/tests/test_fixture_io.py`.

다음 D04 선택 테스트는 기본 TODO에서 `NotImplementedError: TODO_D04_SELECT_PERSON`으로 **예상 RED**이다. 함수를 직접 구현한 뒤에만 GREEN이다. D05 `measure_person_range()` 테스트가 남아 있어 전체 `block_B/tests`는 D04 완료 시점에도 실패할 수 있다.

**이번 WSL2 회귀의 실제 공개 CI:** [RED #43159446189](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43159446189)에서 외부 `pytest11` 플러그인의 `No module named 'yaml'` 오류를 모사하고, 수정 전 안내·CPU 설치 경계 **3 failed / 기존 12 passed**를 확인했다. [GREEN #43160240955](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43160240955)에서 **15 passed**, [실제 CPU YOLO #43160241004](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43160241004)에서 **4 persons / CSV 4 rows / PASS**를 확인했다. 환경 회귀는 공개 CI의 재현 모의 플러그인 테스트이며, **사용자 WSL2의 pytest를 이 CI가 직접 실행한 것은 아니다**. 학생 `select_person()` TODO의 GREEN이나 Gazebo/ROS 실기 PASS로 승격하지 않는다.

---

## 0-A. 강의 슬라이드별 소스 코드 지도 — 학생이 열어볼 파일

| 슬라이드 | 주제 / 코드 | 학생에게 공개된 위치 | 실행 범위 |
|---|---|---|---|
| 8장 | 공식 Waffle Pi RGB를 임시 모델에 결합 | [D04 ROS 코드 해설](D04_ROS_CODE_WALKTHROUGH_KO.md) `overlay.py` 발췌 | 개념 학습, 강사용 P1 전체는 비공개 |
| 9장 | YOLO DetectionPlugin 설정 | [D04 ROS 코드 해설](D04_ROS_CODE_WALKTHROUGH_KO.md) `config.py` 발췌 | 설명용 YAML, 모델을 새로 개발하지 않음 |
| 10장 | ROS 이미지 브리지와 upstream YOLO launch | [D04 ROS 코드 해설](D04_ROS_CODE_WALKTHROUGH_KO.md) `d04_p1_yolo.launch.py` 발췌 | 강사 P1 원본을 포함하므로 학생 단독 ROS launch는 아님 |
| 21장 | **강사와 동일한 YOLO Python 이미지 추론** | [`block_B/day04/yolo_single_image_demo.py`](yolo_single_image_demo.py) | **학생 개인 PC에서 실제 CPU 추론 가능** |
| 23장 | 합성 CSV·SHA256 판독 | [`block_B/fixture_io.py`](../fixture_io.py) | 필수 |
| 25장 | 기대 결과·예외 단위 테스트 | [`block_B/tests/test_block_b_public.py`](../tests/test_block_b_public.py) | 필수 |
| 27장 | 사람 후보 선택 TODO 구현 | [`block_B/block_b_todo.py`](../block_b_todo.py) | **학생이 직접 완성** |

강사 Python 데모의 **동일한 파일 바이트를 학생용으로 복제**했다(Git blob SHA: `9eb5fb41ea3836da5bade7fcdb3bce99969fc212`). 따라서 강사가 화면에서 해설한 `YOLO(...)`, `model.predict(...)`, `boxes.cls/conf/xyxy`, `detections.csv` 저장 코드를 그대로 따라가며 실행할 수 있다. 이 코드는 **강사 정답 코드인 `block_b_reference.py`나 hidden tests를 포함하지 않는다.**

> 강사 **실제 Gazebo/ROS2 동적 Bounding Box**는 비공개 P1과 공식 Nav2를 포함하는 별도 통합 시연이다. 아래 Python **정지 이미지 1장 추론**은 그 전체 ROS 실행기를 복제하는 것이 아니다. 학생에게도 영상→YOLO→검출 데이터의 핵심만 재현하도록 범위를 좁혔다.

## 0-B. 강사와 동일한 Python YOLO 시연 재현 — 선택 과제

**성취 목표:** 학생 PC에서도 사진을 YOLO로 실제 추론한 뒤 `class`·`confidence`·`bbox`를 추출하여 `detections.csv`와 `run_manifest.json`을 만든다. 이를 통해 1번 학습 목표(구조 이해)를 직접 관찰한다.

**권장 환경:** WSL2 Ubuntu 24.04 / Python 3.12 / 인터넷 연결 / CPU 추론 가능. 설치와 첫 모델 다운로드는 환경에 따라 오래 걸릴 수 있으므로 수업 전 준비 또는 수업 후 선택 과제로 수행한다. **필수 CSV TDD 수업을 멈춰가며 설치하지 않는다.**

### 기존 학생 저장소의 활용

**필수 CSV 실습은 0절의 `~/axia-robot-safety-student-d04`를 재사용**한다. 별도의 `~/axia_d04_student_yolo`를 이미 다운로드하여 실제 YOLO 추론에 성공했다면 **그 성과물·가상환경을 유지하고 재설치하지 않는다.** 두 저장소를 반복 clone할 필요는 없다. 저장소가 없다면 0절 명령 한 번으로 준비한다.

### 실제 이미지 YOLO CPU 데모 — 한 번에 실행

학생 저장소 루트에서:

~~~bash
bash block_B/day04/run_teacher_yolo_demo_once.sh --self-check
bash block_B/day04/run_teacher_yolo_demo_once.sh --run
~~~

- `--self-check`: 소스 존재·구문 경계만 확인하며 모델이나 ROS를 실행하지 않는다.
- `--run`: 학생 전용 venv `~/.venvs/axia-d04-student-yolo`를 준비하고, **새 설치에서는 공식 CPU 전용 PyTorch/Torchvision을 먼저 설치한 다음** Ultralytics `8.4.211`을 확인·필요 시 설치한다. 이어 공식 YOLO26n `yolo26n.pt`와 Ultralytics 제공 `bus.jpg`를 **학생의 로컬 캐시**에 준비한 뒤, 강사 코드와 똑같은 Python 스크립트로 한 장을 CPU 추론한다.
- 재실행은 설치·다운로드 캐시를 재사용한다. 모델·사진·개인 결과는 **학생 Git 저장소가 아닌 `~/.cache/axia/d04_student_yolo`와 `~/axia_d04_student_results`**에 보관한다. 모델/원본 사진을 Git에 추가하거나 배포하지 않는다.
- 이미 Ultralytics가 설치된 다른 Python을 사용하려면 `AXIA_D04_STUDENT_PYTHON="/절대경로/bin/python" bash block_B/day04/run_teacher_yolo_demo_once.sh --run`을 사용한다.

**실제 성공 시에만 예상하는 출력 패턴** (정확한 검출 수는 모델/이미지에 따라 달라짐):

~~~text
D04_STUDENT_ULTRALYTICS_IMPORT_OK
D04_STUDENT_OFFICIAL_IMAGE_READY
LOCAL_YOLO_CPU_ONLY: N persons; output=/home/.../axia_d04_student_results/...
D04_STUDENT_REAL_IMAGE_LOCAL_CSV_ROWS=N
D04_STUDENT_INFERENCE_SCOPE=LOCAL_YOLO_CPU_ONLY
D04_STUDENT_ROS_GAZEBO_NAV2_SAFETY=NOT_RUN
~~~

**현장 실측:** 제공된 로그에서는 `LOCAL_YOLO_CPU_ONLY: 4 persons`와 `D04_STUDENT_REAL_IMAGE_LOCAL_CSV_ROWS=4`를 확인했다.

**성공 판독:** `D04_STUDENT_STATIC_PASS`는 소스와 정적 구문 확인, `D04_STUDENT_DOCTOR_PASS=PREREQUISITES_ONLY`는 실행 전 준비 완료, `LOCAL_YOLO_CPU_ONLY: 4 persons`는 실제 이미지 1장에서 사람 4명 추론, `D04_STUDENT_REAL_IMAGE_LOCAL_CSV_ROWS=4`는 해당 결과의 CSV 기록 수 확인이다. `D04_STUDENT_ROS_GAZEBO_NAV2_SAFETY=NOT_RUN`은 **실패가 아니라** 이 Python 데모에서는 ROS 2·Gazebo·Nav2·안전 정지를 수행하지 않았다는 **검증 범위 표시**다. 이미 이 출력이 나왔다면 다시 모델을 실행하거나 내려받지 않는다.
 이는 이미 성공한 실행이며, 테스트 환경 수정 때문에 다시 YOLO를 실행할 필요가 없다. 이전 설치에서 대용량 CUDA 패키지가 내려받아졌더라도 자동 제거하거나 venv를 삭제하지 않는다. 새 환경에서만 CPU 전용 PyTorch 설치 순서를 적용한다.

`N`은 실측할 값이다. 특정 인원 수·confidence를 고정된 정답처럼 주장하지 않는다. **이 과정은 실제 Python YOLO 추론이고, 기존 4×4 합성 CSV의 `f001/f002/f003`과는 출처·이미지 크기·검출 결과가 전혀 다르다.**

### 출력 직접 확인 및 코드 해설

~~~bash
ls -dt "$HOME"/axia_d04_student_results/teacher_same_code_* | head -n 1
OUT="$(ls -dt "$HOME"/axia_d04_student_results/teacher_same_code_* | head -n 1)"
head -n 5 "$OUT/detections.csv"
cat "$OUT/run_manifest.json"
sed -n '1,120p' block_B/day04/yolo_single_image_demo.py
~~~

강사가 질문한다면 다음 순서로 설명한다: **① `YOLO(model)` 모델 준비 → ② `predict(image,device="cpu")` → ③ 사람 아닌 클래스 제거 → ④ `boxes.cls/conf/xyxy` → ⑤ CSV 기록 → ⑥ 모델·사진 SHA256과 검증 범위 manifest 기록.** 다음 필수 과제에서 그 검출 결과와 **동일한 필드 구조를 갖춘 합성 CSV**를 사용해 `select_person()`을 스스로 구현한다.

**구현 범위 구분:** 공개된 강사 데모 코드는 **복사·실행·분석용**이다. 학생 TODO 정답이 아니다. `block_B/block_b_todo.py::select_person`은 기존대로 직접 구현한다. D05 `measure_person_range`는 변경하지 않는다.

**최초 오류별 진단:**
- `No module named ultralytics` → `python3`를 직접 호출하지 말고 위 `--run` 실행기의 선택한 venv에서 import하도록 한다.
- `yolo26n.pt` 또는 `bus.jpg` 다운로드 실패 → 인터넷 접근·공식 URL·로컬 캐시 상태 점검. 가짜 빈 파일로 통과시키지 않는다.
- `Output directory must not exist` → 기존 결과를 보존하고 새 출력 폴더 사용(원샷은 자동 생성).
- `0 persons` → 추론 성공일 수 있다. 이미지·모델·confidence 판단을 분리하고 person 검출을 보장하지 않는다.
- `ROS topic /camera/image_raw`가 없음 → 이 데모는 **ROS와 무관**하다. 실제 ROS 실기는 별도 강사 프로그램이다.

**자산·라이선스:** Ultralytics 제공 `yolo26n.pt`와 샘플 `bus.jpg`는 학생 PC에서 **직접 공식 배포처로부터 다운로드**하며 저장소에 포함하지 않는다. Ultralytics YOLO26 모델·코드는 **AGPL-3.0 또는 별도 Enterprise 라이선스** 대상이므로 이용 목적·재배포 조건을 검토한다. [공식 YOLO26 빠른 시작](https://docs.ultralytics.com/ko/models/yolo26), [Ultralytics Licensing](https://docs.ultralytics.com/), [Ultralytics 이미지 예제](https://ultralytics.com/images/bus.jpg). 실습용 Python 프로그램 자체를 공개했다고 해서 해당 모델의 라이선스가 변경되는 것은 아니다.

**테스트 증거 구분:** 공개 CI의 모의 YOLO API 테스트가 `PASS`여도 실물 모델의 품질·학생 PC 실추론까지 보장하지 않는다. 실제 로컬 `LOCAL_YOLO_CPU_ONLY` 인수는 본인이 출력·manifest를 확인한 뒤 보고한다. Nav2 Goal·안전정지·인증 E-Stop 검증은 범위 밖이다.

---

## 0-C. 강사 Gazebo 실기의 로봇 상태를 RViz2로 확인 (관찰 선택 과제)

슬라이드 8~10장의 **실제 로봇 상태 파악**을 위해 [공개 D04 RViz2 관찰 가이드](https://github.com/silverbjin/axia-robot-safety-ci-public/blob/fix/d04-course-field-preflight-20261112/docs/D04_RVIZ_ROBOT_STATE_GUIDE_KO.md)와 [바로 여는 `axia_d04_robot_state.rviz` 구성파일](https://github.com/silverbjin/axia-robot-safety-ci-public/blob/fix/d04-course-field-preflight-20261112/rviz/axia_d04_robot_state.rviz)을 제공한다. 강사는 기존 D04 Gazebo/ROS2 원샷에 RViz2 자동 열기를 포함했다.

- **RobotModel:** `/robot_description`에서 Waffle 링크 모델 확인
- **LaserScan:** `/scan` 데이터의 거리점과 frame_id/Best Effort QoS 확인
- **TF:** `/tf`, `/tf_static`이 Fixed Frame `odom`까지 연결되는지 확인
- **Camera:** `/camera/image_raw`(실제 RGB)와 `/yolo/cam0/debug_image`(bbox) 비교
- **Odometry:** `/odom`; 강사 D04는 Goal 없이 정지된 로봇 시연

**중요한 실행 범위:** 앞의 `run_teacher_yolo_demo_once.sh`는 **사진 한 장을 Python으로 추론**하므로 ROS 2/Gazebo·로봇 모델·LaserScan·TF를 실행하지 않는다. 따라서 **학생 개인 PC에서 단일 이미지 데모만 실행한 경우 RViz에 로봇은 나타나지 않는다.** 이 RViz 실습은 강사가 라이브 D04 ROS 시연을 띄운 환경을 함께 관찰하거나, 학생이 합법적으로 사용 가능한 별도 TurtleBot3 ROS 시뮬레이션을 실행하는 경우에만 한다.

강사 D04 원샷은 기존 비공개 P1을 참조하므로 학생의 독립 저장소만으로 전체 D04 ROS launch를 재현하도록 요구하지 않는다. RViz 관찰 체크리스트는 별도 5분 미션이며 학생 TODO `select_person()`의 합격 판정과도 별개다. 안전 TTL/인증 E-Stop은 RViz 화면만으로 검증되지 않는다.

---

## 1. 오늘의 미션: 검출된 후보 중 '유효한 사람 1명' 선택

강사는 실제 YOLO 영상에서 `class`, `confidence`, `bbox`를 보여준다. 여러분은 **`SYNTHETIC_COURSE_FIXTURE`로 표시된 합성 검출 데이터**를 읽고, 어떤 후보를 사용할 수 있는지 판단하는 코드를 작성한다. 학생 전원이 동일한 입력으로 TDD를 재현하도록 만든 데이터이며, 선택형 YOLO 실추론 결과에서 자동 생성된 데이터가 아니다.

~~~text
[실제 시스템, 강사 선택 시연]
Gazebo Waffle Pi RGB → ros_gz_image → yolo_ros C++/ONNX
                               ├─ /yolo/cam0/detections
                               └─ /yolo/cam0/debug_image
[독립적인 학생 필수 실습 — 자동 연결 아님]
fixtures/detections.csv → load_fixtures() → select_person() → person/None
~~~

- `person` 이외의 클래스는 제외한다. 예를 들어 `chair 0.97`보다 `person 0.92`를 선택한다.
- `confidence >= 0.5`인 유효한 사람 중 최고 점수 **1개**를 선택한다. 동점이면 먼저 들어온 사람을 유지한다.
- `bbox`는 `[x1,y1,x2,y2)`의 정수 픽셀 좌표이고, 이미지 내부에 있는 양수 면적의 사각형이어야 한다.
- 잘못된 사람의 숫자·좌표는 조용히 보정하지 않고 `ValueError`를 발생시킨다.
- 해당 임계값 이상의 사람이 없으면 `None`을 반환한다. 이것은 **안전이 확인됐다는 뜻이 아니다**.

## 2. 준비: 터미널 A 하나만 열기 (약 10분)

**0절 명령을 먼저 실행한다.** 학생 코드 저장소가 이미 있고 `.venv`에 `pytest==8.3.5`가 설치되어 있으면 재설치하지 않는다. 새 실행기가 학생 저장소의 `.venv/bin/python`을 선택하고 필요할 때만 pytest를 설치한다. **ROS 2·Gazebo·YOLO 설치 불필요**.

~~~bash
cd "$HOME/axia-robot-safety-student-d04"
git rev-parse HEAD
git status --short
bash block_B/day04/run_student_fixture_once.sh --fixture
~~~

**기대 확인:** 커밋 SHA, 수정사항 여부, `4 passed`, `D04_FIXTURE_ISOLATED_PASS`. `git status`에 개인 수정사항이 있으면 삭제하지 않고 보존한다. `python3 -m venv`에서 `ensurepip`가 없다면 Ubuntu의 `python3-venv` 설치 여부를 확인한다. 개인 구현은 `work/block-b-d04-person-내학번` 브랜치에서 수행하며, 강사/공개 강의 자료 브랜치에 정답을 직접 push하지 않는다.

## 3. 데이터 파악과 무결성 검사 (약 20분)

~~~bash
head -n 5 block_B/fixtures/detections.csv
bash block_B/day04/run_student_fixture_once.sh --fixture
~~~

**예상 CSV (제공된 합성 데이터):**

~~~csv
frame_id,stamp_s,category,confidence,x1,y1,x2,y2,image_width,image_height
f001,1.00,person,0.92,1,1,3,3,4,4
f001,1.00,chair,0.97,0,0,2,2,4,4
f002,2.00,person,0.34,1,1,3,3,4,4
f003,3.00,person,0.80,0,0,2,2,4,4
~~~

**예상 fixture pytest:** `4 passed`와 `D04_FIXTURE_ISOLATED_PASS` (실행 환경에 따라 시간 표시는 달라짐). `Fixture hash mismatch`는 파일 변경·손상을 뜻한다. 체크섬을 다시 만들어 통과시키지 말고 **원본을 복구**한다. 파일 해시는 무결성 검사이지 실제 카메라 출처 인증은 아니다.

강사 발문: f001에서 가장 높은 score가 `chair`인데, 왜 사람 후보가 다르게 선택되는가? f002에는 `person 0.34`가 있는데 왜 출력은 `None`이어야 하는가?

## 4. RED — 실패를 먼저 확인한다 (약 15분)

~~~bash
bash block_B/day04/run_student_fixture_once.sh --red
~~~

**미구현 TODO의 예상 오류:** 내부 pytest는 `NotImplementedError: TODO_D04_SELECT_PERSON`으로 RED(exit code 1). 공개 실행기는 이 메시지와 실패를 확인하고 `D04_STUDENT_TODO_EXPECTED_RED rc=1`로 보고한다. D04 대상 일부 테스트는 의도적으로 RED이며 정상 교육 단계다. **정확한 실패 개수는 실제 pytest 출력으로 기록**한다. 설치·import·fixture 해시 오류는 의도한 RED가 아니다.

- 구현 파일: `block_B/block_b_todo.py`
- 구현 대상: `select_person(detections, min_confidence=0.5)` **한 함수만**
- `measure_person_range`는 **D05 과제**이므로 변경하지 않는다.
- 강사에게 정답 코드를 요청하기 전에 첫 실패 테스트의 입력, 예상 조건, 실제 에러를 1문장으로 정리한다.

## 5. GREEN A — '사람 하나를 제대로 고르는' 최소 구현 (약 25분)

`block_B/block_b_todo.py`를 열고 `select_person()`을 작성한다. 먼저 다음 흐름을 직접 코드로 옮긴다.

1. 입력 리스트를 순회하며 `category == "person"`인지 확인한다.
2. confidence를 숫자로 파싱하고 최소 임계값 이상인지 확인한다.
3. 유효한 사람 중 가장 높은 confidence 1개를 반환한다.
4. 해당하는 사람이 없으면 `None`을 반환한다.

아직 경계 조건에서 실패할 수 있다. **테스트의 실패 지점이 이전과 어떻게 달라졌는지** 확인하고 다음 단계로 간다.

## 6. GREEN B — 실무형 입력 검증 (약 20분)

다음 입력은 **반례**이며, 실제 코드에서 허용해서는 안 된다.

| 데이터 | 요구 동작 | 이유 |
|---|---|---|
| `person, confidence="NaN"` | `ValueError` | 비교 불가능한 비유한 수 |
| `person, confidence=1.1` 또는 `-0.1` | `ValueError` | 범위 [0,1] 위반 |
| `person, confidence=True` | `ValueError` | bool을 숫자로 취급하지 않음 |
| `bbox x1=-1` | `ValueError` | 이미지 밖 좌표 |
| `bbox x1=x2` | `ValueError` | 면적 0 |
| `confidence=0.50` | 선택 허용 | 임계값 포함 경계 |
| 같은 confidence 사람 2개 | 먼저 나온 후보 | 결정적 결과 |

상세 계약: 좌표 6개(`x1`, `y1`, `x2`, `y2`, `image_width`, `image_height`) 모두 정수이며 `0 <= x1 < x2 <= width`, `0 <= y1 < y2 <= height`, `width,height>0`. 숫자 문자열 `"1"`은 허용하되 `"1.5"`는 좌표로 허용하지 않는다.

## 7. REFACTOR → REVIEW — D04 대상만 회귀검사 (약 15분)

~~~bash
bash block_B/day04/run_student_fixture_once.sh --green
git diff -- block_B/block_b_todo.py
~~~

**성공 기준:** 선택된 D04 대상 테스트가 모두 PASS하고, 수정 파일이 `block_B/block_b_todo.py`의 D04 함수 범위로 제한됨. `pytest`가 실패하면 마지막 `FAILED` 메시지가 아니라 **가장 먼저 발생한 Assertion/ValueError/NotImplementedError**를 분석한다.

**중요:** `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q block_B/tests`는 D05의 미완성 TODO까지 포함하므로 **D04만 끝난 날 전체 PASS를 요구하지 않는다.** D04 단위 테스트 결과와 D05 미검증을 분리한다.

## 8. 결과 재생 — 실제 출력과 예상값 비교 (약 10분)

~~~bash
.venv/bin/python - <<'PY'
from pathlib import Path
from block_B.fixture_io import load_fixtures
from block_B.block_b_todo import select_person

rows, _ = load_fixtures(Path('block_B/fixtures'))
for frame in ('f001', 'f002', 'f003'):
    candidates = [row for row in rows if row['frame_id'] == frame]
    selected = select_person(candidates)
    score = 'NONE' if selected is None else f"person {float(selected['confidence']):.2f}"
    print(f'{frame}: {score}')
PY
~~~

**올바른 구현의 예상 출력** (합성 CSV 재생):

~~~text
f001: person 0.92
f002: NONE
f003: person 0.80
~~~

`f002: NONE`은 **후처리 정책상 선택된 사람이 없음**을 뜻하지, 모델에서 `person` 후보가 전혀 생성되지 않았다는 뜻이 아니다. 강사 실제 YOLO 엔진의 threshold 0.15와 이 실습의 threshold 0.5는 다른 단계의 값이다.

## 9. 문제가 생겼다면 어디부터 볼까?

| 첫 관측 오류 | 확인 지점 | 해결 범위 |
|---|---|---|
| `No module named 'yaml'` / `launch_testing` | ROS의 pytest11 자동 플러그인이 학생 venv로 유입됨 | `run_student_fixture_once.sh --fixture` 또는 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 적용 |
| `ModuleNotFoundError` (기타) | `.venv/bin/python` 및 저장소 루트·필수 pytest 확인 | 환경 |
| `Fixture hash mismatch` | `SHA256SUMS`와 원본 fixture | 입력 |
| `TODO_D04_SELECT_PERSON` | 구현 파일/대상 함수 | 구현 |
| 예상 `None` 대신 사람 선택 | 클래스 및 임계값 비교 | 후보 선택 |
| 비정상 좌표 통과 | bbox 경계·정수 확인 | 데이터 계약 |
| D04 테스트는 GREEN, 전체는 RED | D05 `measure_person_range` | 다음 수업; D04 성공 유지 |

## 10. 제출물과 수업 종료

- 본인이 수정한 `select_person()`, D04 표적 pytest의 **실제 stdout/exit code**, f001~f003 **실제 출력**.
- 가장 먼저 재현된 오류 한 건의 `증상 → 원인 → 수정 → 회귀 테스트` 설명.
- `git rev-parse HEAD`와 개인 변경사항(`git diff`) 기록, 실행 환경·미검증 항목 명시.
- 본 가이드는 `.venv/bin/python`을 직접 실행하므로 `deactivate`가 불필요하다. 이전에 직접 `source .venv/bin/activate`를 실행했다면 마지막에 `deactivate`한다. 새로운 ROS/Gazebo 터미널은 이 실습에 필요 없다.

**검증 수준:** 필수 TODO TDD PASS는 `PYTHON_SYNTHETIC_D04_ONLY`. 선택형 이미지 데모를 실제 실행하고 CSV·manifest를 확인한 학생만 `LOCAL_YOLO_CPU_ONLY`를 별도로 보고한다. **ROS 2 실시간 구독·Gazebo 동작·Nav2 Goal·사람 안전 정지·인증 E-Stop은 검증하지 않았다**. `None`을 CLEAR 또는 자동 재주행 허가로 해석하지 않는다.

**참고:** [기존 D04 LAB](LAB.md), [공통 Block B 가이드](../README_KO.md), [Ultralytics Predict](https://docs.ultralytics.com/modes/predict), [ROS 2 Jazzy Topic CLI](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html)
