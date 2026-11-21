# AXIA D13 초심자를 위한 상세 실습 가이드 — Reachability와 시간별 경로 충돌 판정

**수업일:** 2026-11-25(수) 19:00–23:00 · 총 240분(교육 220분 + 휴식 20분)  
**누구를 위한 문서인가?** Python/리눅스 명령어가 익숙하지 않은 **초심자**도 터미널에서 그대로 따라 하고, 중간 결과가 왜 나오는지 설명할 수 있도록 작성했습니다.  
**준비물:** Ubuntu 24.04 또는 WSL2 Ubuntu 24.04, Python 3.12 계열, Git, 선택적으로 웹브라우저. Python **표준 라이브러리만** 사용하므로 ROS 2, Gazebo, Nav2, pip 패키지 설치는 필요 없습니다.  
**주의:** 교육용 **오프라인 합성 데이터 L0** 실습입니다. 실제 사람 인식, ROS topic, Nav2 Goal, 로봇 구동, SW STOP, 인증 E-Stop 및 현장 안전 타이밍을 시험하는 자료가 아닙니다.

## 0. 오늘 두 가지 주제와 도달 목표부터 확인

**주제 1. Reachability 기반 사람 이동 가능 영역 계산 구조 이해** — "사람이 지금 여기 있다면 1초 뒤 어디에 있을까?"를 시간별 점유영역으로 표현합니다. D13은 **등속도 예상 중심 + 고정 원 반경**인 간소화 모델이며, 사람이 방향·속도를 바꾸며 갈 수 있는 모든 위치를 계산하는 엄밀한 Reachability 전체는 구현하지 않습니다.

**주제 2. 공간예측 및 경로 충돌 판정 실습** — 로봇과 사람이 같은 장소뿐 아니라 **동일 시각**에 겹치는지 비교합니다. 결과는 P(예측 중첩), N(예측 비중첩), U(판정 불가)입니다.

수업을 마쳤을 때 다음을 **직접 보여 줄 수 있어야** 합니다.

1. CSV의 로봇 시간표가 왜 **16개 시점**인지 설명한다.
2. JSON 사람의 위치·속도로 특정 시각의 예상 위치를 손으로 계산한다.
3. 두 원의 중심거리와 반경 합을 계산해 P/N의 차이를 설명한다.
4. stale/future/confidence/경로 손상 등 **U** 상황을 구별한다.
5. 학생 TODO를 작성해 공개 **10개 테스트**와 8개 시연 사례를 검증한다.
6. 합성 판단과 실제 로봇 안전제어가 다르다는 점을 설명한다.

| 시간 | 실습 흐름 | 확인 증거 |
|---|---|---|
| 19:00–19:30 | 복도 이야기, P/N/U, 학습 목표 | 질문 A |
| 19:30–20:10 | Reachability, 아키텍처/데이터 흐름, CSV/JSON, 수치 | 손계산 B |
| 20:10–20:20 | 휴식 | — |
| 20:20–21:20 | 최초 RED → TODO 4단계 → 재테스트 | 코드·로그 D |
| 21:20–21:30 | 휴식 | — |
| 21:30–22:30 | 8사례 시연, HTML·JSON, 오류 분석 | 사례표 C |
| 22:30–23:00 | 결과 공유, 안전 범위, 제출 | 성찰 E |

**자료 사용법:** 명령은 반드시 저장소 루트(예: `~/axia-d13-student`)에서 실행합니다. 각 `예상 출력`은 정상적인 시작 TODO 또는 예시 데이터 기준이며, **본인의 실제 실행 성공을 대신하지 않습니다**. 명령을 한 블록씩 복사하고 바로 아래 '왜?'를 읽으세요.

## 1. 시작 전 용어 10개만 익히기 (처음 보는 분)

| 용어 | 쉬운 의미 | 오늘의 예 |
|---|---|---|
| 터미널(Terminal) | 컴퓨터에게 문자 명령을 내리는 창 | Ubuntu/WSL2 터미널 |
| 현재 폴더/경로(path) | 명령을 실행하는 현재 위치 | `~/axia-d13-student` |
| Git clone | GitHub 자료를 내 PC에 처음 복사 | `git clone ...` |
| 저장소(repository) | 코드·문서·이력을 함께 관리하는 폴더 | `axia-robot-safety-student` |
| main / SHA | 정식 배포 브랜치 / 소스 버전 식별값 | `git rev-parse HEAD` |
| CSV | 쉼표로 구분한 표 형태 데이터 | 로봇 16개 위치 |
| JSON | 이름과 값으로 묶인 구조화된 데이터 | 사람 속도, 예시 8건 |
| 함수(function) | 입력을 받아 정해진 처리를 수행하는 코드 | `load_cases()` |
| TODO / unittest | 학습자가 채울 빈 함수 / 코드 자동 검증 | 2개 의도된 FAIL |
| exit code(종료 코드) | 명령이 끝나고 남기는 숫자 상태 | unittest 실패 1, runner 불일치 2 |

**`~`**는 사용자 홈 폴더, **`cd`**는 폴더 이동, **`ls`**는 목록, **`pwd`**는 현재 위치 출력입니다. 오류가 난다면 먼저 `pwd`를 확인하세요. `#`으로 시작하는 설명 줄은 명령이 아닙니다.

## 2. GitHub 클론부터 환경 확인까지 — 실행 1

