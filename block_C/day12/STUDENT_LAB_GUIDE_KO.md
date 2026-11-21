# AXIA Block C D12 — 초심자용 120분 실습 가이드 (클론 → JSONL → ROS → 운영자 피드백)

**수업:** 2026-11-24 19:00–22:00 (이론 60분 + **실습 120분**).  
**학습목표 1:** ROS2 알림ㆍ로그ㆍ대시보드 기반 위험 이벤트 모니터링 구조 이해.  
**학습목표 2:** 이상 이벤트 시각화 및 운영자 피드백 실습.  
**입력:** 공개 **SYNTHETIC_COURSE_FIXTURE**와 `EDUCATION_TRANSPORT_DEMO` 12개 교육용 가상 이벤트.  
**반드시 구분:** D11 비공개 IF/AE 모델 기록 ≠ D12 공개 12건 샘플. AI **WARNING** ≠ 실제 SW Stop ≠ **인증된 E-Stop**. 이 실습에 로봇 제어권은 없습니다.

## 처음 실습하는 분을 위한 길잡이

- **Trace:** 하나의 합성 사건 흐름. **Window:** 같은 Trace의 연속 Sample 묶음. **event_id:** 사건을 고유하게 추적하는 이름. **JSONL:** 한 줄에 JSON 객체 하나.
- **Publisher:** ROS 2 메시지 발행자. **Subscriber:** 같은 토픽을 받아 읽는 노드. **DiagnosticArray:** 여러 DiagnosticStatus를 담을 수 있는 메시지. **QoS:** 통신 조건. **/rosout:** ROS logger의 로그 경로.
- **Dashboard:** 여러 사건을 한눈에 관찰하는 UI. **현재 실습에서 구현되어 있는 화면은 텍스트 상태 목록/타임라인**입니다. 기존 PPT S25·S27의 클릭형 대시보드·피드백 저장 버튼은 **미구현 설계 시안**입니다.
- **운영자 피드백:** 사람의 "확인/조사/오탐 의심/품질 확인" 의견을 사건 ID와 함께 남기는 기록. 이는 안전 정지 명령이 아닙니다.
- `EXPECTED_RED`: 학생 TODO가 아직 비어 있어 의도적으로 실패하는 시험. ROS나 Gazebo의 장애를 의미하지 않습니다.


### 초심자를 위한 1분 용어 — 데이터부터 운영자 화면까지

| 용어 | 쉬운 뜻 | D12 실제 예시 |
|---|---|---|
| Raw/Sample | 한 시점의 센서 수치(본 과정은 합성) | D09의 가상 전류·토크·가속도 |
| Trace | 같은 시나리오의 연속 데이터 묶음 | TST_N_00 |
| Window | Trace 내부 연속 Sample을 묶은 구간 | 10샘플에서 통계 6개 |
| Risk score | 이상 가능성을 보여 주는 점수 | 공개 12건은 임의 점수, 실제 AE 추론 아님 |
| Threshold | 판정 기준 | 공개 FAKE 예시에서 0.5 |
| Event ID | 사건을 나중에 다시 찾기 위한 고유 ID | DEMO:TST_N_00:002 |
| JSON | 이름:값 형태의 한 데이터 객체 | {"level":"WARNING"} |
| JSONL | 한 줄당 JSON 객체 1개씩 저장 | sample_events.jsonl, 12줄 |
| Publisher | ROS 2 메시지를 보내는 노드 | ros_diagnostic_bridge.py |
| Subscriber | 같은 토픽의 메시지를 받는 노드 | ros_l1_probe.py |
| Topic | ROS 노드 사이의 데이터 채널 이름 | /axia/education/diagnostics |
| DiagnosticArray | 여러 DiagnosticStatus를 담는 진단 메시지 | 기존 C05는 1건씩 |
| QoS | 메시지 전달 정책 | 구독 호환성, depth |
| ROS 로그 | get_logger()가 남기는 로그 | /rosout에서 관찰 가능 |
| Dashboard | 사건의 시간선·건수·상세를 한눈에 보는 화면 | 현재 CLI 기반 미니 대시보드 |
| 운영자 피드백 | 사람이 확인한 사건과 판단의 기록 | operator_feedback.jsonl |

**왜 필요한가:** 센서 수치(원본), 모델 판단(경고), 전송 메시지(ROS), 사람의 판단(운영자 기록)은 서로 다른 정보입니다. 경고가 한 번 보였다는 사실과 실제 로봇이 한 번 안전 정지했다는 사실은 같지 않습니다.

~~~text
[강사 비공개 D09~D11 경로] 합성 Raw → Trace/Window → 기존 IF/AE 점수 → 104건
                                        (학생 12건과 데이터 출처가 다름)

