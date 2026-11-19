# AXIA Block C D10 — 학생용 120분 실습 가이드

- 수업 **2026-11-20 20:00–22:00** (앞선 19:00–20:00 이론을 전제로 함).
- 과제: `block_C/day10/student_if_todo.py`의 **`fit_evaluate_if(feature_dir, output_dir)`를 직접 구현**합니다. 완료 이전 `NotImplementedError`는 의도된 상태입니다.
- 강사 정답/hidden tests를 공개 저장소에 복사하지 않습니다. 학습·임계값·평가 순서는 **정상 Train만 fit → 정상 Valid만 임계값 → 고정된 Test만 평가**.
- 목표: 단순 코드 실행뿐 아니라 **Isolation Forest 구조를 설명**하고 **초기 WARNING 시점·오탐·미탐을 근거로 조기 경고 여부를 검증**합니다.

## 0. 사전 준비와 작업 원칙 (10분)

학생 저장소 루트에서 실행합니다. 기존 사용자 브랜치·파일은 삭제/초기화하지 않습니다.

~~~bash
bash block_C/scripts/block_c_once.sh --doctor
python3 block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures
python3 - <<'PY'
import importlib.util
for name in ('numpy','sklearn','pytest'):
    print(name, 'OK' if importlib.util.find_spec(name) else 'MISSING')
PY
export AXIA_D10_LAB="$HOME/axia_d10_student_lab"
mkdir -p "$AXIA_D10_LAB/c02" "$AXIA_D10_LAB/c03"
git rev-parse --short HEAD
~~~

기대: Python 3.12.x, `C01_FIXTURE_CONTRACT_PASS`, 4,599행/46 Trace. `MISSING`이 있다면 수업 Python 3.12 가상환경에서 `python3 -m pip install numpy scikit-learn pytest`를 사용합니다. 학습은 CPU로 충분하며 ROS/Gazebo/torch는 D10 필수 의존성이 아닙니다.

## 1. D09 특징 입력을 확인합니다 (10분)

**중요 사전조건:** 공개 저장소는 원본 CSV 및 미완성 D09 TODO를 제공합니다. **D09 학생 과제가 끝나지 않았다면 6특징 CSV는 자동으로 존재하지 않습니다.** 수업 전 D09 과제를 완성했거나, 강사가 별도로 제공한 **데이터만 포함한** D09 특징 CSV 3개를 `$AXIA_D10_LAB/c02`에 복사합니다. 강사의 Python 정답 파일은 복사하지 않습니다.

D09 기능을 본인이 구현한 경우 예시:

~~~bash
PYTHONPATH=block_C/day09 python3 - <<'PY'
import os
from pathlib import Path
from student_eda_todo import make_features
out=Path(os.environ['AXIA_D10_LAB'])/'c02'
result=make_features(Path('block_C/fixtures'), out)
print('D09_student_result=',type(result).__name__)
PY
~~~

기대: 학생이 구현한 함수가 정상 반환하고 아래 3개 파일을 만듭니다. 아직 D09 TODO가 미구현이면 `NotImplementedError`가 **예상 RED**입니다.

