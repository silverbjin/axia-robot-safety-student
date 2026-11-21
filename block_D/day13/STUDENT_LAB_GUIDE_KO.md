# AXIA D13 — 초심자부터 따라 하는 Reachability·시간 동기 충돌 판정 실습서 (개정 v3)

> **오늘의 질문:** 로봇과 사람이 같은 복도를 지나가는데, 두 경로가 교차하면 반드시 충돌할까요? 두 사람이 같은 자리에 **같은 시간에** 있었는지부터 확인해야 합니다.

**수업:** 2026-11-25(수) 19:00–23:00 · 220분 학습 + 20분 휴식  
**준비물:** Ubuntu 24.04 또는 WSL2 Ubuntu 24.04, 터미널, Git, Python 3.12(표준 라이브러리). 추가 pip 패키지·ROS 2·Gazebo가 필요하지 않습니다.  
**학습목표:** ① Reachability의 뜻과 이번 축약 모델의 한계 설명 ② 16개 시점의 사람 예측 위치와 두 원의 거리 계산 ③ 데이터 검증을 바탕으로 P/N/U를 분류 ④ 자신의 TODO만 완성해 10개 공개 테스트 GREEN 달성 ⑤ 실제 로봇 안전제어와 교육용 예측의 경계 설명.

**가장 중요한 약속:** 이번 코드는 **합성 파일을 읽는 오프라인 교육 실습**입니다. 실제 사람 검출, Nav2 Goal, /cmd_vel, Collision Monitor, 로봇 SW STOP, 인증 하드웨어 E-Stop을 실행하지 않습니다. 이 수업의 N은 '이번 단순 모델에서 겹치지 않음'이지 '실제 주행해도 안전함'이 아닙니다.

## 0. 첫 5분 — 전체 실습 흐름 보기

```text
① 저장소 클론
       ↓
② CSV(로봇 경로)와 JSON(사람·실험 조건) 읽기
       ↓
③ 처음 공개 테스트 → 의도된 RED 두 건 관찰
       ↓
④ TODO 4단계 구현(오직 reachability_student.py 수정)
       ↓
⑤ 공개 10개 테스트와 8사례 CLI → GREEN 확인
       ↓
⑥ HTML 시간 슬라이더로 P/N 비교 + U 사례 분석
       ↓
⑦ 워크시트 · 코드 · 실행 로그 제출
```

| 시간 | 강의·실습 | 내가 남길 증거 |
|---|---|---|
| 19:00–19:30 | 복도 이야기, P/N/U, 시작 확인 | 개념 답변 |
| 19:30–20:10 | CSV/JSON·16시점·거리 계산·함수 연결 | 손계산 표 |
| 20:10–20:20 | 휴식 | |
| 20:20–21:20 | 최초 RED → TODO 작성 → 테스트 반복 | RED와 GREEN 로그 |
| 21:20–21:30 | 휴식 | |
| 21:30–22:30 | 8사례 실행·HTML 슬라이더·U 반례 | JSON·화면/설명 |
| 22:30–23:00 | 안전 한계·발표·제출 | 워크시트 |

## 1. 초심자 용어 사전 — 이 용어만 알고 시작하세요

| 용어 | 쉽게 이해하기 | 오늘 나오는 곳 |
|---|---|---|
| **터미널(Terminal)** | 컴퓨터에 글자로 명령을 내리는 창 | bash 명령 입력 |
| **CLI** | 마우스가 아닌 명령줄로 프로그램을 실행하는 방식 | `python3 ... --out ...` |
| **리포지토리(Repository)** | 코드·문서·테스트가 같이 들어 있는 저장소 | 학생 GitHub |
| **clone** | 원격 저장소를 내 컴퓨터로 복사 | `git clone` |
| **branch/main** | 저장소의 작업 흐름; `main`은 배포 기준 브랜치 | `--branch main` |
| **CSV** | 쉼표로 열을 구분한 표 파일 | 시간·로봇 위치 16행 |
| **JSON** | 중괄호와 이름/값으로 표현하는 구조화 데이터 | 사례·사람 관측값 8개 |
| **Python 함수** | 입력을 받아 처리하고 값을 돌려주는 이름 붙은 코드 | `load_cases()` 등 |
| **매개변수/인수** | 함수가 받는 값/호출할 때 전달하는 실제 값 | `now_sec=10.1` |
| **키워드 전용 인수** | 함수 선언에서 별표 `*` 뒤에 있으므로 이름을 붙여 전달해야 하는 인수 | `*, now_sec` |
| **list** | 순서가 있는 여러 값의 묶음; 첫 번째 인덱스는 0 | 로봇 경로 16개 |
| **dict** | `{"x": 2.1}`처럼 이름(key)으로 값을 찾는 자료구조 | 로봇 점·사람 데이터 |
| **float** | 소수점이 있는 수를 표현하는 Python 형식 | 10.1, 0.2 |
| **`math.hypot(a,b)`** | 두 축의 차이에서 직선거리 `sqrt(a²+b²)` 계산 | 두 점유 원 중심 거리 |
| **return** | 함수가 결과를 호출한 쪽으로 돌려줌 | `"P"`/`"N"`/`"U"` |
| **fixture** | 테스트 결과를 예상할 수 있도록 만든 예제 입력 | 합성 8개 사례 |
| **unittest** | 코드의 기대 결과와 실제 결과가 같은지 자동 확인 | 공개 10개 테스트 |
| **assertion** | '이 결과가 반드시 맞아야 한다'라는 검사 문장 | `assertEqual` |
| **RED/GREEN** | 테스트 실패/성공으로 구현 과정을 추적 | 의도된 P/N 2 FAIL → 10 PASS |
| **Exit code** | 명령 실행 후 프로그램이 남긴 숫자 상태 | 0 성공, D13 초기 runner 2 |