[학생 공개 전송 경로] FAKE sample_events.jsonl 12건
                       ├─ 표준 Python → 상태별 건수·CLI 시간선
                       └─ [Jazzy 설치 PC만] ROS Bridge → DiagnosticArray 8건
                                                  → 독립 Subscriber → verdict.json

[운영자 피드백 경로] 사건 ID 선택 → 판단 근거 기록 → operator_feedback.jsonl
                                      └─ 제어권 없음, cmd_vel/Goal/Stop 발행 안 함
~~~

**학습 확인:** 클릭형 웹 대시보드의 필터 버튼·자동 저장 기능은 아직 미구현 설계 시안입니다. 이 수업에서 실제 수행하는 시각화는 Python으로 출력하는 CLI 기반 미니 대시보드와 JSONL 기록입니다.

### 실습 시작 전 — 현재 터미널을 읽는 법

이후 별도 표기가 없는 명령은 모두 학생 저장소 루트에서 실행합니다. `$HOME`은 Linux 사용자 홈 디렉터리, `pwd`는 현재 위치, `git rev-parse HEAD`는 코드의 실제 버전입니다.

~~~bash
pwd
ls block_C/day12/
git rev-parse HEAD
python3 --version
~~~

**실행 전 예상 출력:** 경로가 `axia-robot-safety-student`로 끝나고, 폴더에 STUDENT_LAB_GUIDE_KO.md / ros_transport / student_event_todo.py 등이 보입니다. 40자리 Git SHA는 학생 PC마다 달라질 수 있습니다. 기존 실행기의 `--doctor`는 Python 3.12를 요구합니다.

**첫 실패 지점:** `ls: cannot access 'block_C/day12/'`라면 지금 작업 폴더가 잘못된 것입니다. `cd "$HOME/axia_d12_course/axia-robot-safety-student"`로 이동하고 `pwd`를 다시 확인합니다. 기존 작업 파일을 지우는 `git reset --hard`를 사용하지 마세요.

**실무 사례:** 다른 프로젝트 폴더에서 명령을 실행해 잘못된 CSV를 읽는 사고가 자주 발생합니다. 코드를 디버깅하기 전에 현재 폴더, 입력 경로, Git SHA부터 확인하는 습관을 들이세요.

## 시간표와 제출물

| 구간 | 시간 | 필수 수행 | 남길 증거 |
|---|---|---|---|
| 실습 A | 20:00–20:40, 40분 | 클론·원본 확인·JSONL 12건·중복/순서·상태 시간선 | `events_view.log` |
| 실습 B | 20:40–21:20, 40분 | 실제 ROS Jazzy L1 **가능하면** 송수신 검증; 아니면 fallback 및 불가 이유 | `verdict.json` 또는 `ros_blocked.log` |
| 실습 C | 21:20–22:00, 40분 | 경고·품질 사건의 운영자 판단 기록, 인계 보고서 | `operator_feedback.jsonl`, `d12_report.md` |

네 파일 중 실습 A/C의 3개(`events_view.log`, `operator_feedback.jsonl`, `d12_report.md`)는 필수입니다. ROS 증거는 **실행 가능한 학생만** 추가합니다. 발표자료·수업 예제 출력은 **실행 전 예상 결과**이며 내 PC의 실제 출력을 반드시 구분합니다.

## 실습 A — 20:00~20:40

### A1. 공개 저장소를 처음부터 클론하기 (5분)

WSL2 Ubuntu 24.04 터미널을 열고 아래 블록을 그대로 입력합니다.

~~~bash
mkdir -p "$HOME/axia_d12_course"
cd "$HOME/axia_d12_course"
if [ ! -d axia-robot-safety-student/.git ]; then
  git clone https://github.com/silverbjin/axia-robot-safety-student.git
fi
cd axia-robot-safety-student
pwd
git status --short
git branch --show-current
git rev-parse HEAD
python3 --version
~~~

이미 클론해 둔 폴더를 사용하는 경우 **현재 main이고 수정사항이 없을 때만** 아래 명령으로 갱신합니다. 변경 파일은 덮어쓰지 않습니다.

~~~bash
if [ "$(git branch --show-current)" = main ] && [ -z "$(git status --porcelain)" ]; then
  git pull --ff-only origin main
else
  echo "D12_LOCAL_CHANGES_PRESERVED"
fi
~~~

**명령어 한 줄씩:** `mkdir -p`는 작업 폴더를 만들고 이미 있으면 그대로 둡니다. `cd`는 현재 폴더를 이동합니다. `git clone`은 저장소를 내려받습니다. `pwd`는 내가 어느 폴더인지 출력합니다. `status`는 로컬 수정 상태, `rev-parse HEAD`는 내 컴퓨터가 가진 소스의 정확한 커밋입니다. Python은 **3.12.x**를 권장합니다. 기존 작업을 임의 `reset --hard`로 지우지 마세요.

