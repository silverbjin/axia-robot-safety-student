# AXIA Block C D10 — 초심자용 120분 실습 가이드 (상세 해설판)

> **오늘의 목표 ①** Isolation Forest 기반 이상신호 탐지 구조 이해  
> **오늘의 목표 ②** 정상 패턴 기준 이상탐지 및 조기 경고 검증 실습  
> 시간: 20:00–22:00(120분). 이론 19:00–20:00에서 소개한 개념을 직접 확인합니다.

**자료 출처:** `SYNTHETIC_COURSE_FIXTURE`(seed 2409, 합성 10Hz).

**핵심 한 문장:** 정상 Train으로 모델을 학습하고, 정상 Valid로 경고 기준을 정한 뒤, 마지막에 Test로 결과를 평가합니다. **AI WARNING은 교육용 비인증 경고**이며 실제 ROS 2 안전정지, SW Stop 또는 인증된 E-Stop이 아닙니다. 실제 TurtleBot3 Waffle 센서·모터 데이터도 사용하지 않습니다.

이 문서는 Python 초심자를 전제로 합니다. 명령어의 의미, 파일 위치, 예상 출력, 오류 처리 및 제출 내용을 한 단계씩 안내합니다. `student_if_todo.py`의 **정답 구현은 포함하지 않습니다.** 코드는 직접 작성하는 과제이며 시작 시 `NotImplementedError`는 정상적인 **EXPECTED_RED**입니다.

## 0. 실습 지도 — 지금 내가 어디에 있나요?

```text
[공개 합성 원본 CSV 4,599행 / 46 Trace]
              │  C01 원본 파일/시간·품질 계약 확인
              ▼
[D09: Trace 전체 검사 → 10샘플씩 Window → 평균·표준편차 6개]
              │
              ├─ Train: 240 VALID, 정상  → 스케일러·IF 학습(fit)
              ├─ Valid:  80 VALID, 정상  → 경고 임계값 결정(95% 분위수)
              └─ Test:  100 VALID + 4 INSUFFICIENT_DATA → 마지막 평가
                                                    │
                          Test VALID 100개에서 NORMAL/WARNING
                          품질 4개는 점수 없이 INSUFFICIENT_DATA
                                                    │
                          TP/FP/FN/TN 및 최초 WARNING 시점 분석
```

**단어부터 알아봅시다.** `Sample`은 한 시점의 측정값 한 줄, `Trace`는 같은 `trace_id`의 샘플 묶음, `Window`는 하나의 Trace에서 연속된 샘플 10개, `Feature`는 Window를 요약한 숫자입니다. 원본은 합성 10Hz이므로 샘플 간격은 0.1초입니다. 정상 형식의 Trace는 100샘플을 10개 Window로 바꿉니다. 품질 통과 42 Trace × 10 = **420개 VALID Window**, 품질 실패 4 Trace × 상태행 1 = **4개 INSUFFICIENT_DATA**, 합계 **424개 특징·상태행**입니다. 전체 4,599행은 46×100=4,600에서 `SAMPLE_GAP` 1행이 의도적으로 누락된 결과입니다.

| 구분 | 의미 | **이 실습에서의 역할** |
|---|---|---|
| `status=VALID` | 입력 형식·시간·품질 검사 통과 | 모델 점수 계산 가능. **정상 라벨을 뜻하지 않음** |
| `truth_label=0/1` | 합성 데이터의 정상/이상 정답표 | Test에서 채점에만 사용. 모델 입력 6특징에 넣지 않음 |
| `INSUFFICIENT_DATA` | 측정 결측·누락·시간 오류로 점수 계산 불가 | 정상(`NORMAL`)이나 경고(`WARNING`)로 억지 분류 금지 |
| `fit` | 데이터에서 스케일러·모델의 내부 상태를 학습 | 정상 Train만 사용 |
| `transform` | 이미 학습한 스케일러를 다른 데이터에 적용 | Valid·Test에서 다시 `fit`하지 않음 |
| `risk_score` | `-decision_function`으로 방향을 뒤집은 점수 | 커질수록 더 이상 후보 |
| `threshold` | 정상 Valid 점수의 95% 분위수 | Test 전에 고정되는 WARNING 경계 |

## 1. 20:00–20:10 (10분) — 안전하게 터미널·Python 준비

