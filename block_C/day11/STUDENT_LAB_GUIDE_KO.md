# AXIA Block C D11 — 초심자와 함께하는 AutoEncoder 실습 (120분 완전 안내서)

**일정:** 2026-11-23(월) 20:00–22:00, 이론은 19:00–20:00.  
**학습 목표 1:** **AutoEncoder 기반 정상상태 재구성 원리 이해**.  
**학습 목표 2:** **재구성 오차 기반 이상상태 판정 실습**.  
**권장 실습 PC:** Ubuntu 24.04 / WSL2, Python 3.12, Git, 터미널. 별도의 GPU·ROS 2·Gazebo가 없어도 **필수 실습은 진행할 수 있습니다**.

> **데이터 출처 주의:** 이 수업은 SYNTHETIC_COURSE_FIXTURE(seed 2409, 합성 10Hz)의 **가상 전류·토크·가속도**만 이용합니다. TurtleBot3 Waffle의 실제 모터 계측값이 아닙니다. AI WARNING은 비인증 교육용 경고이며, Nav2 Goal, cmd_vel, SW Stop, **인증된 E-Stop**과 연결되지 않습니다.

## 처음 실습하는 분을 위한 길잡이

### 오늘 무엇을 하게 되나요?

1. **원본 데이터 살펴보기**: CSV에서 1행(Sample)과 1개 Trace를 찾아봅니다.
2. **10개의 Sample로 6개 특징 만들기**: 전류·토크·가속도의 평균과 표준편차를 구해 봅니다.
3. **AutoEncoder 구조 이해하기**: 6개 값을 받아 압축한 뒤 다시 6개로 복원하는 과정을 그림으로 따라갑니다.
4. **실제 실행 가능한 Python 계산하기**: 입력과 복원값의 차이로 MSE를 계산하여 정상·경고·데이터 부족을 구분합니다.
5. **결과 설명하기**: 강사가 보여주는 기존 AE 참조 결과와 D10 IF를 비교하고 실무 오류 사례를 해석합니다.

### 내가 구현해야 하는 것과 관찰하는 것을 구분하세요

| 활동 | 누구의 실행 결과인가요? | 실습에서 필수? |
|---|---|---|
| 공개 CSV 무결성 검사, CSV 읽기, 10개 Sample 평균/표준편차 | **내 PC에서 직접 실행** | 필수 |
| mse_toy_practice.py: 정규화된 숫자를 이용한 MSE 수학 계산 | **내 PC에서 직접 실행**. 학습된 AE 모델이 아님 | 필수 |
| 강사 비공개 AE checkpoint 학습·평가 화면 | **INSTRUCTOR_REFERENCE** 또는 강사 시연. 학생 PC 재학습 아님 | 관찰 필수 |
| student_ae_todo.py의 PyTorch AE 전체 구현 | 학생 스스로 작성해야 할 **EXPECTED_RED 과제** | 심화 선택 |

**주의: TOY 계산은 실제 AE 추론이 아닙니다.** 모델의 원리를 이해하기 위한 수학 실습이며, 학습된 가중치를 사용하지 않습니다. 강사 시연에서는 기존 실제 CPU AE 코드와 checkpoint를 관찰합니다. 강사 체크포인트·정답 Python·비공개 테스트는 공개 학생 저장소에 넣지 않습니다.

### 전체 실습 시간표 (120분)

| 시간 | 단계 | 소요 | 초심자가 얻어야 할 결과 |
|---|---|---:|---|
| 20:00–20:10 | 1. Git 클론·환경·원본 검사 | 10분 | 내 소스 SHA와 원본 PASS/HOLD 구별 |
| 20:10–20:20 | 2. Raw·Trace·Window·6특징 | 10분 | 10개 Sample이 6개 특징이 되는 이유 |
| 20:20–20:30 | 3. 정상 재구성·강사 시연 관찰 | 10분 | x(6) → z(3) → xhat(6) 그림 설명 |
| 20:30–20:45 | 4. 학생 TODO·Python 기본 코드 읽기 | 15분 | 함수·인자·반환값과 EXPECTED_RED 이해 |
| 20:45–21:00 | 5. 실제 MSE 실행·연습문제 A | 15분 | 0.01 / 1.0 / UNSCORED 직접 계산 |
| 21:00–21:15 | 6. Valid-only 판정·품질·연습문제 B | 15분 | 정상/경고/데이터 부족을 분리 |
| 21:15–21:30 | 7. IF와 AE 평가 비교 | 15분 | TP/FP/FN/TN 및 Precision/Recall |
| 21:30–21:50 | 8. 실무 현장형 사례 | 20분 | 첫 오류 증거와 잘못된 복구의 차이 |
| 21:50–22:00 | 9. 보고서 제출·스스로 점검 | 10분 | 실행 증거·정답·한계 설명 |
| **총계** | | **120분** | |

### 1분 용어 사전