**실행 전 예상 결과:** `pwd` 경로가 `.../axia_d12_course/axia-robot-safety-student`로 끝나고 `main` 브랜치(새 클론), 40자리 SHA, Python3.12.x가 표시됩니다. 기존 클론이나 별도 브랜치이면 출력은 달라질 수 있습니다.

### A2. 데이터와 환경 점검 (5분)

~~~bash
mkdir -p "$HOME/axia_d12_course/student_evidence"
python3 block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures
bash block_C/scripts/block_c_once.sh --doctor
test -s block_C/day12/ros_transport/sample_events.jsonl
echo D12_PUBLIC_SAMPLE_PRESENT
~~~

**해설:** generator `--check`는 공개 원본의 포맷·해시·분할 검사를 호출하며 새 데이터를 무작위 생성하지 않습니다. `--doctor`는 Python3.12 조건을 확인하지만 ROS/Gazebo를 가동하지 않습니다. `test -s`는 파일이 존재하며 비어 있지 않은지 확인합니다.

**예상 출력 핵심:** `BLOCK_C_STUDENT_DOCTOR python=3.12.x`, `D12_PUBLIC_SAMPLE_PRESENT`. `python=3.13`이거나 `BLOCK_C_ENV_DIFF_BLOCKED`이면 이후 ROS 결과를 무리하게 성공 처리하지 마세요.

> 선택: pytest가 없는 PC는 Python 3.12 가상환경을 만들 수 있습니다. `python3 -m venv --system-site-packages "$HOME/axia_d12_course/.venv"`, `source "$HOME/axia_d12_course/.venv/bin/activate"`, `python -m pip install pytest==8.3.5`. WSL2에 `python3-venv`가 없거나 인터넷 연결이 없으면 **표준 라이브러리 A/C 실습을 먼저** 수행합니다. ROS Python 패키지는 공식 Jazzy 설치가 별도로 필요합니다.

### A3. 파일을 실제로 읽고 상태별 건수를 세기 (10분)

~~~bash
python3 - <<'PY' | tee "$HOME/axia_d12_course/student_evidence/events_view.log"
import json
from collections import Counter
from pathlib import Path

p = Path("block_C/day12/ros_transport/sample_events.jsonl")
events = [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]
counts = Counter(e["level"] for e in events)
print("TOTAL_EVENTS=", len(events))
for level in ("NORMAL", "CAUTION", "WARNING", "INSUFFICIENT_DATA"):
    print(level, "=", counts[level])
print("FIRST_WARNING=", next(e["event_id"] for e in events if e["level"] == "WARNING"))
print("FIRST_QUALITY=", next(e["event_id"] for e in events if e["level"] == "INSUFFICIENT_DATA"))
PY
~~~

**코드 해설:** `Path`는 파일 경로, `read_text`는 파일 내용, `splitlines()`는 줄 분리, `json.loads`는 JSON→사전 변환입니다. `Counter`는 같은 level이 몇 번 등장했는지 계산합니다. `next`는 첫 조건 일치 항목을 선택합니다. `tee`는 화면과 `events_view.log`에 동시에 출력합니다.

**실행 전 예상 출력(기본 공개 12건을 변경하지 않은 경우):**

~~~text
TOTAL_EVENTS= 12
NORMAL = 3
CAUTION = 3
WARNING = 3
INSUFFICIENT_DATA = 3
FIRST_WARNING= DEMO:TST_N_00:002
FIRST_QUALITY= DEMO:TST_N_00:003
~~~

이는 **공개 FAKE score**의 분포이지 강사 비공개 AE 성능이 아닙니다. `input_sha256 = 'a'×64`는 테스트용 placeholder이므로 원본 파일을 실제 해시한 값이라고 설명하지 않습니다.

### A4. 교육용 사건 시간선 읽기 (8분)

~~~bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path("block_C/day12/ros_transport/sample_events.jsonl")
for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
    e = json.loads(line)
    score = "UNSCORED" if e["risk_score"] is None else f'{e["risk_score"]:.2f}'
    print(f'{i:02d} | {e["source_timestamp_ns"]/1e9:.1f}s | {e["level"]:18s} | {score:8s} | {e["event_id"]}')
PY
~~~

**예상 처음 4행:** `NORMAL 0.10` → `CAUTION 0.45` → `WARNING 0.90` → `INSUFFICIENT_DATA UNSCORED`. 이 순서는 학습용 합성 이벤트입니다. `source_timestamp_ns`는 Trace 내부 시각이므로 `time.time_ns()`나 ROS 수신 시각과 빼서 지연·안전 TTL을 계산하면 안 됩니다.

**질문:** 품질 결손의 점수를 0.0이라고 만들어 NORMAL로 저장하면 어떤 일이 생길까요? → 데이터 미수신이 정상 판단으로 둔갑합니다.


### A4-1. CLI 기반 미니 대시보드 만들기 (A4와 같은 시간에 진행)