**실습 PC:** Ubuntu 24.04/WSL2, Python 3.12. `jinho@...:~$`에서 시작해도 됩니다. **사용자 터미널 전체에 `set -e`를 복사하지 마세요.** 먼저 다음 한 블록으로 학생 저장소를 준비합니다. 기존 작업 파일을 지우거나 `git reset --hard` 하지 않습니다.

```bash
(
  set -Eeuo pipefail
  ROOT="$HOME/axia_d10_course/axia-robot-safety-student"
  mkdir -p "$(dirname "$ROOT")"
  if [[ ! -d "$ROOT/.git" ]]; then
    git clone https://github.com/silverbjin/axia-robot-safety-student.git "$ROOT"
  fi
  cd "$ROOT"
  if [[ "$(git branch --show-current)" == main && -z "$(git status --porcelain)" ]]; then
    git pull --ff-only origin main
  else
    echo 'D10_STUDENT_SOURCE_UNTOUCHED: 기존 브랜치/변경사항 유지'
  fi
  git rev-parse --short HEAD
  python3 --version
) || echo 'D10_SOURCE_HOLD: 위의 첫 오류를 확인해 강사에게 알려주세요.'
```

- `mkdir -p`: 폴더가 없다면 만듭니다.
- `git clone`: 공개 학생 저장소가 없을 때에만 내려받습니다.
- `cd`: 명령을 실행하는 **현재 폴더**를 옮깁니다. 파일은 이동하지 않습니다.
- `git rev-parse --short HEAD`: 지금 사용 중인 코드 버전을 기록합니다.
- `|| echo`: 오류가 생겨도 **바깥 터미널은 계속 열려 있습니다**.

**이후 모든 단계의 시작 위치는 학생 저장소 루트**입니다. 새 터미널을 열었다면 아래 세 줄을 다시 입력합니다.

```bash
cd "$HOME/axia_d10_course/axia-robot-safety-student"
export AXIA_D10_LAB="$HOME/axia_d10_student_lab"
mkdir -p "$AXIA_D10_LAB/c02" "$AXIA_D10_LAB/c03"
```

**Python 가상환경(한 번만 설치):** 다른 수업 패키지와 충돌하지 않도록 저장소 바깥에 만듭니다. `python3 --version`이 3.12.x인지 먼저 확인합니다. 다른 버전이라면 `python3.12 --version`으로 설치 여부를 확인하고, 3.12가 없으면 강사에게 환경을 요청하십시오. 시스템 Python을 임의로 교체하지 않습니다.

```bash
# python3 -m venv 사용 전 python3가 반드시 3.12인지 확인합니다.
python3 --version
(
  set -Eeuo pipefail
  VENV="$HOME/axia_d10_course/.venv"
  python3 -m venv "$VENV"
  "$VENV/bin/python" -m pip install --disable-pip-version-check --no-input \
    'numpy>=1.26,<3' 'scikit-learn==1.8.0' 'pytest==8.3.5'
  "$VENV/bin/python" -c 'import sys,numpy,sklearn; assert sys.version_info[:2]==(3,12); print("PYTHON",sys.version.split()[0],"NUMPY",numpy.__version__,"SKLEARN",sklearn.__version__)'
  echo D10_STUDENT_VENV_READY
) || echo 'D10_STUDENT_VENV_HOLD: 설치 오류를 해결하기 전에는 다음 단계로 진행하지 마세요.'
if [[ -x "$HOME/axia_d10_course/.venv/bin/python" ]] &&
    "$HOME/axia_d10_course/.venv/bin/python" -c 'import numpy,sklearn,pytest' 2>/dev/null; then
  source "$HOME/axia_d10_course/.venv/bin/activate"
  bash block_C/scripts/block_c_once.sh --doctor
else
  echo 'D10_STUDENT_ENV_HOLD: 가상환경이 준비되지 않았습니다. 다음 단계로 진행하지 마세요.'
fi
```

예상: `PYTHON 3.12.x ... SKLEARN 1.8.0` 및 `BLOCK_C_STUDENT_DOCTOR python=3.12.x`. 가상환경 재사용은 `source "$HOME/axia_d10_course/.venv/bin/activate"` 한 줄이면 됩니다. **D10은 CPU 오프라인 Python 수업**이므로 Gazebo, ROS 2, GPU, PyTorch, `cmd_vel`이 필수 조건이 아닙니다.

