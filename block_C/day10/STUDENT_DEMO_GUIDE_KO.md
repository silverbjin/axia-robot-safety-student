# AXIA Block C D10 — 학생용 데모 관찰 가이드

- 수업: **2026-11-20(금) 19:00–22:00**, 이론 60분/실습 120분.
- 학습 주제 ① **Isolation Forest 기반 이상신호 탐지 구조 이해**; ② **정상 패턴 기준 이상탐지 및 조기 경고 검증 실습**.
- 데이터: **SYNTHETIC_COURSE_FIXTURE**, seed=2409, 10 Hz, 4,599 Raw/46 Trace. 실제 TurtleBot3 전류·토크·가속도 계측 자료가 아닙니다.
- 강사 라이브 화면: 20장 확장 D10 교안을 사용합니다. **현재 저장소에 있는 기존 D10 12장 PPT와 혼동하지 마십시오.** 20장 파일은 강사가 수업 때 별도로 제공/공유합니다.

## 0. 저장소 준비 (Ubuntu 24.04/WSL2)

~~~bash
git --version
mkdir -p "$HOME/axia_d10_course"
cd "$HOME/axia_d10_course"
if [ ! -d axia-robot-safety-student/.git ]; then
  git clone https://github.com/silverbjin/axia-robot-safety-student.git
fi
cd axia-robot-safety-student
if [ "$(git branch --show-current)" = main ] && [ -z "$(git status --porcelain)" ]; then
  git pull --ff-only origin main
else
  echo "작업 중인 브랜치/변경 파일을 보존합니다. 자동 갱신 생략"
fi
git rev-parse --short HEAD
bash block_C/scripts/block_c_once.sh --doctor
~~~

예상: Python `3.12.x`, `BLOCK_C_STUDENT_DOCTOR`, 교육용 `NO_GOAL_NO_CMD_VEL`. 이는 기기·환경 점검이며 모델 성공을 의미하지 않습니다. 이 저장소에 있는 D10 학생 TODO는 기본 `NotImplementedError`이며, **수업 전 정상적인 EXPECTED_RED 상태**입니다. 강사 비공개 정답은 학생 저장소에서 다운로드하거나 복제하지 않습니다.

## 1. 데모 중에 반드시 관찰할 구조

~~~text
[고정 Synthetic CSV 4,599 / 46 Trace]
             ↓ 무결성·타임스탬프·Trace 검사
[D09: 비중첩 10샘플 Window / 6개 mean,std]
             ↓ 420 VALID + 4 INSUFFICIENT_DATA
     ┌───────────┬───────────┐
     ↓           ↓           ↓
Train 240      Valid 80     Test 100 VALID (+품질 4)
NORMAL         NORMAL       정상 82/이상 18
     ↓           ↓           │
  IF fit       상위 95%      │
  Scaler fit   임계값        │
     └─────────┬─┘           │
               ↓             │
      고정 모델/임계값 ───────┘
               ↓
        NORMAL / WARNING      품질 오류 → INSUFFICIENT_DATA
               ↓
          FP/FN/최초 경고 분석
~~~

실제 `Safety Supervisor / FSM / Stop / Nav2`는 이 교육용 분석에 연결되어 있지 않습니다. AI 점수는 **비인증 경고**이며 차량의 `cmd_vel`이나 Nav2 Goal을 발행하지 않습니다.

## 2. 강사 화면에서 확인할 5개 체크포인트

| 시각(수업) | 확인할 화면 | 학생 질문 |
|---|---|---|
| 19:00–19:22 | 2개 학습 목표, D09의 CURRENT_SPIKE/TORQUE_DRIFT/ACCEL_VIBRATION 그래프, 시스템 아키텍처 | 어느 계층이 안전정지를 수행하나요? → 이 AI 데모에는 없습니다. |
| 19:22–19:51 | Train/Valid/Test, IF random isolation, `risk_score=-decision_function`, Valid 95% 임계값 | 왜 Test 점수로 경고선을 변경하면 누수인가요? |
| 19:51–20:00 | 주입 시점·10샘플 윈도우·첫 참양성 경고와 혼동행렬 | 조기 경고는 어떤 시점 기준인가요? |
| 20:00–21:15 | C01 `generator.py --check`, D09 특징 CSV, IF 실행 단계 | 6개 숫자 특징 외에 label을 fit에 사용했나요? |
| 21:15–22:00 | 기준 결과와 실제 Trace/Window 분석 | 미탐 17개를 성공으로 말할 수 있나요? |

