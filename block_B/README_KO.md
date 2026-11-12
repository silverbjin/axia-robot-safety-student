# AXIA Block B — D04 사람 검출 / D05 거리 측정 (학생용)

**상태:** 합성 CSV/Depth 교육 실습. 실제 ROS 2 / Gazebo / 로봇 주행 안전 인증이 아닙니다.

- 필요: Python 3.12+, pytest 8.3.5 (필수 경로에 torch, GPU, 카메라, ROS 없음)
- 입력: `fixtures/detections.csv`, `fixtures/depth_samples.json`, `fixtures/scenario_manifest.json`, `fixtures/SHA256SUMS`
- TODO: `block_b_todo.py`의 `select_person`, `measure_person_range` 두 함수만 작성
- 정상 센서 유효성 판단: bbox/image bounds, confidence, 단위 m, 0/NaN/Inf 필터, 최소 ROI 유효 비율 50%, 영상/Depth stamp 차이 0.05s 이하(교육용 예시값)

## 시작 명령 (저장소 최상위에서, 터미널 하나)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pytest==8.3.5
python -m pytest -q block_B/tests/test_fixture_io.py
python -m pytest -q block_B/tests/test_block_b_public.py
```

최초 TODO 상태에서 fixture 검증은 PASS, TODO 관련 공개 테스트는 예상 RED입니다. 이를 바꾸지 않고 README만 수정해서 PASS를 위장하면 안 됩니다.

TODO 완성 후에는:

```bash
python -m pytest -q block_B/tests
python -m block_B.run_lab --out results/d04_d05_run1
cat results/d04_d05_run1/person_range.csv
```

`--out` 경로는 **새 디렉터리**여야 합니다. 같은 경로 재실행은 `LAB_BLOCKED`로 차단됩니다. `results/`는 제출 자료로만 이용하며 Git에 올리지 않습니다.

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
- 수업 종료: 가상환경 `deactivate`; 새 터미널 불필요.

## D08 온라인 통합 실습 (2026-11-18, 19:00~23:00)

D04~D07의 학생 TODO를 먼저 완성했다면, [**D08 4시간 실습 시작 가이드**](day08/D08_LAB_KO.md)에서 **최초 clone → RED → GREEN → 6사례 분석 → SHA256 ZIP 제출** 순서로 진행합니다.

- **실무 진단 보충:** [실제 Gazebo·YOLO 분류 실패를 어떻게 진단할까?](day08/D08_FIELD_DIAGNOSTIC_CASE_KO.md) — 본 수업 첫 시간 15~20분 활동
- **학생 구현 파일:** `day08/integration_todo.py`의 `integrate_case()` 한 함수
- **검증 명령:** `python -m pytest -q block_B/day08/tests/test_d08_public.py` (미구현 상태는 의도적 RED)
- **제출 파일:** `results/d08_submission.zip` 하나. 결과 CSV·JSON·실제 pytest 로그·본인 소스·SHA256SUMS 총 5파일
- **검증 수준:** Python synthetic L0 교육 실습. ROS/Gazebo/실제 주행, AI 안전 인증 또는 하드웨어 E-Stop 결과가 아님

D08 자료는 `feature/d08-online-integration-todo-20261110` 브랜치에 게시됩니다. `main`으로 병합되기 전에는 **가이드의 명시된 브랜치로 clone**하세요. 강사 정답은 이 저장소에 존재하지 않습니다.
