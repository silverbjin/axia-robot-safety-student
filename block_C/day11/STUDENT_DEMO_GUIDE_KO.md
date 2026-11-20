# AXIA D11 — 학생용 데모 관찰 가이드 (클론부터 화면 해석까지)

**수업:** 2026-11-23(월) 19:00–22:00, 이론60분+실습120분.  
**목표① AutoEncoder 기반 정상상태 재구성 원리 이해** / **목표② 재구성 오차 기반 이상상태 판정 실습**.

**출처:** SYNTHETIC_COURSE_FIXTURE(seed=2409, 합성 10Hz). TurtleBot3 모터의 실제 전류·토크·가속도 계측이 아닙니다. AI WARNING은 교육용 비인증 경고이며, 인증 E-Stop·SW Stop·Nav2 Goal·cmd_vel로 연결되지 않습니다.

## 0. Ubuntu 24.04/WSL2 시작하기: 저장소 클론

터미널이 현재 홈(~) 위치여도 실행할 수 있도록 절대 경로를 사용합니다. 기존 작업이 있으면 강제로 초기화하지 않습니다.

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
    echo "D11_STUDENT_WORKTREE_PRESERVED"
  fi
  echo "D11_STUDENT_SOURCE_SHA=$(git rev-parse HEAD)"
  bash block_C/scripts/block_c_once.sh --doctor
) || echo "D11_STUDENT_PREP_HOLD: 터미널을 닫지 말고 위 첫 오류 확인"
~~~

- clone: 학생 공개 자료만 다운로드. **강사 비공개 저장소를 클론하지 않습니다.**
- pull --ff-only: 깨끗한 main일 때만 안전하게 갱신.
- rev-parse HEAD: 현장 문제가 나면 어떤 코드 버전이었는지 기록.
- doctor: Python3.12와 환경 확인일 뿐 AE 학습·추론 PASS가 아님.

**예상(학생 PC 미실측):** BLOCK_C_STUDENT_DOCTOR python=3.12.x, BLOCK_C_NO_GOAL_NO_CMD_VEL_NO_CERTIFIED_ESTOP. Python3.12가 아니면 system Python을 임의 교체하지 말고 수업 환경을 점검합니다.

## 1. 강의 화면에 등장하는 전체 데이터·모델 파이프라인

~~~text
합성 Raw 4,599행 / 46 Trace
  ├ Train 24 Trace 2,400 Raw → Window 240 VALID (정상)
  ├ Valid  8 Trace   800 Raw → Window  80 VALID (정상)
  └ Test  14 Trace 1,399 Raw → Window 100 VALID + 품질오류 상태행 4개
                │ 같은 Trace의 연속 10 sample만 사용
                ▼
          6 특징 (전류/토크/가속도 각각 mean·std)
                │
 Train(정상) → StandardScaler.fit + AE 가중치 학습
 Valid(정상) → 같은 scaler.transform → 재구성 MSE의 95% cutoff
 Test(VALID) → 같은 scaler.transform → AE 복원 xhat → MSE와 cutoff 비교
 품질 불량 → 점수 계산 생략 → INSUFFICIENT_DATA
                │
          NORMAL / WARNING / INSUFFICIENT_DATA
~~~

**VALID ≠ NORMAL.** VALID는 품질 검사 통과, truth_label=0/1은 평가용 정상/이상 정답입니다. 같은 Trace를 나누어 Train/Test에 섞으면 시나리오 누수가 생깁니다. 6특징은 current_a_mean, current_a_std, torque_nm_mean, torque_nm_std, accel_mps2_mean, accel_mps2_std. 시간·Trace ID·정답라벨은 AE 입력이 아닙니다.

## 2. 26장 강사 PPT 관찰 큐시트

이번 D11 수업은 별도 제작된 **26장 개편 슬라이드**를 강사가 화면 공유할 수 있습니다. 저장소에 있는 기존 D11_AutoEncoder.pptx는 구형 12장 자료로 **동일 파일이 아닙니다**. 이 학생 저장소에는 강사 26장 PPTX/솔루션/체크포인트를 게시하지 않습니다.

