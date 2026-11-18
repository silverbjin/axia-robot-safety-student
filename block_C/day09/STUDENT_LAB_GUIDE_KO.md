# D09 학생 실습 가이드 — 장비 상태 학습 데이터 구성 (120분)

**학습 목표:** ① 전류·토크·가속도 등 시계열 데이터 특성 이해 ② 장비 상태 데이터 수집 및 학습 데이터 구성 실습. 필수 데이터는 `SYNTHETIC_COURSE_FIXTURE`이며 **실제 Waffle 센서 측정값이 아닙니다**. `cmd_vel`이나 Goal을 송신하지 않습니다. SW 정지는 인증된 E-Stop이 아닙니다.

## A. 준비와 원본 확인 — 0~20분

학생 저장소 루트에서 실행하세요. Python 3.12 및 `pytest`가 필요합니다. 실습 코드는 `block_C/day09/student_eda_todo.py`에 있습니다.

```bash
cd ~/axia-robot-safety-student   # 실제 위치가 다르면 해당 경로로 수정
python3 --version
bash block_C/scripts/block_c_once.sh --doctor
python3 block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures
bash block_C/scripts/block_c_once.sh --unit
```

`--unit`은 공개 fixture와 scaffold 검증입니다. 아직 학생 TODO 정답을 검증하는 명령이 **아닙니다**. 기대 증거는 `C01_FIXTURE_CONTRACT_PASS`, `BLOCK_C_STUDENT_SCAFFOLD_PUBLIC_L0_PASS`입니다.

**입력 스키마 확인:** `block_C/fixtures/schema.json`과 `scenario_manifest.json`을 열어 `trace_id`, `sample_idx`, `timestamp_ns`, `current_a`, `torque_nm`, `accel_mps2`, `truth_label`을 찾습니다. 샘플링 주기는 **10 Hz**, 시간 간격은 **100,000,000 ns**입니다. `truth_label`은 평가·정답 필드이며 **6개 모델 특징에 포함하면 안 됩니다**.

## B. 실제 데이터 행/Trace 집계 — 20~40분

다음은 정답 알고리즘이 아니라 파일 개수를 확인하는 독립적인 관찰 코드입니다. 합성 수집 데이터의 **행 수**와 시간적으로 연결된 **Trace 수**가 다른 이유를 이해하세요.

```bash
python3 - <<'PY'
import csv
from pathlib import Path
root = Path("block_C/fixtures")
for name in ("normal_train.csv", "normal_valid.csv", "test_mixed.csv"):
    with (root / name).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    print(name, "rows=", len(rows), "traces=", len({r["trace_id"] for r in rows}))
PY
```

고정 fixture에서의 예상 출력:

```text
normal_train.csv rows= 2400 traces= 24
normal_valid.csv rows= 800 traces= 8
test_mixed.csv rows= 1399 traces= 14
```

합계는 **46 Trace / 4,599행**입니다. `train/valid/test` 간 같은 `trace_id`가 중복되면 학습 누수로 판정합니다. 이미 나뉜 파일을 임의로 다시 섞지 마세요.

## C. 시계열 패턴과 데이터 품질 구분 — 40~55분

`scenario_manifest.json`의 `anomaly_cases`와 `quality_cases`를 확인하세요. 다음 구분은 **장비 상태 이상 후보**와 **잘못 기록된 값**의 차이를 보여줍니다.

| 사례 | 뜻 | 정답 처리 방향 |
|---|---|---|
| `CURRENT_SPIKE` | 전류가 짧은 구간 크게 증가 | VALID인 경우 통계 특징 계산 |
| `TORQUE_DRIFT` | 토크가 시간에 따라 증가 | VALID인 경우 통계 특징 계산 |
| `ACCEL_VIBRATION` | 가속도가 빠르게 교대 진동 | VALID인 경우 표준편차도 관찰 |
| `MISSING_VALUE` | 숫자 공백 | INSUFFICIENT_DATA |
| `SAMPLE_GAP` | sample_idx 누락 | INSUFFICIENT_DATA |
| `STAMP_REGRESSION` | 시간 역행 | INSUFFICIENT_DATA |
| `TIMESTAMP_DRIFT` | 100ms 간격 불일치 | INSUFFICIENT_DATA |

수집 오류 4 Trace는 숫자 0으로 채워 NORMAL 처리하지 않습니다. CSV의 `timestamp_ns`는 Trace 로컬 경과시간이므로 ROS 시간과 혼동하지 마세요.