**왜 필요한가:** JSON 객체 하나만 보면 전체 사건 중 얼마나 많은 WARNING이 있는지 알기 어렵습니다. 그래서 운영자는 상태별 건수, 발생 순서, 점수와 사건 ID를 한 화면에 나란히 놓습니다. 아래 코드는 데이터를 **읽기만** 하며 새 웹 서버나 로봇 제어를 실행하지 않습니다.

~~~bash
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path

p = Path("block_C/day12/ros_transport/sample_events.jsonl")
events = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
counts = Counter(event["level"] for event in events)

print("=== D12 CLI DASHBOARD : EDUCATION ONLY ===")
for level in ("NORMAL", "CAUTION", "WARNING", "INSUFFICIENT_DATA"):
    print(f'{level:18s} {counts[level]:2d} | {"#" * counts[level]}')

print("TIME(s) | LEVEL              | SCORE    | EVENT_ID")
for e in events[:4]:
    seconds = e["source_timestamp_ns"] / 1_000_000_000
    score = "UNSCORED" if e["risk_score"] is None else f'{e["risk_score"]:.2f}'
    print(f'{seconds:7.1f} | {e["level"]:18s} | {score:8s} | {e["event_id"]}')

first = next(e["event_id"] for e in events if e["level"] == "WARNING")
print(f"D12_BEGINNER_TIMELINE_PASS events={len(events)} first_warning={first}")
PY
~~~

**실행 전 예상 출력(공개 가상 이벤트 12건 기준):**

~~~text
=== D12 CLI DASHBOARD : EDUCATION ONLY ===
NORMAL              3 | ###
CAUTION             3 | ###
WARNING             3 | ###
INSUFFICIENT_DATA   3 | ###
TIME(s) | LEVEL              | SCORE    | EVENT_ID
    0.0 | NORMAL             | 0.10     | DEMO:TST_N_00:000
    0.1 | CAUTION            | 0.45     | DEMO:TST_N_00:001
    0.2 | WARNING            | 0.90     | DEMO:TST_N_00:002
    0.3 | INSUFFICIENT_DATA  | UNSCORED | DEMO:TST_N_00:003
D12_BEGINNER_TIMELINE_PASS events=12 first_warning=DEMO:TST_N_00:002
~~~

**코드 한 줄씩 해설:**

1. `p = Path(...)`는 **입력 파일 위치**를 가리킵니다. 이 명령은 파일을 변경하지 않습니다.
2. `p.read_text(...).splitlines()`는 줄 단위로 나눕니다. JSONL은 JSON 객체가 **줄마다 하나씩** 들어 있습니다.
3. `json.loads(line)`는 한 줄의 JSON 문자열을 Python의 사전(dict)으로 변환합니다.
4. `Counter(event["level"] for event in events)`는 NORMAL 등 네 상태의 건수를 셉니다.
5. `"#" * counts[level]`는 건수만큼 문자 막대를 그립니다. 3건이면 ###이 됩니다.
6. `events[:4]`는 처음 4건을 뜻합니다. 전체 사건을 보려면 `events[:4]`를 `events`로 바꿔보세요.
7. `source_timestamp_ns / 1_000_000_000`은 **합성 Trace의 나노초를 초로 표현**할 뿐, 현재 시각이나 안전 반응 시간이 아닙니다.
8. `risk_score is None`은 **점수가 존재하지 않는 상태**를 뜻합니다. 그때 0.0이 아니라 UNSCORED로 출력합니다.
9. `next(... if ... == "WARNING")`는 첫 번째 WARNING 사건 ID를 찾아 화면에 표시합니다. 로봇을 정지시키지 않습니다.

**직접 확인:** 4건을 표시할 때와 8건을 표시할 때 첫 번째 WARNING ID는 달라지나요? 바뀌지 않습니다. 몇 줄을 화면에 보여줄지만 달라집니다.

**스스로 점검:** WARNING이 3건이라고 실제 로봇의 E-Stop이 3번 동작한 것인가요? → **아닙니다.** 교육용 WARNING은 모델·전송 예시의 상태 정보이며 인증된 E-Stop과 무관합니다.

**실무 사례:** 관제 담당자가 건수만 보고 위험이라고 단정하면 품질 불량(INSUFFICIENT_DATA)이 정상 데이터에 섞여 버릴 수 있습니다. 원본 score=null과 event_id를 함께 표시하는 이유입니다.

### A5. 코드로 실제 계약 확인 (12분)

원본을 **읽기만** 합니다.

~~~bash
sed -n '1,160p' block_C/day12/ros_transport/event_contract.py
sed -n '1,110p' block_C/day12/ros_transport/ros_diagnostic_bridge.py
~~~

다음 짧은 Python 코드를 실행합니다.

~~~bash
python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path("block_C/day12/ros_transport").resolve()))
from event_contract import EventGate, sample_events, to_diagnostic_payload

