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