Ubuntu 터미널을 열고 아래 순서대로 입력합니다. Windows라면 시작 메뉴의 Ubuntu 또는 Windows Terminal의 Ubuntu 탭에서 입력합니다. **Windows PowerShell 프롬프트가 아니라 Ubuntu 셸**을 이용하세요.

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

**명령별 뜻**

- `git --version`, `python3 --version`: Git과 Python이 준비됐는지 확인합니다. Ubuntu 24.04의 기본 Python은 보통 3.12 계열입니다. 버전 출력 자체는 실행 확인이지 정답 검증이 아닙니다.
- `git clone --branch main --depth 1`: 공개 저장소의 `main` 최신 이력 한 단계만 내려받습니다. 개인 코드나 강사 정답을 받는 명령이 아닙니다.
- `cd ~/axia-d13-student`: 앞으로 모든 상대 경로의 기준인 프로젝트 루트로 이동합니다.
- `git rev-parse HEAD`: 클론된 정확한 버전의 SHA를 출력합니다. 강사 공지 SHA와 비교할 때 사용합니다.
- `ls block_D/day13`: 오늘의 데이터·실습 코드·문서·테스트가 있는지 확인합니다.

**예상 출력의 예시**(SHA와 Git/Python 버전은 실행 시점에 따라 다름):

```text
Python 3.12.x
/home/<계정>/axia-d13-student
<40자리 Git 커밋 SHA>
STUDENT_LAB_GUIDE_KO.md  reachability_student.py  run_lab.py  fixtures  tests ...
```

**막힐 때:** `git: command not found`라면 Git이 설치되지 않은 것입니다. Ubuntu에서 `sudo apt update` 후 `sudo apt install -y git`을 사용하세요. `python3: command not found`라면 `sudo apt install -y python3`로 준비합니다. 기존 `axia-d13-student` 폴더가 있으면 삭제하지 말고 `axia-d13-student-2` 같은 새 이름으로 클론하고 이후 `cd` 경로도 일치시키세요. 수업 중 강사에게 기존 데이터 삭제를 요구하지 않습니다.

## 3. 파일을 열어 보며 '누가 무엇을 하는가?' 구별 — 실행 2

```bash
cd ~/axia-d13-student
ls -R block_D/day13
head -6 block_D/day13/fixtures/robot_trajectory.csv
sed -n '1,45p' block_D/day13/reachability_student.py
```

| 파일 | 입력/역할 | 수정할까? |
|---|---|---|
| `fixtures/robot_trajectory.csv` | 로봇의 `t_sec,x,y,radius` 16개 행 | **아니요** |
| `fixtures/cases.json` | 사람 관측, P/N/U 8개 사례, 프레임 | **아니요** |
| `reachability_student.py` | `classify_time_indexed()` 함수 TODO, 처음은 `return "U"` | **예 — 이 파일만** |
| `run_lab.py` | CSV+JSON을 읽고 판정 함수를 호출해 CLI·JSON·HTML 생성 | 아니요 |
| `tests/test_d13_public.py` | 학생 분류 함수의 P/N/U·무결성 테스트 | 아니요 |
| `tests/test_d13_runner.py` | 8개 fixture·프레임·HTML 생성 범위 검사 | 아니요 |
| `STUDENT_DEMO_GUIDE_KO.md` | P/N 시연 순서, GUI 실패 시 대체 절차 | 읽기 |
| `STUDENT_WORKSHEET_KO.md` | 손계산·실행 로그·성찰 기록 | 작성 |

**핵심:** '실제 실행기'는 `run_lab.py`이고 '내가 구현할 알고리즘'은 `reachability_student.py`입니다. 두 파일을 헷갈리지 마세요.

## 4. CSV를 처음 읽는 학생: 로봇의 16칸 미래 시간표 — 실행 3

CSV는 표입니다. 가장 위는 열 이름이며, 다음 줄부터 한 시각의 값입니다. 실제 첫 5행은 다음과 같습니다.

```csv
t_sec,x,y,radius
10.1,0.0,0.0,0.15
10.3,0.2,0.0,0.15
10.5,0.4,0.0,0.15
10.7,0.6,0.0,0.15
```

- `t_sec`: 예측 시점(초). 시계의 초와 같은 **시간 단위**입니다.
- `x`, `y`: 2차원 지도상의 로봇 중심 좌표(m).
- `radius`: 로봇을 단순한 원으로 나타낼 때 원의 반경(m). 실제 복잡한 몸체/제동거리는 표현하지 않습니다.
- CSV 읽기에서는 문자열이 반환되므로 수치 계산할 때는 `float(...)`로 바꿉니다.

**파일을 손대지 않고 읽어 보는 Python 미니 실험** — 아래 블록 전체를 복사하세요.

```bash
cd ~/axia-d13-student
python3 - <<'PY'
import csv
with open("block_D/day13/fixtures/robot_trajectory.csv",
          newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
print("samples =", len(rows))
print("first_t =", rows[0]["t_sec"], "last_t =", rows[-1]["t_sec"])
print("robot_x_at_11.1 =", next(r["x"] for r in rows if r["t_sec"] == "11.1"))
PY
```

**예상 출력:**

```text
samples = 16
first_t = 10.1 last_t = 13.1
robot_x_at_11.1 = 1.0
```

