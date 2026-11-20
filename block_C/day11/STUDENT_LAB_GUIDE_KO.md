# AXIA D11 — 학생용 120분 실습 가이드 (초심자용 상세판)

**2026-11-23(월) 20:00–22:00** · 이론 19:00–20:00. **학습 목표① AutoEncoder 기반 정상상태 재구성 원리 이해, 목표② 재구성 오차 기반 이상상태 판정 실습.** 자료는 SYNTHETIC_COURSE_FIXTURE(seed 2409, 합성 10Hz)이고 실제 TurtleBot3의 계측이 아닙니다. AI WARNING은 비인증 교육용 판정이며 ROS/Gazebo/Nav2/Goal/cmd_vel/SW Stop/인증된 E-Stop과 무관합니다.

## 전체 실습 시간표

| 시간 | 실습 | 산출물 |
|---|---|---|
| 20:00–20:10 | 학생 저장소 clone, doctor, SHA, fixture 검사 | SHA·환경 출력 |
| 20:10–20:20 | Raw/Trace/Window/6특징 | split과 특징 메모 |
| 20:20–20:30 | 정상 AE 구조·checkpoint 관찰 | x→xhat→MSE 해설 |
| 20:30–20:45 | 학생 TODO 읽기·의도적 RED | EXPECTED_RED 설명 |
| 20:45–21:00 | Python MSE 직접 실행·손계산 | mse_practice.log |
| 21:00–21:15 | Valid cutoff, Test holdout, 품질 4개 | 오차/품질 판단 근거 |
| 21:15–21:30 | IF/AE 혼동행렬 | precision/recall |
| 21:30–21:50 | 실무 사건 A/B/C 토의 | 최초 증거·금지 조치 |
| 21:50–22:00 | 보고서 제출·종합 | d11_report.md |

## 1. 저장소를 처음 클론합니다

Ubuntu 24.04/WSL2 터미널의 홈에서 다음 **한 블록**을 실행합니다. 기존 파일은 강제로 삭제하거나 reset하지 않습니다.

~~~bash
(
  set -Eeuo pipefail
  ROOT="$HOME/axia_d11_course/axia-robot-safety-student"
  mkdir -p "$(dirname "$ROOT")"
  if [[ ! -d "$ROOT/.git" ]]; then
    git clone https://github.com/silverbjin/axia-robot-safety-student.git "$ROOT"
  fi
  cd "$ROOT"
  if [[ "$(git branch --show-current)" == "main" && -z "$(git status --porcelain)" ]]; then
    git pull --ff-only origin main
  else
    echo D11_STUDENT_WORKTREE_PRESERVED
  fi
  echo "D11_STUDENT_SHA=$(git rev-parse HEAD)"
  bash block_C/scripts/block_c_once.sh --doctor
) || echo "D11_SOURCE_OR_ENV_HOLD: 위의 최초 오류를 점검하세요."
~~~

**해설:** 괄호는 사용자 부모 셸에 errexit을 남기지 않습니다. clone은 최초 1회, clean main에만 fast-forward pull, rev-parse는 사용 버전 기록입니다. doctor는 Python3.12 검사일 뿐 AE 실행 PASS가 아닙니다.

~~~bash
cd "$HOME/axia_d11_course/axia-robot-safety-student"
mkdir -p "$HOME/axia_d11_course/student_evidence"
python3 --version
python3 block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures
~~~

**예상(현장 신규 실측 아님):** Python 3.12.x 및 C01_FIXTURE_CONTRACT_PASS; Raw 4599, Trace 46, 품질 Trace4. --check는 기존 데이터를 검사만 합니다.

## 2. Raw와 Window, 특징을 확인합니다

~~~bash
python3 - <<'PY'
import csv
from pathlib import Path
p=Path("block_C/fixtures")
for name in ("normal_train.csv","normal_valid.csv","test_mixed.csv"):
    with (p/name).open(encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f))
    print(name, "raw",len(rows),"traces",len({r["trace_id"] for r in rows}))
PY
~~~

**예상 결과:**

~~~text
normal_train.csv raw 2400 traces 24
normal_valid.csv raw 800 traces 8
test_mixed.csv raw 1399 traces 14
~~~

한 Trace는 시나리오 전체, 한 Window는 **같은 Trace 내 연속 10 Sample**입니다. 각 Window에서 전류·토크·가속도 mean/std를 계산하여 6특징을 만듭니다. Train240 정상 VALID, Valid80 정상 VALID, Test100 VALID(정상82/이상18) + 품질오류 4개 상태행입니다. 6특징 순서는 current_a_mean, current_a_std, torque_nm_mean, torque_nm_std, accel_mps2_mean, accel_mps2_std입니다. truth_label/trace_id/timestamp_ns는 모델 입력에서 제외합니다.