> **점검 질문:** `(1)` 지금 `pwd`는 어디입니까? `(2)` `python --version`은 무엇입니까? `(3)` `which python`이 `.venv/bin/python`을 가리킵니까?

## 2. 20:10–20:20 (10분) — 원본 CSV 무결성과 Trace를 눈으로 보기

```bash
python block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures
head -n 3 block_C/fixtures/normal_train.csv
```

**예상 메시지(한 줄 JSON의 핵심 필드):**

```text
C01_FIXTURE_CONTRACT_PASS ... "rows": 4599, "traces": 46, "quality_traces": 4, "status": "PASS", "ros_actual": false ...
```

- `--check`: 이미 있는 파일의 내용·SHA256·스키마·Trace를 검사합니다. **원본을 다시 만들거나 변경하지 않습니다.**
- `head -n 3`: CSV 제목행과 데이터 2행을 보여줍니다.
- 숫자 `2.036000`은 합성 전류값 A이며, 실제 로봇의 전류를 뜻하지 않습니다.

실제로 데이터가 몇 줄이고 Trace가 몇 개 있는지 확인합니다. 아래 코드는 **읽고 세기만 하는 예제**로 D10 정답이 아닙니다.

```bash
python - <<'PY'
import csv
from pathlib import Path
base = Path('block_C/fixtures')
for name in ('normal_train.csv','normal_valid.csv','test_mixed.csv'):
    with (base / name).open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    print(name, 'rows=', len(rows), 'traces=', len({r['trace_id'] for r in rows}))
PY
```

```text
normal_train.csv rows= 2400 traces= 24
normal_valid.csv rows= 800 traces= 8
test_mixed.csv rows= 1399 traces= 14
```

**학생에게 질문:** 46×100=4,600인데 왜 4,599일까요? → `TST_Q_01`에서 인덱스 55 샘플행 1개를 일부러 누락했기 때문입니다. 결측(`TST_Q_00`), 샘플 누락(`TST_Q_01`), 시간 역행(`TST_Q_02`), 시간 드리프트(`TST_Q_03`)는 **정상 숫자 0으로 채우면 안 됩니다.**

## 3. 20:20–20:30 (10분) — D09에서 만든 6개 특징 CSV 준비

**여기가 초심자의 가장 중요한 분기점입니다.** **D09 학생 과제가 끝나지 않았다면** 강사가 제공한 특징 CSV가 필요합니다. 공개 학생 저장소에는 원본 CSV와 **미구현 D09 TODO**가 들어 있습니다. 따라서 원본 검사에 성공했어도 D10에 필요한 `features_train.csv`, `features_valid.csv`, `features_test.csv`는 자동으로 생기지 않습니다.

- **경로 A(초심자·수업 권장):** 강사가 미리 제공한 **데이터 파일 3개만** `$AXIA_D10_LAB/c02`에 넣습니다. 강사 정답 Python 코드는 제공하거나 복사하지 않습니다. 파일이 없으면 다음 단계로 진행하지 말고 강사에게 특징 데이터 준비를 요청합니다.
- **경로 B(D09 과제를 이미 끝낸 학생):** 자신이 완성한 `student_eda_todo.py`를 실행합니다.

```bash
# 경로 B에서만 실행: 학생이 D09 TODO를 직접 완성한 경우
PYTHONPATH=block_C/day09 python - <<'PY'
import os
from pathlib import Path
from student_eda_todo import make_features
out = Path(os.environ['AXIA_D10_LAB']) / 'c02'
print('D09_RESULT_TYPE=', type(make_features(Path('block_C/fixtures'), out)).__name__)
PY
```

`NotImplementedError: D09 TODO not implemented`가 뜨면 **D09 과제가 미완성이라는 뜻**입니다. Python 설치 문제나 D10 모델 오류가 아닙니다. 초심자는 경로 A로 이동합니다.

입력 파일이 준비됐다면 다음 코드로 행 수와 품질 상태를 검수합니다.