~~~bash
ls -lh "$AXIA_D10_LAB/c02"/features_{train,valid,test}.csv
python3 - <<'PY'
import csv,os
from pathlib import Path
p=Path(os.environ['AXIA_D10_LAB'])/'c02'
for split,expected in [('train',240),('valid',80),('test',104)]:
    with (p/f'features_{split}.csv').open(newline='',encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    good=sum(r['status']=='VALID' for r in rows)
    bad=sum(r['status']=='INSUFFICIENT_DATA' for r in rows)
    print(split, len(rows), good, bad)
    assert len(rows)==expected
PY
~~~

기대: `train 240 240 0` / `valid 80 80 0` / `test 104 100 4`. 실제 출력이 다르면 먼저 D09 특징·Trace 품질을 수정합니다. 임의 숫자/이상 라벨을 만들어 빈 특징 파일을 채우지 마십시오.

## 2. RED — 미완성 D10 TODO를 확인합니다 (10분)

~~~bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  block_C/tests/test_student_task_expected_red.py -k d10
~~~

기본 배포본의 `NotImplementedError: D10 TODO not implemented`는 **정상적인 과제 RED**입니다. 다른 3차시 테스트를 함께 실행할 필요는 없습니다. 이 공개 테스트는 함수의 반환형만 확인하고 실데이터 분리·점수·안전 경계까지 검증하지 않으므로, GREEN만으로 D10 인수 성공이라고 주장할 수 없습니다.

## 3. 구현 활동 A — 정상 데이터만 학습 (15분)

`block_C/day10/student_if_todo.py`를 편집합니다. 이 함수의 첫 번째 인수는 **원본 3 CSV가 아니라 6특징이 담긴 feature directory**로 사용합니다(기존 매개변수 이름 `fixture_dir`은 유지해도 됨).

구현 체크포인트:
- `features_train.csv`만 읽고 `status=VALID`, `split=train`, `truth_label=0`을 검증.
- `current_a_mean, current_a_std, torque_nm_mean, torque_nm_std, accel_mps2_mean, accel_mps2_std` **순서대로** 배열 구성; 다른 열을 모델에 넣지 않음.
- Train의 240×6 입력으로 `StandardScaler.fit` 및 `IsolationForest.fit`만 수행.
- 권장 고정 설정(기존 강사 기준): `n_estimators=100`, `random_state=2409`, `contamination='auto'`, `n_jobs=1`. 기존 sklearn 버전을 기록.

학생 질문: "왜 Test를 fit에 먼저 넣으면 최종 시험이 공정하지 않을까요?"

## 4. 구현 활동 B — 정상 Valid로 cutoff 결정 (15분)

- Train에서 fit한 scaler·IF만으로 `features_valid.csv`의 정상 80×6 점수를 얻습니다.
- 점수 방향은 `risk_score = -decision_function(scaler.transform(X))` (높을수록 더 이상).
- 정상 Valid 위험점수의 **0.95 분위수**를 threshold로 고정합니다. 공개된 학생 과제에는 임계값 코드 정답을 제공하지 않습니다.
- `risk_score > threshold` → `WARNING`; 아니면 `NORMAL`. threshold를 정한 뒤에만 Test 파일을 평가에 사용합니다.
- sklearn 내부 `contamination='auto'`에 따른 0 기준을 **별도 최종 threshold로 사용하지 마십시오**.

학생 질문: "왜 Test의 FN을 줄이기 위해 95%를 80%로 변경하면 안 될까요?"

## 5. 구현 활동 C — Test holdout 평가 (15분)

- `features_test.csv`는 VALID 100개와 `INSUFFICIENT_DATA` 4개. **100개만 모델 점수화/혼동행렬 평가**.
- 유효 Test의 `truth_label`은 **TP/FP/FN/TN 계산에만** 사용.
- 품질 오류 4행은 `risk_score`/`threshold`를 공란으로 두고 `prediction=INSUFFICIENT_DATA`.
- `if_metrics.json`에 최소한 `train_count,valid_count,test_valid_count,test_invalid_count,threshold,threshold_source,risk_score_direction,confusion,precision,recall,fpr,fit_on_test,test_threshold_tuned` 기록.
- `if_scores_test.csv`에는 최소한 `trace_id,window_id,timestamp_ns,status,quality_reason,truth_label,risk_score,threshold,prediction` 기록.

**예시 기준값(기존 강사 결과, 학생 신규 실행 보증 아님):** threshold `0.10199750`, TP1/FP2/FN17/TN80, Recall 0.0556. 점수가 다르면 버전/feature 순서/전처리와 첫 차이를 확인하고 Test로 threshold를 튜닝하지 않습니다.

## 6. 구현 활동 D — 자기 결과 실행·검사 (15분)

~~~bash
PYTHONPATH=block_C/day10 python3 - <<'PY'
import os
from pathlib import Path
from student_if_todo import fit_evaluate_if
p=Path(os.environ['AXIA_D10_LAB'])
result=fit_evaluate_if(p/'c02', p/'c03')
print('STUDENT_D10_RESULT_TYPE=',type(result).__name__)
print('STUDENT_D10_OUTPUT=',p/'c03')
PY
python3 - <<'PY'
import csv,json,os
from collections import Counter
from pathlib import Path
p=Path(os.environ['AXIA_D10_LAB'])/'c03'
m=json.loads((p/'if_metrics.json').read_text(encoding='utf-8'))
with (p/'if_scores_test.csv').open(newline='',encoding='utf-8') as f:
    rows=list(csv.DictReader(f))
assert len(rows)==104, len(rows)
assert sum(r['prediction']=='INSUFFICIENT_DATA' and not r['risk_score'] for r in rows)==4
assert sum(m['confusion'].values())==100
assert m['threshold_source']=='normal_valid_only'
assert m['fit_on_test'] is False and m['test_threshold_tuned'] is False
print('D10_STUDENT_DATA_CHECK_PASS',Counter(r['prediction'] for r in rows),m['confusion'])
PY
~~~

기대: 학생 작성이 완료되어 출력 규격을 지켰다면 `D10_STUDENT_DATA_CHECK_PASS`와 104개 행의 상태 분포. 값이 다르면 **첫 오류와 파일 경로를 기록**하고 개별 단계로 돌아갑니다. 이 구문은 기능 정답을 제공하는 게 아니라 학생 산출물을 검사합니다.

## 7. 조기 경고 타임라인 검증 (13분)

**합성 시계열 해석**: 10Hz에서 sample_idx 40에 이상을 주입합니다(4.0초). W4=4.0~4.9초, W5=5.0~5.9초, W6=6.0~6.9초. 각 Window의 `timestamp_ns`는 마지막 샘플 시각입니다.

학생은 `if_scores_test.csv`에서 `TST_A_00`~`TST_A_05`를 살피고 **truth_label=1이면서 WARNING인 첫 윈도우**를 찾습니다. **해당 Trace에서 검출 없으면 NOT_DETECTED**로 기록합니다. 품질 오류 4건을 탐지 지연 0초로 둬서는 안 됩니다.

~~~bash
python3 - <<'PY'
import csv,json,os
from pathlib import Path
root=Path(os.environ['AXIA_D10_LAB'])
cases=json.loads(Path('block_C/fixtures/scenario_manifest.json').read_text(encoding='utf-8'))['anomaly_cases']
with (root/'c03/if_scores_test.csv').open(newline='',encoding='utf-8') as f:
    rows=list(csv.DictReader(f))
onset_ns=40*100_000_000
for tid in sorted(cases):
    hits=[r for r in rows if r['trace_id']==tid and r['status']=='VALID'
          and r['truth_label']=='1' and r['prediction']=='WARNING']
    if not hits:
        print(tid,'NOT_DETECTED')
    else:
        first=min(hits,key=lambda r:int(r['timestamp_ns']))
        print(tid,'W'+first['window_id'],
              'synthetic_delay_s=',round((int(first['timestamp_ns'])-onset_ns)/1e9,1))
PY
~~~

기존 기준 참조: `TST_A_00 W5 synthetic_delay_s=1.9`, 나머지 5 Trace `NOT_DETECTED`. 이 분석은 **주입 시작 이후의 합성 Window 기반**이며 실제 로봇의 실시간 Safety TTL/고장 이전 예지 성능이 아닙니다.

## 8. 제출·회고 (7분)

제출물(개별 PC의 경로·커밋·환경 포함):
- `architecture_explanation.md` — 원본/6특징/Train/Valid/Test/경고와 생산 Safety 계층 분리 설명.
- `student_if_todo.py` — 자신의 코드(강사 정답 복사 금지).
- `if_metrics.json`, `if_scores_test.csv` — 평가 산출물.
- `early_warning_report.md` — 최초 탐지 Trace·Window·합성 지연·NOT_DETECTED·FP 사례.
- `command_evidence.log` — 실제 버전·원본 SHA·실행 명령·최초 실패·GREEN 검증.

**학습 종료 질문:** ① IF가 무엇을 학습했습니까? ② 정상 Valid만으로 무엇을 결정했습니까? ③ 현재 결과가 실제 E-Stop 성공이라는 주장에 왜 반대해야 합니까?

## 9. 시간표·검증 경계

10+10+10+15+15+15+15+13+7 = **110분**입니다. 남은 **10분은 D09 입력이 없는 학생 지원/개별 질의/예외 처리**에 배정해 실습 전체 120분을 구성합니다.

학생 실습의 자체 GREEN과 공개 CI에서 **TODO 4건 EXPECTED_RED**를 보장하는 교재 스캐폴드 검증은 별개입니다. 학생 개인 과제 구현으로 공식 배포본을 덮어쓰거나 공개 기본 브랜치에 정답을 올리지 마십시오. 기존 ROS/NAV2/Safety Supervisor/FSM/Stop에는 어떤 제어도 수행하지 않습니다.
