# AXIA D08 — 온라인 4시간 통합 실습 및 제출 ZIP (교육생용)
교육일: **2026-11-18(수) 19:00~23:00**. 학습형태: 온라인/개별 Python 실습.

## 학습 목표
1. D04 사람 검출 → D05 깊이 중간값 → D06 STOP/SLOWDOWN/CLEAR/UNKNOWN → D07 recorded route replan 해설을 **새로운 ROS 제어 코드 없이** 연결한다.
2. 잘못된 인식·거리 정렬·유효시각을 발견하면 UNKNOWN을 CLEAR 또는 모터 재주행 허가로 처리하지 않는다.
3. 6개 합성 시나리오의 실제 `trace.csv`, `summary.json`, `pytest.txt`, `SHA256SUMS`를 **ZIP 1개**로 제출한다.

**사전 조건:** D04 `block_B/block_b_todo.py`, D06 `day06/safety_bubble_todo.py`, D07 `day07/route_todo.py` 기능을 지난 실습에서 구현했어야 한다. 미완료라면 동일 TODO를 먼저 완성한다. 강사 정답 제공 금지.

## 수강 전 — 최초 다운로드와 사전 학습 확인

**실습 플랫폼:** Python 3.12 이상과 pytest만 필요합니다. 학생 PC에서 ROS 2, Gazebo, GPU, 실제 로봇은 사용하지 않습니다. 강사용 정답 저장소도 다운로드하지 않습니다.

처음 받는 학생은 **터미널 하나**를 열어 아래 순서로 실행합니다.

```bash
git clone --branch feature/d08-online-integration-todo-20261110 --single-branch \
  https://github.com/silverbjin/axia-robot-safety-student.git
cd axia-robot-safety-student
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'pytest==8.3.5'
python --version
```

이미 다른 브랜치에서 작업한 코드가 있다면 덮어쓰기나 `git reset --hard` 대신 새 폴더에 위 브랜치를 복제합니다. 다음 모든 명령은 **저장소 루트**에서 실행합니다.

**선행 GREEN:** D04 `select_person`·`measure_person_range`, D06 `bubble_policy`, D07 `assess_replan`의 학생 본인 구현이 준비돼 있어야 합니다. 선행 TODO가 미완성이라면 D08 실패를 억지로 PASS 처리하지 말고 부족한 함수부터 보완합니다.

## 실제 사고로 연결하는 15~20분 토의

[실제 Gazebo·YOLO 분류 실패의 데이터 파이프라인 진단](D08_FIELD_DIAGNOSTIC_CASE_KO.md)을 읽습니다. 초기 사람은 로봇에서 약 1.35m 앞에 있었고, WSL2 현장에서는 `person=0 / umbrella=64`였습니다. 반면 가까운 0.36m의 실제 Gazebo 영상 재생에서는 `yolo_ros`가 `person`을 검출했습니다. 원거리 분류 실패의 원인이 **거리만**이라고 확정하지 말고 RGB-D 최근 정합, 검출 결과, LiDAR 안전 계층의 각 검증 수준을 구분합니다. 이 활동은 19:00~20:00의 복습 시간에 포함하며 별도 설치·Goal을 요구하지 않습니다.

## 일정/터미널
| 시각 | 내용 | 강사의 확인 포인트 |
|---|---|---|
| 19:00~20:00 | D04→D07 흐름 복습 + 실제 YOLO 현장 장애 진단(15~20분) | 실제 사람과 합성 person_xy 좌표가 TF로 정렬됐다고 주장하지 않음 |
| 20:00~21:00 | `integration_todo.py` 하나만 구현, RED→GREEN | STOP 우선, 오래된 데이터 UNKNOWN |
| 21:00~22:00 | 여섯 사례 실행·CSV/JSON 분석 | CLEAR/REPLAN, SLOWDOWN, STOP, lost/stale 3건 |
| 22:00~23:00 | 검사결과 저장, SHA256 ZIP 제출 및 발표 | 누락·위조·심볼릭링크 ZIP 거부 |

**터미널:** 기존 가상환경/터미널 1개만 사용. 파일 생성 시 새 터미널 불필요. 완료 후 `deactivate`.

## 0. 준비/기대 출력 (저장소 루트)
```bash
python -m pytest -q block_B/day08/tests/test_d08_public.py::test_d08_synthetic_fixture_contract \
  block_B/day08/tests/test_d08_submission_zip.py
```
**예상:** fixture/ZIP 테스트 **10 passed**. 이 단계는 student TODO GREEN이 아니다.

## 1. RED → 단일 TODO 구현
```bash
python -m pytest -q block_B/day08/tests/test_d08_public.py
```
**미구현이면 기대:** `test_d08_synthetic_fixture_contract` 1 PASS, `TODO_D08_INTEGRATE_CASE` 때문에 통합 테스트 2 FAIL. 실패 시 바로 다음 단계에서 `block_B/day08/integration_todo.py`의 `integrate_case()`를 채운다.

함수는 기존 `select_person`, `measure_person_range`, `bubble_policy`, `assess_replan`을 **재사용**하고 `case_id, person_detected, distance_m, range_status, route_status, advice, expected_ratio` 및 고정된 **모든 false 검증 플래그**를 반환한다. ROS/`/cmd_vel`/NavigateToPose 호출 불가.