```bash
python - <<'PY'
import csv,os
from pathlib import Path
root = Path(os.environ['AXIA_D10_LAB']) / 'c02'
for split, total, good, bad in [('train',240,240,0),('valid',80,80,0),('test',104,100,4)]:
    path = root / f'features_{split}.csv'
    if not path.is_file():
        raise SystemExit(f'D10_INPUT_MISSING: {path}\n강사가 제공한 특징 CSV 또는 완료된 D09 결과가 필요합니다.')
    with path.open(newline='',encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    valid = sum(r['status']=='VALID' for r in rows)
    invalid = sum(r['status']=='INSUFFICIENT_DATA' for r in rows)
    assert (len(rows),valid,invalid)==(total,good,bad), (split,len(rows),valid,invalid)
    print(split, 'total=',len(rows),'VALID=',valid,'INSUFFICIENT_DATA=',invalid)
print('D10_INPUT_COUNTS_PASS')
PY
```

```text
train total= 240 VALID= 240 INSUFFICIENT_DATA= 0
valid total= 80 VALID= 80 INSUFFICIENT_DATA= 0
test total= 104 VALID= 100 INSUFFICIENT_DATA= 4
D10_INPUT_COUNTS_PASS
```

**숫자가 의미하는 것:** Train 24 Trace × 10 Window = 240, Valid 8×10=80, Test 유효 Trace 10×10=100에 품질 오류 4개 상태행이 붙어 104입니다. **`status=VALID`는 정상 라벨이라는 뜻이 아닙니다.** Test VALID 100개 안에는 정상 라벨 82개와 이상 라벨 18개가 있습니다.

참고로 원본의 한 윈도우(10샘플)를 요약할 때 쓰는 숫자는 `전류 평균·표준편차`, `토크 평균·표준편차`, `가속도 평균·표준편차`의 6개입니다. Python의 `statistics.pstdev`는 **모집단 표준편차**를 계산합니다. 첫 정상 윈도우 `TRN_00/W0`의 예시는 `current_a_mean=2.064500`, `current_a_std=0.045955`입니다. D09 생성 코드 해설과 구분해 이해하세요.

## 4. 20:30–20:40 (10분) — RED: 왜 테스트가 실패해야 하나요?

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q \
  block_C/tests/test_student_task_expected_red.py -k d10