**초심자 체크포인트 1:** 아래 세 가지를 말해 보세요. (a) CSV는 로봇을, JSON은 사람과 사례를 설명하는 이유 (b) 함수가 return하는 값의 뜻 (c) `main` 브랜치를 클론하는 이유.

## 2. 환경 확인과 새 폴더로 클론하기 — 한 줄씩 입력

**주의:** 터미널 프롬프트 `user@computer:~$`는 입력하지 않습니다. 복사할 부분은 코드 블록 안의 명령뿐입니다. `\`는 다음 줄까지 이어지는 줄바꿈 표기입니다.

```bash
cd ~
pwd
git --version
python3 --version
git clone --branch main --depth 1 \
  https://github.com/silverbjin/axia-robot-safety-student.git \
  axia-d13-student
cd ~/axia-d13-student
pwd
git rev-parse HEAD
ls block_D/day13
```

**각 명령 의미와 확인:** `cd ~`는 홈 폴더로 이동, `pwd`는 현재 폴더 출력, `git --version`과 `python3 --version`은 설치 확인, `git clone`은 공개 저장소 복사, `cd`는 실습 폴더로 이동, `git rev-parse HEAD`는 내가 복사한 버전의 정확한 commit SHA 출력, `ls`는 실습 파일 확인입니다. 가이드에 표시한 SHA는 배포 후 변할 수 있으므로 **수업 공지 SHA와 내 출력값을 비교**하세요.

**오류가 나면:** `git: command not found` → 강사에게 문의하거나 인터넷 연결 가능한 Ubuntu에서 `sudo apt update && sudo apt install -y git` (Git만 설치). `python3: command not found` → 환경이 Ubuntu 24.04인지 확인한 뒤 강사에게 도움을 요청하세요. `destination path ... already exists` → 기존 자료를 지우지 말고 클론 대상 폴더명을 `axia-d13-student-2`처럼 바꾸고 이후 `cd` 경로도 맞춥니다. `fatal: unable to access` → 네트워크·프록시·GitHub 접속을 점검하세요.

**초심자 체크포인트 2:** `pwd`가 `/home/…/axia-d13-student` 형태이고, `ls block_D/day13`에 `run_lab.py`·`reachability_student.py`·`fixtures`·`tests`가 보이면 다음 단계로 넘어갑니다.

## 3. 파일 지도를 그려 보기 — 수정할 파일은 딱 하나

```text
axia-d13-student/                      ← 저장소 루트: 명령은 대부분 여기서 실행
└── block_D/
    └── day13/
        ├── fixtures/
        │   ├── robot_trajectory.csv   ← 로봇 위치 표(16시점)
        │   └── cases.json             ← 사람 관측·8가지 사례
        ├── reachability_student.py    ← ★ 여러분이 작성하는 TODO 함수
        ├── run_lab.py                 ← 파일 읽고 판단·HTML/JSON 만드는 실행기
        ├── tests/
        │   ├── test_d13_public.py     ← 알고리즘 시험
        │   └── test_d13_runner.py     ← 실행기·데이터·HTML 시험
        ├── STUDENT_DEMO_GUIDE_KO.md   ← 데모 보조 자료
        └── STUDENT_WORKSHEET_KO.md    ← 작성·제출용 활동지
