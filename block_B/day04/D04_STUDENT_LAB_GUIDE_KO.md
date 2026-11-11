# AXIA D04 — 학생용 실습 가이드: YOLO 사람 검출 결과를 검증하는 개발자

> **대상:** 2026-11-12 D04 (19:00–22:00, 이론 60분 + 실습 120분)  
> **실습 범위:** Python 3.12+, pytest 8.3.5, **합성 CSV 데이터**. ROS 2/Gazebo/카메라/모델 설치 불필요.  
> **관련 교안:** D04 v4 32장, 특히 11–16장(데이터 경계), 22–31장(실습·코드·검증).
> **주의:** 여기서는 실제 YOLO를 실행하지 않는다. D04의 학습용 `select_person`은 ROS 실시간 노드와 자동 연결되지 않는다.

## 1. 오늘의 미션: 검출된 후보 중 '유효한 사람 1명' 선택

강사는 실제 YOLO 영상에서 `class`, `confidence`, `bbox`를 보여준다. 여러분은 **검출 결과처럼 생긴 기록 데이터**를 읽고, 어떤 후보를 사용할 수 있는지 판단하는 코드를 작성한다.

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

**처음 다운로드하는 경우:** Ubuntu 24.04 / WSL2 또는 일반 Linux 터미널에서 아래를 순서대로 실행한다. 폴더가 이미 있다면 중복 clone하지 말고 해당 저장소로 이동하여 현재 브랜치를 확인한다.

~~~bash
git clone --single-branch --branch feature/block-b-d04-guides-20261112 \
  https://github.com/silverbjin/axia-robot-safety-student.git \
  axia-robot-safety-student-d04
cd axia-robot-safety-student-d04
git rev-parse HEAD
git status --short
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pytest==8.3.5
~~~

**예상 확인:** `git rev-parse HEAD`에 40자리 SHA 출력, `git status --short`는 깨끗한 상태에서 아무 줄도 없음, `python --version`은 3.12 이상, `pytest` 설치 정상 종료. 이 단계는 모델 추론이나 ROS 실기 검증이 아니다.

- `No module named venv` 또는 `ensurepip` 오류: Ubuntu 패키지 `python3-venv` 설치가 필요한지 확인한다.
- 기존 작업 디렉터리를 덮어쓰지 않는다. 강사는 배포 브랜치/커밋 SHA를 수업 시작 전에 공지한다.
- 학생 개인 구현은 `git switch -c work/d04-person-내학번`처럼 **개인 작업 브랜치**에서 한다. 교사 공유 브랜치에 push하지 않는다.

## 3. 데이터 파악과 무결성 검사 (약 20분)

~~~bash
head -n 5 block_B/fixtures/detections.csv
python -m pytest -q block_B/tests/test_fixture_io.py
~~~

**예상 CSV (제공된 합성 데이터):**

~~~csv
frame_id,stamp_s,category,confidence,x1,y1,x2,y2,image_width,image_height
f001,1.00,person,0.92,1,1,3,3,4,4
f001,1.00,chair,0.97,0,0,2,2,4,4
f002,2.00,person,0.34,1,1,3,3,4,4
f003,3.00,person,0.80,0,0,2,2,4,4
~~~

**예상 pytest:** `4 passed` (실행 환경에 따라 시간 표시는 달라짐). `Fixture hash mismatch`는 파일 변경·손상을 뜻한다. 체크섬을 다시 만들어 통과시키지 말고 **원본을 복구**한다. 파일 해시는 무결성 검사이지 실제 카메라 출처 인증은 아니다.

강사 발문: f001에서 가장 높은 score가 `chair`인데, 왜 사람 후보가 다르게 선택되는가? f002에는 `person 0.34`가 있는데 왜 출력은 `None`이어야 하는가?

## 4. RED — 실패를 먼저 확인한다 (약 15분)

~~~bash
python -m pytest -q block_B/tests/test_block_b_public.py \
  -k 'select_person or confidence or bbox'
~~~

**미구현 TODO의 예상 오류:** `NotImplementedError: TODO_D04_SELECT_PERSON` 및 비정상 종료(exit code 1). D04 대상 일부 테스트는 의도적으로 RED이며 정상 교육 단계다. **정확한 실패 개수는 실제 pytest 출력으로 기록**한다. 설치·import·fixture 해시 오류는 의도한 RED가 아니다.

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
python -m pytest -q block_B/tests/test_block_b_public.py \
  -k 'select_person or confidence or bbox'
git diff -- block_B/block_b_todo.py
~~~

**성공 기준:** 선택된 D04 대상 테스트가 모두 PASS하고, 수정 파일이 `block_B/block_b_todo.py`의 D04 함수 범위로 제한됨. `pytest`가 실패하면 마지막 `FAILED` 메시지가 아니라 **가장 먼저 발생한 Assertion/ValueError/NotImplementedError**를 분석한다.

**중요:** `python -m pytest -q block_B/tests`는 D05의 미완성 TODO까지 포함하므로 **D04만 끝난 날 전체 PASS를 요구하지 않는다.** D04 단위 테스트 결과와 D05 미검증을 분리한다.

## 8. 결과 재생 — 실제 출력과 예상값 비교 (약 10분)

~~~bash
python - <<'PY'
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
| `ModuleNotFoundError` | venv 활성화 / 현재 저장소 루트 | 환경 |
| `Fixture hash mismatch` | `SHA256SUMS`와 원본 fixture | 입력 |
| `TODO_D04_SELECT_PERSON` | 구현 파일/대상 함수 | 구현 |
| 예상 `None` 대신 사람 선택 | 클래스 및 임계값 비교 | 후보 선택 |
| 비정상 좌표 통과 | bbox 경계·정수 확인 | 데이터 계약 |
| D04 테스트는 GREEN, 전체는 RED | D05 `measure_person_range` | 다음 수업; D04 성공 유지 |

## 10. 제출물과 수업 종료

- 본인이 수정한 `select_person()`, D04 표적 pytest의 **실제 stdout/exit code**, f001~f003 **실제 출력**.
- 가장 먼저 재현된 오류 한 건의 `증상 → 원인 → 수정 → 회귀 테스트` 설명.
- `git rev-parse HEAD`와 개인 변경사항(`git diff`) 기록, 실행 환경·미검증 항목 명시.
- 마지막 터미널에서 `deactivate`. 새로운 ROS/Gazebo 터미널은 이 실습에 필요 없다.

**검증 수준:** 통과해도 `PYTHON_SYNTHETIC_D04_ONLY`. YOLO 실제 추론, ROS 2 실시간 구독, Gazebo 동작, Nav2 Goal, 사람 안전 정지, 인증 E-Stop은 **검증하지 않았다**. `None`을 CLEAR 또는 자동 재주행 허가로 해석하지 않는다.

**참고:** [기존 D04 LAB](LAB.md), [공통 Block B 가이드](../README_KO.md), [Ultralytics Predict](https://docs.ultralytics.com/modes/predict), [ROS 2 Jazzy Topic CLI](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html)
