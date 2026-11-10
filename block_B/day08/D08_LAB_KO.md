# AXIA D08 — 온라인 4시간 통합 실습 및 제출 ZIP (교육생용)
교육일: **2026-11-18(수) 19:00~23:00**. 학습형태: 온라인/개별 Python 실습.

## 학습 목표
1. D04 사람 검출 → D05 깊이 중간값 → D06 STOP/SLOWDOWN/CLEAR/UNKNOWN → D07 recorded route replan 해설을 **새로운 ROS 제어 코드 없이** 연결한다.
2. 잘못된 인식·거리 정렬·유효시각을 발견하면 UNKNOWN을 CLEAR 또는 모터 재주행 허가로 처리하지 않는다.
3. 6개 합성 시나리오의 실제 `trace.csv`, `summary.json`, `pytest.txt`, `SHA256SUMS`를 **ZIP 1개**로 제출한다.

**사전 조건:** D04 `block_B/block_b_todo.py`, D06 `day06/safety_bubble_todo.py`, D07 `day07/route_todo.py` 기능을 지난 실습에서 구현했어야 한다. 미완료라면 동일 TODO를 먼저 완성한다. 강사 정답 제공 금지.

## 일정/터미널
| 시각 | 내용 | 강사의 확인 포인트 |
|---|---|---|
| 19:00~20:00 | D04→D07 데이터 흐름과 read-only 정책 복습 | 실제 사람과 합성 person_xy 좌표가 TF로 정렬됐다고 주장하지 않음 |
| 20:00~21:00 | `integration_todo.py` 하나만 구현, RED→GREEN | STOP 우선, 오래된 데이터 UNKNOWN |
| 21:00~22:00 | 여섯 사례 실행·CSV/JSON 분석 | CLEAR/REPLAN, SLOWDOWN, STOP, lost/stale 3건 |
| 22:00~23:00 | 검사결과 저장, SHA256 ZIP 제출 및 발표 | 누락·위조·심볼릭링크 ZIP 거부 |

**터미널:** 기존 가상환경/터미널 1개만 사용. 파일 생성 시 새 터미널 불필요. 완료 후 `deactivate`.

## 0. 준비/기대 출력 (저장소 루트)
```bash
python3 -m pip install 'pytest==8.3.5'
python3 -m pytest -q block_B/day08/tests/test_d08_public.py::test_d08_synthetic_fixture_contract \
  block_B/day08/tests/test_d08_submission_zip.py
```
**예상:** fixture/ZIP 테스트 **10 passed**. 이 단계는 student TODO GREEN이 아니다.

## 1. RED → 단일 TODO 구현
```bash
python3 -m pytest -q block_B/day08/tests/test_d08_public.py
```
**미구현이면 기대:** `test_d08_synthetic_fixture_contract` 1 PASS, `TODO_D08_INTEGRATE_CASE` 때문에 통합 테스트 2 FAIL. 실패 시 바로 다음 단계에서 `block_B/day08/integration_todo.py`의 `integrate_case()`를 채운다.

함수는 기존 `select_person`, `measure_person_range`, `bubble_policy`, `assess_replan`을 **재사용**하고 `case_id, person_detected, distance_m, range_status, route_status, advice, expected_ratio` 및 고정된 **모든 false 검증 플래그**를 반환한다. ROS/`/cmd_vel`/NavigateToPose 호출 불가.

## 2. GREEN → 결과 관찰
```bash
python3 -m pytest -q block_B/tests block_B/day06/tests block_B/day07/tests block_B/day08/tests \
  | tee /tmp/axia_d08_pytest.txt
python3 -m block_B.day08.run_lab --out results/d08_run1
cat results/d08_run1/trace.csv
```
**기대:** 기존 TODO까지 모두 완성했을 때 모든 pytest 통과, `D08_PYTHON_FIXTURE_REPLAY_PASS cases=6`. 기록된 합성 데이터의 `advice`는 다음 순서:
`REPLAN_REVIEW`, `SLOWDOWN_EXPECTED`, `STOP_EXPECTED`, `UNKNOWN_REVIEW` 3건.
선행 TODO가 미완성이라면 `D08_LAB_BLOCKED:NotImplementedError`이며 결과 출력이 생성되지 않아야 정상이다.

## 3. ZIP 1개 제출
```bash
cp /tmp/axia_d08_pytest.txt results/d08_run1/pytest.txt
python3 -m block_B.day08.submission_zip \
  --run-dir results/d08_run1 --out results/d08_submission.zip
python3 - <<'PY'
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

**ZIP에 포함된 코드:** `run_lab.py`가 실행에 성공할 때 D08 `integration_todo.py`의 **학생 본인 버전**을 결과 디렉터리에 복사합니다. 강사 정답, 이전 D04~D07 전체 패키지나 개인정보를 ZIP에 추가하지 마십시오.\n\n**안전·범위:** 여섯 사례는 새로 작성한 *합성* 4×4 깊이/검출/지도상 가상 사람 위치 자료다. 실제 YOLO 카메라→Nav2 map 좌표 TF 정렬이 아니며 ROS/Gazebo/실제 주행/충돌 0회 검증이 아니다. 출력은 설명/분석용이고 산업용 안전 명령이 아니다. SW_STOP과 인증 하드웨어 E-Stop은 다르다.

**오류 복구:** 결과 경로/ZIP 존재 시 덮어쓰지 않는다. `results/d08_run2`와 `results/d08_submission2.zip`처럼 새 이름을 사용한다. 누락 pytest, 실패 로그, 부정확한 보고, 심볼릭 링크, 큰 파일, 잘못된 해시는 BLOCKED되어야 한다. ZIP 제출 후 venv 종료.