**코드 해설:** `csv.DictReader`는 열 이름을 키(key)로 하는 사전(dictionary)을 만듭니다. `list(...)`는 모든 행을 차례로 저장합니다. `len(rows)`는 행 수, `rows[0]`은 첫 번째, `rows[-1]`은 마지막입니다. `next(...)`는 조건을 만족하는 첫 행의 x를 읽습니다. 위 코드는 **파일 내용 확인용**이며 TODO 알고리즘을 구현하지 않습니다.

**왜 16개일까?** 10.1초부터 13.1초까지 구간의 길이는 3.0초이고 간격은 0.2초입니다. `3.0 / 0.2 = 15`는 **사이의 간격 수**이므로 출발점까지 더해 `15 + 1 = 16`개의 시점입니다. `i=0~15`일 때 `t_i = 10.1 + i*0.2`입니다. **0.2초는 미래 예측 샘플 간격**이지 실제 LiDAR·DDS 발행/수신 주기가 아닙니다.

## 5. JSON을 처음 읽는 학생: 사람이 지금 어디 있고 얼마나 빠른가? — 실행 4

JSON은 여러 개의 '이름: 값'을 묶을 수 있습니다. `cases.json`에는 사례별 `id`, 기대값 `expected`, 로봇과 사람의 `frame`, 사람의 `x,y,vx,vy,radius,confidence,observed_sec`가 있습니다.

```bash
cd ~/axia-d13-student
python3 - <<'PY'
import json
with open("block_D/day13/fixtures/cases.json", encoding="utf-8") as f:
    data = json.load(f)
p = data["cases"][0]["person"]
print("cases =", len(data["cases"]))
print("first_id =", data["cases"][0]["id"])
print("person_x =", p["x"], "person_vx =", p["vx"])
print("now_sec =", data["now_sec"])
PY
```

**예상 출력:**

```text
cases = 8
first_id = P_same_time_overlap
person_x = 2.1 person_vx = -1
now_sec = 10.1
```

**코드 해설:** `json.load(f)`는 JSON 파일을 Python 사전/리스트로 변환합니다. `data["cases"]`는 8개 사례 리스트, `[0]`은 그 첫 번째, `["person"]`은 사람 사전입니다. `vx=-1`은 **x축의 음의 방향으로 초당 1m 이동**한다는 뜻입니다. `confidence=0.9`는 이 합성 추적 정보의 신뢰도 값이며 실제 검출기가 90% 정확하다는 인증이 아닙니다.

**관측 시각과 예측 시각을 구분하세요.** `observed_sec=10.0`은 사람이 관측된 시각, `now_sec=10.1`은 지금 분류하는 기준 시각, `t_sec=11.1`은 비교하려는 **미래 시각**입니다. 세 시각을 혼동하면 P/N 판정이 달라집니다.

## 6. 시스템 구조: 실물 로봇 개념과 이번 오프라인 파이프라인은 다릅니다

**실제 로봇 안전 구조의 개념**(이 수업의 실행 대상 아님):

```text
LiDAR·Camera 등 센서 → 사람 감지·추적 → 위치/속도 추정 → 미래 점유 영역
                → 위험 판단 정보 → 기존 Supervisor / Collision Monitor / Guard
                → 별도 주행 제한/정지 정책
```

이 그림은 **가능한 통합 구조의 설명**이지 오늘 로봇에서 센서 값이 연결되어 동작했다는 증거가 아닙니다.

**오늘 실제로 실행할 데이터 파이프라인**(학생이 파일을 확인하며 따라갈 순서):

```text
robot_trajectory.csv ───┐
                         ├→ load_cases() ─→ evaluate_case() ─┬→ frame 다름: U
cases.json ──────────────┘                                    └→ frame 같음
                                                                │
                                                    classify_time_indexed()
                                                   (학생 TODO, P / N / U)
                                                                │
                   ┌────────────────── main() ←─────────────────┘
                   │                   │
                   ├─ 콘솔 D13_CASE=... 출력
                   ├─ d13_results.json (8개 결과)
                   └─ render_html() → ID별 HTML/SVG 시각화
tests/test_d13_public.py + test_d13_runner.py ─ 별도 unittest 검증
```

### 소스 코드를 읽는 순서와 함수별 입출력

| 함수 | 파일 | 입력 → 출력 | 왜 필요한가? |
|---|---|---|---|
| `main()` | `run_lab.py` | CLI 인수 → 종료코드 0 또는 2, 파일 생성 | 실행 진입점입니다. `--list`만 사용하면 ID만 출력합니다. |
| `load_cases()` | `run_lab.py` | CSV와 JSON → 8개 사전 리스트 | 두 파일을 하나의 실험 데이터로 묶습니다. 누락·시간이상 사례도 주입합니다. |
| `evaluate_case()` | `run_lab.py` | 사례 사전 → `id/expected/actual/pass/reason/scope` 사전 | 좌표 frame이 다르면 함수 호출 전에 U로 분류합니다. |
| `classify_time_indexed()` | `reachability_student.py` | 로봇 16시점·사람 관측·now 등 → `"P"/"N"/"U"` | **학생이 구현하는 핵심 함수**입니다. |
| `render_html()` | `run_lab.py` | 사례·판정 결과 → HTML 문자열 | 시간 슬라이더로 각 시점의 원과 거리를 보여줍니다. |
| `test_...()` | `tests` 두 파일 | 작은 준비 사례 → 예상·실제 비교 | 코드를 반복해서 검증하는 자동시험입니다. |