```

**기본 배포본의 예상 결과:** `NotImplementedError: D10 TODO not implemented` 및 **1 failed**. 학생에게 이 실패는 잘못된 설정이 아니라 **아직 구현할 과제가 남았다는 출발 표시(RED)**입니다. 공개 테스트는 함수의 반환형만 기본 확인하며, 실제 학습의 데이터 누수·정답·안전 경계 전체를 보증하지 않습니다. `-k d10`은 D09·D11·D12 과제는 빼고 D10만 선택합니다. `pytest` 종료 코드가 1이더라도 터미널을 닫지 말고 에러 메시지를 확인하세요.

이제 `block_C/day10/student_if_todo.py`를 편집기로 열어 봅니다. 함수 이름은 반드시 **`fit_evaluate_if`**를 유지하고, 매개변수는 `(fixture_dir, output_dir)` 그대로 둡니다. 첫 번째 인수 이름이 `fixture_dir`이지만 D10에서는 **6특징 CSV들이 들어 있는 폴더**로 전달합니다. 학생 TODO 전체를 복사해 정답으로 만드는 것은 학습 목표에 맞지 않습니다.

**TDD 원칙:** RED(미구현 확인) → GREEN(본인 코드로 기능 통과) → REFACTOR(중복 정리) → REVIEW(누수·품질·안전 경계 점검) → COMMIT(개인 작업 브랜치에만). 공식 교재 `main`이나 공개 강사 저장소에 정답을 게시하지 않습니다.

## 5. 20:40–20:55 (15분) — 활동 A: 정상 Train으로만 학습

**한 문장:** `fit`은 '학습에 사용할 정보를 보고 내부 기준을 만드는 일'입니다. Test에서 학습하면 시험 답안을 미리 본 것과 같습니다.

학생 코드에서 구현할 작업(완성 코드 대신 체크리스트 제공):

1. `features_train.csv`를 `csv.DictReader`로 읽습니다.
2. `split == 'train'`, `status == 'VALID'`, `truth_label == '0'`인지 모두 확인합니다. 데이터행은 정확히 **240개**입니다.
3. 아래 여섯 특징만 **정해진 순서**로 `float` 변환합니다. `trace_id`, `window_id`, `timestamp_ns`, `truth_label`은 모델 입력에서 제외합니다.
4. `StandardScaler`는 **Train으로만 `fit`**합니다. 동일한 스케일러를 뒤에서 Valid·Test에 `transform`합니다.
5. `IsolationForest(n_estimators=100, random_state=2409, contamination='auto', n_jobs=1)`를 **Train만으로 학습**합니다.

```python
# 학생이 직접 구현할 때 사용하는 이름·설정 힌트 (전체 정답 아님)
FEATURES = (
    'current_a_mean', 'current_a_std',
    'torque_nm_mean', 'torque_nm_std',
    'accel_mps2_mean', 'accel_mps2_std',
)
# TODO A: train 행 검증 → X_train (240행×6열)
# TODO B: scaler.fit(X_train) → scaler.transform(X_train)
# TODO C: IsolationForest(...).fit(변환된 정상 Train)
```

**설명:** `scaler`는 단위와 크기가 다른 숫자를 Train의 평균·분산 기준으로 변환합니다. 트리 모델에서 표준화가 언제나 성능을 높인다고 단정할 수는 없지만, 이 수업에서는 기준 코드와의 재현성을 위해 동일하게 사용합니다. `random_state=2409`는 무작위 분할의 재현성을 높입니다.

**셀프 체크:** 모델 입력 배열의 모양이 `(240, 6)`입니까? `truth_label`이 그 6열에 끼어 있지는 않습니까? `scaler.fit()`이 Valid·Test에도 실행되지 않았습니까?

## 6. 20:55–21:10 (15분) — 활동 B: 정상 Valid 80개로 경고선 결정

Isolation Forest의 `decision_function`은 **값이 작을수록 비정상적인 방향**입니다. 수업에서는 학생이 직관적으로 이해할 수 있도록 부호를 한 번 뒤집어 다음처럼 정의합니다.

```text
risk_score = -decision_function(Train에서 학습한 scaler로 변환한 특징)
```

따라서 **`risk_score`가 높을수록 이상 후보**입니다. 모델이 내부적으로 제공하는 `0` 경고선을 그대로 쓰지 않고, **정상 Valid 80개 점수의 95% 분위수**를 교재 임계값으로 선택합니다.

**95% 분위수의 의미:** 정상 데이터의 위험점수를 작은 순서로 나열했을 때 상위 약 5%를 가르는 위치입니다. 정확히 '이상 발견률 95%'라는 뜻이 아닙니다. 이 실습의 기준 결과는 정상 Valid에서 **4/80개가 경고선을 초과**합니다.

```python
# TODO D: scaler.transform(X_valid)로만 변환 (다시 fit 금지)
# TODO E: if_model.decision_function(...)에 음수 부호 1회 적용
# TODO F: 정상 Valid 위험점수의 0.95 분위수 보간으로 threshold 결정
# TODO G: 이제 threshold를 고정하고 나서 Test에 접근
```

예전 강사 참조 산출물(직접 학생 실행한 결과는 아님): `threshold=0.10199750`. Test 결과가 기대보다 나쁘더라도 Test를 보고 경고선을 고쳐서는 안 됩니다.

**셀프 체크:** 점수 방향이 `higher_is_more_anomalous`입니까? `threshold_source`가 `normal_valid_only`입니까? Test 파일을 먼저 읽거나 점수 분포를 보고 분위수를 바꾸지는 않았습니까?

## 7. 21:10–21:25 (15분) — 활동 C: Test와 품질 오류를 분리

처음으로 Test 파일을 읽습니다. Test **104개 전체를 모델에 입력하지 않습니다.** `status == 'VALID'`인 **100개만** 모델 점수를 계산하고, 품질 오류 **4개**는 별도 출력행으로 보존합니다.

- VALID 100개: 이미 고정된 모델·스케일러·임계값으로 `NORMAL` 또는 `WARNING` 결정
- `risk_score > threshold`인 경우만 `WARNING`, 같으면 `NORMAL`
- INVALID 4개: `prediction = INSUFFICIENT_DATA`, `risk_score`와 `threshold`는 **빈 문자열**
- `truth_label`은 모델 학습이나 경고선 선택이 아닌 **Test 채점에만 사용**

```text
입력: features_test.csv (104행)
   ├─ status=VALID: 100행 → transform → 위험점수 → NORMAL/WARNING
   └─ 나머지:       4행 → 점수 계산 생략 → INSUFFICIENT_DATA