events = sample_events()
gate = EventGate(stale_after_ns=250_000_000)
gate.accept(events[0], arrival_mono_ns=1_000_000_000, arrival_wall_ns=1_700_000_000_000_000_000)
try:
    gate.accept(events[0], arrival_mono_ns=1_100_000_000, arrival_wall_ns=1_700_000_000_100_000_000)
except ValueError as exc:
    print("DUPLICATE_REJECTED=", str(exc))
print("DEMO_STALE_AFTER_250MS=", gate.stale(1_250_000_001))
for event in events[:4]:
    p = to_diagnostic_payload(event)
    print(event["level"], "->", p["level"], p["message"])
PY
~~~

**예상 출력 핵심:**

~~~text
DUPLICATE_REJECTED= duplicate event_id
DEMO_STALE_AFTER_250MS= True
NORMAL -> 0 EDUCATION ONLY / NON-CERTIFIED: NORMAL
CAUTION -> 1 EDUCATION ONLY / NON-CERTIFIED: CAUTION
WARNING -> 2 EDUCATION ONLY / NON-CERTIFIED: WARNING
INSUFFICIENT_DATA -> 3 EDUCATION ONLY / NON-CERTIFIED: INSUFFICIENT_DATA
~~~

**왜 필요한가?** 중복 event_id는 동일 사건의 반복 보고로 오해할 수 있습니다. `EventGate.stale`은 **실습용 수신 monotonic 시간**을 검사합니다. 여기서 설정한 250ms는 학습 반례를 보여주기 위한 테스트 값이며 **생산 Safety Supervisor TTL**이 아닙니다. level의 0/1/2/3은 ROS `DiagnosticStatus` 코드 OK/WARN/ERROR/STALE에 대응하지만 교육용 WARNING=ERROR는 인증된 정지가 아닙니다.

## 실습 B — 20:40~21:20, 실제 Jazzy ROS 메시지 전송(선택 조건부)

### B1. ROS 설치 여부·메시지 타입 확인 (10분)

~~~bash
if [ -f /opt/ros/jazzy/setup.bash ]; then
  echo D12_JAZZY_SETUP_PRESENT
else
  echo D12_ROS_BLOCKED_JAZZY_NOT_INSTALLED
fi
~~~

Jazzy가 있다면 **새 ROS 터미널**에서 `source /opt/ros/jazzy/setup.bash` 한 뒤 아래를 확인합니다.

~~~bash
ros2 interface show diagnostic_msgs/msg/DiagnosticArray
ros2 interface show diagnostic_msgs/msg/DiagnosticStatus
~~~

**해설:** `DiagnosticArray`는 header와 status 배열입니다. `DiagnosticStatus`는 `name`, `level`, `message`, `hardware_id`, `values`를 담습니다. level의 Python 바이트형 처리 실수가 기존 C05 실제 ROS CI에서 오류를 일으킨 전례가 있습니다. CLI는 인터페이스만 출력하므로 로봇 동작을 발생시키지 않습니다.

### B2. 독립 Publisher/Subscriber를 실제로 검증 (20분)

~~~bash
cd "$HOME/axia_d12_course/axia-robot-safety-student"
export ROS_DOMAIN_ID=92
export AXIA_BLOCK_C_EVIDENCE_DIR="$HOME/axia_d12_course/student_evidence/ros_probe"
bash block_C/scripts/block_c_once.sh --ros-l1
cat "$AXIA_BLOCK_C_EVIDENCE_DIR/ros_l1/verdict.json"
~~~

**한 줄씩:** `ROS_DOMAIN_ID=92`는 이 실습의 ROS 그래프를 다른 실험과 되도록 분리합니다. `AXIA_BLOCK_C_EVIDENCE_DIR`은 수신 로그·JSON 저장 폴더입니다. 기존 실행기 `--ros-l1`은 **실제 rclpy Publisher와 독립 Subscriber를 한 번에** 실행하고 종료합니다. 모든 `/cmd_vel*`·Nav2 Goal 발행은 없습니다.

**예상 출력 패턴(실행 전 예시, 실제 실측 아님):**

~~~text
C05_REAL_ROS_L1 {"status": "PASS_REAL_ROS_L1_EDUCATION_ONLY", "sample_count": 8, ...}
BLOCK_C_STUDENT_JAZZY_ROS_L1_ONLY_PASS owner_wsl2_verified=false
~~~

`verdict.json`에는 `period_min_ms`, `period_max_ms`, `levels`, `cmd_vel_publisher_count`, `pub_rc`도 기록됩니다. 코드의 100ms 목표 발행 주기와 **측정된 수신 주기**를 구분하세요. 이 기존 L1 검사기는 수신 간격 **20~600ms** 범위를 허용하므로 100ms의 엄격한 보증이나 생산 안전 TTL PASS라고 발표하면 안 됩니다.