```

**실습 규칙:** `fixtures`, `tests`, `run_lab.py`는 읽기만 합니다. 학생은 `reachability_student.py`의 TODO 함수만 편집합니다. 테스트 파일을 바꿔서 GREEN을 만드는 것은 학습 목표를 달성한 것이 아닙니다.

## 4. 데이터 읽기 ① — 로봇 CSV를 눈으로 확인

```bash
cd ~/axia-d13-student
head -7 block_D/day13/fixtures/robot_trajectory.csv
wc -l block_D/day13/fixtures/robot_trajectory.csv
```

**예상 CSV 앞부분:**

```csv
t_sec,x,y,radius
10.1,0.0,0.0,0.15
10.3,0.2,0.0,0.15
10.5,0.4,0.0,0.15
10.7,0.6,0.0,0.15
10.9,0.8,0.0,0.15
11.1,1.0,0.0,0.15
```

`wc -l` 예상 17: 제목 1행 + 데이터 16행입니다. 각 열은 시간(초), x좌표(m), y좌표(m), 로봇 원 반경(m)입니다. 로봇은 y=0을 따라 x=0에서 3.0m까지 나아가는 합성 궤적입니다.

**왜 16개인가?** 10.1부터 13.1까지 차이는 3.0초. 0.2초씩 이동하면 `3.0/0.2=15`개 **간격**이 있고, 시작점까지 포함하면 `15+1=16`개 **위치 샘플**입니다.

| 인덱스 `i` | 시각 `t = 10.1+i×0.2` | 로봇 x | 설명 |
|---:|---:|---:|---|
| 0 | 10.1 | 0.0 | 출발 |
| 1 | 10.3 | 0.2 | 한 칸 이동 |
| 5 | 11.1 | 1.0 | P/N 대표 비교 시각 |
| 7 | 11.5 | 1.4 | 시간 교란이 적용되는 자리 |
| 15 | 13.1 | 3.0 | 마지막 시각 |

**중요:** 0.2초는 **미래 예측에 사용한 시간 간격**입니다. 실제 LiDAR가 0.2초마다 발행·수신된다는 증거가 아닙니다.

## 5. 데이터 읽기 ② — 사람·사례 JSON을 이해하기

```bash
python3 -m json.tool block_D/day13/fixtures/cases.json | head -65
```

JSON에는 `now_sec=10.1`, `dt_sec=0.2`, `horizon_sec=3.0`, `robot_csv` 경로 및 `cases` 목록이 있습니다. 예를 들어 첫 번째 P 사례의 사람 데이터:

```json
{
  "x": 2.1,
  "y": 0,
  "vx": -1,
  "vy": 0,
  "radius": 0.2,
  "confidence": 0.9,
  "observed_sec": 10
}
```

- `x,y`: 관측했던 순간의 사람 중심 좌표(m).
- `vx,vy`: 속도(m/s). 음수 `vx`는 x가 작아지는 방향으로 이동한다는 뜻입니다.
- `radius`: 사람 점유 원 반경(m). 사람이 정확한 원형이라는 뜻이 아니라 교육용 단순화입니다.
- `confidence`: 관측 신뢰도를 나타내는 교육용 점수. 0.9는 최소 0.5 이상입니다.
- `observed_sec`: **사람을 관측한 시각 10.0초**, 계산 기준 `now_sec=10.1`과 다릅니다.
- `robot_frame/person_frame`: 좌표를 같은 기준으로 표현했는지 확인. `map`과 `odom`이 다르면 직접 비교하지 않습니다.

**초심자 체크포인트 3:** `observed_sec`와 `now_sec`를 혼동하지 않고 각각 10.0과 10.1이라고 말할 수 있나요?

## 6. Reachability는 무엇인가? 이번 모델이 계산하는 것·하지 않는 것

일상적으로는 "사람이 앞으로 **어디에 있을 수 있을까?**"라는 질문입니다. 일반적인 Reachability(도달가능 영역)는 여러 속도·가속·회전·불확실성을 고려하면 **가능한 위치들의 집합**이 됩니다. 이번 수업의 공식은 훨씬 단순합니다. **사람이 현재 추정 속도로 직선 이동한다고 가정한 미래 중심 한 점**을 구하고, 그 주변에 **고정 반경의 원**을 둡니다.

```text
실제 일반적 도달가능 집합 (개념)      D13에서 실제 구현하는 모델
가능한 가속·방향·오차가 여러 개      속도 vx,vy가 미래에도 일정하다고 가정
미래 위치가 여러 곳이 될 수 있음    미래 시각마다 중심점 1개 + 원형 반경 1개
불확실성에 따라 영역이 변할 수 있음 고정 반경 (교육용)
```

**이 모델만으로 실제 충돌·정지거리·인증된 안전성을 보증하지 않습니다.** 오늘은 '같은 공간의 같은 시각'이라는 논리부터 정확하게 배우는 단계입니다.

## 7. 핵심 수학 — 사람의 미래 위치와 동시간 거리 직접 계산

사람 위치 공식은 `미래 위치 = 관측 당시 위치 + 속도 × 경과시간`입니다.

```text
human_x(t) = person["x"] + person["vx"] × (t - observed_sec)
human_y(t) = person["y"] + person["vy"] × (t - observed_sec)