| 처음 보는 용어 | 초심자를 위한 뜻 | 이 수업의 예 |
|---|---|---|
| Terminal(터미널) | 명령어를 한 줄씩 입력하는 창 | git, python3 명령 입력 |
| Git clone | GitHub의 공개 실습 파일을 내 PC로 복사 | 학생 저장소 다운로드 |
| Python | 우리가 실행할 프로그래밍 언어 | mse() 계산 |
| CSV | 쉼표로 열을 구분한 표 형식의 텍스트 파일 | normal_train.csv |
| Sample | 한 시각의 측정값 한 줄 | 전류·토크·가속도와 timestamp |
| Trace | 하나의 시나리오에 속하는 Sample 묶음 | TRN_00, TST_A_00 |
| Window | 같은 Trace에서 **연속 10개 Sample**을 묶은 부분 | W0 = Sample 0~9 |
| Feature(특징) | Window를 대표하는 계산값 | 전류 평균·표준편차 등 6개 |
| Train | 스케일러/모델을 학습할 데이터 | 정상 Window 240 |
| Valid | 학습을 마친 뒤 경고 기준값을 정할 데이터 | 정상 Window 80 |
| Test holdout | 기준을 정한 뒤 마지막에 성능을 채점할 데이터 | 유효 Window 100 |
| AutoEncoder(AE) | 입력과 비슷한 값을 복원하도록 학습한 신경망 | 6→8→3→8→6 |
| Encoder / Decoder | 입력을 압축 / 다시 복원하는 신경망 부분 | 6→3 / 3→6 |
| x, xhat | 모델 입력값 / 모델이 복원한 값 | 각각 6개의 숫자 |
| MSE | 대응하는 값의 차이를 제곱해서 평균한 값 | 작을수록 잘 복원됨 |
| Threshold(cutoff) | 경고와 정상 판정을 나누는 경계값 | TOY: 0.5, 강사 AE: 0.90363125 |
| VALID / NORMAL | 데이터 품질 통과 / 정상이라고 판단·표기 | 서로 다른 의미 |
| INSUFFICIENT_DATA | 데이터 품질 문제로 점수를 계산할 수 없는 상태 | 결측·간격 누락·시각 오류 |
| RED → GREEN | 실패를 재현한 후 최소 수정으로 통과시키는 과정 | 학생 TODO는 의도적 RED로 남음 |

## 1. GitHub 저장소를 클론하고 실행 준비하기 (20:00–20:10)

### 1-1. 명령어를 어디에 입력하나요?

Windows에서 Ubuntu(WSL2)를 실행하거나 Ubuntu 터미널을 엽니다. 화면의 끝에 달러 기호($)가 있다면 **그 뒤에** 명령을 입력합니다. 이 가이드의 코드 블록에는 프롬프트 기호를 포함하지 않았으므로 전체를 복사하시면 됩니다.

처음에 확인할 명령:

~~~bash
pwd
git --version
python3 --version
~~~

**명령어 한 줄씩 해설:** pwd는 **현재 폴더**, git --version은 Git 설치 여부, python3 --version은 Python 버전을 표시합니다. Python 3.12.x가 수업 기준입니다. 버전이나 Git 설치 문제가 있으면 아래 오류 표를 참고하세요.

**실행 전 예상 결과:** pwd는 /home/본인계정 형태, git은 git version ... 형태, Python은 Python 3.12.x 형태입니다. 실제 버전 숫자와 홈 경로는 PC마다 다릅니다.

### 1-2. 기존 파일을 지우지 않고 공개 학생 저장소 받기

아래 블록을 **처음 한 번만 전체 복사**하여 실행합니다.

~~~bash
(
  set -Eeuo pipefail
  ROOT="$HOME/axia_d11_course/axia-robot-safety-student"
  mkdir -p "$(dirname "$ROOT")"
  if [[ ! -d "$ROOT/.git" ]]; then
    git clone https://github.com/silverbjin/axia-robot-safety-student.git "$ROOT"
  fi
  cd "$ROOT"
  if [[ "$(git branch --show-current)" == main &&
        -z "$(git status --porcelain)" ]]; then
    git pull --ff-only origin main
  else
    echo "D11_STUDENT_WORKTREE_PRESERVED"
  fi
  echo "D11_STUDENT_SHA=$(git rev-parse HEAD)"
  bash block_C/scripts/block_c_once.sh --doctor
) || echo "D11_SOURCE_OR_ENV_HOLD: 위의 첫 오류를 확인하세요."
~~~

**복사한 명령의 의미:**

- 괄호 (...)는 이 명령만 잠시 독립 실행합니다. 내부에서 오류가 나도 **현재 터미널에 set -e 설정이 남지 않습니다**.
- ROOT는 학생 공개 저장소를 저장할 위치입니다. HOME은 내 홈 폴더를 뜻합니다.
- mkdir -p는 폴더가 없으면 생성합니다. **기존 파일 삭제 명령이 아닙니다.**
- git clone은 폴더가 없는 첫 실행에서만 다운로드합니다.
- cd는 이후 명령을 실행할 폴더로 이동합니다.
- git pull --ff-only는 작업 파일을 수정하지 않은 main 브랜치에서만 최신 내용을 가져옵니다.
- git rev-parse HEAD는 내가 받은 버전을 40자리 커밋 SHA로 기록합니다.
- --doctor는 실습 PC의 Python 환경을 검사합니다. **AE 학습/예측을 수행하지 않습니다.**

**예상 화면(내 PC에서 아직 실행한 결과가 아님):**

~~~text
D11_STUDENT_SHA=<학생저장소_40자리_SHA>
BLOCK_C_STUDENT_DOCTOR python=3.12.x role=student ros_required_for_unit=false gazebo_required=false
BLOCK_C_NO_GOAL_NO_CMD_VEL_NO_CERTIFIED_ESTOP
~~~

doctor가 Python 버전 오류를 출력해도 이후 **표준 Python만 이용하는 TOY 수학 실습 자체는 별개**입니다. 다만 공식 수업 환경 3.12 준비는 강사와 확인하십시오. 시스템 Python을 마음대로 바꾸지 않습니다.

### 1-3. 새 터미널을 열었다면 항상 이 위치로 이동