**VALID는 센서 품질 통과이고 NORMAL은 정상 라벨/판정입니다.** 같은 Trace의 Window를 train/test에 나누어 넣지 마세요. 공개 학생 D09 TODO가 미완성이면 실제 특징 CSV는 자동 생성되지 않습니다. 선택적 전체 AE 구현에는 본인의 완성된 D09 출력 또는 **강사가 제공한 특징 CSV 3종**이 필요합니다. 강사 정답 Python·checkpoint는 복사하지 않습니다.

## 3. 강사 화면에서 정상 AE 재구성을 관찰합니다

~~~text
정상 Train → train-only StandardScaler.fit → 정규화 x(6)
                                      ↓
                     Encoder: 6→8→3, Tanh
                                      ↓
                         잠재 표현 z(3)
                                      ↓
                     Decoder: 3→8→6, Tanh
                                      ↓
                         복원값 xhat(6)
                                      ↓
                       MSE = mean((x-xhat)^2)
~~~

입력과 같은 정상 6특징을 복원하도록 학습합니다. 중간 3차원은 고장 라벨 3종이 아닙니다. 참조 checkpoint 추론은 강사 화면에서 관찰하며 학생 저장소에서 재학습하거나 공개 가중치를 다운로드하지 않습니다. **기존 학습 loss 그래프와 checkpoint 추론은 다른 작업**입니다.

## 4. 미구현 학생 TODO는 의도적으로 실패합니다

~~~bash
cd "$HOME/axia_d11_course/axia-robot-safety-student"
sed -n '1,80p' block_C/day11/student_ae_todo.py
# 아래는 pytest가 설치된 경우에만 실행합니다.
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  block_C/tests/test_student_task_expected_red.py -k d11
~~~

**예상:** NotImplementedError: D11 TODO not implemented = EXPECTED_RED. 설치 오류나 모델 장애가 아닙니다. 선택 구현 함수는 fit_evaluate_ae(fixture_dir: Path, output_dir: Path) -> dict이며 fixture_dir에 D09의 features_train.csv/features_valid.csv/features_test.csv를 담은 폴더를 입력하도록 설계합니다. 이번 필수 120분 성취는 AE 전체 재구현보다 재구성과 MSE 판정 이해/실행입니다. pytest가 없다면 RED 확인을 생략해도 필수 실습을 진행할 수 있습니다.

## 5. Python으로 MSE를 직접 계산합니다 (외부 패키지 불필요)

~~~bash
cd "$HOME/axia_d11_course/axia-robot-safety-student"
python3 block_C/day11/mse_toy_practice.py \
  | tee "$HOME/axia_d11_course/student_evidence/mse_practice.log"
~~~

**예상 출력 — 직접 만든 TOY 수학값이지 실제 모델 점수 아님:**

~~~text
D11_TOY_DEMO_BEGIN source=HAND_CRAFTED_NOT_MODEL_PREDICTION
D11_TOY case=normal mse=0.010000 threshold=0.500000 prediction=NORMAL
D11_TOY case=anomaly mse=1.000000 threshold=0.500000 prediction=WARNING
D11_TOY case=missing mse=UNSCORED threshold=0.500000 prediction=INSUFFICIENT_DATA
D11_TOY_DEMO_PASS only_classroom_math=true model_training=false robot_control=false
~~~

mse() 함수는 정규화된 여섯 입력/복원값 차이 제곱의 평균을 계산합니다. 정상 예에서 차이가 각각 ±0.1이므로 6×0.01/6=0.01, 이상 예는 차이 1.0으로 6×1/6=1.0입니다. decide()는 quality가 VALID가 아니면 risk=None을 반환합니다. 그 다음 유효한 점수에서만 risk가 TOY_THRESHOLD(0.5)보다 **클 때** WARNING입니다. 같은 값이면 NORMAL입니다.

**학생 질문:** TOY_THRESHOLD를 1.0으로 바꾸면 anomaly score=1.0은? → NORMAL. 이것은 수학 연습용 임계값 변경이며 실제 Test를 보고 AE 임계값을 조정하는 것과 다릅니다.

## 6. 정상 Valid 임계값·Test holdout·4개 품질 오류

정상 Train240으로 scaler와 AE를 학습한 뒤, 정상 Valid80의 MSE 95% 분위수만으로 cutoff를 고정합니다. 이후 Test VALID100을 한 번 평가합니다. 기존 강사 AE cutoff 참조는 0.90363125입니다. **TOY 0.5와 혼동하지 않습니다.**

