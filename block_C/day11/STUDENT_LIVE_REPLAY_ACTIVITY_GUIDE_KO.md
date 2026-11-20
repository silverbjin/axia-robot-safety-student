# AXIA D11 — 학생 참여형 라이브 Replay 실습 활동지 (12분 + MSE 실습 연결)

**학습목표 ① AutoEncoder 기반 정상상태 재구성 원리 이해.**  
**학습목표 ② 재구성 오차 기반 이상상태 판정 실습.**

이번 데모는 **SYNTHETIC_COURSE_FIXTURE**(seed 2409, 합성10Hz) 기록을 강사 화면에서 **오프라인 재생**하는 것입니다. 현장 로봇·Gazebo/ROS2가 실제로 동작하거나 AI가 지금 새로 학습/추론하는 화면이 아닙니다. 비인증 AI WARNING을 SW Stop·인증된 E-Stop·Nav2/cmd_vel 제어로 해석하지 않습니다.

## 수업 시작 전 준비 (학생 PC에서 실제 실행 가능한 명령)

처음부터 공개 학생 저장소를 받습니다. 기존 클론은 강제로 reset하지 않습니다.

~~~bash
(
  set -Eeuo pipefail
  ROOT="$HOME/axia_d11_course/axia-robot-safety-student"
  mkdir -p "$(dirname "$ROOT")"
  if [[ ! -d "$ROOT/.git" ]]; then
    git clone https://github.com/silverbjin/axia-robot-safety-student.git "$ROOT"
  fi
  cd "$ROOT"
  if [[ "$(git branch --show-current)" == main && -z "$(git status --porcelain)" ]]; then
    git pull --ff-only origin main
  fi
  echo "D11_STUDENT_SHA=$(git rev-parse HEAD)"
  python3 block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures
  mkdir -p "$HOME/axia_d11_course/student_evidence"
  python3 block_C/day11/mse_toy_practice.py \
    | tee "$HOME/axia_d11_course/student_evidence/mse_practice.log"
) || echo "D11_STUDENT_PREP_HOLD: 첫 실패 단계의 오류를 확인하세요."
~~~

실행 전 예상(실제 내 PC에서 나온 값만 결과 보고서에 기록):

~~~text
C01_FIXTURE_CONTRACT_PASS ... rows=4599 traces=46 quality_traces=4
D11_TOY case=normal mse=0.010000 threshold=0.500000 prediction=NORMAL
D11_TOY case=anomaly mse=1.000000 threshold=0.500000 prediction=WARNING
D11_TOY case=missing mse=UNSCORED threshold=0.500000 prediction=INSUFFICIENT_DATA
~~~

이 TOY MSE 값은 직접 만든 숫자이며 강사가 보여주는 실제 AE 참조 점수와 같지 않습니다. 전체 AE 모델 재학습은 필수 과제가 아니며 student_ae_todo.py는 EXPECTED_RED로 남습니다.

## 12분 몰입형 시연: 수사관처럼 먼저 예측해 보세요

| 시간 | 강사 화면 동작 | 내가 먼저 할 질문 | 적을 답 |
|---:|---|---|---|
| 0–2분 | CASE TST_A_00, 그래프 재생, AI 점수 숨김 | 이상 주입이 시작된 Window를 예상해 보세요. | 예상 W____ |
| 2–4분 | W4에서 **IF 판정 공개**, 그다음 **AE 판정 공개** | 두 모델의 판단이 같았나요? 다르면 어떤 근거가 다른가요? | IF ____ / AE ____ |
| 4–5분 | W5로 이동하면 답이 다시 숨겨짐 | 다음 Window에서도 똑같을까요? | 이유 ____ |
| 5–7분 | CASE TST_N_02, W4 | 정상 정답인데 경고가 나올 수도 있나요? | 예측 ____ |
| 7–9분 | CASE TST_A_04, W8 | 이상 주입이 끝난 뒤에는 반드시 NORMAL일까요? | 예측 ____ |
| 9–10분 | CASE TST_Q_01 | 센서 sample 누락이면 MSE가 0일까요, 점수 없음일까요? | 선택 ____ |
| 10–12분 | 합성 정답 공개, 두 모델의 TP/FP/FN/TN 비교 | 오탐(FP), 미탐(FN)을 자기 말로 설명하세요. | FP ____ / FN ____ |