~~~bash
cd "$HOME/axia_d11_course/axia-robot-safety-student"
mkdir -p "$HOME/axia_d11_course/student_evidence"
git rev-parse HEAD
python3 block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures
~~~

**실행 전 예상 결과:** C01_FIXTURE_CONTRACT_PASS, rows=4599, traces=46, quality_traces=4. 이 네 가지가 기준과 다르면 원본을 고치지 말고 최초 오류 메시지와 Git SHA를 기록하세요. generator.py의 --check는 **이미 있는 원본 데이터의 무결성 검사**이며 새 데이터를 생성하지 않습니다.

**1단계 완료 체크:** 원본 PASS, SHA 확보, 결과 저장 폴더 준비. 단, 학생 PC의 검증 수준은 실제 stdout를 확인한 경우에만 PASS입니다.

## 2. Sample → Trace → Window → 6특징 직접 확인 (20:10–20:20)

### 2-1. 왜 원본을 Window로 바꾸나요?

센서 신호는 매 순간 숫자가 바뀝니다. 한 Sample의 전류값만 보면 순간적인 흔들림인지 지속된 변화인지 판단하기 어렵습니다. 그래서 **같은 시나리오의 연속 Sample 10개를 하나로 묶어** 평균과 표준편차를 계산합니다.

~~~text
TST_A_00 (한 Trace = 한 시나리오)
 ├─ Sample  0~ 9 → Window W0 → 6특징
 ├─ Sample 10~19 → Window W1 → 6특징
 ├─ Sample 20~29 → Window W2 → 6특징
 ...
 └─ Sample 90~99 → Window W9 → 6특징

합성 10Hz = 0.1초마다 Sample 1개
→ 10개를 묶으면 Window 하나가 나타내는 길이는 약 1초
→ Train/Valid/Test는 Window 생성 전부터 Trace 단위로 분리
~~~

Trace를 따로 구분하는 이유는 **같은 시험의 Window가 Train과 Test 양쪽에 섞이는 누수**를 막기 위해서입니다. 원래 4,599 Raw는 Train 2,400/24 Trace, Valid 800/8 Trace, Test 1,399/14 Trace입니다. 한 품질 오류 Trace의 Sample이 의도적으로 1행 빠져 4,600이 아닌 4,599입니다.

### 2-2. 실제 CSV 행 수를 Python으로 읽어 봅니다

**입력할 명령:**

~~~bash
cd "$HOME/axia_d11_course/axia-robot-safety-student"
python3 - <<'PY'
import csv
from pathlib import Path
root = Path("block_C/fixtures")
for name in ("normal_train.csv", "normal_valid.csv", "test_mixed.csv"):
    with (root / name).open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    traces = {row["trace_id"] for row in rows}
    print(name, "raw", len(rows), "traces", len(traces))
PY
~~~

**코드 해설:** import csv는 CSV 읽기, Path는 폴더 경로 다루기, for는 파일 3개를 차례로 검사하는 반복문입니다. DictReader는 CSV의 첫 줄을 열 이름으로 읽어 각 행을 사전(dict)처럼 만듭니다. len(rows)는 전체 행 수, 중괄호 {...}는 중복 없이 Trace ID만 모은 집합입니다.

**예상 출력(고정 합성 원본 기준):**

~~~text
normal_train.csv raw 2400 traces 24
normal_valid.csv raw 800 traces 8
test_mixed.csv raw 1399 traces 14
~~~

### 2-3. 실제 Train Trace 10개 Sample로 평균·표준편차 구하기

다음 코드는 추가 패키지를 설치하지 않고 Python 표준 statistics 모듈로 계산합니다. **주의:** 이것은 특징 추출 원리를 관찰하는 연습이며 D09 정답 파이프라인 전체가 아닙니다.

~~~bash
python3 - <<'PY'
import csv
from pathlib import Path
from statistics import fmean, pstdev

path = Path("block_C/fixtures/normal_train.csv")
with path.open(encoding="utf-8", newline="") as file:
    rows = list(csv.DictReader(file))

window = [row for row in rows
          if row["trace_id"] == "TRN_00"
          and 0 <= int(row["sample_idx"]) < 10]
print("TRACE=TRN_00 WINDOW=W0 SAMPLES=", len(window))

for signal in ("current_a", "torque_nm", "accel_mps2"):
    values = [float(row[signal]) for row in window]
    print(signal, "mean=", f"{fmean(values):.6f}",
          "std=", f"{pstdev(values):.6f}")
PY
~~~

**코드 한 줄씩 해설:**

- window = [...]은 TRN_00에서 Sample 번호 0~9만 고르는 **목록(list)**입니다.
- values = [...]는 지정한 한 신호의 10개 숫자를 모읍니다.
- fmean(values)는 평균, pstdev(values)는 모집단 표준편차입니다. 표준편차는 **값이 평균 주변에서 얼마나 흔들렸는지**를 나타냅니다.
- **.6f**는 소수점 아래 여섯 자리로 출력한다는 뜻입니다.
- 신호 3종 × 평균/표준편차 2종 = **6개 모델 특징**입니다.

**실행 전 예상 결과:** TRACE=TRN_00 WINDOW=W0 SAMPLES= 10 및 current_a, torque_nm, accel_mps2의 mean/std가 각각 숫자로 출력됩니다. 여기서 개별 실숫자는 PC가 아니라 동일 고정 fixture로 계산되므로 같아야 하지만, 문서에서는 계산하지 않은 숫자를 임의로 적지 않습니다.