### B2-1. 실제 ROS verdict.json을 직접 읽고 의미 해석하기 (B2 시간 안에)

**왜 필요한가:** 화면에 PASS라는 문구가 보이는 것만으로는 데이터가 실제로 도착했는지 알 수 없습니다. 실무에서는 실행 명령, 종료 코드, 독립 수신 건수, 수신 간격을 **같은 증거 파일**에서 비교합니다.

~~~bash
python3 - <<'PY'
import json
from pathlib import Path

p = Path.home() / "axia_d12_course/student_evidence/ros_probe/ros_l1/verdict.json"
if not p.exists():
    print("TEST_HOLD ROS_L1_NOT_MEASURED verdict.json missing")
else:
    d = json.loads(p.read_text(encoding="utf-8"))
    for k in ("status", "sample_count", "expected_count", "levels",
              "period_target_ms", "period_min_ms", "period_max_ms",
              "pub_rc", "ros_actual", "gazebo_actual",
              "production_guard_ttl_verified"):
        print(k, "=", d.get(k))
    if d.get("status") == "PASS_REAL_ROS_L1_EDUCATION_ONLY":
        print("D12_ROS_EDUCATION_EVIDENCE_PRESENT")
    else:
        print("TEST_HOLD ROS_L1_FAILED_OR_INCOMPLETE")
PY
~~~

**실행 전 예상 출력:** 실제 Jazzy 실행을 하지 않은 PC에서는 `TEST_HOLD ROS_L1_NOT_MEASURED verdict.json missing`이 표시됩니다. 이 상태는 정상적인 **미실행/HOLD**입니다. 실제 성공 로그가 생성된 PC에서만 sample_count=8, levels=[0,1,2,3], pub_rc=0, ros_actual=True 같은 필드를 확인할 수 있습니다.

**코드 한 줄씩 해설:**

1. `p.exists()`는 **내 PC에 실제 증거 파일이 생성되었는지** 확인합니다. 다른 사람의 성공 로그를 복사하지 않습니다.
2. `json.loads(...)`는 기존 독립 Subscriber가 쓴 결과 JSON을 읽습니다. JSONL 입력과 달리 verdict는 **단일 JSON 객체**입니다.
3. `sample_count`는 실제 구독자가 받은 건수, `expected_count`는 이 실행기의 목표 건수(8)입니다.
4. `levels`는 수신한 네 개 ROS 진단 코드 (0/1/2/3)입니다. 값 2는 교육 WARNING의 표시 코드이며 로봇 Stop 신호가 아닙니다.
5. `period_target_ms`는 **발행 목표 주기 100ms**, `period_min_ms/max_ms`는 독립 수신자의 **실측 수신 간격**입니다. 같은 수치일 것이라고 가정하면 안 됩니다.
6. `pub_rc`는 발행 프로세스 종료 코드입니다. 정상 종료인 0과 Subscriber 수신 증거가 모두 필요합니다.
7. `gazebo_actual=false`, `production_guard_ttl_verified=false`는 **검증하지 않은 분야를 명시**하는 올바른 결과입니다.

**최초 실패 지점 조사:** ROS_DOMAIN_ID가 달라 Subscriber가 구독하지 못할 수 있습니다. 실습에서 92를 사용한 경우 각 ROS 셸에서 `echo "$ROS_DOMAIN_ID"`를 확인하세요. 이어서 `python3 --version`과 `python3 -c "import rclpy; print('RCLPY_OK')"`를 확인합니다. venv Python으로 전환하면서 Jazzy 시스템 패키지를 찾지 못하는 경우도 있으므로, 오류의 최초 출력과 사용 Python 경로를 기록하십시오.

**실무 사례:** 프로젝트의 송신 목표 주기 100ms와 실제 DDS 수신 간격은 다릅니다. 기존 C05 테스트의 수신 주기 허용 범위는 20~600ms입니다. 이 숫자로 센서→Safety Supervisor→Stop까지의 **종단 안전 TTL**이 검증됐다고 결론내려서는 안 됩니다. 시간은 동일한 monotonic 수신 시계 안에서 비교해야 하며, 합성 source_timestamp_ns와 단순 감산하면 안 됩니다.

**스스로 점검:** 로봇을 움직이지 않고도 ROS L1을 검증할 수 있나요? → 네. 교육용 DiagnosticArray의 독립 발행/구독만 검증하고 Nav2 Goal·cmd_vel을 발행하지 않습니다.

### B3. /rosout·rqt_console과 DiagnosticArray의 차이 (10분)