## D. D09 학생 TODO — 55~95분

대상: `block_C/day09/student_eda_todo.py`, 함수 `make_features(fixture_dir, output_dir) -> dict`.

**작성해야 할 처리 순서** (완성 정답 코드는 제공하지 않습니다):

1. fixture의 SHA256·schema·split 검사를 통과했는지 확인합니다.
2. 입력 CSV를 `train`, `valid`, `test` 순으로 읽고 같은 `trace_id`끼리 묶습니다.
3. 각 Trace의 `sample_idx` 및 `timestamp_ns`를 검사합니다. 깨진 Test Trace는 **단일 상태행**으로 기록하고 숫자 특징 6개를 비웁니다. Train/Valid 품질 불량은 정상 데이터로 받아들이지 않습니다.
4. 정상 Trace는 **10개의 연속 샘플을 비중복 윈도우**로 묶습니다. 서로 다른 Trace 또는 split 경계를 넘는 윈도우는 허용하지 않습니다.
5. 각 윈도우에서 전류·토크·가속도의 **평균과 모집단 표준편차**(`std`, 표본 표준편차와 다름)를 계산해 총 6개 숫자 특징을 만듭니다. `truth_label`은 특징 계산 입력이 아닙니다.
6. `features_train.csv`, `features_valid.csv`, `features_test.csv`, `features.csv`를 결과 폴더에 작성합니다. 가능하다면 `eda_report.md`와 시간축 그래프를 추가합니다.

참고 계산: 모집단 표준편차는 `sqrt(sum((x-mean)**2)/N)`입니다. 10개의 샘플 첫 시각과 마지막 시각 차이는 **0.9초**입니다.

## E. RED → GREEN → 검수 — 95~115분

아직 구현하지 않은 상태에서 다음은 **EXPECTED_RED**로 1건 실패해야 합니다.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  block_C/tests/test_student_task_expected_red.py \
  -k test_d09_should_build_trace_safe_features
```

기대되는 초기 오류: `NotImplementedError: D09 TODO not implemented`, `1 failed`. TODO를 작성한 뒤 같은 시험을 다시 실행해 GREEN을 확인합니다. 그러나 이 공개 시험은 주로 함수의 반환 계약만 확인하므로, **실제 CSV 결과 검수도 필수**입니다.

코드 작성 후 결과 폴더에 `features.csv`가 생겼다면 다음과 같이 구성과 상태를 검증하세요. 실제 폴더를 지정하세요.

```bash
export D09_OUT="$HOME/axia_d09_lab/my_features"
python3 - <<'PY'
import csv, os
from pathlib import Path
from collections import Counter
p = Path(os.environ["D09_OUT"]) / "features.csv"
assert p.is_file(), f"결과 파일이 없습니다: {p}"
with p.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
print("rows", len(rows))
print("split", dict(Counter(r["split"] for r in rows)))
print("status", dict(Counter(r["status"] for r in rows)))
assert len(rows) == 424
assert Counter(r["status"] for r in rows) == {"VALID": 420, "INSUFFICIENT_DATA": 4}
PY
```

기대 결과 (완성 구현의 계약):

```text
rows 424
split {'train': 240, 'valid': 80, 'test': 104}
status {'VALID': 420, 'INSUFFICIENT_DATA': 4}
```

이 검수는 일부 조건만 확인합니다. 추가로 `INSUFFICIENT_DATA`의 특징 6개가 모두 빈칸인지, `trace_id`가 split 간 중복되지 않는지, `truth_label`이 특징 입력에 섞이지 않았는지도 확인합니다.

## F. 제출과 회고 — 115~120분

제출할 항목: 변경한 `student_eda_todo.py`, `features.csv`, split별 CSV, `eda_report.md`/그래프(작성한 경우), 테스트 실제 출력·실패 시 최초 Trace ID, 소스 Git SHA. 실습 결과는 강사 정답과 독립된 학생 작업물입니다.

**구두 질문:** 왜 Test의 104행 중 4행은 모델에 넣지 않을까요? 왜 같은 Trace를 Train/Test에 나누면 위험할까요? 전류·토크·가속도의 평균과 표준편차가 각각 어떤 다른 정보를 제공할까요?

실측 ROS 2 관찰은 [학생 데모 가이드](STUDENT_DEMO_GUIDE_KO.md)의 **선택** 단계입니다. 실제 토픽이 없으면 합성 fixture로 실습을 완주합니다. 시연의 SW 정지 또는 AI 경고를 인증된 E-Stop으로 부르지 마세요.