**초심자 질문:** 단일 Sample 1개로 표준편차를 구하면 왜 많은 정보를 잃을까요? → 10개 Sample 사이의 변동을 보지 못하기 때문입니다.

### 2-4. 학습에 들어가는 6개 값과 제외할 값

- 모델 6특징 순서: current_a_mean, current_a_std, torque_nm_mean, torque_nm_std, accel_mps2_mean, accel_mps2_std.
- 모델에 넣지 않는 열: trace_id, window_id, timestamp_ns, truth_label, status, quality_reason. 이 열들은 **출처·순서·품질·평가**를 위해 남겨 둡니다.
- Train 240 VALID / Valid 80 VALID / Test 100 VALID = **유효 Window 420개**.
- 품질 문제 Test Trace 4개는 각각 상태행 1개를 남깁니다. 유효 Window 420 + 상태행 4 = 전체 특징·상태행 424개.
- **VALID는 측정 데이터의 품질 통과를 뜻하며 NORMAL이라는 정답/판정이 아닙니다.**

## 3. 정상상태 재구성 원리 이해·강사 시연 관찰 (20:20–20:30)

### 3-1. AutoEncoder는 정상 데이터를 어떻게 학습하나요?

~~~text
(정상 Train 240개 Window)
        ↓ train-only StandardScaler.fit
   정규화된 입력 x: 6개 숫자
        ↓ Linear(6→8), Tanh
        ↓ Linear(8→3), Tanh
   잠재 표현 z: 3개 숫자  [Encoder가 압축]
        ↓ Linear(3→8), Tanh
        ↓ Linear(8→6)
   복원값 xhat: 6개 숫자 [Decoder가 복원]
        ↓
   차이: x - xhat (6개)
        ↓
   MSE = 여섯 차이 제곱의 평균
        ↓
   정상 Valid로 정한 cutoff와 비교
~~~

**핵심 의미:** 정상 패턴을 잘 복원하도록 학습했다면 비슷한 정상 입력의 MSE는 상대적으로 작을 수 있습니다. 익숙하지 않은 패턴은 복원이 어려워 MSE가 커질 수 있지만, **높은 MSE = 특정 고장 원인 확정**은 아닙니다. 가운데 3차원 잠재표현은 고장 클래스 세 개가 아닙니다.

**StandardScaler가 왜 필요할까요?** 전류(A), 토크(N·m), 가속도(m/s²)의 숫자 범위가 달라 큰 단위/크기의 열이 오차 계산을 좌우하지 않도록 Train에서 정한 평균과 표준편차로 정규화합니다. 평균과 표준편차 자체도 학습된 상태라 Train에서만 fit해야 합니다.

### 3-2. 강사 화면에서 질문 3개에 답하세요

1. 지금 보여주는 모델은 GPU가 필요한가요? → **아니요. 기존 강사 참조 구현은 CPU입니다.**
2. 강사가 checkpoint 파일을 로드했다면 그때 다시 학습한 것인가요? → **아니요. 저장된 가중치로 추론합니다.**
3. 강사가 보여준 AE threshold=0.90363125를 내가 실행한 수학 예제의 threshold=0.5와 같다고 볼 수 있나요? → **아니요. 실제 AE는 정상 Valid 점수로 정한 값이고 TOY는 수작업 예시값입니다.**

강사 기준 합성 Test 결과 TP18/FP4/FN0/TN78은 **INSTRUCTOR_REFERENCE**입니다. 내 PC의 TOY 출력이나 실물 로봇의 검증값이라고 보고하지 않습니다.

## 4. Python 기초·학생 TODO 이해 (20:30–20:45)

### 4-1. 파일의 기본 구조부터 읽어봅니다

~~~bash
cd "$HOME/axia_d11_course/axia-robot-safety-student"
sed -n '1,90p' block_C/day11/student_ae_todo.py
sed -n '1,120p' block_C/day11/mse_toy_practice.py
~~~

**해설:** sed -n '1,90p'는 파일의 1~90번째 줄을 **화면에 출력**만 하며 수정하지 않습니다. 파일이 어떤 위치에 있는지, 함수 이름과 입력값을 먼저 보는 과정입니다.

student_ae_todo.py에는 fit_evaluate_ae(fixture_dir: Path, output_dir: Path) -> dict 형태의 미구현 과제가 있습니다. Path는 폴더·파일 경로, -> dict는 결과를 사전 형태로 반환한다는 표시입니다. **raise NotImplementedError**는 아직 구현하지 않았다는 뜻으로, 학생용 정상 **EXPECTED_RED**입니다.

### 4-2. 미구현을 '오류가 난 코드'와 혼동하지 마세요

pytest가 이미 설치된 경우에 한해 다음 선택 명령으로 출발점을 확인합니다.

~~~bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  block_C/tests/test_student_task_expected_red.py -k d11
~~~

**예상 실패 메시지:** NotImplementedError: D11 TODO not implemented. 이 단계는 의도된 RED이므로 **학생 실습의 필수 MSE 과제는 계속 진행**합니다. pytest가 설치되지 않아 No module named pytest가 나오면 선택 RED 확인은 생략해도 됩니다.

**심화로 전체 AE를 완성하려는 학생**은 features_train.csv, features_valid.csv, features_test.csv가 있는 D09 특징 디렉터리를 준비해야 합니다. 공개 저장소의 D09 TODO도 미완성이므로 파일 3종이 자동 생성된다고 가정하면 안 됩니다. 직접 D09를 완성했거나 강사가 제공한 **특징 CSV 3종만** 활용합니다. 강사 정답 Python/비공개 checkpoint를 복사하지 않습니다.