d(t) = sqrt( (robot_x(t) - human_x(t))²
           + (robot_y(t) - human_y(t))² )

겹침 조건: d(t) <= robot_radius(t) + person_radius
```

**P 손계산:** `t=11.1`에서 경과시간은 `11.1−10.0=1.1초`입니다. 사람 x는 `2.1 + (-1.0)×1.1 = 1.0m`. 로봇 CSV에서도 11.1초의 x는 1.0m. 두 중심 간 거리 `0.0m`, 두 반경 합 `0.15+0.20=0.35m` → 해당 시각 원이 겹칩니다.

**N 손계산:** 사람 시작 x=0.9m, 속도 vx=+1.0m/s라면 11.1초 사람 x는 `0.9+1.0×1.1=2.0m`. 로봇 x는 여전히 1.0m. 거리 `1.0m > 0.35m`이므로 **이 한 시각에서는** 겹치지 않습니다. 최종 N이라고 하려면 **나머지 15개 시각도 모두 유효·비중첩**이어야 합니다.

**주의:** 거리 비교에서 경계 `<=`는 **접하기만 해도 겹침**으로 처리합니다. 시간은 두 이동체 모두 **똑같은 t**를 사용해야 합니다.

## 8. 프로그램 함수 지도 — 실제 공개 코드가 어떤 순서로 실행되나?

```text
[run_lab.py / main()]
       |
       v
[load_cases()] ────── CSV/JSON을 읽어 8개 case(dict)를 생성
       |
       v
[evaluate_case(case)] ─┬─ 다른 좌표계? → U (여기서 종료)
                       |
                       └─ 같은 좌표계 → classify_time_indexed(...) [학생 TODO]
                                                      |
                                                      v
                                           P / N / U 실제값
       |                                               |
       └── [render_html(case,result)] ←───────────────┘
                |
           사례별 HTML 8개 + d13_results.json + CLI 결과
별도 경로: python3 -m unittest ... → 공개 테스트 10개
```

### 8-1. `load_cases()` — 두 파일을 하나의 실험 입력으로 묶기

`run_lab.py`의 `load_cases`는 `json.loads(...)`로 JSON을 읽고, `csv.DictReader`로 행마다 `{"t_sec": ..., "x": ..., "y": ..., "radius": ...}` 모양의 dict를 만듭니다. 숫자 텍스트는 `float(...)`로 변환합니다. 그리고 case별로 로봇 경로의 **복사본**과 사람 관측값을 함께 구성합니다.

왜 복사할까요? 한 사례에서 마지막 점을 제거하거나 시간을 바꾸더라도 다른 사례의 데이터가 함께 변하면 안 되기 때문입니다. `U_missing_last_sample`은 마지막 한 점을 제거하고, `U_time_jump`는 인덱스 7(8번째 점)의 시간 `11.5`를 **11.54**로 바꾸는 합성 오류를 만듭니다.

### 8-2. `evaluate_case(case)` — 좌표계를 먼저 확인

`robot_frame`과 `person_frame`이 둘 다 정상 문자열이며 같아야 학생 분류 함수를 호출합니다. 다르면 즉시 `"U"`, reason은 `FRAME_MISMATCH_OR_UNKNOWN`입니다. 이는 **교육용 어댑터의 사전검사**입니다. 원본 G09 분류 함수가 TF를 자동 변환하지 않습니다.

### 8-3. `classify_time_indexed()` — 내가 구현할 핵심 TODO

함수의 첫 인수 `robot_trajectory`는 list(로봇 시점 16개), 두 번째 `person`은 dict(사람 관측), `now_sec`는 판단 기준 시각(10.1초)입니다. 선택 인수 `dt_sec`=0.2, `horizon_sec`=3.0, `stale_sec`=0.5, `confidence_min`=0.5는 검사 규칙입니다.

```python
def classify_time_indexed(robot_trajectory, person, *, now_sec,
                          dt_sec=0.2, horizon_sec=3.0, stale_sec=0.5,
                          confidence_min=0.5):
    # 실제 학생 소스에는 이 함수의 TODO가 들어 있습니다.
    # '*' 뒤의 now_sec 등은 이름을 붙여 전달하는 키워드 전용 인수입니다.
    ...