**이름을 자세히 보면:** `expected`는 출제자가 정한 정답, `actual`은 **현재 학생 함수**가 낸 결과, `pass`는 두 값 일치 여부입니다. `reason=TIME_INDEXED_ORACLE`은 **분류 함수를 호출한 경로**를 표시할 뿐, U가 된 상세 원인을 자동 진단했다는 뜻이 아닙니다. `scope=SYNTHETIC_OFFLINE_L0_NOT_ROS_OR_GAZEBO`는 로봇 실제 테스트 아님을 명시합니다.

**프레임(frame) 주의:** 로봇 좌표가 `map`이고 사람 좌표가 `odom`이면, 변환 없이 같은 숫자를 비교할 수 없습니다. D13 `evaluate_case()`는 U를 먼저 반환합니다. **실제 TF 변환을 구현하거나 실행하지 않습니다.**

## 7. Reachability와 실제 계산: 미래 '점'에서 미래 '점유 원'으로

Reachability는 "어떤 조건에서 미래 시간 t에 도달 가능한 상태의 집합"을 뜻합니다. 여기서는 학생이 직접 구현할 수 있도록 **등속도 예측 중심을 원의 중심으로 쓰는 근사 교육 모델**을 택했습니다.

```text
현재 관측: (x, y), 관측 시각 observed_sec, 속도 (vx, vy)
             ↓ 시각 t까지 경과 시간 Δt = t - observed_sec
예측 중심: (x + vx*Δt, y + vy*Δt)
             ↓ 사람 반경 r_h를 더해 점유 원 생성
같은 t의 로봇 원 중심·반경과 비교
             ↓ 유효한 전체 16시점에서 하나라도 겹치면 P
```

**주의:** 사람의 가속, 회전, 속도 범위, 관측 불확실성의 증가를 함께 계산한 '모든 가능한 사람 이동영역'이 아닙니다. 원 반경도 항상 일정하다는 가정입니다. 따라서 이 모델의 N은 실제 안전 보장이 아닙니다.

### 계산 공식

```text
human_x(t) = x + vx × (t - observed_sec)
human_y(t) = y + vy × (t - observed_sec)

distance(t) = sqrt((robot_x(t) - human_x(t))²
                   + (robot_y(t) - human_y(t))²)
overlap_at_t = distance(t) <= robot_radius(t) + human_radius
```

Python에서는 두 좌표의 차이로 `math.hypot(dx, dy)`를 호출하면 거리(m)를 계산합니다. `<=`에는 '딱 접하는 경우도 겹침으로 판정'한다는 뜻이 포함됩니다.

```bash
python3 - <<'PY'
import math
robot = (1.0, 0.0)
human = (1.0, 0.0)
d = math.hypot(robot[0]-human[0], robot[1]-human[1])
print("distance =", d)
print("r_sum =", 0.15 + 0.20)
print("overlap =", d <= 0.15 + 0.20)
PY
```

**예상 출력:**

```text
distance = 0.0
r_sum = 0.35
overlap = True
```

이 코드는 두 점의 단일 시점 거리 **학습용 미니 실험**입니다. 전체 16개 시간표 판정과 유효성 검사 알고리즘의 정답을 제공하지 않습니다.

### P와 N을 같은 시각에서 비교한 숫자 표

| 시각 | 로봇 x | P 사람 x (2.1, -1m/s) | P 거리 | N 사람 x (0.9, +1m/s) | N 거리 |
|---|---:|---:|---:|---:|---:|
| 10.1s (index 0) | 0.0 | 2.0 | 2.0 | 1.0 | 1.0 |
| 10.9s (index 4) | 0.8 | 1.2 | 0.4 | 1.8 | 1.0 |
| **11.1s (index 5)** | **1.0** | **1.0** | **0.0** | **2.0** | **1.0** |
| 11.3s (index 6) | 1.2 | 0.8 | 0.4 | 2.2 | 1.0 |
| 13.1s (index 15) | 3.0 | -1.0 | 4.0 | 4.0 | 1.0 |

반경 합은 **0.15+0.20=0.35m**입니다. P 예는 11.1초에 0.0m≤0.35m로 겹치고, N 예는 모든 시점에서 거리가 1.0m이므로 비중첩입니다. 단, **최종 P/N은 전체 유효성 검사 후** 결정합니다. 표는 대표 일부만 보여줍니다.

**스스로 답해 보기:** "로봇과 사람이 언제라도 같은 x=1.0에 도달한다"는 정보만으로 P라고 할 수 있을까요? → **아니요. 도달한 시각을 맞춰 비교해야 합니다.**

## 8. P / N / U를 확실히 구별하기

| 기호 | 뜻 | 성립 조건 | 주의 |
|---|---|---|---|
| **P** | Predicted overlap: 예측 중첩 | 모든 입력 유효 + 동일 시각 중첩 1회 이상 | 실제 충돌 발생을 증명하지 않음 |
| **N** | No predicted overlap: 예측 비중첩 | 모든 입력 유효 + 16시점 중첩 없음 | 실제 주행 허가·안전 보증이 아님 |
| **U** | Unknown: 판정 불가 | 추적 오래됨, 미래 관측, 저신뢰도, 경로 시간 오류, NaN 등 | U를 N으로 바꾸면 안 됨 |

**관측 데이터 시간 유효성:** `0 <= now_sec - observed_sec <= stale_sec`이며 `stale_sec=0.5`초입니다. 이것은 **사람 관측값의 오래됨** 조건이고, ROS DDS 수신 시간·안전 보호 계층의 TTL과는 **서로 다른 조건**입니다.