### 4-3. 실제 실습 코드 핵심 4줄 이해

파일 mse_toy_practice.py의 핵심은 다음과 같습니다.

~~~python
def mse(x, x_hat):
    if len(x) != 6 or len(x_hat) != 6:
        raise ValueError("D11_TOY_FEATURE_COUNT_MUST_BE_6")
    return sum((a - b) ** 2 for a, b in zip(x, x_hat)) / 6
~~~

**코드 한 줄씩:**

- def mse(...): 이름이 mse인 함수를 정의합니다. x는 입력 6개, x_hat는 복원 6개입니다.
- len(...): 목록 길이. 6개가 아니라면 값을 잘못 넣었다는 **ValueError**를 발생시킵니다.
- zip(x, x_hat): 입력 첫 번째와 복원 첫 번째, 두 번째와 두 번째처럼 **같은 위치끼리 짝**을 만듭니다.
- a - b: 각 짝의 차이(잔차).
- ** 2: 차이를 제곱. 음수 차이도 양수 오차 크기로 바뀝니다.
- sum(...)/6: 여섯 제곱오차의 평균, 즉 **MSE**입니다.
- return: 계산 결과를 함수 밖으로 돌려줍니다.

**왜 제곱할까요?** +1과 -1의 차이를 그대로 더하면 서로 상쇄되어 오차가 없는 것처럼 보일 수 있기 때문입니다.

## 5. 재구성 MSE를 직접 실행·해석 (20:45–21:00)

### 5-1. 수업용 MSE 프로그램 실행

~~~bash
cd "$HOME/axia_d11_course/axia-robot-safety-student"
mkdir -p "$HOME/axia_d11_course/student_evidence"
python3 block_C/day11/mse_toy_practice.py \
  | tee "$HOME/axia_d11_course/student_evidence/mse_practice.log"
~~~

**명령어 한 줄씩:** python3는 프로그램 실행, 파이프(|)는 화면 출력을 다음 명령으로 전달, tee는 결과를 **화면에도 보이고 mse_practice.log 파일에도 저장**합니다. 실행 증거를 남기는 용도이며 소스 코드는 변경하지 않습니다.

### 실행 전 예상 결과

~~~text
D11_TOY_DEMO_BEGIN source=HAND_CRAFTED_NOT_MODEL_PREDICTION
D11_TOY case=normal mse=0.010000 threshold=0.500000 prediction=NORMAL
D11_TOY case=anomaly mse=1.000000 threshold=0.500000 prediction=WARNING
D11_TOY case=missing mse=UNSCORED threshold=0.500000 prediction=INSUFFICIENT_DATA
D11_TOY_DEMO_PASS only_classroom_math=true model_training=false robot_control=false
~~~

**실제 출력과 예상 출력:** 위는 코드로 결정적으로 계산 가능한 기준 패턴입니다. 학생 PC에서 나온 실제 stdout은 mse_practice.log에 들어갑니다. **코드가 PASS했다고 해서 학습된 AutoEncoder가 동작한 것은 아닙니다.** TOY는 손으로 정한 숫자(학습된 가중치 없음)입니다.

### 5-2. 연습문제 A — 직접 손으로 계산하기

TOY_THRESHOLD=0.5, 입력 x=[0,0,0,0,0,0]이라고 하겠습니다.

| 사례 | 복원 xhat(6개) | 차이 제곱 | MSE | 판정 |
|---|---|---|---|---|
| 정상 예 | [0.1, -0.1, 0.1, -0.1, 0.1, -0.1] | 0.01×6 | 0.01 | NORMAL |
| 이상 후보 예 | [1, 1, 1, 1, 1, 1] | 1×6 | 1.0 | WARNING |
| 데이터 부족 예 | 품질이 VALID가 아님 | 계산 생략 | UNSCORED | INSUFFICIENT_DATA |

**힌트:** (0-0.1)² = 0.01, (0-1)² = 1입니다. 여섯 개를 더하고 6으로 나누면 됩니다.

**질문:** 이상 후보 예의 MSE가 크다고 **실제 모터 고장 종류**까지 알 수 있나요? → 아니요. 복원하기 어렵다는 뜻이지 고장 원인 증명은 아닙니다.

### 5-3. Python으로 결과를 한 번 더 확인

~~~bash
python3 - <<'PY'
from block_C.day11.mse_toy_practice import mse, decide
x = [0.0] * 6
print("NORMAL_MSE=", mse(x, [0.1, -0.1] * 3))
print("ANOMALY_MSE=", mse(x, [1.0] * 6))
print("TOY_DECISION=", decide("VALID", x, [1.0] * 6)[0])
print("QUALITY_DECISION=", decide("MISSING_VALUE", x, [1.0] * 6)[0])
PY
~~~

**예상 결과:** NORMAL_MSE=는 0.010000...에 가까운 실수(부동소수점 표현 차이 허용), ANOMALY_MSE=1.0, TOY_DECISION=WARNING, QUALITY_DECISION=INSUFFICIENT_DATA입니다. 마지막은 입력 숫자가 크더라도 **품질이 나쁘므로 모델 점수를 내지 않는다**는 규칙을 보여줍니다.

## 6. Valid-only 임계값·품질 오류 판정 (21:00–21:15)

### 6-1. Train, Valid, Test holdout을 왜 나눌까요?

~~~text
Train 240 정상 Window
   ├ StandardScaler.fit : 정규화 평균/표준편차 학습
   └ AutoEncoder 학습   : 정상 x를 xhat로 복원