## 3. 실제 합성 기준 결과 — 관찰할 숫자

- D09 Raw: 정상 Train 2,400 + 정상 Valid 800 + Test 1,399 = **4,599행 / 46 Trace**.
- D09 Feature: **Train 240 NORMAL VALID, Valid 80 NORMAL VALID, Test 100 VALID + 품질 4행 = 총 424행**.
- 각 모델 입력: `current_a_mean/std`, `torque_nm_mean/std`, `accel_mps2_mean/std` (6개); `truth_label`, `trace_id`, `window_id`, `timestamp_ns`는 학습 특징이 아닙니다.
- 기존 강사 참조 IF 점수: Valid 95% 임계값 **0.10199750**, `risk_score`가 초과하면 WARNING. Valid에서 기준 초과 4/80개.
- 기존 합성 Test 혼동행렬: **TP=1 / FP=2 / FN=17 / TN=80**, Precision 33.33%, Recall 5.56%, FPR 약 2.44%. 4개 품질행은 이진 평가 제외.
- 유일한 주입 구간 참양성: `TST_A_00/W5`, 합성 기록 종료 시각 5.9초. 주입 시작 4.0초 대비 **1.9초 이후**. 다른 이상 Trace 5개에서는 주입 중 참양성 없음.
- 별도 정상 윈도우 오탐: `TST_A_03/W9`, `TST_A_04/W8`. Trace 이름에 `A`가 들어가도 특정 윈도우의 실제 label이 0일 수 있습니다.

위 수치는 **기존 참조 산출물**입니다. 학생 PC에서 새로 실행한 결과를 뜻하지 않습니다. sklearn/Python 버전이 다르면 점수/임계값은 달라질 수 있으므로 환경을 기록합니다. Test에 맞춰 threshold를 재조정하면 안 됩니다.

## 4. 학생 화면에서 직접 확인하기 — 모델 실행 전

~~~bash
# 학생 저장소 루트
python3 block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures
head -n 3 block_C/fixtures/normal_train.csv
python3 - <<'PY'
import json
from pathlib import Path
p=Path('block_C/fixtures/scenario_manifest.json')
j=json.loads(p.read_text(encoding='utf-8'))
print('raw_rows=',sum(j['expected_rows'].values()),'trace_count=',sum(j['trace_counts'].values()))
print('anomaly_cases=',j['anomaly_cases'])
PY
~~~

**기대:** `C01_FIXTURE_CONTRACT_PASS`, `raw_rows=4599 trace_count=46`, 이상 시나리오 6개. 합성 생성기에서 고정된 입력 계약을 관찰하는 단계입니다. SHA 검증 실패 시 원본 CSV를 직접 수정하지 않습니다.

## 5. 이상 경고를 해석할 때 지켜야 할 경계

- `WARNING`은 학습된 이상 점수와 고정 임계값으로 분류한 **교육용 상태**입니다. 실제 장비 고장 원인 진단·인증 안전 정지가 아닙니다.
- `INSUFFICIENT_DATA`는 정상 판정도 이상 경고도 아닙니다. 결측/샘플 누락/타임스탬프 역행/드리프트 Trace에는 수치 점수를 붙이지 않습니다.
- '첫 경고 지연 1.9초'는 **합성 Trace에서 주입 시작부터 참양성 Window 끝까지의 간격**입니다. 현장 센서→DDS→ROS 콜백→Stop까지의 지연이 아닙니다.
- 전원, 모터, 실제 E-Stop을 조작할 필요가 없습니다. 필수 강의는 ROS·Gazebo 없이 오프라인 Python으로 수행합니다.

## 6. 다음 단계

**[D10 학생 실습 가이드](STUDENT_LAB_GUIDE_KO.md)**에서 `student_if_todo.py`를 직접 완성하고 실습 증거를 남깁니다. 학생용 공개 CI의 스캐폴드 PASS는 미완성 TODO의 정답을 확인한 것이 아닙니다.

**제출할 관찰 문장 3개:** “Train/Valid/Test의 역할은…”, “첫 WARNING의 기록 시각과 의미는…”, “AI 경고가 Safety Supervisor의 STOP과 다른 이유는…”.