품질 오류 MISSING_VALUE, SAMPLE_GAP, STAMP_REGRESSION, TIMESTAMP_DRIFT는 INSUFFICIENT_DATA이며 score와 threshold를 공란으로 남깁니다. 데이터가 없어 점수를 못 냈다는 사실은 NORMAL(score=0)과 다르고 TP/FP/FN/TN 분모에 포함되지 않습니다.

## 7. IF와 AE 비교: 합성 Test 100 VALID만

| 강사 기존 참조 | TP | FP | FN | TN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| D10 IF | 1 | 2 | 17 | 80 | 33.3% | 5.6% |
| D11 AE | 18 | 4 | 0 | 78 | 81.8% | 100% |

같은 Test에서 AE는 탐지가 증가했지만 FP도 2→4로 늘었습니다. IF risk=-decision_function와 AE risk=MSE의 임계값 숫자는 서로 다른 척도이므로 직접 크기를 비교하지 않습니다. 합성 성능을 실제 로봇 안전 성능으로 일반화하지 않습니다.

## 8. 실무 사건 분석 (하나 선택)

- A 운전 모드 변화: 정상인데 MSE가 상승. 먼저 정상 Train의 모드 범위, 대상 Trace/6특징 확인. **금지:** Test로 cutoff 재설정.
- B 센서 누락·시각 역행: 최초 trace_id/sample_idx/timestamp_ns/quality_reason 확인. **금지:** NaN을 0으로 치환해 NORMAL 판정.
- C 정상 Window에서 AE FP(TST_N_02 등): 최초 truth_label/window_id/risk_score/threshold 확인. **금지:** 교육 WARNING을 SW Stop·인증 E-Stop이라고 보고.

기록 형식은 **관찰 → 최초 원인 후보 → 실제 증거 → 허용 조치 → 금지 조치**입니다.

## 9. 제출 (21:50–22:00)

~~~bash
cat > "$HOME/axia_d11_course/student_evidence/d11_report.md" <<'EOF'
# D11 실습 보고
- 내 Git SHA 및 Python 버전:
- 목표1: 정상 입력을 AE가 6→8→3→8→6으로 복원하는 이유:
- 목표2: 정상 MSE=0.01 / 이상 MSE=1.0 계산 과정:
- Valid-only cutoff와 Test holdout을 구분해야 하는 이유:
- 품질 4개를 INSUFFICIENT_DATA로 유지해야 하는 이유:
- IF(1/2/17/80)와 AE(18/4/0/78)의 FP/FN 비교:
- 사건 A/B/C 중 하나: 증거·가설·금지 행동:
- 직접 실행한 stdout vs 기존 강사 참조값:
EOF
echo "D11_STUDENT_REPORT_CREATED=$HOME/axia_d11_course/student_evidence/d11_report.md"
~~~

제출 파일 **mse_practice.log + d11_report.md**. 100점 루브릭: 정상 재구성 25, MSE 수학 20, Valid/Test 경계 20, 품질 15, IF/AE 비교 10, 실무 사건 10.

## 10. 오류·복구 대응표

| 오류 | 최초 실패 경계 | 복구 |
|---|---|---|
| git: command not found | Git 미설치 | Ubuntu git 설치 후 시작 |
| cd/No such file | 저장소 위치 | 1절 ROOT 절대경로 확인 |
| BLOCK_C_ENV_DIFF_BLOCKED expected=3.12 | Python 버전 | 시스템 Python 교체 금지, 강사에게 환경 요청 |
| No module named pytest | 선택 RED 시험 | 선택 단계 생략 가능; MSE 실습은 표준 Python |
| NotImplementedError: D11 TODO not implemented | EXPECTED_RED | 의도적인 학생 TODO 시작점 |
| No module named torch | CPU AE 의존성 없음 | 학생 TOY 단계는 torch 불필요 |
| INSUFFICIENT_DATA | 입력 품질 불량 | 최초 위반 확인; 0점 정상화 금지 |
| 모델 참조 수치 불일치 | 입력/환경/체크포인트 | 최초 다른 trace/window와 SHA, 버전 기록 |

공식 링크: [PyTorch MSELoss](https://docs.pytorch.org/docs/stable/generated/torch.nn.MSELoss.html), [PyTorch Optimization](https://docs.pytorch.org/tutorials/beginner/basics/optimization_tutorial.html), [scikit-learn Data Leakage](https://scikit-learn.org/1.8/common_pitfalls.html).

**검증 수준:** TOY 공개 Python 계산과 기존 강사 AE reference는 서로 다릅니다. 학생 PC/Owner WSL2 현장 PASS 미검증. ROS/Gazebo 실행 없음.