Valid 80 정상 Window
   └ 같은 scaler로 변환 → 복원 MSE → 95% 분위수 threshold **고정**

Test 100 VALID Window
   └ 같은 scaler/AE/threshold 사용 → 최종 NORMAL 또는 WARNING 평가

품질 불량 Test 4건
   └ 점수 없음 → INSUFFICIENT_DATA
~~~

**Train-only**는 학습과 스케일러 적합을 정상 Train에 한정한다는 뜻입니다. **Valid-only**는 경고 임계값을 정상 Valid에서만 정한다는 뜻입니다. **Test holdout**은 최종 시험지를 미리 보지 않는다는 뜻입니다. Test 성능을 보고 threshold를 올리거나 낮추면 평가를 속일 수 있습니다.

기존 강사 모델 기준 정상 Valid95%의 cutoff는 0.90363125(**INSTRUCTOR_REFERENCE**). 현재 공개 TOY의 cutoff=0.5는 손으로 정한 수학 예시이므로 두 값을 직접 혼동해서는 안 됩니다.

### 6-2. 연습문제 B — 임계값과 품질 조건을 직접 판단

TOY threshold=0.5이며 조건은 score가 **0.5보다 클 때(>)** WARNING입니다.

| quality | score | 학생이 먼저 답할 것 |
|---|---:|---|
| VALID | 0.10 | NORMAL / WARNING / INSUFFICIENT_DATA? |
| VALID | 0.50 | 정상·경고 중 어느 쪽? |
| VALID | 0.51 | 정상·경고 중 어느 쪽? |
| MISSING_VALUE | 계산 불가능 | 점수 0으로 만들까요? |
| STAMP_REGRESSION | 계산 불가능 | NORMAL 처리해도 될까요? |

**힌트:** 품질을 먼저 확인하고, VALID일 때에만 숫자를 threshold와 비교합니다.

**정답/해설:** 0.10→NORMAL, 0.50→NORMAL(같으면 초과가 아님), 0.51→WARNING, MISSING_VALUE→INSUFFICIENT_DATA, STAMP_REGRESSION→INSUFFICIENT_DATA. 품질 불량의 score는 0이 아닌 **공란/UNSCORED**입니다.

### 6-3. 왜 품질 오류 4건은 NORMAL로 계산하지 않을까요?

Test의 품질 문제는 MISSING_VALUE(토크 결측), SAMPLE_GAP(샘플 번호 누락), STAMP_REGRESSION(시간 역행), TIMESTAMP_DRIFT(주기 오차)입니다. 잘못된 입력은 AE의 복원 오차를 정상적으로 해석할 수 없으므로 점수를 계산하지 않습니다. 이 4개 상태행은 Test VALID 100의 혼동행렬 분모에도 들어가지 않습니다.

실제 원본을 관찰하는 명령(원본 수정 없음):

~~~bash
python3 - <<'PY'
import csv
from collections import defaultdict
from pathlib import Path
p=Path("block_C/fixtures/test_mixed.csv")
with p.open(encoding="utf-8",newline="") as f:
    rows=list(csv.DictReader(f))
by_trace=defaultdict(list)
for row in rows:
    by_trace[row["trace_id"]].append(row)
for trace in ("TST_Q_00","TST_Q_01","TST_Q_02","TST_Q_03"):
    part=by_trace[trace]
    indices={int(row["sample_idx"]) for row in part}
    print(trace,"rows=",len(part),"sample55_exists=",55 in indices)
PY
~~~

**예상:** TST_Q_00 / Q_02 / Q_03는 rows=100, TST_Q_01만 rows=99 및 sample55_exists=False입니다. 데이터 결측·시간 역행은 단순 행 수로 구분되지 않으므로 추가 품질 검사 필요. **품질 오류를 0으로 채워 학습/정상 판정하는 것은 금지**입니다.

## 7. D10 IF와 D11 AE를 같은 기준으로 비교 (21:15–21:30)

### 7-1. 먼저 TP·FP·FN·TN을 생활 속 용어로 바꿔 보세요

- TP(참양성): 이상 정답인데 경고한 것 — **제대로 경고**
- FP(거짓양성): 정상 정답인데 경고한 것 — **오경보**
- FN(거짓음성): 이상 정답인데 정상으로 지나간 것 — **놓친 이상**
- TN(참음성): 정상 정답이고 정상으로 판단한 것 — **제대로 통과**

**Precision(정밀도)** = TP/(TP+FP) : 내가 울린 경고 중 정말 이상이었던 비율.  
**Recall(재현율)** = TP/(TP+FN) : 실제 이상 중 경고로 잡은 비율.

### 7-2. 강사 기준 합성 결과를 직접 계산합니다

| 기존 강사 참조값 | TP | FP | FN | TN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| D10 Isolation Forest | 1 | 2 | 17 | 80 | 1/3 = 33.3% | 1/18 = 5.6% |
| D11 AutoEncoder | 18 | 4 | 0 | 78 | 18/22 = 81.8% | 18/18 = 100% |

아래 코드로 수학을 검산합니다. **참조 수치를 입력해 계산할 뿐 실제 모델을 실행하지 않습니다.**

~~~bash
python3 - <<'PY'
for name, tp, fp, fn, tn in (("IF",1,2,17,80),("AE",18,4,0,78)):
    precision=tp/(tp+fp)
    recall=tp/(tp+fn)
    print(name, "total=",tp+fp+fn+tn,
          "precision=",f"{precision:.3f}",
          "recall=",f"{recall:.3f}")
PY
~~~

**예상 출력:**