**왜 U가 중요할까?** 관측이 잘못된 상황을 N(비중첩)으로 표시하면, 실제로 판단할 정보가 없는데도 "문제없다"고 주장하게 됩니다. 예측이 틀릴 수 있는 상황을 별도로 표현하는 것이 U의 역할입니다.

## 9. 테스트를 먼저 실행해 RED 확인 — 실행 5

```bash
cd ~/axia-d13-student
python3 -m unittest discover -s block_D/day13/tests -p 'test_*.py' -v
echo "student_tests_rc=$?"
```

**처음 배포된 TODO 상태에서의 예상 출력 발췌:**

```text
test_N_same_path_different_time ... FAIL
test_P_same_time_overlap ... FAIL
Ran 10 tests
FAILED (failures=2)
student_tests_rc=1
```

**왜 실패가 정상일까?** `reachability_student.py`는 함수 형태만 갖춘 학습 출발점이며 `return "U"`로 끝납니다. 유효한 P 예시나 N 예시도 U를 반환하므로 그 **두 테스트만 FAIL**하는 것이 출발 지점입니다. 총 10개는 **unittest 메서드 수**이고, `subTest`로 여러 U를 검사해도 그 수가 늘어나지는 않습니다. 학생의 TODO를 완성해야 진정한 GREEN이 됩니다.

**테스트는 무엇을 확인할까?**

- `test_d13_public.py`: P 한 건, N 한 건, stale/future/low confidence, 누락/시간 점프, NaN 검증 등 **5개 메서드**.
- `test_d13_runner.py`: 사례 수·시점 수, 프레임 어댑터 U, U 6사례, HTML 로컬 코드, 실제 ROS/Gazebo 아님 확인 등 **5개 메서드**.

출력의 `FAIL`은 **내 구현이 정답과 다름**, `ERROR`는 **코드 실행 중 예외**입니다. `runner_rc=2`와 테스트의 `student_tests_rc=1`은 명령마다 다른 종료 코드이므로 혼동하지 마세요.

## 10. RED → GREEN 실습: 한 함수의 네 가지 TODO 작성 — 실행 6

```bash
cd ~/axia-d13-student
nano block_D/day13/reachability_student.py
```

편집기가 낯설다면 `nano`에서 입력 후 **Ctrl+O → Enter(저장), Ctrl+X(종료)**입니다. VS Code를 설치했다면 `code block_D/day13/reachability_student.py`로 열 수도 있습니다. `run_lab.py`와 테스트 파일은 수정하지 않습니다.

**고정할 함수 형식**(이미 파일에 있음):

```python
def classify_time_indexed(robot_trajectory, person, *, now_sec,
                          dt_sec=0.2, horizon_sec=3.0, stale_sec=0.5,
                          confidence_min=0.5):
    # 아래 TODO 내부만 본인이 채웁니다.
    return "U"
```

**매개변수 하나씩:** `robot_trajectory`는 로봇 시점 사전 16개의 리스트, `person`은 사람의 관측 사전입니다. `now_sec`은 현재 기준 시각, `dt_sec`은 예측 시점 사이의 간격, `horizon_sec`은 미래 시간 범위, `stale_sec`은 관측 데이터 최대 나이, `confidence_min`은 최소 신뢰도입니다. 별표 `*` 뒤의 `now_sec`은 **이름을 써서 전달**해야 합니다.

### TODO 1. 입력이 말이 되는지 확인 — 유효하지 않으면 U

**질문:** '사람의 x가 NaN인데 거리를 계산하면 어떻게 될까?'

- Python 기본 `math` 모듈을 사용할 수 있습니다.
- 숫자의 타입과 유한성은 `type(value) in (int,float)`와 `math.isfinite(value)` 같은 조건으로 구분할 수 있습니다.
- `dt_sec`, `horizon_sec`, `stale_sec`은 양수여야 합니다.
- 사람 `radius`는 0 이상, `confidence`는 설정된 범위, `observed_sec`는 미래가 아니고 너무 오래되지 않아야 합니다.
- 유효하지 않으면 `"U"`입니다.

**도움말 미니 실험:**

```bash
python3 - <<'PY'
import math
print("ordinary =", math.isfinite(1.0))
print("missing-number =", math.isfinite(float("nan")))
print("age =", 10.1 - 9.5)
PY
```

예상: `ordinary = True`, `missing-number = False`, `age = 0.5999999999999996`처럼 부동소수점 근삿값. 따라서 시간 계산은 소수 끝자리가 정확히 표시되지 않을 수 있으며, `0.6 > 0.5`라는 판단에는 변함이 없습니다.

### TODO 2. 로봇 경로의 길이와 모든 시각을 확인

**질문:** '16개 중 마지막 1개가 빠진 파일을 안전하다고 판정해도 될까?'

- 필요한 개수는 `round(horizon_sec / dt_sec) + 1`, 기본값에서 **16개**입니다.
- `len(robot_trajectory)`로 행 수를 확인합니다.
- `enumerate(robot_trajectory)`는 `(index, point)`를 하나씩 제공합니다.
- `point["t_sec"]`가 `now_sec + index*dt_sec`에서 너무 벗어나는지 검사합니다. 부동소수점 오차 때문에 작은 허용오차(예: 1e-6)를 둘 수 있습니다.
- 각 점의 x/y/radius도 유한·비음수 반경인지 **마지막 점까지** 검사합니다.

**미니 실험:**