- `ros2 topic echo /axia/education/diagnostics`는 **발행자가 살아 있는 동안만** 메시지를 볼 수 있습니다. `--ros-l1`의 송신기는 8건 전송 후 종료하므로 순서가 뒤바뀌면 토픽이 안 보일 수 있습니다. **토픽 미발견 = 항상 오류**는 아닙니다.
- `rqt_console`은 노드가 `get_logger().info/warn/error`로 기록한 **ROS 로그**를 살펴보는 도구입니다. 기존 Bridge는 사건별 `get_logger()` 호출을 하지 않으므로 이 수업에서 이벤트 8건이 rqt에 자동으로 쌓인다고 주장하지 않습니다.
- ROS나 GUI가 준비되지 않은 PC는 A단계 `events_view.log`와 C단계 운영자 기록을 중심으로 수행하고, `ros_blocked.log`에 미실행 사유를 기록합니다.

~~~bash
if [ ! -f /opt/ros/jazzy/setup.bash ]; then
  printf '%s\n' 'ROS_L1_NOT_RUN: Jazzy not installed; JSONL fallback completed' \
    > "$HOME/axia_d12_course/student_evidence/ros_blocked.log"
fi
~~~

## 실습 C — 21:20~22:00, 위험 이벤트 시각화와 운영자 피드백

### C1. 경고 한 건과 품질 한 건을 운영자가 판단하기 (15분)

**실무 상황:** 관제 화면의 WARNING은 고장을 확정하지 않습니다. 운영자는 사건 ID, 점수, 품질 상태, 타임스탬프를 먼저 확인합니다. 미수신·오탐·실제 장비 위험은 추가 근거가 있어야 구분됩니다.

아래 코드는 **정답을 강제로 정하지 않고** 수업용 두 사건에 대해 학생의 판단 예시를 생성합니다. `operator_action`과 `reason`은 본인의 조사 내용으로 바꿔도 됩니다.

~~~bash
python3 - <<'PY'
import json
from datetime import datetime, timezone
from pathlib import Path

src = Path("block_C/day12/ros_transport/sample_events.jsonl")
rows = [json.loads(line) for line in src.read_text(encoding="utf-8").splitlines() if line]
cases = [
    (next(e for e in rows if e["level"] == "WARNING"), "INVESTIGATE",
     "risk_score > threshold; 실제 로봇 고장 여부는 미확인"),
    (next(e for e in rows if e["level"] == "INSUFFICIENT_DATA"), "CHECK_QUALITY",
     "quality_reason 확인; 점수를 0으로 대체하지 않음"),
]
now = datetime.now(timezone.utc).isoformat()
feedback = [
    {"event_id": event["event_id"], "operator_action": action,
     "reason": reason, "reviewed_at_utc": now, "control_authority": False}
    for event, action, reason in cases
]
out = Path.home() / "axia_d12_course/student_evidence/operator_feedback.jsonl"
out.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in feedback), encoding="utf-8")
print("D12_OPERATOR_FEEDBACK_COUNT=", len(feedback))
for item in feedback:
    print(item["event_id"], item["operator_action"])
PY
~~~

**예상 출력(고정 가상 이벤트 기준):**

~~~text
D12_OPERATOR_FEEDBACK_COUNT= 2
DEMO:TST_N_00:002 INVESTIGATE
DEMO:TST_N_00:003 CHECK_QUALITY
~~~

**코드 해설:** `next`는 첫 경고·첫 품질 상태를 찾습니다. `datetime.now(timezone.utc)`는 **운영자가 검토한 실제 벽시계 시각**을 기록합니다. 이는 source_timestamp_ns와 다르며 둘의 차이는 안전 반응시간이 아닙니다. `write_text`는 내 출력 파일에 저장합니다. `control_authority=False`로 어떤 서비스·Goal·정지 명령도 요청하지 않습니다.

### C2. 파일 내용 확인 및 보고서 작성 (15분)

~~~bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path.home() / "axia_d12_course/student_evidence/operator_feedback.jsonl"
rows = [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s]
print("D12_FEEDBACK_VALID_COUNT=", len(rows))
print("D12_FEEDBACK_NO_CONTROL=", all(r["control_authority"] is False for r in rows))
assert len({r["event_id"] for r in rows}) == len(rows)
assert {r["operator_action"] for r in rows} == {"INVESTIGATE", "CHECK_QUALITY"}
PY
~~~

**예상 출력:** `D12_FEEDBACK_VALID_COUNT= 2`, `D12_FEEDBACK_NO_CONTROL= True`. 이 결과는 JSONL의 구조·운영자 의견을 확인한 것이며 **실제 로봇 위험을 해소했다는 증거가 아닙니다**.

보고서를 다음 파일에 작성합니다.