~~~text
IF total= 100 precision= 0.333 recall= 0.056
AE total= 100 precision= 0.818 recall= 1.000
~~~

**질문 1:** AE가 이 Test에서 이상 18개를 모두 잡았어도 추가 확인해야 할 점은? → FP 4개를 발생시켰고, 작은 합성 Test만의 결과라는 점입니다.  
**질문 2:** AE MSE cutoff 0.90363125가 IF cutoff 0.10199750보다 크니 AE가 더 엄격한가요? → 아니요. IF는 -decision_function, AE는 MSE이므로 척도가 달라 직접 비교하지 않습니다.  
**질문 3:** 실제 산업 현장이나 인증된 E-Stop에도 같은 Recall이 보장되나요? → 아니요.

## 8. 실무에서 겪는 문제 세 가지 (21:30–21:50)

**A. 정상 부하가 바뀌면서 오경보 증가**  
예: 이동 로봇이 평지에서 경사면으로 옮겨가면 가상 전류·토크 패턴이 달라질 수 있습니다. **처음 볼 것:** 해당 Trace/window의 값과 정상 Train 분포, 운전 조건. **잘못된 해결:** Test에 맞춰 scaler나 threshold를 몰래 다시 fit. **올바른 접근:** 정상 운전 조건이 학습 범위에 포함됐는지 기록하고 별도 검증을 설계합니다. 이 수업에서는 모델 재학습으로 확장하지 않습니다.

**B. 센서값 누락으로 이상탐지 불가능**  
예: torque_nm 열이 비었거나 sample_idx=55가 누락되었습니다. **처음 볼 것:** trace_id, sample_idx, timestamp_ns, quality_reason. **잘못된 해결:** 빈 값을 0으로 채워 NORMAL 처리. **올바른 접근:** INSUFFICIENT_DATA로 분리하고 센서/로그 품질 문제를 조사합니다.

**C. 정상 윈도우도 WARNING(오탐)**  
기존 AE 참조에서는 TST_N_02와 TST_N_03 등을 포함한 FP가 있습니다. **처음 볼 것:** 그 window의 truth_label=0, risk_score, threshold, 입력·복원값, source SHA. **잘못된 해결:** 교육용 WARNING을 실제 로봇 Stop, SW Stop이나 **인증된 E-Stop**으로 서술. **올바른 접근:** 비인증 분석 결과로 보고하며 자동 정지 제어를 추가하지 않습니다.

**작성법 예시(정답 문장 샘플):** “TST_Q_01에서 원본 sample_idx 55 누락을 관찰했습니다. 모델 점수를 0으로 채우지 않고 INSUFFICIENT_DATA로 분리해야 합니다. 실제 제어권은 없습니다.”

## 9. 스스로 점검하고 결과 제출하기 (21:50–22:00)

### 9-1. 스스로 점검: 7가지 질문

1. Trace와 Window를 왜 나누나요? → **Trace가 시나리오 경계, Window가 한 시나리오 안의 부분**이기 때문입니다.
2. 6개 특징은 어디서 왔나요? → **3가지 센서 신호의 평균/모집단 표준편차**입니다.
3. AutoEncoder는 무엇을 복원하나요? → **정상 Train에서 학습한 정규화 6특징 입력 자체**입니다.
4. MSE는 어떤 숫자인가요? → **입력 x와 복원 xhat의 여섯 차이 제곱 평균**입니다.
5. 모델 학습/threshold/Test는 어디서 하나요? → **Train / 정상 Valid / Test holdout**입니다.
6. 결측 4개는 정상인가요? → **아니요. 점수 없는 INSUFFICIENT_DATA**입니다.
7. 교육용 AI WARNING은 안전 정지인가요? → **아니요. SW Stop·인증 E-Stop 모두 아닙니다.**

### 9-2. 제출용 보고서 생성

아래는 문서 파일의 **빈 양식만 생성**합니다. 꼭 자신의 말로 각 항목을 채웁니다.

~~~bash
cat > "$HOME/axia_d11_course/student_evidence/d11_report.md" <<'EOF'
# AXIA D11 실습 보고서
- 학생(또는 실습조):
- Python 버전 / 공개 학생 저장소 Git SHA:
- 실제 실행한 명령과 stdout (mse_practice.log 위치):
- 목표 1: AutoEncoder 정상 재구성 과정 6→8→3→8→6을 설명하세요.
- 목표 1: 전류·토크·가속도 mean/std가 6개 특징인 이유를 쓰세요.
- 목표 2: TOY NORMAL MSE=0.01 계산 과정을 식으로 쓰세요.
- 목표 2: TOY WARNING MSE=1.0과 threshold=0.5 판정 이유를 쓰세요.
- Train-only / Valid-only / Test holdout을 각각 한 문장으로 설명하세요.
- 품질 오류 4건을 INSUFFICIENT_DATA로 남기는 이유를 쓰세요.
- 기존 INSTRUCTOR_REFERENCE: IF 1/2/17/80, AE 18/4/0/78을 비교하세요.
- 실무 사건 A/B/C 중 하나: 관찰·첫 증거·금지 행동·올바른 접근:
- 실제 실행과 기존 참조 결과 구분:
EOF
echo "D11_STUDENT_REPORT_CREATED=$HOME/axia_d11_course/student_evidence/d11_report.md"
~~~

**제출 파일:** student_evidence/mse_practice.log와 student_evidence/d11_report.md. 터미널에서 파일 내용을 확인하려면 다음을 입력합니다.

~~~bash
cat "$HOME/axia_d11_course/student_evidence/mse_practice.log"
cat "$HOME/axia_d11_course/student_evidence/d11_report.md"
~~~