```bash
python3 - <<'PY'
for index in (0, 5, 15):
    print(index, round(10.1 + index * 0.2, 1))
PY
```

예상: `0 10.1`, `5 11.1`, `15 13.1`. 사례 `U_time_jump`는 **index 7**의 시간에 0.04초가 더해지며, `U_missing_last_sample`은 16점이 아니라 15점입니다.

### TODO 3. 같은 시각의 사람 위치·두 원의 겹침 계산

**질문:** '사람은 t=11.1에 x=1.0, 로봇도 x=1.0이라면?'

- 모든 `robot_point["t_sec"]`마다 `t - person["observed_sec"]`를 구합니다.
- 같은 시각의 사람 중심을 x/y 각각 투영합니다.
- 로봇과 사람 중심의 거리 `math.hypot(dx,dy)`를 구합니다.
- 거리와 **로봇 반경 + 사람 반경**을 비교합니다.

단지 과거에 경로가 교차했는지(공간 교집합)만으로 P를 판정하면 안 됩니다. **공간 + 시간의 동시성**이 핵심입니다.

### TODO 4. 마지막까지 검사한 후 결과 한 번 결정

- 겹침을 발견하면 "이번 16점 중 겹침이 있었다"는 사실을 **기록**합니다.
- 겹침을 찾았다고 바로 P를 반환하지 마세요. 뒤쪽 시간점의 좌표·반경이 NaN일 수 있습니다.
- 모든 조건이 유효하면 기록된 겹침 여부에 따라 P 또는 N을 결정합니다.
- 유효하지 않은 관측·누락·시간이상이면 **U가 우선**입니다.

**초심자용 의사코드 — 완성 정답이 아니며 그대로 실행되지 않음:**

```text
입력값 검사                  → 잘못되면 U
경로 샘플 개수 검사          → 잘못되면 U
모든 시각에 대해:
    로봇 시점·좌표 유효성 검사 → 잘못되면 U
    같은 시각의 사람 중심 예측
    두 원의 거리가 반경 합 이내인지 기록
모든 데이터가 정상일 때만       → 겹친 적이 있으면 P, 없으면 N
```

**학습 중 점검 명령** (변경 파일 이름·문법 오류만 확인):

```bash
python3 -m py_compile block_D/day13/reachability_student.py
git diff --name-only
python3 -m unittest discover -s block_D/day13/tests -p 'test_*.py' -v
echo "student_tests_rc=$?"
```

`py_compile` 성공은 **문법이 맞다**는 뜻이지 P/N/U 알고리즘이 맞다는 뜻은 아닙니다. 완성 목표는 아래 테스트와 시연 결과 둘 다 GREEN입니다. 학습자가 해결하지 못했을 때는 강사가 오답 원인을 안내하되 **비공개 강사 정답 파일을 학생 저장소로 복사하지 않습니다**.

## 11. 8개 사례 실행: ID 목록, 1건 실행, 전체 실행을 구분 — 실행 7

### 11-1. 사례 목록만 확인

```bash
cd ~/axia-d13-student
python3 block_D/day13/run_lab.py --list --out /tmp/axia-d13
```

**예상:** 다음 ID 8개를 한 줄씩 출력하고 종료 코드 0. **목록만 출력**하므로 이 명령은 HTML을 생성하지 않습니다.

```text
P_same_time_overlap
N_same_route_different_time
U_stale_track
U_future_stamp
U_low_confidence
U_frame_mismatch
U_missing_last_sample
U_time_jump
```

### 11-2. P 한 건만 실행

```bash
python3 block_D/day13/run_lab.py --case P_same_time_overlap --out /tmp/axia-d13
echo "single_rc=$?"
```

학생 TODO 미완성 기준 **예상**:

```text
D13_CASE=P_same_time_overlap expected=P actual=U status=RED_EXPECTED_TODO
D13_REPORT=/tmp/axia-d13/d13_results.json
D13_STUDENT_RESULT=RED_EXPECTED_TODO
single_rc=2
```

이 명령은 결과 JSON에 **P 한 사례만** 기록합니다. `status`는 해당 사례의 `expected`와 `actual` 일치 여부이고, HTML은 현재 TODO에서도 생성됩니다.

### 11-3. 8개 전체 실행

```bash
python3 block_D/day13/run_lab.py --out /tmp/axia-d13
echo "runner_rc=$?"
ls -lh /tmp/axia-d13
python3 -m json.tool /tmp/axia-d13/d13_results.json
```

**처음 TODO일 때 예상하는 핵심 결과**:

```text
D13_CASE=P_same_time_overlap expected=P actual=U status=RED_EXPECTED_TODO
D13_CASE=N_same_route_different_time expected=N actual=U status=RED_EXPECTED_TODO
D13_CASE=U_stale_track expected=U actual=U status=PASS
...
D13_STUDENT_RESULT=RED_EXPECTED_TODO
runner_rc=2
```

그 뒤 `/tmp/axia-d13`에 **8개 HTML + `d13_results.json`**이 있습니다. 학생의 TODO가 정확히 완성되었다면 다음과 같은 **목표 출력**이 나타납니다(개인 실행 로그로 입증해야 함).

```text
D13_CASE=P_same_time_overlap expected=P actual=P status=PASS
D13_CASE=N_same_route_different_time expected=N actual=N status=PASS
...
D13_STUDENT_RESULT=GREEN
runner_rc=0
```