강사는 정답과 모델 점수를 단계적으로 공개합니다. **이 활동지는 강사의 비공개 모델 정답을 선공개하지 않으므로 직접 예측한 뒤 공개 결과를 확인하십시오.** 화면에 있는 두 점수는 IF 위험점수와 AE 재구성 MSE로 서로 다른 척도입니다. 큰 숫자만 보고 모델의 우열을 정하지 않습니다.

## 공개된 뒤에 채울 증거 표

| 시나리오 | 실제 관찰한 Window | 내 사전 예측 | 공개된 IF 판정 | 공개된 AE 판정 | 합성 정답 / 오차 유형 |
|---|---|---|---|---|---|
| 전류 변화 TST_A_00 | W____ | ____ | ____ | ____ | ____ |
| 정상 오경보 TST_N_02 | W____ | ____ | ____ | ____ | ____ |
| 진동 후 TST_A_04 | W____ | ____ | ____ | ____ | ____ |
| 품질 TST_Q_01 | W0 | ____ | ____ | ____ | ____ |

**품질 미점수**가 중요한 이유: 측정값 자체가 없는데 위험점수 0을 만들어 NORMAL이라고 보고하면 측정 실패가 정상 데이터로 둔갑합니다. INSUFFICIENT_DATA는 정상도 경고도 아닌 별도 판정입니다.

## 이해도 확인 질문 5개

1. Normal Train 240 Window를 AE가 6→8→3→8→6으로 처리하는 이유는 무엇일까요? → 여섯 특징을 압축한 뒤 같은 입력 차원으로 복원해 오차를 계산하기 위해서입니다.
2. x와 복원값 xhat의 차이 여섯 개는 어떻게 한 개 MSE가 될까요? → 대응하는 숫자끼리 차이를 제곱하고 여섯 개를 평균합니다.
3. IF cutoff와 AE cutoff를 숫자만 비교해 “더 안전한 모델”을 정할 수 있을까요? → 점수 정의가 달라 불가합니다.
4. Test 성능을 보고 정상 Valid의 경고선을 조정하면 어떤 문제가 생기나요? → 평가 누수가 발생합니다.
5. 교육용 AI WARNING이 안전 인증 E-Stop과 같은가요? → 아닙니다. 실제 제어권이 없습니다.

## 기대 효과 — 학생 스스로 확인하는 성취 (정량 효과는 아직 미측정)

| 기대 효과 | 학생의 행동으로 확인할 근거 |
|---|---|
| 몰입·관찰 집중 | 정답 공개 전에 이상 Window와 상태를 스스로 예측했는가? |
| AutoEncoder 원리 이해 | 입력 6특징의 압축·복원과 MSE의 인과관계를 설명할 수 있는가? |
| 판정 기준 이해 | VALID 확인을 먼저 하고 cutoff 초과 조건을 설명하는가? |
| 오탐·미탐 토론 능력 | 정상인데 경고=FP, 이상인데 놓침=FN을 구분하는가? |
| 기술적 보고 능력 | 합성 참조/실제 내 코드 실행/안전 기능 미검증을 구분해 기록하는가? |

이는 수업 설계에 따른 **기대 효과**입니다. 실제 학생 성취도 향상률이나 몰입도 상승률은 측정한 적이 없으므로 수치로 주장하지 않습니다.

## 결과 제출 (기존 120분 실습과 연결)

새 파일 제출을 강제하지 않습니다. 기존 필수 제출물 두 개를 유지합니다.

- **mse_practice.log:** 내 PC에서 실행한 공개 TOY stdout.
- **d11_report.md:** 두 학습 목표 설명, 직접 MSE 손계산, IF/AE 참조 해석, 본 활동지에서 예측이 달라졌던 사례 1개와 판단 이유.

예시 문장(학생이 자신의 결과를 채워야 함): “저는 ____ Window를 WARNING으로 예측했지만 공개된 ____ 모델은 ____였습니다. 따라서 ____ 모델의 점수/threshold 또는 품질 상태를 재확인해야 합니다. 이는 합성 교육용 결과로 실제 로봇 정지를 의미하지 않습니다.”

기존 [120분 초심자 상세 실습 가이드](STUDENT_LAB_GUIDE_KO.md)와 [학생 데모 가이드](STUDENT_DEMO_GUIDE_KO.md)를 이어서 사용하십시오. 강사 화면의 비공개 HTML·AE/IF score CSV나 가중치를 공개 학생 저장소에 저장하지 않습니다.