### 채점 루브릭 (100점)

| 항목 | 점수 | 최소 충족 조건 |
|---|---:|---|
| 정상 재구성 원리 이해 | 25 | 6→8→3→8→6, x와 xhat, 정상 Train의 의미 설명 |
| 재구성 MSE 손계산과 Python 실행 | 20 | 0.01/1.0/UNSCORED, 판정 기준 설명 |
| train-only / Valid-only / Test holdout | 20 | 누수 없는 역할 설명 |
| 센서 품질 문제 4건 | 15 | INSUFFICIENT_DATA, 점수 공란 구분 |
| IF와 AE 비교 | 10 | TP/FP/FN/TN·precision/recall 비교 |
| 실무 사례와 검증 경계 | 10 | 최초 증거·금지 조치·비인증 WARNING |
| **전체** | **100** | |

**초심자 필수 과제는 1~9절을 수행하는 것**입니다. PyTorch 전체 네트워크·가중치 학습·학생 TODO 완성은 추가 학습이며, 이 120분 필수 통과 조건이 아닙니다.

## 10. 처음부터 고치는 오류 복구표 (실패한 지점만 확인)

| 처음 나타난 메시지 | 무엇이 잘못됐나요? | 다음 조치 |
|---|---|---|
| git: command not found | Git 미설치 | Ubuntu에서 Git 설치·버전 확인 후 1절 재실행 |
| fatal: destination path ... already exists | 같은 위치에 폴더 존재 | 기존 폴더가 Git clone인지 확인, 강제 삭제 금지 |
| Repository not found / 인터넷 오류 | GitHub 공개 URL·네트워크 문제 | 공개 주소 확인. 강사 비공개 저장소 클론하지 않음 |
| cd: No such file or directory | 명령을 실행 중인 폴더가 다름 | 1-3절 절대경로와 pwd 확인 |
| BLOCK_C_ENV_DIFF_BLOCKED expected=3.12 | Python 3.12 환경이 아님 | 시스템 Python 임의 교체 금지, 강사에게 점검 요청 |
| No module named pytest | 선택 RED 확인용 패키지 미설치 | 선택 단계만 생략, MSE는 표준 Python으로 진행 |
| NotImplementedError: D11 TODO not implemented | 학생 TODO의 의도적 EXPECTED_RED | 정상 출발점, 필수 MSE 계산으로 진행 |
| No module named torch | AE 학습 환경 없음 | **TOY 실습에는 torch가 필요 없음** |
| ValueError: D11_TOY_FEATURE_COUNT_MUST_BE_6 | 입력/복원값 길이가 6이 아님 | 목록의 요소 수 확인 |
| mse 값이 예상과 다름 | 입력/복원값/threshold 변경 가능성 | 원본 파일 SHA, 각 숫자, 실제 stdout 확인 |
| INSUFFICIENT_DATA | 결측·시간 오류 등 품질 불량 | NORMAL=0으로 바꾸지 말고 최초 품질 위반 조사 |
| 수업 중 ROS/Gazebo/Goal 관련 요청 | D11 수업 범위를 벗어남 | 실물 제어 없이 오프라인 Python 학습만 수행 |

**가장 중요한 복구 원칙:** 마지막에 뜬 오류 메시지만 보고 같은 명령을 반복하지 마세요. 먼저 어떤 단계(클론/환경/원본/수학/품질)에서 **최초 실패**했는지 확인한 뒤 해당 단계만 복구합니다.

## 11. 공식 자료와 더 공부할 거리

- [PyTorch nn.Sequential](https://docs.pytorch.org/docs/stable/generated/torch.nn.Sequential.html): 여러 신경망 층을 순서대로 연결하는 방법.
- [PyTorch MSELoss](https://docs.pytorch.org/docs/stable/generated/torch.nn.MSELoss.html): 입력·출력 차이의 평균제곱오차 정의.
- [PyTorch 최적화/학습 과정 튜토리얼](https://docs.pytorch.org/tutorials/beginner/basics/optimization_tutorial.html): zero_grad, backward, step이 뜻하는 것.
- [scikit-learn 전처리·데이터 누수 공식 설명](https://scikit-learn.org/1.8/common_pitfalls.html): train에만 fit하고 test에는 transform하는 이유.
- [학생 데모 관찰 가이드](STUDENT_DEMO_GUIDE_KO.md) · [학생 TODO](student_ae_todo.py) · [MSE 수학 연습 코드](mse_toy_practice.py).

**검증 경계:** 공개 CSV 검사와 TOY 계산의 성공은 공개 Python L0 수업 성취에 한정됩니다. 강사 비공개 AE checkpoint 실행, 학생의 전체 AE TODO 완성, 학생 PC WSL2 최종 PASS, ROS/Gazebo/실물 로봇 안전정지 PASS를 뜻하지 않습니다.


## 보충 활동 — D11 12분 몰입형 라이브 Replay

기존 120분 실습의 강사 시연·모델 비교 구간에서 [학생용 Replay 예측 활동지](STUDENT_LIVE_REPLAY_ACTIVITY_GUIDE_KO.md)를 함께 사용하십시오. 학생은 화면에서 정답이 공개되기 전에 IF/AE 경고 위치와 품질 상태를 먼저 예측하고 공개된 후 판단 차이를 보고서에 한 문단으로 작성합니다. **새 모델 훈련·강사 비공개 checkpoint 다운로드·추가 필수 파일 제출은 요구하지 않습니다.** 12분은 기존 120분에 포함되며 추가 수업시간이 아닙니다.