**주의:** `--case`는 `d13_results.json`을 한 사례로 다시 작성합니다. 제출용 결과는 반드시 **전체 `--out` 명령을 가장 마지막에** 실행해 생성하세요. 테스트의 `student_tests_rc`와 실행기의 `runner_rc`는 서로 다릅니다.

### 11-4. JSON의 필드를 실제로 읽어 보기

```bash
python3 - <<'PY'
import json
with open("/tmp/axia-d13/d13_results.json", encoding="utf-8") as f:
    report = json.load(f)
print("cases =", len(report["cases"]))
print("all_pass =", report["all_pass"])
for item in report["cases"][:2]:
    print(item["id"], "expected=", item["expected"], "actual=", item["actual"])
PY
```

**전체 8사례를 실행했고 아직 TODO일 때 예상:**

```text
cases = 8
all_pass = False
P_same_time_overlap expected= P actual= U
N_same_route_different_time expected= N actual= U
```

`expected`는 사례의 기대값, `actual`은 **현재 학생 함수**의 출력, `all_pass`는 8사례의 `pass`가 전부 참인지 여부입니다. `reason=TIME_INDEXED_ORACLE`은 자세한 근본 원인 메시지가 아니므로 U의 정확한 원인을 그 필드만 보고 단정하지 마세요.

## 12. 8개 사례를 해설하며 원인 찾기

| 사례 ID | 기대 | 입력 데이터의 핵심 | 무엇을 먼저 물어볼까? |
|---|---|---|---|
| `P_same_time_overlap` | P | t=11.1에서 거리 0.0m ≤ 0.35m | "같은 때 겹치나?" |
| `N_same_route_different_time` | N | 전 시각에서 거리 1.0m > 0.35m | "교차하는 좌표만 봤나?" |
| `U_stale_track` | U | `10.1-9.5=0.6s` > 0.5s | "너무 오래된 관측인가?" |
| `U_future_stamp` | U | `10.2 > 10.1` | "미래에서 관측했다고 기록됐나?" |
| `U_low_confidence` | U | `0.05 < 0.5` | "신뢰도가 기준 미만인가?" |
| `U_frame_mismatch` | U | 로봇 `map`, 사람 `odom` | "다른 좌표계를 그대로 뺐나?" |
| `U_missing_last_sample` | U | 16개가 아니라 15개 | "시각 13.1이 빠졌나?" |
| `U_time_jump` | U | index 7의 11.5s → 11.54s | "0.2초 규칙을 어겼나?" |

**중요한 인과관계:** 프레임 mismatch는 `evaluate_case()`의 사전검사에서 U가 되고, 나머지 U의 주요 판정은 학생 `classify_time_indexed()`의 유효성 규칙에서 구현합니다. 초기에 U 6개가 모두 PASS여도 초기 함수가 **무조건 U를 반환하기 때문**일 수 있습니다. P와 N이 올바른지 반드시 확인하세요.

## 13. HTML 시간 슬라이더 데모 — 실행 8

WSL2 + Windows 브라우저를 사용하는 경우:

```bash
explorer.exe "$(wslpath -w /tmp/axia-d13/P_same_time_overlap.html)"
explorer.exe "$(wslpath -w /tmp/axia-d13/N_same_route_different_time.html)"
```

일반 Linux 데스크톱은 파일 탐색기에서 HTML을 더블클릭하거나 설치된 웹 브라우저에서 `/tmp/axia-d13/P_same_time_overlap.html`을 열면 됩니다. **HTML은 로컬 파일이고 인터넷이나 ROS 노드가 없어도 동작하도록 만들어졌습니다.**

브라우저 화면에서 **시간 슬라이더를 11.1초**로 움직입니다. 파란 원=로봇 점유 원, 빨간 원=예측 사람 점유 원, 아래의 `동시간 거리`와 `반경 합`을 읽습니다. P 예제는 `0.000m / 0.350m / YES`, N은 `1.000m / 0.350m / NO`가 됩니다.

**매우 중요:** 화면의 `기하학적 겹침 YES/NO`는 시각화 JavaScript의 해당 시각 계산입니다. `actual=U`인 미완성 학생 코드 상태에서도 화면은 YES라고 할 수 있습니다. **시각화가 분류기를 자동으로 완성하거나 실제 로봇을 멈추지 않습니다.**

**GUI가 안 뜨면 수업을 멈추지 마세요.** 아래 명령으로 동일한 실습의 `expected/actual`을 확인하고 화면 검증을 **HTML_BROWSER_NOT_RUN**으로 기록합니다.

```bash
test -s /tmp/axia-d13/d13_results.json && echo JSON_PRESENT
python3 -m json.tool /tmp/axia-d13/d13_results.json
```

위 CLI/JSON이 정상이어도 **브라우저를 열어 본 사실**을 임의로 PASS 처리하지 않습니다.

## 14. 초심자 디버깅 표: 무엇부터 확인할까?