## 2. GREEN → 결과 관찰

```bash
mkdir -p results
set -o pipefail
python -m pytest -q block_B/tests block_B/day06/tests block_B/day07/tests block_B/day08/tests \
  2>&1 | tee results/d08_pytest_capture.txt
# 위 명령이 종료코드 0인 경우에만 다음 단계를 실행합니다.
python -m block_B.day08.run_lab --out results/d08_run1
cat results/d08_run1/trace.csv
```
**기대:** 기존 TODO까지 모두 완성했을 때 모든 pytest 통과, `D08_PYTHON_FIXTURE_REPLAY_PASS cases=6`. 기록된 합성 데이터의 `advice`는 다음 순서:
`REPLAN_REVIEW`, `SLOWDOWN_EXPECTED`, `STOP_EXPECTED`, `UNKNOWN_REVIEW` 3건.
선행 TODO가 미완성이라면 `D08_LAB_BLOCKED:NotImplementedError`이며 결과 출력이 생성되지 않아야 정상이다.

## 3. ZIP 1개 제출
```bash
cp results/d08_pytest_capture.txt results/d08_run1/pytest.txt
python -m block_B.day08.submission_zip \
  --run-dir results/d08_run1 --out results/d08_submission.zip
python - <<'PY'
import hashlib,zipfile
with zipfile.ZipFile('results/d08_submission.zip') as z:
    assert sorted(z.namelist())==sorted(['trace.csv','summary.json','pytest.txt','integration_todo.py','SHA256SUMS'])
    assert z.testzip() is None
    for row in z.read('SHA256SUMS').decode().splitlines():
        digest,name=row.split('  ')
        assert hashlib.sha256(z.read(name)).hexdigest()==digest
print('D08_ZIP_HASH_VERIFY_PASS')
PY
```
**예상:** `D08_SUBMISSION_ZIP_PASS`와 `D08_ZIP_HASH_VERIFY_PASS`. 제출 ZIP에는 학생이 실제 작성한 `integration_todo.py`도 자동 포함되므로 강사가 함수를 검토할 수 있습니다. `results/d08_submission.zip`만 제출한다.

### 제출 전 자가 확인

- 반드시 `pytest` **종료코드 0**을 확인합니다. 쉘 파이프라인에서 실패를 놓치지 않도록 위의 `set -o pipefail`을 그대로 사용합니다.
- `trace.csv` 6행의 판정과 `summary.json` 6개 결과를 비교합니다. `lost`·`stale_depth`·`stale_track`은 모두 `UNKNOWN_REVIEW`여야 합니다.
- ZIP은 결과 4파일(`trace.csv`, `summary.json`, `pytest.txt`, `integration_todo.py`)과 `SHA256SUMS` **총 5파일**입니다. 실제 CI/WSL2 안전 인증 증거가 아닙니다.
- `results/d08_submission.zip` **1개**만 제출합니다.

**ZIP에 포함된 코드:** `run_lab.py`가 실행에 성공할 때 D08 `integration_todo.py`의 **학생 본인 버전**을 결과 디렉터리에 복사합니다. 강사 정답, 이전 D04~D07 전체 패키지나 개인정보를 ZIP에 추가하지 마십시오.

**안전·범위:** 여섯 사례는 새로 작성한 *합성* 4×4 깊이/검출/지도상 가상 사람 위치 자료다. 실제 YOLO 카메라→Nav2 map 좌표 TF 정렬이 아니며 ROS/Gazebo/실제 주행/충돌 0회 검증이 아니다. 출력은 설명/분석용이고 산업용 안전 명령이 아니다. SW_STOP과 인증 하드웨어 E-Stop은 다르다.

**오류 복구:** 결과 경로/ZIP 존재 시 덮어쓰지 않는다. `results/d08_run2`와 `results/d08_submission2.zip`처럼 새 이름을 사용한다. 누락 pytest, 실패 로그, 부정확한 보고, 심볼릭 링크, 큰 파일, 잘못된 해시는 BLOCKED되어야 한다. ZIP 제출 후 venv 종료.

## 검증 범위 / 실습 배포 상태

- 공개 학생 GitHub Actions의 D08 스캐폴드·ZIP L0: [최신 가이드 포함 검증 기록](https://github.com/silverbjin/axia-robot-safety-student/actions/workflows/d08-online-integration-student.yml). 이 검사는 합성 fixture 및 ZIP 계약 **10개 PASS**와 미구현 `integrate_case`의 **의도된 RED**를 확인한다.
- 선행 D04~D07과 D08을 모두 학생 본인이 구현해 통과하는 `FULL_STUDENT_GREEN`은 학생별 결과에 따라 별도 판정한다. 강사 정답/hidden tests는 이 공개 저장소에 없다.
- [실제 Gazebo NO-GOAL L2](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43117842587)와 [실제 YOLO ROS 영상 재생 L1](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43118537433)은 **강사 설명용 근거**다. 학생 D08 Python 실습이 로봇 주행·안전 제어를 검증했다고 해석하면 안 된다.