```

**위 블록은 함수 서명을 이해하기 위한 설명용 발췌이지, 실행 가능한 정답 코드가 아닙니다.** 실제 학생 파일에서 `return "U"`를 본인 구현으로 대체하세요. 이 함수는 모터 명령이나 ROS 토픽을 발행하지 않습니다.

### 8-4. `render_html()` — '판정'과 '그림'을 구분하는 함수

이 함수는 HTML/SVG를 만들고 시간 슬라이더를 움직일 때 해당 시각의 두 원과 중심 거리를 표시합니다. **그림의 기하학적 YES/NO는 슬라이더가 계산하는 값**이고 학생 코드의 `actual`을 대신하지 않습니다. 그래서 최초 TODO 상태에서 **P 사례의 그림은 YES여도 actual은 U**일 수 있습니다.

### 8-5. `main()` — 명령 인수 해석·결과 저장·종료 코드

`--list`는 사례 ID만 출력. `--case NAME`은 한 사례만 실행. `--out DIR`은 결과를 저장할 폴더(필수 인수)입니다. 일반 전체 실행은 8개 사례의 HTML 파일과 `d13_results.json`을 만들고 결과 일치 여부에 따라 **0 또는 2**로 종료합니다. 

**초심자 체크포인트 4:** `load_cases()`, `evaluate_case()`, `classify_time_indexed()`, `render_html()`, `main()`을 한 문장씩 설명해 보세요. '함수의 출력'과 'HTML 시각화'를 혼동하지 마세요.

## 9. 먼저 일부러 실패 확인 — RED는 정상입니다

**터미널에서 정확히 아래 순서로 입력하세요.** `echo` 앞에 다른 명령을 넣으면 `$?`가 다른 프로그램의 종료 코드를 가리킵니다.

```bash
cd ~/axia-d13-student
python3 -m unittest discover -s block_D/day13/tests -p 'test_*.py' -v
echo "student_tests_rc=$?"
```

**미완성 학생 TODO 기준 예상 출력(실제 테스트 실행 결과가 아닌 안내 예시):**

```text
test_P_same_time_overlap ... FAIL
test_N_same_path_different_time ... FAIL
Ran 10 tests
FAILED (failures=2)
student_tests_rc=1
```

`unittest discover`는 테스트를 찾아 실행, `-s`는 검색할 폴더, `-p`는 파일 이름 규칙, `-v`는 자세한 출력을 의미합니다. 출력의 긴 Traceback은 당황할 필요 없습니다. **처음에는 P/N 두 테스트 실패가 교육 의도**입니다. U 테스트 통과가 전체 구현 완성을 의미하지는 않습니다.

**예상과 달리 다른 실패가 나오면:** 먼저 `pwd`와 `python3 --version`, 테스트 파일을 수정하지 않았는지 확인하세요. 새로운 ImportError/SyntaxError는 의도된 RED와 다른 오류입니다.

## 10. TODO 구현 4단계 — 정답 복사 없이 논리를 세우기

파일 편집:

```bash
nano block_D/day13/reachability_student.py
```

**nano 사용법:** 커서 이동은 방향키, 저장은 **Ctrl+O** → Enter, 종료는 **Ctrl+X**. Python 코드는 줄 앞의 빈칸(들여쓰기)이 중요한 문법입니다. 함수 내부는 같은 수준끼리 같은 개수의 공백을 사용하세요. 함수 이름·매개변수는 변경하지 마세요.

작은 Python 기초 실습(판정 함수 정답이 아님):

```python
import math
p = {"x": 2.1, "vx": -1.0}
times = [10.1, 10.3, 10.5]
print(p["x"])           # dict에서 값 찾기
print(len(times))        # list 길이 확인
print(math.hypot(3, 4))  # 두 축 거리: 5.0
```

이 예제는 Python 터미널에서 `python3`을 실행한 뒤 입력하거나 파일로 실험할 수 있습니다. 판정 함수의 완성 구현과는 다릅니다.

### TODO(1) — 입력이 믿을 수 있는가?

검사 질문: `now_sec`·`dt_sec`·`horizon_sec`·`stale_sec`·`confidence_min`이 정상 숫자이고 유한한가? `dt,horizon,stale`가 양수인가? confidence가 0~1 범위이며 최소값 이상인가? 사람 `x,y,vx,vy,radius,observed_sec`가 누락되지 않고 유한한가? 반경이 음수가 아닌가? 관측 나이가 `0 <= now_sec-observed_sec <= 0.5`인가?

**왜 먼저 검사할까요?** 오래된 사람이 '지금도 같은 속도로 걷는다'고 믿을 근거가 없기 때문입니다. invalid 입력은 P나 N이 아니라 **U**입니다. `NaN`은 숫자 형태로 보일 수 있어도 `math.isfinite`로 걸러야 합니다.

### TODO(2) — 시간표 16칸이 모두 정상인가?

`round(horizon_sec/dt_sec)+1`을 이용해 예상 점 수를 계산하고 실제 리스트 길이를 확인하세요. 모든 시점에서 `t_sec`가 `now_sec + index*dt_sec`와 맞는지, x/y/radius가 유한한지 검사하세요. 부동소수점 비교는 계산 오차가 있으므로 **작은 허용오차**가 필요합니다.

**반례:** `U_missing_last_sample`은 15개, `U_time_jump`은 인덱스 7 시각이 11.54라서 예상 11.5와 0.04초 차이가 납니다. 먼저 어떤 시점이 첫 위반인지 기록하세요.

### TODO(3) — 같은 시각에 사람 원은 어디 있나?

각 로봇 점의 `t_sec`을 가져와 사람의 `x + vx×(t_sec-observed_sec)`와 y 위치를 계산하세요. `math.hypot`으로 같은 시각의 거리 `d`를 얻고, 두 반경 합과 비교합니다.

**절대 하지 말 것:** 두 경로가 지도에서 언젠가 만난다고 해서 P로 분류하기. 시간을 빼면 N 사례를 틀리게 판정합니다.

### TODO(4) — 왜 P를 발견해도 바로 반환하지 않을까?

한 시점의 겹침이 있으면 `overlap` 같은 상태에 기록만 하고, **남은 모든 로봇 점을 검증**합니다. 만약 마지막 데이터가 NaN이라면 이전 겹침과 상관없이 최종 **U**입니다. 전 구간 유효하고 한 번 이상 겹치면 P, 유효하고 한 번도 겹치지 않으면 N입니다.

구현 흐름을 스스로 채우는 빈칸:

```text
입력 검사 → 무효라면 ___
16개 시간표 확인 → 잘못됐으면 ___
반복하면서 사람의 미래 x/y를 ___ 시각으로 계산
겹침이 있어도 ____ 반환하지 않고 기록
전체 유효할 때 기록이 True면 ___ / False면 ___
```

**중요:** 학생용 저장소에 강사 정답을 붙여 넣지 않습니다. 막히면 먼저 현재까지 구현한 코드를 강사에게 보여 주고, 입력 검사→시간 검사→거리 계산 순서로 오류를 좁힙니다.

편집 후 문법 검토와 재테스트:

```bash
python3 -m py_compile block_D/day13/reachability_student.py
echo "syntax_rc=$?"
python3 -m unittest discover -s block_D/day13/tests -p 'test_*.py' -v
echo "student_tests_rc=$?"
```

`syntax_rc=0`은 **문법이 맞는다**는 뜻이지 판정이 맞다는 뜻이 아닙니다. 모든 구현을 끝냈을 때의 목표: `Ran 10 tests`, `OK`, `student_tests_rc=0`. 아직 실패하면 FAIL 이름부터 읽고 해당 TODO 단계만 살펴보세요.

## 11. 합성 8사례 — 같은 규칙을 어떤 상황에서 검증하나?

```bash
python3 block_D/day13/run_lab.py --list --out /tmp/axia-d13
echo "list_rc=$?"
```

**예상:** 아래 8개 ID가 한 줄씩 출력되고 `list_rc=0`. **`--list`는 ID만 보여 주고 결과 파일을 만들지 않습니다.**

| ID | 기대 | 확인할 이유 |
|---|---|---|
| `P_same_time_overlap` | P | 유효한 전체 입력 + 같은 시각 겹침 |
| `N_same_route_different_time` | N | 같은 공간을 지나지만 전체 유효 시점에 비중첩 |
| `U_stale_track` | U | `now 10.1 - observed 9.5 = 0.6초`, 한계 0.5초 초과 |
| `U_future_stamp` | U | 관측 10.2초가 현재 10.1초보다 미래 |
| `U_low_confidence` | U | confidence 0.05 < 0.5 |
| `U_frame_mismatch` | U | robot=map, person=odom → CLI 사전 검사 |
| `U_missing_last_sample` | U | 16개 대신 15개 |
| `U_time_jump` | U | index 7 예상 11.50, 실제 11.54 |

**처음 오류 지점을 찾는 연습:** U 사례가 왜 U인지 최종 예외 문구 대신 **어떤 필드·시간·프레임이 최초로 계약을 위반했는지** 말해 보세요.

## 12. 전체 실행·출력 파일·종료 코드 읽기

먼저 단일 P 사례를 실행하고, 그다음 전체 8개를 실행하세요.

```bash
cd ~/axia-d13-student
python3 block_D/day13/run_lab.py --case P_same_time_overlap --out /tmp/axia-d13
echo "single_rc=$?"
python3 block_D/day13/run_lab.py --out /tmp/axia-d13
echo "runner_rc=$?"
ls -lh /tmp/axia-d13
python3 -m json.tool /tmp/axia-d13/d13_results.json | head -65
```

**중요한 순서:** `--case`는 JSON을 단일 사례 결과로 갱신합니다. **반드시 전체 실행을 마지막**에 진행해 8개 결과를 제출하세요.

**미완성 TODO의 예상 로그 발췌:**

```text
D13_CASE=P_same_time_overlap expected=P actual=U status=RED_EXPECTED_TODO
D13_CASE=N_same_route_different_time expected=N actual=U status=RED_EXPECTED_TODO
D13_CASE=U_stale_track expected=U actual=U status=PASS
...
D13_STUDENT_RESULT=RED_EXPECTED_TODO
runner_rc=2
```

**완성 목표(실제 성공을 주장하는 출력이 아니라 학생이 만들어야 하는 증거):**

```text
Ran 10 tests
OK
student_tests_rc=0
D13_STUDENT_RESULT=GREEN
runner_rc=0
```

- `d13_results.json`: `expected`는 정답표, `actual`은 내 코드 판정, `pass`는 둘이 같은지, `reason`은 검증 경로, `scope`는 오프라인 합성이라는 뜻입니다.
- `P_same_time_overlap.html` 등 8개: 브라우저에서 시간별 원을 보는 **읽기 전용** 자료입니다.
- 초기 RED여도 HTML과 JSON은 정상적으로 생성됩니다. 이 때문에 `runner_rc=2`를 곧바로 파일 생성 실패로 해석하지 않습니다.

## 13. HTML 시간 슬라이더 — 같은 위치와 같은 시각은 다릅니다

WSL2에서 Windows 브라우저를 이용할 때만 아래 명령을 사용합니다.

```bash
explorer.exe "$(wslpath -w /tmp/axia-d13/P_same_time_overlap.html)"
explorer.exe "$(wslpath -w /tmp/axia-d13/N_same_route_different_time.html)"
```

일반 Ubuntu라면 파일 탐색기에서 `/tmp/axia-d13`에 있는 HTML을 브라우저로 직접 열면 됩니다.

**슬라이더 사용법:** 표시되는 시간 `t`를 **11.1초(인덱스 5, 여섯 번째 위치)**로 바꾸고 두 창의 중심거리와 반경 합을 비교하세요.

| 항목 | P 화면 | N 화면 |
|---|---:|---:|
| t | 11.1초 | 11.1초 |
| 로봇 x | 1.0m | 1.0m |
| 사람 예측 x | 1.0m | 2.0m |
| 중심 거리 | 0.0m | 1.0m |
| 반경 합 | 0.35m | 0.35m |
| 이 시각 기하학적 겹침 | YES | NO |

**꼭 구분:** HTML의 `기하학적 겹침 YES/NO`는 그 시각 그림의 계산값입니다. 초기 학생 TODO가 `actual=U`여도 화면에서 P의 원은 겹칠 수 있습니다. 이는 프로그램 두 부분이 맡은 역할이 다르기 때문입니다.

브라우저가 안 열리면 HTML 생성 여부를 확인하고 JSON과 CLI 표로 설명합니다. **브라우저가 실제로 실행되지 않았다면 `HTML_BROWSER_NOT_RUN`이라고 적어야 합니다.** ROS/Gazebo 화면은 처음부터 요구되지 않습니다.

## 14. 초심자 오류 해결 카드 — 첫 증거부터 확인하세요

| 증상 | 먼저 확인할 명령/의미 | 다음 행동 |
|---|---|---|
| Git clone 폴더가 이미 존재 | `ls ~` | 새 이름으로 클론, 기존 자료 보존 |
| `ModuleNotFoundError` | `pwd`, `ls block_D/day13` | 저장소 루트로 이동 |
| `SyntaxError` / `IndentationError` | `python3 -m py_compile ...` | 잘못된 줄 번호·들여쓰기 확인 |
| P가 U | 기존 TODO 여부, `now/observed` | TODO(1)(3)(4)부터 차례로 |
| N이 P | 두 이동체가 같은 `t_sec`인가 | 시간까지 맞춰 비교 |
| U가 N | 관측 age/NaN/누락 시점 | 처음 유효성 위반부터 찾기 |
| P를 일찍 반환 | 마지막 샘플 유효성 | 겹침 발견해도 끝까지 검증 |
| `FAILED (failures=2)` | 학생 TODO가 미완성인가 | **예상된 초기 RED**, 계속 개발 |
| 다른 개수의 FAIL | 불필요한 파일 변경·코드 오류 | `git diff --name-only` 및 최초 오류 |
| `runner_rc=2` | P/N expected와 actual 비교 | 완료 전에는 정상 RED 경로 |
| HTML이 비어 보임 | `ls -lh /tmp/axia-d13` | JSON/CLI로 대체, GUI NOT_RUN |
| Gazebo가 실행되지 않음 | 합성 오프라인 L0 여부 | Gazebo는 실행 대상 아님 |

## 15. 제출·평가표 — 무엇을 증거로 제출할까?

```bash
cd ~/axia-d13-student
git diff --name-only
git rev-parse HEAD
ls -lh /tmp/axia-d13/d13_results.json
```

**제출 준비 체크리스트:** `STUDENT_WORKSHEET_KO.md`에 답 작성, `reachability_student.py` 수정 파일, 최초 RED와 최종 GREEN 테스트 로그(아직 GREEN 미달이면 그대로 표시), `d13_results.json` 8개 사례, P/N HTML 캡처 또는 브라우저 미실행·JSON 해설, Git SHA 및 변경 목록. 학생 코드 완료 전에도 "어디까지 통과했는지" 정직하게 제출해야 합니다.

**평가(100점):** 입력·시간 무결성 25 / 동시간 P/N 30 / U 반례 20 / 시각화·결과표 15 / 안전 한계 10.

### 최종 스스로 답할 다섯 질문

1. Reachability는 무엇이며, 이번 고정 반경 등속도 모델은 무엇을 생략했나요?
2. 왜 `3.0/0.2`는 15인데 예측 시점은 16개인가요?
3. 왜 '같은 좌표'보다 **같은 시각**이 중요한가요?
4. 초반 P 원 중첩이 있더라도 마지막 값이 NaN이면 왜 U인가요?
5. SW Stop과 인증 E-Stop이 다른 이유는 무엇인가요?

**실습 완료의 정확한 의미:** 학생의 10개 오프라인 공개 테스트·8개 합성 사례 PASS. 로봇의 안전 TTL, 사람 센서, Nav2 또는 실제 ROS/Gazebo 인수를 완료했다고 보고하지 않습니다.


## 16. 선택형 몰입 데모 — TIME × SPACE Live Replay

교육용 슬라이더와 별도로 파란 로봇·빨간 사람의 **두 장면을 동기 자동 재생**하고, 학생이 먼저 P/N/U를 예상한 뒤 fixture 기대값과 학생 코드 actual을 구분하는 화면을 제공합니다. 6개 U 사례의 첫 입력 위반도 볼 수 있습니다.

```bash
cd ~/axia-d13-student
python3 block_D/day13/live_replay.py --out /tmp/axia-d13-live
explorer.exe "$(wslpath -w /tmp/axia-d13-live/axia_d13_live_replay.html)"
```

실행 경로가 다르면 본인 클론 폴더로 `cd`를 변경하세요. **[Live Replay 초심자 상세 가이드](STUDENT_LIVE_REPLAY_GUIDE_KO.md)**에 16시점 재생, 11.1초 비교, 퀴즈, U 원인, 오류 대응 및 JSON 대체 절차를 정리했습니다. 이 화면은 `run_lab.py`의 원래 10개 테스트 및 8개 JSON 제출을 대체하지 않습니다. ROS/Gazebo/Goal/E-Stop은 NOT_RUN입니다.