| 시각 | 화면 | 학생 질문/예상 답 |
|---|---|---|
| 19:00–19:18 | 두 학습목표·실무 센서 사례·Raw→Trace→Window | 왜 Trace별로 분할하나? → 데이터 누수 방지 |
| 19:18–19:35 | VALID 품질·train-only scaler·AE 6→8→3→8→6 | 잠재 3개 값이 고장 클래스인가? → 아님 |
| 19:35–19:47 | 정상 입력 x와 복원 xhat, MSE, 역전파 | 모델이 학습 시 복원하는 목표는? → 정상 입력 자체 |
| 19:47–20:00 | Valid 95% cutoff와 IF/AE 혼동행렬 | Test로 cutoff 재조정? → 불가 |
| 20:00–22:00 | Python 수학 연습·오류 사례·제출 | 품질 오류에 MSE=0 부여? → 불가 |

## 3. 학생이 즉시 실행하는 데모 — 외부 Python 패키지 불필요

~~~bash
cd "$HOME/axia_d11_course/axia-robot-safety-student"
python3 block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures
python3 block_C/day11/mse_toy_practice.py
~~~

**합성 원본 검사 예상:** C01_FIXTURE_CONTRACT_PASS; 전체 Raw 4599, Trace 46, 품질 Trace 4. **TOY 코드의 결정적 출력**(실제 AE checkpoint가 아님):

~~~text
D11_TOY_DEMO_BEGIN source=HAND_CRAFTED_NOT_MODEL_PREDICTION
D11_TOY case=normal mse=0.010000 threshold=0.500000 prediction=NORMAL
D11_TOY case=anomaly mse=1.000000 threshold=0.500000 prediction=WARNING
D11_TOY case=missing mse=UNSCORED threshold=0.500000 prediction=INSUFFICIENT_DATA
D11_TOY_DEMO_PASS only_classroom_math=true model_training=false robot_control=false
~~~

**해석:** 정규화된 여섯 입력과 복원의 차이 제곱을 평균(MSE)합니다. 정상 예는 0.01로 낮고, 이상 예는 1.0으로 TOY cutoff 0.5를 초과합니다. 결측은 점수 없음이지 0점 정상 상태가 아닙니다.

## 4. 강사 기존 합성 참조값과 질문

| 모델 | TP | FP | FN | TN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| D10 Isolation Forest | 1 | 2 | 17 | 80 | 33.3% | 5.6% |
| D11 Autoencoder | 18 | 4 | 0 | 78 | 81.8% | 100% |

동일한 Test VALID 100개에서 비교했으며 품질 오류 4개는 이진 혼동행렬에 넣지 않습니다. IF 위험점수(-decision_function)와 AE 재구성 MSE는 단위가 다르므로 숫자만 직접 비교하면 안 됩니다. 이 수치는 **기존 강사 참조 기록**이며 학생 PC 또는 WSL2 현장 신규 검증이 아닙니다.

## 5. 오류와 복구

| 첫 증상 | 의미 | 대응 |
|---|---|---|
| cd 실패 | 클론 경로 또는 현재 폴더 오류 | 0절의 절대 ROOT부터 확인 |
| BLOCK_C_ENV_DIFF_BLOCKED | Python 3.12 아님 | 시스템 Python 교체 금지; 강사와 환경 확인 |
| NotImplementedError: D11 TODO not implemented | 학생 TODO 의도적 EXPECTED_RED | 수업 출발점 정상, 실습 진행 |
| torch 모듈 없음 | 학습용 CPU PyTorch 미설치 | 학생의 MSE 수학 실습에는 불필요 |
| INS UFFICIENT_DATA 또는 데이터 결측 | 품질·입력 오류 가능성 | 점수를 0으로 채우지 말고 최초 위반 조사 |
| AI WARNING | 수업용 판정 | 물리적 안전 정지 동작으로 오인 금지 |

**다음:** [120분 단계별 실습·제출 가이드](STUDENT_LAB_GUIDE_KO.md), [의도적 학생 TODO](student_ae_todo.py), [MSE 예제](mse_toy_practice.py).

공식 참고: [PyTorch MSELoss](https://docs.pytorch.org/docs/stable/generated/torch.nn.MSELoss.html), [PyTorch Sequential](https://docs.pytorch.org/docs/stable/generated/torch.nn.Sequential.html), [scikit-learn Data Leakage](https://scikit-learn.org/1.8/common_pitfalls.html).