```

**학생이 만들어야 하는 파일:** `if_scores_test.csv` (104개 데이터행) 및 `if_metrics.json`. CSV에는 `trace_id`, `window_id`, `timestamp_ns`, `status`, `quality_reason`, `truth_label`, `risk_score`, `threshold`, `prediction` 열을 둡니다. JSON에는 최소 `train_count`, `valid_count`, `test_valid_count`, `test_invalid_count`, `threshold`, `threshold_source`, `risk_score_direction`, `confusion`, `precision`, `recall`, `fpr`, `fit_on_test`, `test_threshold_tuned`를 기록합니다.

**셀프 체크:** 네 품질행의 점수가 모두 공란입니까? `fit_on_test`와 `test_threshold_tuned`가 모두 `false`입니까? `INSUFFICIENT_DATA`는 정상 0으로 취급되지 않았습니까?

## 8. 21:25–21:40 (15분) — 활동 D: TP·FP·FN·TN을 계산하고 검증

모델은 AI가 예측한 경고 여부를 출력합니다. `truth_label`은 합성 데이터에 이미 있는 정답표입니다. 둘을 비교하면 아래 네 가지 결과가 나옵니다.

| 실제 정답(Truth) | 모델 예측(Prediction) | 분류 | 뜻 |
|---|---|---|---|
| 이상 1 | WARNING | **TP** | 이상을 맞게 경고 |
| 정상 0 | WARNING | **FP** | 정상인데 잘못 경고 |
| 이상 1 | NORMAL | **FN** | 이상인데 놓침 |
| 정상 0 | NORMAL | **TN** | 정상임을 맞게 판단 |

**정밀도(Precision)** = TP / (TP + FP), **재현율(Recall)** = TP / (TP + FN). FPR은 FP / (FP + TN)입니다. 품질 오류 4행은 이진 평가 분모에 넣지 않습니다.

**교재 참조 결과(정답 코드 공개가 아니라 비교할 통계값):** TP=1, FP=2, FN=17, TN=80, Recall=1/18≈**5.56%**, Precision=1/3≈**33.33%**, FPR=2/82≈**2.44%**. 이것은 **모델의 높은 탐지 성능을 의미하지 않습니다.** 낮은 재현율을 숨기거나 Test에 맞춰 재튜닝하지 않습니다.

이제 직접 만든 코드를 실행합니다. `AXIA_D10_LAB`은 앞 단계에서 설정한 환경변수입니다.

```bash
PYTHONPATH=block_C/day10 python - <<'PY'
import os
from pathlib import Path
from student_if_todo import fit_evaluate_if
root = Path(os.environ['AXIA_D10_LAB'])
result = fit_evaluate_if(root/'c02', root/'c03')
print('D10_STUDENT_RETURN_TYPE=', type(result).__name__)
print('D10_STUDENT_OUTPUT_DIR=', root/'c03')
PY
```

미완성 상태라면 `NotImplementedError`가 발생합니다. 이는 **자기 코드가 아직 완성되지 않았다는 상태**입니다. 코드가 완료돼 JSON/CSV를 썼다면 아래 확인을 진행하세요.

```bash
python - <<'PY'
import os,csv,json
from pathlib import Path
out = Path(os.environ['AXIA_D10_LAB'])/'c03'
m = json.loads((out/'if_metrics.json').read_text(encoding='utf-8'))
with (out/'if_scores_test.csv').open(newline='',encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
assert len(rows)==104, len(rows)
assert sum(r['prediction']=='INSUFFICIENT_DATA' and not r['risk_score'] for r in rows)==4
assert sum(m['confusion'].values())==100
assert m['threshold_source']=='normal_valid_only'
assert m['fit_on_test'] is False and m['test_threshold_tuned'] is False
print('D10_STUDENT_DATA_CHECK_PASS',m['confusion'],'threshold=',m['threshold'])
PY
```

**기대:** `D10_STUDENT_DATA_CHECK_PASS ...`. 이 점검은 **출력 기본 계약 일부**만 검사합니다. 실제 학습 누수·계산식·모델 정답을 모두 검증하는 테스트는 아니므로, 예상 숫자가 같다는 이유만으로 안전 성능을 주장하지 마세요.

## 9. 21:40–21:52 (12분) — 최초 경고가 몇 초에 나왔을까요?

합성 데이터는 10Hz이고 이상 주입이 sample 40에서 시작됩니다. 따라서 **주입 시작 시각 4.0초**, W4는 4.0~4.9초, W5는 5.0~5.9초, W6은 6.0~6.9초입니다. Window의 `timestamp_ns`는 **끝 샘플 시각**을 기록합니다.

```text
합성 시간 (초)      4.0      4.9      5.0      5.9      6.0      6.9
                    ├── W4 ───┤        ├── W5 ───┤        ├── W6 ───┤
기준 TST_A_00      주입 시작         W4 NORMAL     W5 WARNING
                                ↑            ↑
                        모델 첫 경고 아님    참양성 첫 경고(5.9초)
```

기존 참조 결과에서 `TST_A_00/W5`가 처음 참양성 WARNING입니다. **5.9−4.0=1.9초**는 *합성 데이터 기록 시각* 기준 지연이지, 실제 로봇의 감지→Stop 또는 인증 E-Stop 지연이 아닙니다. 다른 이상 Trace 5개는 주입 구간을 놓쳤습니다(`NOT_DETECTED`). `TST_A_03/W9`, `TST_A_04/W8`은 이상 Trace에 속해도 그 Window 자체의 정답은 정상 0이므로 FP입니다.

```bash
python - <<'PY'
import csv,json,os
from pathlib import Path
out = Path(os.environ['AXIA_D10_LAB'])/'c03'
with (out/'if_scores_test.csv').open(newline='',encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
cases=json.loads(Path('block_C/fixtures/scenario_manifest.json').read_text(encoding='utf-8'))['anomaly_cases']
for trace_id in sorted(cases):
    hits=[r for r in rows if r['trace_id']==trace_id and r['status']=='VALID'
          and r['truth_label']=='1' and r['prediction']=='WARNING']
    if not hits:
        print(trace_id,'NOT_DETECTED')
    else:
        r=min(hits,key=lambda x:int(x['timestamp_ns']))
        delay=(int(r['timestamp_ns'])-4_000_000_000)/1_000_000_000
        print(trace_id,'W'+r['window_id'],'synthetic_delay_s=',round(delay,1))
PY
```

기존 강사 참고 결과는 `TST_A_00 W5 synthetic_delay_s= 1.9` (`synthetic_delay_s=1.9`)와 나머지 5 Trace의 `NOT_DETECTED`입니다. 학생 구현 결과가 다르면 **처음 차이 난 입력·특징·점수부터** 확인해야 하며 Test를 보고 경고선을 바꾸면 안 됩니다.

## 10. 21:52–22:00 (8분) — 제출·회고·정리

**제출 체크리스트** (본인 실습 브랜치·파일만 제출):

- [ ] `student_if_todo.py`: 본인이 작성한 구현. 강사 정답/비공개 테스트 복사 없음
- [ ] `if_metrics.json`, `if_scores_test.csv`: Test 100 VALID + 품질 4행 반영
- [ ] `architecture_explanation.md`: Train/Valid/Test 차이와 `VALID` ≠ 정상 이유
- [ ] `early_warning_report.md`: 첫 경고 Trace/Window/합성 지연, `NOT_DETECTED`, FP 사례
- [ ] `command_evidence.log`: Python·sklearn 버전, Git SHA, 명령, 최초 오류와 해결 기록

**짧은 회고 질문:** `(1)` 모델을 학습시킨 데이터는 무엇입니까? `(2)` 경고 임계값은 어느 데이터에서 계산했습니까? `(3)` 이상이 18개인데 FN이 17개라는 결과는 무엇을 뜻합니까? `(4)` 왜 AI WARNING이 SW Stop 또는 인증된 E-Stop이 아니라고 설명해야 합니까?

```bash
# 학생 개인 작업 브랜치에서만 사용: main으로 직접 푸시하지 않습니다.
git status --short
git rev-parse --short HEAD
```

## 11. 처음 겪는 오류 — 첫 번째 메시지부터 해결하기

| 처음 나타나는 오류/현상 | 실제 원인 후보 | 가장 작은 다음 행동 |
|---|---|---|
| `test -f day10/...`에서 창 종료 | 현재 폴더가 `~`, 상대경로 + 셸 `set -e` | 1단계 위치 이동 후 명령. 전체 터미널에 `set -e` 금지 |
| `ModuleNotFoundError: No module named 'sklearn'` | 시스템 Python 또는 다른 가상환경에서 실행했거나 sklearn 미설치 | `which python`과 `python -m pip show scikit-learn` 확인, `.venv/bin/python -m pip install 'scikit-learn==1.8.0'` 실행 후 import 검사 |
| `BLOCK_C_ENV_DIFF_BLOCKED expected=3.12 ...` | Python 버전 불일치 | `python3.12 --version` 확인, 강사에게 환경 요청 |
| `externally-managed-environment` | 시스템 Python에 직접 pip 설치 시도 | 시스템 대신 `.venv` 만들고 `python -m pip` 사용 |
| `ensurepip is not available` / `venv_creation_failed` | Ubuntu Python 3.12용 `venv` 패키지 미설치 | `python3.12 --version`을 확인하고 강사에게 `python3.12-venv` 설치를 요청, 시스템 Python을 덮어쓰지 않음 |
| `pip_install_failed` / HTTPS timeout | 네트워크·프록시·패키지 인덱스 문제 | 설치 로그의 **최초 오류** 확인, 강사 제공 오프라인 wheel 또는 사전 준비된 가상환경 사용. 같은 명령 무한 재시도 금지 |
| `C01_CONTRACT_FAIL` | 원본 SHA/스키마/Trace 위반 | CSV를 직접 고치지 말고 Git SHA 및 첫 파일 오류를 기록 |
| `D10_INPUT_MISSING: ...features_train.csv` | D09 미완성/특징 데이터 미제공 | 경로 A(강사 제공 데이터) 또는 본인 D09 완료 |
| `NotImplementedError: D09 TODO not implemented` | D09 과제 미구현 | D09 보완 또는 데이터만 제공받아 D10 진행 |
| `NotImplementedError: D10 TODO not implemented` | D10 과제 미구현 | **EXPECTED_RED** — 활동 A~D를 차례로 구현 |
| `KeyError: 'current_a_mean'` | 특징 CSV 열 이름이나 파일 선택 오류 | 첫 줄 헤더, `features_*.csv` 여부 확인 |
| `FileNotFoundError: if_metrics.json` | D10 코드가 아직 산출물을 쓰지 못함 | 코드 실행의 **가장 첫 예외**부터 확인, 없는 JSON을 만들지 않음 |
| `ValueError / AssertionError` | 행 수·상태·정답·스키마 불일치 | 최초 실패 조건과 Trace ID를 확인하고 해당 단계만 수정 |
| 값은 다르지만 실행은 끝남 | sklearn 버전/6특징 순서/전처리 차이 | 버전·Train fit 범위·Valid threshold부터 비교. Test 재튜닝 금지 |

### 강의가 끝날 때 반드시 기억할 세 가지

**① `status=VALID`는 측정 품질의 통과이지 정상 라벨이 아닙니다.**  
**② 모델은 정상 Train으로만 학습하고, 경고선은 정상 Valid로만 고정합니다.**  
**③ 합성 이상탐지의 WARNING·1.9초는 실제 로봇 Safety Supervisor의 정지 성공 증거가 아닙니다.**

---

**참고 자료:** [학생 데모 관찰 가이드](STUDENT_DEMO_GUIDE_KO.md) · [D10 소개](README_KO.md) · [scikit-learn 1.8 데이터 누수 주의](https://scikit-learn.org/1.8/common_pitfalls.html) · [IsolationForest 공식 문서](https://scikit-learn.org/1.8/modules/generated/sklearn.ensemble.IsolationForest.html)

**검증 경계:** 이 가이드는 학생의 코드가 작성되기 전부터 사용하도록 설계했습니다. 교재 원본의 예상 출력은 기존 고정 합성 참조 결과이며, 학생 각자의 새로운 Python 실행·ROS 2·Gazebo·실제 안전 동작을 대신 검증한 것은 아닙니다.