| 오류/상태 | 주로 발생하는 이유 | 처음 할 일 |
|---|---|---|
| `git clone`에 `destination path ... already exists` | 같은 폴더에 이미 자료 있음 | 새 폴더 이름으로 클론, 기존 작업 보존 |
| `git: command not found` | Git 미설치 | Ubuntu에서 Git 설치 |
| `python3: command not found` | Python 미설치 | Ubuntu에서 Python3 설치 |
| `No such file or directory` | 명령 실행 폴더가 다름 | `pwd`, `cd ~/axia-d13-student` |
| `ModuleNotFoundError` | 경로 불일치/다른 Python 파일 실행 | 저장소 루트와 파일 경로 확인 |
| `SyntaxError` / `IndentationError` | 괄호·콜론·들여쓰기 오류 | `python3 -m py_compile ...`, 줄 번호 확인 |
| `FAILED (failures=2)` 초기 상태 | 정상 TODO 시작 상태 | P/N 알고리즘을 단계별 구현 |
| `ERROR` 발생 | 실행 중 코드 예외 | 트레이스의 처음 문제가 생긴 줄·자료 확인 |
| N인데 P | 같은 시각이 아닌 서로 다른 시간 비교 | `t_sec` 동기화 |
| U인데 N | stale/future/NaN/누락 검사 불충분 | 첫 무효 관측·시간 인덱스 검사 |
| 앞에서 P인데 뒤에 NaN | 너무 이른 P 반환 | 모든 16개 유효성 검사 후 결론 |
| `runner_rc=2` | 현재 예측과 fixture 정답 불일치 | `d13_results.json`의 최초 불일치 ID 확인 |
| HTML 안 열림 | WSLg/브라우저/경로 문제 | JSON·CLI로 대체, GUI는 NOT_RUN |
| Gazebo 창 없음 | 이 수업은 Gazebo를 실행하지 않음 | 문제가 아님 |

`FAILED`와 `ERROR`를 구별하고, 마지막 예외만 보지 말고 **가장 먼저 깨진 입력 조건·시간 index**를 찾는 연습을 합니다. 동일한 현장 오류를 반복해서 재시도하는 것은 해결이 아닙니다.

## 15. 제출 전 최종 점검 — 실행 9

학생의 개인 파일 수정은 **`block_D/day13/reachability_student.py` 하나만**이어야 합니다. (워크시트는 별도 제출 문서로 작성합니다.)

```bash
cd ~/axia-d13-student
python3 -m py_compile block_D/day13/reachability_student.py
python3 -m unittest discover -s block_D/day13/tests -p 'test_*.py' -v
echo "student_tests_rc=$?"
python3 block_D/day13/run_lab.py --out /tmp/axia-d13
echo "runner_rc=$?"
git diff --name-only
git rev-parse HEAD
```

**성공 목표:** `Ran 10 tests ... OK`, `student_tests_rc=0`, `D13_STUDENT_RESULT=GREEN`, `runner_rc=0`, JSON 8/8 일치. **미완성이어도 결과를 조작하지 말고** 실제 실패 출력과 원인을 제출하세요.

**제출할 것:** (a) 수정한 `reachability_student.py`, (b) `STUDENT_WORKSHEET_KO.md` 활동 A–E, (c) unittest 로그·종료 코드, (d) `d13_results.json`, (e) 대표 P/N/U HTML 관찰 캡처 또는 JSON 대체 증거, (f) `git rev-parse HEAD`와 `git diff --name-only` 결과. 강사 정답 파일·비공개 코드는 제출하거나 학생 저장소로 복제하지 않습니다.

평가(100점): 입력 유효성 25, 동시간 P/N 30, U 6반례 20, 시각화 및 결과 해설 15, 실제 안전 경계 설명 10.

**학생 개인 테스트와 배포 검증은 다릅니다.** `block_D/tools/verify_student_release.py`는 배포된 **미완성 Starter**를 점검하는 명령이라 P/N의 의도된 RED 2건을 기대합니다. 학생이 TODO를 구현한 작업 폴더에서 이 배포 검사를 실행해 PASS를 목표로 삼지 마세요. 학생 완성은 위 `day13/tests`와 `run_lab.py`로 평가합니다.

## 16. 한 페이지 총정리와 학습 성찰

1. **Reachability 주제:** 우리는 등속도 사람 중심 위치를 16개 시점에서 예측하고 고정 반경을 더해 시간별 점유영역을 만들었습니다. 모든 가능 경로의 보장된 Reachability는 아닙니다.
2. **공간예측·충돌 판정 주제:** 같은 t에서 로봇 원과 사람 원의 중심거리를 계산하고, 한 번이라도 겹치면 P, 전 구간 유효·비중첩이면 N, 판단 불가면 U입니다.
3. **시스템 데이터 흐름:** CSV/JSON → `load_cases()` → `evaluate_case()` → 학생 `classify_time_indexed()` → CLI/JSON/HTML. `unittest`는 별도 검증 경로입니다.
4. **실습의 원칙:** 처음의 P/N 2개 RED는 의도된 출발점. TODO를 구현하고 테스트 결과로 GREEN을 증명합니다.
5. **안전 경계:** P/N/U는 주행 허가·실제 STOP 증거가 아닙니다. SW Stop은 **인증 E-Stop**과 다릅니다. ROS/Gazebo/WSL2 로봇 안전 인수는 이번 시간에 NOT_RUN입니다.

**학습 성찰 질문:** "같은 장소를 지나도 N인 이유는?", "U가 N보다 먼저 판단돼야 하는 사례는?", "HTML에서 원이 겹치는데 actual=U라면 어느 함수부터 확인할까?" 정답 문장을 외우는 것보다 **시간과 코드 처리 순서**를 연결해 설명해 보세요.

> 이 수업에 필요한 것은 새로운 로봇 제어기를 만드는 것이 아니라, 입력 데이터가 왜 유효한지와 **같은 시각의 점유영역 중첩**이라는 판단 근거를 정확하게 검증하는 능력입니다.