~~~bash
cat > "$HOME/axia_d12_course/student_evidence/d12_report.md" <<'EOF'
# AXIA D12 실습 보고서
- 소스 SHA: (git rev-parse HEAD 실제 결과)
- ROS 수준: L0_ONLY / ROS_L1_PASS / ROS_BLOCKED 중 1개(실제 로그 기준)
- 첫 WARNING event_id: DEMO:TST_N_00:002
- 첫 품질 오류 event_id: DEMO:TST_N_00:003
- 사건 해석: (score, threshold, quality_reason를 직접 해설)
- 운영자 피드백: INVESTIGATE / CHECK_QUALITY를 선택한 근거
- 로그·대시보드 차이: DiagnosticArray, /rosout, 설계 시안을 구분
- 안전 한계: 교육용 WARNING은 SW Stop 또는 인증된 E-Stop이 아님
- 실제 출력 vs 예상 출력: (차이를 직접 기록)
- 미검증: (현재 PC의 Jazzy/GUI/Gazebo/안전 TTL 중 미실행 항목)
EOF
~~~

### C3. 스스로 점검·제출 (10분)

- "왜 `INSUFFICIENT_DATA`를 NORMAL로 치환하면 위험한가?" → 데이터 부재를 정상 판정으로 위장하기 때문입니다.
- "`DiagnosticStatus.ERROR=2`가 명령을 발생시키는가?" → 아닙니다. 상태 정보이며 제어권이 없습니다.
- "공개 12행과 강사 AE 104행의 차이는?" → 공개 12행은 전송용 인공 가상 점수, 강사 104행은 기존 비공개 합성 모델 기록입니다.
- "대시보드가 실제로 클릭되어 저장되었는가?" → 아닙니다. 이번 기본 수업은 **터미널 시간선 + 학생의 JSONL 기록**입니다.
- "내가 실제 DDS를 검증했는가?" → `verdict.json`에 실제 ROS 수신 8건과 `pub_rc=0`이 있어야만 그렇다고 답할 수 있습니다.

**제출 경로:** `$HOME/axia_d12_course/student_evidence/`. `events_view.log`, `operator_feedback.jsonl`, `d12_report.md` 필수. ROS 가능 PC는 `ros_probe/ros_l1/verdict.json`도 포함합니다. 강사 비공개 HTML, 모델 weights, 정답 Python, hidden tests는 제출하거나 공개 저장소에 올리지 않습니다.

## 학생 TODO는 왜 아직 RED인가요? (선택 심화, 필수 120분과 별개)

~~~bash
sed -n '1,100p' block_C/day12/student_event_todo.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  block_C/tests/test_student_task_expected_red.py -k d12
~~~

**예상 실패:** `NotImplementedError: D12 TODO not implemented`. 공개 CI의 `EXPECTED_RED`와 구분합니다. 심화 과제 `make_event_jsonl(fixture_dir, output_dir)`는 입력 경로 설명과 기존 공개 테스트(`scores.csv` 파일 경로 전달)가 불일치하므로 **기본 120분 수업의 성공 조건에 넣지 않습니다.** 지도교사는 요구 인자 계약을 확정한 후 별도 TDD로 지도합니다. 강사용 완성 코드와 비공개 checkpoint를 학생 저장소로 복사하지 않습니다.

## 현장에서 자주 발생하는 오류와 첫 확인

| 오류 | 최초 확인 명령/증거 | 수업 계속 방법 |
|---|---|---|
| Git 404/Repository not found | `git remote -v` | 공개 학생 저장소 URL·인증 확인 |
| `python3: can't open file` | `pwd`, `ls block_C/day12` | 저장소 루트로 이동 |
| Python 3.13 / `ENV_DIFF_BLOCKED` | `python3 --version` | 목표 3.12로 전환, 실제 출력 보존 |
| `pytest` 없음 | `python -m pytest --version` | 표준 Python A/C 계속, 선택 테스트는 보류 |
| `NotImplementedError` | student TODO | 의도적 EXPECTED_RED |
| `ROS_L1_BLOCKED_JAZZY_NOT_INSTALLED` | `ls /opt/ros/jazzy` | ros_blocked.log + 오프라인 제출 |
| `ModuleNotFoundError: rclpy` | ROS setup/파이썬 경로 | Jazzy ROS 환경 확인, ROS PASS 주장 금지 |
| `Unknown topic` | ROS 송신기 생존·ROS_DOMAIN_ID | 독립 probe 증거 확인, 동일 재시도 반복 금지 |
| rqt가 비어 있음 | `/rosout` logger 경로 | 기존 Bridge의 print≠logger 설명 |
| JSON decode 오류 | 최초 줄 번호·raw 문자열 | 입력 파일을 원본과 비교, 자동 복구·정답 조작 금지 |

오류가 새로 발견되면 **첫 실패 시각·첫 데이터/시간 경계**를 기록합니다. 가능한 부분을 공개 CI 회귀에 RED로 추가한 후 GREEN 처리합니다. 범위를 넘어 Safety Supervisor/Collision Monitor/Nav2를 수정하지 않습니다.

**공식 학습 링크:** [ROS Jazzy Topics](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html) · [ROS Logging](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Logging.html) · [ROS QoS](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html) · [diagnostic_msgs](https://docs.ros.org/en/jazzy/p/diagnostic_msgs/index.html).
