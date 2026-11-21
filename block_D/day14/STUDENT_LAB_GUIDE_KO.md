# AXIA BLOCK_D D14 — 초심자부터 따라 하는 정책 안전 실습

**수업:** 2026-11-26(목) 19:00–22:00, 3시간 · **환경:** WSL2 Ubuntu 24.04 또는 Ubuntu 24.04, Python 3 · **준비:** 터미널 1개, Git, 텍스트 편집기 (ROS/Gazebo 불필요).
**실습 범위:** `OFFLINE_SYNTHETIC_L0_NO_ROS_GAZEBO`. 로봇/사람/센서/상태 전이는 합성 데이터다. 소프트웨어 **SW Stop**과 실제 인증된 **E-Stop**은 다르다.

- **실습 목표 1 — 사람 접근·고장 신호·예측 위험:** D13의 P/N/U를 검토하고 `LIMITED_REQUEST`를 내거나 유지하는 조건을 설명한다.
- **실습 목표 2 — 감속·회피·정지:** SLOW(속도 제한), AVOID(경로 재계획 요청), STOP(안전 정지)의 실제 담당 계층과 선택 기준을 시나리오로 분류한다. 이 Starter의 `choose_action_intent()`는 **NOT_IMPLEMENTED**; 별도 동작 선택기나 `/cmd_vel` 출력은 없다.
- **실습 목표 3 — 증거:** 정책 단위 테스트 20개와 합성 fixture 16개를 통과시킨 뒤 G10의 최초 장애·Latch·zero 명령·Cancel·Reset 순서를 설명한다.

[학생용 데모 순서](STUDENT_DEMO_GUIDE_KO.md)와 [빈칸 워크시트](STUDENT_WORKSHEET_KO.md)를 함께 사용한다.

## 초심자용 출발 안내 — 이 문서를 읽는 순서

**이 문서는 학생 정답 코드가 아니라 실행·사고과정·관찰 방법을 알려주는 안내서**입니다. `apply_verdict()`와 `expired_verdict()`의 구현은 스스로 완성합니다. 교재에는 각 단계의 입력, 왜 실행하는지, 예상 출력, 오류가 났을 때 먼저 볼 것을 함께 적었습니다.

| 단계 | 먼저 무엇을 하나? | 통과 확인 | 실제로 제출할 증거 |
|---|---|---|---|
| **체크포인트 A** | 저장소 클론, Python/Git, JSON 입력 읽기 | 경로·버전·합성 16/15 확인 | Git SHA와 fixture 개수 |
| **체크포인트 B** | 학생 TODO의 최초 RED 확인 | 20개 중 예상 실패 11개, unittest rc=1, runner rc=2 | 최초 실패 로그·JSON |
| **체크포인트 C** | 두 TODO를 직접 구현하고 GREEN 재검 | 학생 20/20 및 합성 사례 16/16 | GREEN 로그·예상/실제 비교 |
| **체크포인트 D** | G10 최초 사건·정책 선택·증거 제출 | 안전 경계 설명 + 제출 파일 존재 | 최종 워크시트·로그·본인 코드 |

**처음 보는 용어 7개**

- **터미널:** 명령을 입력하는 창. `# AXIA BLOCK_D D14 — 초심자부터 따라 하는 정책 안전 실습

**수업:** 2026-11-26(목) 19:00–22:00, 3시간 · **환경:** WSL2 Ubuntu 24.04 또는 Ubuntu 24.04, Python 3 · **준비:** 터미널 1개, Git, 텍스트 편집기 (ROS/Gazebo 불필요).
**실습 범위:** `OFFLINE_SYNTHETIC_L0_NO_ROS_GAZEBO`. 로봇/사람/센서/상태 전이는 합성 데이터다. 소프트웨어 **SW Stop**과 실제 인증된 **E-Stop**은 다르다.

- **실습 목표 1 — 사람 접근·고장 신호·예측 위험:** D13의 P/N/U를 검토하고 `LIMITED_REQUEST`를 내거나 유지하는 조건을 설명한다.
- **실습 목표 2 — 감속·회피·정지:** SLOW(속도 제한), AVOID(경로 재계획 요청), STOP(안전 정지)의 실제 담당 계층과 선택 기준을 시나리오로 분류한다. 이 Starter의 `choose_action_intent()`는 **NOT_IMPLEMENTED**; 별도 동작 선택기나 `/cmd_vel` 출력은 없다.
- **실습 목표 3 — 증거:** 정책 단위 테스트 20개와 합성 fixture 16개를 통과시킨 뒤 G10의 최초 장애·Latch·zero 명령·Cancel·Reset 순서를 설명한다.

[학생용 데모 순서](STUDENT_DEMO_GUIDE_KO.md)와 [빈칸 워크시트](STUDENT_WORKSHEET_KO.md)를 함께 사용한다.

 같은 예시 프롬프트 기호는 붙여 넣지 않습니다.
- **클론(clone):** GitHub에 있는 *공개* 학생 저장소를 내 컴퓨터 폴더에 복사하는 것. 타인의 파일이나 강사용 정답을 복사하는 것이 아닙니다.
- **함수(function):** 입력을 받아 결과를 반환하는 Python 코드 묶음. 여기서는 실제 로봇을 구동하지 않습니다.
- **fixture:** 테스트를 위해 미리 만들어 둔 **합성** 입력 자료. 실제 센서 수집 기록이 아닙니다.
- **assertion:** 코드의 실제 결과가 예상값과 같은지 검사하는 문장. 통과 못하면 실패 위치를 알려 줍니다.
- **RED / GREEN:** 실패하는 요구를 먼저 보고(TDD), 코드를 고쳐 통과시키는 학습 순서. *의도된 RED*와 *로봇 안전 인증*은 다릅니다.
- **반환 코드(rc):** 명령의 종료 상태. 보통 0은 정상 종료이며 여기서는 **단위 테스트 최초 rc=1, 정책 러너 최초 rc=2가 의도된 학습 시작 상태**입니다.

**안전 주의:** 이 실습이 만들어 내는 HTML·JSON의 `NORMAL_POLICY`와 `LIMITED_REQUEST`는 **정책 표시**입니다. 실제 모터의 동작 허용·감속·정지 명령이 아니며 **NO_ROS_GAZEBO**입니다. SW Stop은 인증된 E-Stop이 아닙니다.

---

## 1. 전체 그림: 데이터가 실제로 어디까지 흐르는가

```text
D13 P/N/U(개념적 선행 학습)
         ↓  합성 verdict + seq + provenance
policy_events.json (16개의 합성 케이스)
         ↓  load_cases()  → replay(case)
risk_policy_student.py
 ├─ apply_verdict(state,payload,now_mono,...)
 │    → (새 RiskState, action 문자열)
 └─ expired_verdict(state,now_mono)
      → True/False (호스트 수신 TTL)
         ↓
run_lab.py: trace + expected/actual 비교
 ├─ d14_policy_results.json
 └─ d14_policy_timeline.html  ← g10_events.json(15 합성 사건)
```

이 경로에 ROS Topic·실제 Supervisor·Nav2 Goal·`/cmd_vel` 발행이 **없다**. 정책의 `NORMAL_POLICY`는 실제 로봇 운행 허가가 아니며 `LIMITED_REQUEST` 역시 별도 Supervisor의 실제 `NORMAL→LIMITED` 상태 전이 증거가 아니다. **Collision Monitor는 감속/정지 보호 계층이고 Nav2 Planner/Controller·Costmap은 회피 경로계획의 별도 구성요소**다.

## 2. 3시간 시간표

| 시간 | 활동 | 실습에서 남길 것 |
|---|---|---|
| 19:00–19:20 | 식당 복도: P→N 후 자동 해제 가능? D13 회상 | P/N/U 판단표 |
| 19:20–19:50 | 데이터 파이프라인, RiskState, 권한, 수신 TTL | 입력 필드 해설 |
| 19:50–20:00 | 휴식 | |
| 20:00–20:55 | Git clone, RED, 정책 두 TODO 단계별 구현·반복 테스트 | RED/GREEN 로그, 종료 코드 |
| 20:55–21:05 | 휴식 | |
| 21:05–21:40 | SLOW/AVOID/STOP 시나리오 + G10 15사건 Replay | 정책 선택표와 사건 시간표 |
| 21:40–22:00 | 16사례 결과, 한계, 제출 | JSON/HTML, 워크시트 |

## 3. 0부터 시작: GitHub 클론

```bash
cd ~
git clone --branch main --depth 1 \
  https://github.com/silverbjin/axia-robot-safety-student.git axia-d14-student
cd ~/axia-d14-student
git rev-parse HEAD
python3 --version
ls -l block_D/day14/
```

**기대:** `risk_policy_student.py`, `run_lab.py`, `fixtures/`, `tests/`, 본 문서가 보인다. `git rev-parse HEAD`의 결과는 **강사가 당일 공지한 SHA**와 비교해 제출한다. 기존 폴더가 존재하면 삭제하지 말고 새로운 클론 폴더명을 쓴다.

폴더 위치를 잊었다면 `pwd`에서 `.../axia-d14-student`인지 확인한다. **모든 아래 명령은 저장소 루트에서 실행**한다.

### 체크포인트 A — 한 줄씩 따라 하며 환경·파일 확인

**입력하기 전에:** Windows Terminal에서 Ubuntu 탭을 열어 사용합니다. PowerShell에서 `python3`를 실행하는 것이 아니라 **WSL2 Ubuntu 내부**에서 실행합니다. WSL2가 아닌 Ubuntu라면 동일 명령을 그대로 사용합니다. 아래는 복제 후 `~/axia-d14-student`에서 실행합니다.

```bash
pwd
command -v python3
command -v git
python3 --version
git rev-parse HEAD
git status --short
test -f block_D/day14/run_lab.py && echo "RUNNER_FILE_OK"
test -f block_D/day14/fixtures/policy_events.json && echo "FIXTURE_FILE_OK"
```

- `pwd`는 현재 디렉터리이며 `.../axia-d14-student`로 끝나야 합니다.
- `command -v python3`는 Python 실행기 위치(예: `/usr/bin/python3`)를 보여줍니다.
- `git rev-parse HEAD`는 **내가 받은 코드의 정확한 커밋**입니다. 결과는 40자리 SHA이므로 강사가 공지한 수업 기준 SHA와 비교합니다. 이 문서에 적힌 예전 SHA를 최신이라고 가정하지 않습니다.
- `git status --short`가 처음에는 아무것도 표시하지 않는 것이 일반적입니다(작업 파일 미수정). 출력이 있다면 의미를 확인하고 **삭제하지 마세요**.
- 마지막 두 줄은 파일 존재 검증에 통과하면 `RUNNER_FILE_OK`, `FIXTURE_FILE_OK`를 출력합니다.

**오류가 난 경우:**

| 화면 메시지 | 원인 | 학생이 할 조치 |
|---|---|---|
| `git: command not found` | Git 미설치 | `sudo apt update && sudo apt install -y git` |
| `python3: command not found` | Python 미설치 | `sudo apt update && sudo apt install -y python3` |
| `destination path ... already exists` | 같은 이름의 기존 클론 | 삭제하지 말고 `axia-d14-student-2` 폴더명으로 클론 |
| `fatal: not a git repository` | 저장소 밖에서 실행 | `cd ~/axia-d14-student`; 위치를 바꿨다면 본인 실제 폴더명 사용 |
| `No such file or directory` | 명령 위치 또는 파일명 오타 | `pwd`와 `ls block_D/day14`부터 재확인 |

**스스로 확인:** ① 내 폴더는 어디인가? ② 오늘 다운로드한 Git SHA는 무엇인가? ③ 정책 TODO 파일과 runner 파일은 어떻게 다른가? 답을 워크시트에 적습니다.

## 4. 파일을 열기 전에 입력부터 읽기

```bash
python3 - <<'PY'
import json
from pathlib import Path
root=Path("block_D/day14/fixtures")
cases=json.loads((root/"policy_events.json").read_text(encoding="utf-8"))["cases"]
events=json.loads((root/"g10_events.json").read_text(encoding="utf-8"))["events"]
print("POLICY_CASE_COUNT=",len(cases))
print("G10_EVENT_COUNT=",len(events))
for case in cases:
    print(case["id"],"steps=",len(case["steps"]),
          "expected=",case["expected_last_action"])
PY
```

**예상:** `POLICY_CASE_COUNT=16`, `G10_EVENT_COUNT=15`. 각 사건의 `id`는 **시험 이름이 아닌 fixture 이름**이다.

| 대표 케이스 ID | 왜 필요한가? | 기대 개념 |
|---|---|---|
| `N_fresh_keeps_normal` | 초기 신선한 N | 제한 요청 없음 |
| `P_predicted_requests_limit` | 사람과 로봇의 미래 위험 P | 제한 요청 |
| `U_unknown_requests_limit` | 신뢰 불가 U | 제한 요청 (fail-closed) |
| `P_then_N_never_autoclears` | 위험 뒤 안전 N | N 하나로 기존 제한 해제 금지 |
| `U_then_N_never_autoclears` | UNKNOWN 뒤 N | 기존 제한 유지 |
| `duplicate_N_rejected` / `reordered_N_rejected` | 중복·역순 seq | 재전송 거부 |
| `invalid_scope_requests_limit` / `invalid_gate_requests_limit` | 출처·gate 계약 위반 | 의심 입력으로 제한 |
| `two_sources_requests_limit` | 복수 발행자 | 출처 신뢰 불가 |
| `invalid_sequence_requests_limit` | 음수 seq | 무효 입력 |
| `invalid_label_unknown` | `SAFE` 같은 알 수 없는 레이블 | U로 보수적 판정 |
| `N_receipt_stale_requests_limit` | 수신 후 0.52초 무갱신 | TTL 0.5초 초과 |
| `N_clock_regression_requests_limit` | monotonic 시계 역행 | 만료 처리 |
| `no_owned_goal_cannot_arm` / `unhealthy_robot_cannot_arm` | Goal 소유권·장치 건전성 없음 | 권한 생성 불가 (동작 허가 아님) |

**중요:** 마지막 두 케이스는 요청 제한이 `False`여도 *로봇이 안전하게 주행 가능하다는 뜻이 아니다*. `NO_OWNED_HEALTHY_GOAL`은 아예 새 제어 권한을 발급하지 않는다는 별도 결과이다.

### 합성 입력 한 건을 해부해 보기: list, dict, expected

바로 코드를 작성하기 전에 JSON 구조부터 확인합니다. **학생이 직접 코딩해도 실행기는 바뀌지 않는 읽기 전용 조회**입니다.

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path("block_D/day14/fixtures/policy_events.json")
data = json.loads(p.read_text(encoding="utf-8"))
case = next(c for c in data["cases"] if c["id"]=="P_then_N_never_autoclears")
print("CASE_ID=", case["id"])
print("STEP_COUNT=", len(case["steps"]))
for index, step in enumerate(case["steps"], 1):
    print("STEP", index, "seq=", step.get("seq"), "verdict=", step.get("verdict"), "time=", step.get("mono"))
print("EXPECTED_ACTION=", case["expected_last_action"])
print("EXPECTED_LIMITED=", case["expected_limited"])
PY
```

**예상 화면(기준 fixture):**

```text
CASE_ID= P_then_N_never_autoclears
STEP_COUNT= 2
STEP 1 seq= 0 verdict= P time= 5
STEP 2 seq= 1 verdict= N time= 5.1
EXPECTED_ACTION= KEEP_LIMITED_NO_AUTOMATIC_CLEAR
EXPECTED_LIMITED= True
```

**왜 이런 결과를 기대할까?** 5.0초의 P에서 이미 보호 제한을 요청했고, 5.1초의 N은 *새 예측에서 겹침이 없다는 사실*만 나타냅니다. 센서 데이터가 정상이어도 위험 래치를 해제할 권한까지 증명하지는 않습니다. 그래서 `EXPECTED_LIMITED=True`입니다.

- `dict`는 `{"seq":0,"verdict":"P"}`처럼 **이름(key)과 값(value)**이 짝인 Python 자료형입니다.
- `list`는 `cases`나 `steps`처럼 **여러 dict를 순서대로 담은 자료형**입니다.
- `True`/`False`는 Python의 `bool` 값이며 JSON의 `true`/`false`와 표기가 다릅니다.
- `case["expected_last_action"]`은 **시험이 기대하는 답**입니다. **학생 코드의 실제 결과**는 나중에 `d14_policy_results.json`의 `actual_last_action`에서 읽습니다. 기대값을 바꾸는 것은 실습이 아닙니다.

**미니 질문:** `N_fresh_keeps_normal`과 `P_then_N_never_autoclears`는 모두 최종 N을 받을 수 있습니다. 왜 정책 결과가 다를까요? `limited_by_risk` 기억 여부로 설명해 봅니다.

## 5. RED: 실패를 먼저 확인하고 증거를 남긴다

```bash
mkdir -p "$HOME/axia-d14-evidence"
(
  set +e
  python3 -m unittest discover -s block_D/day14/tests -p 'test_*.py' -v \
    2>&1 | tee "$HOME/axia-d14-evidence/red_tests.log"
  TEST_RC=${PIPESTATUS[0]}
  printf 'UNITTEST_RC=%s\n' "$TEST_RC"
)
```

**원본 Starter 예상 결과(실행한 출력이 아니라 기준):**

```text
Ran 20 tests in ...s
FAILED (failures=11)
UNITTEST_RC=1
```

- 총 20개 = 정책 15개 + fixture/HTML/무제어 보존 5개.
- 최초 11개 FAIL은 코드를 직접 구현할 공간이 남아 있다는 신호다.
- 강사 또는 CI에서 Starter의 **의도된 RED를 확인한 PASS**와 학생이 직접 작성한 **GREEN**은 다르다.
- 테스트 기대값을 바꾸거나 원본 비공개 정답을 가져오지 않는다.

### 체크포인트 B — 실패를 안전하게 수집하기

**왜 괄호 `(` ... `)`로 묶을까?** 터미널에 `set -e`가 남아 있으면 실패 명령 뒤 창이 종료될 수 있습니다. 아래는 별도 **서브셸(subshell)**에서만 테스트를 실행하므로 부모 터미널 설정을 건드리지 않습니다. `tee`는 화면과 로그 파일에 동시에 쓰고, `${PIPESTATUS[0]}`은 `tee`가 아닌 **테스트 본체의 종료 코드**를 가져옵니다.

```bash
cd ~/axia-d14-student
mkdir -p "$HOME/axia-d14-evidence"
(
  set +e
  python3 -m unittest discover -s block_D/day14/tests -p 'test_*.py' -v \
    2>&1 | tee "$HOME/axia-d14-evidence/red_tests.log"
  TEST_RC=${PIPESTATUS[0]}
  printf 'UNITTEST_RC=%s\n' "$TEST_RC"
)
```

**원본 Starter라면 예상:** `Ran 20 tests`, `FAILED (failures=11)`, `UNITTEST_RC=1`. 실패 메시지에서 `AssertionError` 아래의 예상/실제 값을 비교합니다. 예컨대 P의 기대 `LIMIT_ON_PREDICTED_P`와 실제 `D14_TODO_NOT_IMPLEMENTED`가 다르면 **작동해야 할 기능을 학생이 아직 쓰지 않았다는 뜻**입니다.

**주의:** 공개 CI가 의도된 RED를 검출해서 PASS라고 해도 **학생 프로그램 GREEN은 아닙니다**. 단위 테스트 실패 숫자를 억지로 줄이려고 공개 테스트 파일을 편집하지 않습니다.

정책 runner도 동일한 방식으로 실행합니다.

```bash
(
  set +e
  python3 block_D/day14/run_lab.py --out /tmp/axia-d14 \
    2>&1 | tee "$HOME/axia-d14-evidence/red_runner.log"
  RUNNER_RC=${PIPESTATUS[0]}
  printf 'RUNNER_RC=%s\n' "$RUNNER_RC"
)
```

**원본 Starter의 예상 표식:**

```text
D14_G10_SYNTHETIC_EVENT_COUNT=15
D14_STUDENT_RESULT=RED_EXPECTED_TODO
RUNNER_RC=2
```

**보너스 확인:** `test -s /tmp/axia-d14/d14_policy_results.json && echo "JSON_CREATED"`. 이 결과는 **파일 생성 성공**일 뿐 학생 알고리즘 성공이 아닙니다.

**어느 실패를 먼저 고칠까?** 아래 순서대로 따라가면 Python 초심자도 한 번에 모든 테스트를 이해할 필요가 없습니다. 시험 이름과 실제 파일 경로를 연결해 둡니다.

## 6. Python 코드 읽기: 구조부터 파악

**실습의 정확한 함수명:** `apply_verdict()`와 `expired_verdict()`를 수정한다. 두 함수의 호출 시 매개변수와 반환형은 아래에서 해설한다.

`block_D/day14/risk_policy_student.py`를 열어본다.

```python
@dataclass(frozen=True)
class RiskState:
    last_seq: int = -1
    last_rx_mono: float | None = None
    ever_received: bool = False
    limited_by_risk: bool = False
    last_verdict: str = "NONE"
```

**한 줄씩 해설:**

- `@dataclass(frozen=True)`: 기존 인스턴스를 수정하지 않는 불변 상태. 새 판단에는 **새 상태 객체를 반환**해야 한다.
- `last_seq=-1`: 첫 합법 seq가 0 이상임을 비교하기 위한 시작값.
- `last_rx_mono=None`, `ever_received=False`: 아직 판정을 받지 않은 부팅 상태; *무한히 안전한 상태*를 뜻하지 않는다.
- `limited_by_risk`: 이전 위험이 남아 있는지 기록하는 래치 성격의 교육용 상태. P→N 이후에도 지우지 않는다.
- `last_verdict`: 마지막으로 정상 처리한 판정 기록. 실제 사람·로봇 위치가 아니다.

`apply_verdict(state,payload,*,now_mono,unique_source,owned_goal,healthy)`는 **두 값 `(RiskState, action)`만 반환**한다. `expired_verdict(state,*,now_mono)`는 수신 정보가 오래됐는지 **bool 하나만 반환**한다. 둘 다 ROS publisher가 아니다.

### 필수 용어

| 입력 | 의미 | 실습 관찰 |
|---|---|---|
| `verdict` | D13의 P/N/U 분류 | P/U 제한, N 이전 제한 유지 |
| `seq` | 송신자가 부여한 증가 순서 | 같은 번호 또는 감소면 재전송 |
| `scope` | 판정이 유효한 합성 시뮬레이션 범위 | 불일치 시 출처 오류 |
| `gate_accepted`, `goal_sent`, `certified_estop` | 합성 정책 계약상의 출처 메타데이터 | 예상치와 다르면 fail-closed |
| `unique_source` | 발행자가 유일한가? | False면 신뢰 불가 |
| `owned_goal`, `healthy` | 현재 Goal 소유권·장치 건전성 | False면 제어 권한 없음 |
| `now_mono`, `last_rx_mono` | 호스트 수신 단조 시간 | 0.5초 정책 receipt TTL |

**D13 사람 관측 stale 0.5초와 D14 메시지 수신 TTL 0.5초는 값이 우연히 같더라도 전혀 다른 데이터·안전 계층의 검사다.**

### 함수의 입력과 반환을 그림으로 이해하기

```text
replay(case)
   │ ① 기존 RiskState, 합성 payload, 수신시각 now_mono
   ▼
apply_verdict(state, payload, *, now_mono, unique_source, owned_goal, healthy)
   │ ② 반환: (다음 RiskState, "LIMIT_ON_PREDICTED_P" 같은 action 문자열)
   ▼
expired_verdict(state, *, now_mono)
   │ ③ 반환: bool (True면 수신 TTL 만료)
   ▼
run_lab.py의 trace 기록 → expected와 actual 비교 → JSON/HTML
```

**Python 문법을 코드에 대입해 보기**

- `def f(a,b):`는 `a,b`를 받아 함수를 정의하는 문법. `def apply_verdict(...)`는 하나의 새 상태와 action 문자열 **두 값을 튜플로 반환**해야 합니다.
- `*` 뒤에 있는 `now_mono=...` 등은 **이름을 지정해서 전달하는 키워드 인수**입니다. 순서를 헷갈려 다른 플래그로 넣는 실수를 막습니다.
- `isinstance(state, RiskState)`는 입력이 맞는 상태형인지 확인합니다.
- `@dataclass(frozen=True)`는 필드를 직접 바꿀 수 없는 설정입니다. 예: `state.limited_by_risk=True` 같은 **직접 대입은 오류**가 납니다. `dataclasses.replace`를 참고하면 기존 값을 보존한 새 객체를 생성할 수 있지만 **어떤 조건에서 업데이트할지는 스스로 작성해야 합니다.**
- `type(seq) is int`를 검사하는 이유: Python의 `True`도 `isinstance(True,int)`가 참이므로, 무효한 `seq=True`를 시퀀스 1로 잘못 받아들이지 않기 위함입니다.
- `return state, "NO_OWNED_HEALTHY_GOAL"`은 **Goal이 없으면 움직여도 된다는 뜻이 아니라** 새 제어 권한을 부여하지 않는다는 뜻입니다.

### 0.5초 TTL을 직접 계산하고 확인하기

D13 관측 stale와 혼동하지 않게 **호스트 수신 시각**만 사용합니다.

```python
last_rx_mono = 5.0
now_mono = 5.52
age = now_mono - last_rx_mono  # 0.52초
expired = age > 0.5           # True: TTL 초과
```

- 5.30초라면 age 0.30초 → `False`.
- 정확히 5.50초라면 age 0.50초 → 경계값 자체는 **초과가 아니므로 False**.
- 5.52초라면 age 0.52초 → `True`.
- 시계가 4.00초로 **역행**했다면 정상 시간 간격이 아니므로 `True`.
- 첫 판정 수신 이전(`ever_received=False`)의 부팅 예외는 `False`이지만 **안전한 주행을 승인한 것은 아닙니다**.
- `expired_verdict()`는 bool을 계산할 뿐 Supervisor의 상태 전이를 구현하지 않습니다.

**학생이 검토할 질문:** `seq`가 중복되어 메시지가 거절됐는데도 `last_rx_mono`를 최신 시간으로 변경하면 어떤 문제가 생길까요? 정답: 재전송만 계속해도 TTL이 갱신된 것처럼 보여 위험한 만료를 숨길 수 있습니다.

## 7. TODO 구현 순서 (정답 코드 제공 없음)

**수정 파일은 `block_D/day14/risk_policy_student.py` 하나만** 허용한다.

1. **RED-1:** `test_N_initial_healthy_normal`을 찾아 정상 최초 N에서 기대 `NORMAL_UNCHANGED_NO_FALSE_RISK`를 확인한다. 이후에도 위험 P를 무시하지 않도록 주의한다.
2. **RED-2:** `test_P_limits`, `test_U_limits`를 보고 위험 P와 알 수 없는 U가 제한을 요청하게 만든다.
3. **RED-3:** `test_N_never_clears_existing_limit`을 확인한다. **기존 P/U 위험 상태는 새로운 N 하나로 절대 해제되지 않는다.**
4. **RED-4:** `test_duplicate_or_reordered_N_rejected` 및 `test_bad_provenance_fail_closed`를 보고 `seq`, 출처, 범위를 검증한다.
5. **RED-5:** `test_stale_fresh_boundary`, `test_clock_regression_expires`, `test_unseen_initial_boot_does_not_expire`를 본다. 5.0초에 수신한 N은 5.3초에 신선, 5.52초에는 만료이고, 4.0초로 시계가 역행해도 만료로 본다.
6. **GREEN:** 20개 단위 테스트 재실행, 이어 16개 fixture 실행.
7. **REFACTOR:** 코드를 읽기 쉽게 정리하되 공개 테스트·입출력 계약·비공개 정답 파일은 건드리지 않는다.
8. **REVIEW:** `git diff --check`, `git diff -- block_D/day14/risk_policy_student.py` 확인 후 수업 과제로 제출한다.

**힌트:** dataclass 상태가 frozen이므로 `dataclasses.replace`를 공부하면 새 상태를 만들 수 있다. 단, 언제 상태를 갱신하고 언제 기존 상태를 그대로 반환해야 하는지는 학생이 테스트로 확인한다. **무조건 `N`을 반환하면 안전하지 않다.**

### 한 번에 전체 구현하지 말고 5개 작은 RED로 나누기

수정 대상은 **`block_D/day14/risk_policy_student.py` 한 파일뿐**입니다. 함수의 입력 순서나 이름은 바꾸지 않습니다. 테스트 파일과 fixture는 정답을 가르쳐 주는 **계약**이므로 수정하지 않습니다.

| 단계 | 어떤 행동을 먼저 구현할까? | 실행할 공개 테스트 | 자주 하는 실수 |
|---|---|---|---|
| ① N 시작 | 첫 N일 때 정상 정책 표시 | `test_N_initial_healthy_normal` | 초기 N과 P 이후 N을 같은 처리로 작성 |
| ② P/U 제한 | 첫 P 또는 U가 제한 요청 | `test_P_limits`, `test_U_limits` | U를 N으로 해석 |
| ③ 위험 기억 | P→N·U→N의 제한 유지 | `test_N_never_clears_existing_limit` | 새로운 N으로 `limited_by_risk=False` 변경 |
| ④ 신뢰성·순서 | `seq` 중복, scope, provenance, 출처 검사 | `test_duplicate_or_reordered_N_rejected`, `test_bad_provenance_fail_closed` | 중복 패킷에서 상태와 수신시각 갱신 |
| ⑤ 시간·권한 | stale, 역행, 부팅 예외, Goal 소유권 | `test_stale_fresh_boundary`, `test_no_owned_goal_does_not_arm` | invalid host clock, 부팅 예외 처리 누락 |

**하나의 테스트만 골라 실행하는 예 (Python `unittest -k` 지원):**

```bash
python3 -m unittest discover -s block_D/day14/tests \
  -p 'test_d14_policy.py' -k 'test_P_limits' -v
```

이 명령은 한 테스트를 빠르게 반복할 때 사용합니다. **한 테스트의 성공만으로 GREEN이라고 선언하지 말고** 전체 20개도 반드시 실행해야 합니다. `test_*.py`는 테스트 파일 패턴이고 `-k`는 시험 이름에 포함된 문자열을 찾습니다.

**학생이 직접 써 볼 3줄 설계 노트** (정답 코드가 아닙니다):
1. 위험 P를 발견했을 때 어떤 필드를 **새 상태**에 저장할까?
2. 이전 위험이 있으면 새 N의 `action` 문자열은 무엇이고 래치는 무엇을 유지해야 할까?
3. 메시지를 믿을 수 없는 경우 어떤 `action`과 상태를 반환해야 이후 실제 안전 계층이 제한을 판단할 수 있을까?

## 8. 재실행: 16개 시나리오 / expected vs actual

```bash
(
  set +e
  python3 block_D/day14/run_lab.py --out /tmp/axia-d14 \
    2>&1 | tee "$HOME/axia-d14-evidence/runner.log"
  RUNNER_RC=${PIPESTATUS[0]}
  printf 'runner_rc=%s\n' "$RUNNER_RC"
)
```

**초기 TODO의 실제 실행을 하지 않은 상태에서 기대하는 출력:**

```text
D14_G10_SYNTHETIC_EVENT_COUNT=15
D14_STUDENT_RESULT=RED_EXPECTED_TODO
D14_REPORT=/tmp/axia-d14/d14_policy_results.json
runner_rc=2
```

학생이 제대로 구현한 뒤 **실제로 확인해야 하는 목표 출력:**

```text
Ran 20 tests in ...s
OK
D14_STUDENT_RESULT=GREEN
runner_rc=0
```

`run_lab.py`가 모든 사례의 expected와 actual action 및 제한 여부를 비교한다. `runner_rc=0`은 **16개 합성 정책 사례가 일치했다**는 뜻일 뿐 Gazebo 동작 인수가 아니다.

```bash
python3 - <<'PY'
import json
from pathlib import Path
data=json.loads(Path("/tmp/axia-d14/d14_policy_results.json").read_text(encoding="utf-8"))
for x in data["cases"]:
    print(x["case_id"], "expected=", x["expected_last_action"],
          "actual=", x["actual_last_action"],
          "limited=", x["actual_limited"], "PASS=",x["pass"])
print("PASS_CASES=",sum(x["pass"] for x in data["cases"]),"/",len(data["cases"]))
PY
```

WSL2 브라우저(선택): `explorer.exe "$(wslpath -w /tmp/axia-d14/d14_policy_timeline.html)"`.
브라우저를 열지 못하면 `python3 -m json.tool /tmp/axia-d14/d14_policy_results.json | head -80`으로 계속한다. `HTML_BROWSER_NOT_RUN`을 기록한다. 파일 생성과 실제 화면의 정상 렌더링은 별도 검증이다.

### 체크포인트 C — 학생 본인 코드의 GREEN과 산출물 검증

단위 테스트 20개를 통과하는 것만으로는 16개 합성 사례가 일치했다고 증명할 수 없습니다. **두 검증을 모두** 기록합니다.

```bash
(
  set +e
  python3 -m unittest discover -s block_D/day14/tests -p 'test_*.py' -v \
    2>&1 | tee "$HOME/axia-d14-evidence/green_tests.log"
  TEST_RC=${PIPESTATUS[0]}
  printf 'UNITTEST_RC=%s\n' "$TEST_RC"
  python3 block_D/day14/run_lab.py --out /tmp/axia-d14 \
    2>&1 | tee "$HOME/axia-d14-evidence/green_runner.log"
  RUNNER_RC=${PIPESTATUS[0]}
  printf 'RUNNER_RC=%s\n' "$RUNNER_RC"
)
```

**아래는 완성된 학생 코드에서 기대하는 목표(이 대화에서 실제 실행한 출력 아님):**

```text
Ran 20 tests in ...s
OK
UNITTEST_RC=0
D14_G10_SYNTHETIC_EVENT_COUNT=15
D14_STUDENT_RESULT=GREEN
RUNNER_RC=0
```

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/tmp/axia-d14/d14_policy_results.json")
r = json.loads(p.read_text(encoding="utf-8"))
print("PASS_CASES=", sum(bool(c["pass"]) for c in r["cases"]),"/",len(r["cases"]))
print("ALL_PASS=",r["all_pass"])
for case in r["cases"]:
    if not case["pass"]:
        print("FIRST_MISMATCH=",case["case_id"])
        print("  expected=",case["expected_last_action"],"actual=",case["actual_last_action"])
        print("  expected_limited=",case["expected_limited"],"actual_limited=",case["actual_limited"])
        break
PY
```

**초기 Starter 기준 예상:** `PASS_CASES= 2 / 16`, `ALL_PASS=False`. **완성 후 목표:** `PASS_CASES= 16 / 16`, `ALL_PASS=True`. 일부만 통과했다면 `FIRST_MISMATCH`의 가장 앞선 입력·상태 전이부터 원인을 확인하고 수정합니다. 전체 결과를 PASS로 올려 보고하지 않습니다.

HTML 화면이 정상이라도 정책 코드가 아직 RED일 수 있고, HTML 브라우저 검증을 하지 않았다면 `HTML_BROWSER_NOT_RUN`입니다. 교육용 정책 L0 PASS가 실제 안전계층 실증은 아닙니다.

## 9. 실무 상황 3개: 감속·회피·정지의 정책 **의도** 설계

이 단계는 26장 수업의 **사례 판단·워크시트 실습**이다. Starter에는 `choose_action_intent()`가 **NOT_IMPLEMENTED** 상태이며 SLOW/AVOID/STOP을 발행하는 새 실행기나 테스트도 없다.

| 현실적인 상황 | 학생이 기록할 의도 | 실제 처리 담당과 주의 |
|---|---|---|
| 사람 접근, 신뢰 가능한 거리·속도 정보, 아직 유효한 완충 공간 | `SLOW_INTENT` | Nav2 속도 제한/Collision Monitor slowdown 등으로 **별도** 구현·검증해야 한다 |
| 이동 경로를 막는 카트, 대체 경로가 지도·Costmap에 있고 센서·위치 추정 정상 | `AVOID_REQUEST` | Nav2 Planner/Controller/Costmap이 **경로를 재계획**; 학생 정책만으로 회피가 일어나지 않는다 |
| 사람 근접·예측 위험 P, 알 수 없는 U, Scan Fault 또는 보호신호 만료 | `STOP_INTENT` 또는 더 보수적 제한 | 실제 CM/Guard/Supervisor의 정지 여부와 측정은 별도; 소프트웨어 SW Stop≠인증 E-Stop |

**설계 질문:** 정지와 회피를 동시에 요청하고 싶을 때 어떤 보호 계층을 우선해야 할까? **보호 정지를 우선하며** 보호 상태가 해제되지 않은 경우 Planner의 새 경로를 로봇 동작으로 사용하면 안 된다. 또한 D14의 P/U 정책 결과 `LIMITED_REQUEST`를 임의로 `AVOID_REQUEST`로 치환하지 않는다.

### 학생이 반드시 직접 판단할 네 가지 질문

1. **접근하는 사람과 여유 거리:** 아직 충돌 경계에 들어오지 않았고 센서가 신선한 경우, 왜 SLOW가 합리적일 수 있을까? 이미 P/U·보호 래치가 있다면 속도 제한만으로 충분할까?
2. **카트가 경로를 차단:** 길을 돌아갈 수 있다는 것은 *경로 계획의 결과*이지 `LIMITED_REQUEST`가 새 Goal을 전송했다는 뜻이 아닙니다. Nav2 Planner·Controller·Costmap의 역할은 무엇인가?
3. **사람 관측 누락(U)과 Scan Fault:** 위험을 안전하다고 간주할 근거가 부족하면 왜 보호 STOP을 우선해야 할까? 현재 코드는 실제 Stop을 내보내는가? (**아니요, 정책 표시만 합니다**.)
4. **P 뒤 N:** 왜 새 N이 들어와도 과거 제한을 보존해야 할까? Owner 승인 없는 Reset/Rearm 또는 자동 재개가 위험한 이유를 설명합니다.

기억하기: 이 실습의 `choose_action_intent()`는 **NOT_IMPLEMENTED**입니다. 스스로 워크시트에 SLOW/AVOID/STOP 의도를 쓰는 활동이지, 로봇이 실제 속도를 낮추거나 경로를 다시 계산했다는 증거는 아닙니다.

## 10. G10 복합 장애 증거 분석 (합성 사건 15개)

```bash
python3 - <<'PY'
import json
from pathlib import Path
events=json.loads(Path("block_D/day14/fixtures/g10_events.json").read_text(encoding="utf-8"))["events"]
for x in events:
    print(f'{x["t_sec"]:.2f}',x["event"])
PY
```

**합성 사건의 실제 이름·시각:**

```text
0.00 GOAL_EXECUTING
0.10 ODOM_MOVING
0.20 SCAN_FAULT
0.25 CM_LOST
0.36 GUARD_LATCH
0.40 FINAL_CMD
1.70 ODOM_STOP_DWELL
1.80 NAV2_GOAL_CANCELED
2.00 RESET_REJECTED_ACTIVE_FAULT
2.20 HEALTH_RESTORED
2.30 OWNER_RESET_APPROVED
2.35 RESET_OK
2.45 OWNER_REARM_APPROVED
2.50 REARM_OK
2.60 NO_AUTO_RESUME
```

`FINAL_CMD` 안의 `vx=0,wz=0`은 **합성 zero 명령 속성**이다. `ODOM_STOP_DWELL` 안의 `stop_t=0.65`, `dwell_sec=1.05` 역시 합성이고 실제 로봇 odom이 아니다.

**첫 사건/첫 위반을 찾는다:** `SCAN_FAULT 0.20` → `CM_LOST 0.25` (50ms 차이) → `GUARD_LATCH 0.36` (CM 이후 110ms 차이). 이 숫자를 RMW 통신 지연, 안전 TTL 성능 또는 실제 정지시간이라고 주장하지 않는다. Reset은 `RESET_REJECTED_ACTIVE_FAULT`를 먼저 보고, 건강 회복·Owner 승인 이후에만 합성 `RESET_OK`가 나온다.

### 초심자용 '이벤트 시각'과 '속성 시각' 차이

G10 JSON은 **실제 로봇 로그가 아니라 시험용 시나리오**입니다. 시간표의 행 `ODOM_STOP_DWELL`은 `t_sec=1.70`초이고, 그 행 내부의 `stop_t=0.65`초는 합성 정지 시각, `dwell_sec=1.05`초는 합성 유지기간입니다. 서로 다른 필드이므로 혼동하지 않습니다.

```bash
python3 - <<'PY'
import json
from pathlib import Path
events = json.loads(Path("block_D/day14/fixtures/g10_events.json").read_text(encoding="utf-8"))["events"]
by_name = {e["event"]: e for e in events}
for name in ("SCAN_FAULT", "CM_LOST", "GUARD_LATCH", "FINAL_CMD", "ODOM_STOP_DWELL"):
    print(name, by_name[name])
print("FAULT_TO_CM_SEC=", round(by_name["CM_LOST"]["t_sec"]-by_name["SCAN_FAULT"]["t_sec"], 2))
print("CM_TO_GUARD_SEC=", round(by_name["GUARD_LATCH"]["t_sec"]-by_name["CM_LOST"]["t_sec"], 2))
print("FAULT_TO_SYNTHETIC_STOP_SEC=", round(by_name["ODOM_STOP_DWELL"]["stop_t"]-by_name["SCAN_FAULT"]["t_sec"], 2))
PY
```

**예상:** `FAULT_TO_CM_SEC=0.05`, `CM_TO_GUARD_SEC=0.11`, `FAULT_TO_SYNTHETIC_STOP_SEC=0.45`. 이벤트 `FINAL_CMD`의 `vx=0,wz=0`도 JSON에 기록된 **합성 zero 값**입니다. 위의 수치 세 개는 **실측 DDS 지연·Guard 최초 타이밍 위반·실제 odom 정지 지연이 아닙니다**.

**고장 후 재출발을 막는 순서:** `RESET_REJECTED_ACTIVE_FAULT` → `HEALTH_RESTORED` → `OWNER_RESET_APPROVED` → `RESET_OK` → `OWNER_REARM_APPROVED` → `REARM_OK` → `NO_AUTO_RESUME`. 마지막 사건은 새 안전 승인과 자동 주행 재개가 서로 다른 문제임을 보여줍니다.

## 11. 트러블슈팅

| 증상 | 최초 확인 | 해결 |
|---|---|---|
| `ModuleNotFoundError` | `pwd`가 repo 루트인가? | `cd ~/axia-d14-student` |
| `FAILED (failures=11)` | 초기 TODO인가? | 정상 RED, 테스트 수정하지 말고 TODO 구현 |
| `runner_rc=2` | `D14_STUDENT_RESULT=RED_EXPECTED_TODO`인가? | 의도된 초기 상태; 구현 후 0 목표 |
| 최초 N인데 LIMITED | 실제 seq/source/gate/scope 검증 | 입력 위변조면 LIMITED가 정상 |
| P 뒤 N이 바로 NORMAL | **첫 P가 언제 래치되었는지** | N에서는 기존 제한 유지 |
| 5.52초에 N fresh | **last_rx_mono / now_mono** | 수신 TTL 0.5초 초과인지 |
| HTML 창이 비어 있음 | JSON 파일 존재 및 CLI 결과 | JSON 대체 시연, `HTML_BROWSER_NOT_RUN` |
| STOP 증거가 없다는 질문 | 이 실습은 합성 L0인가? | 실제 odom/Goal/CM 검증은 범위 밖 |

## 12. 최종 제출 (초심자 체크리스트)

- [ ] `git rev-parse HEAD` 출력, 본인 `git status --short`, 변경한 TODO 파일
- [ ] 최초 RED 20개 중 의도된 실패 11건 로그·종료 코드 1
- [ ] 본인 구현 후 GREEN 20/20 로그·종료 코드 0 (미달이면 미달 사유 기록)
- [ ] `d14_policy_results.json`의 16개 expected/actual 비교표, `runner_rc`
- [ ] HTML 관찰 또는 `HTML_BROWSER_NOT_RUN` 기록
- [ ] `STUDENT_WORKSHEET_KO.md`의 SLOW/AVOID/STOP 의도표, G10 15사건·최초 오류·Reset 순서
- [ ] 실제 로봇 시험 미수행과 SW Stop≠E-Stop 한계 명시

출처: [Nav2 Collision Monitor 설정](https://docs.nav2.org/configuration/packages/collision_monitor/configuring-collision-monitor-node.html) · [Nav2 Concepts](https://docs.nav2.org/concepts/index.html) · [ROS 2 Jazzy QoS](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html).


### 체크포인트 D — 남이 봐도 재현할 수 있는 제출 폴더 만들기

수업 결과를 확인할 강사는 **"어떤 코드의 어떤 실행이 어떤 결과를 냈는지"** 알아야 합니다. 따라서 명령 출력과 결과 JSON을 함께 남깁니다. **원본 저장소·강사용 폴더·raw rosbag·개인 키 파일은 압축하지 않습니다.**

```bash
cd ~/axia-d14-student
mkdir -p "$HOME/axia-d14-submission"
git rev-parse HEAD > "$HOME/axia-d14-submission/git_head.txt"
git status --short > "$HOME/axia-d14-submission/git_status.txt"
git diff --check
git diff -- block_D/day14/risk_policy_student.py > "$HOME/axia-d14-submission/student_todo.patch"
cp -v block_D/day14/risk_policy_student.py "$HOME/axia-d14-submission/"
cp -v /tmp/axia-d14/d14_policy_results.json "$HOME/axia-d14-submission/"
cp -v "$HOME/axia-d14-evidence/"*.log "$HOME/axia-d14-submission/" 2>/dev/null || true
tar -czf "$HOME/axia-d14-submission.tar.gz" -C "$HOME" axia-d14-submission
ls -lh "$HOME/axia-d14-submission.tar.gz"
```

워크시트 `STUDENT_WORKSHEET_KO.md`는 학생 이름·근거를 채워 별도로 제출하거나 그 복사본을 제출 폴더에 포함해도 됩니다. `cp` 실패 시 **파일이 실제로 있는지** `ls -l`로 확인하고, 없으면 아직 실행하지 않은 단계로 돌아갑니다. `git diff --check`는 공백 오류 검사이며 코드 기능 검사를 대체하지 않습니다.

**제출 상태 문장의 예시(개인 실제 결과로 수치를 교체):**

- 학습 시작: 테스트 20개 중 의도된 RED 11개 / unittest rc=1 / 러너 rc=2
- 본인 구현 후: unittest 실제 통과 ___/20, 합성 fixture 실제 일치 ___/16
- HTML 브라우저: `HTML_BROWSER_NOT_RUN` 또는 확인 결과
- 실무 판단: SLOW/AVOID/STOP 의도표 작성 여부와 G10 최초 합성 고장 시간표
- 미검증: ROS/Gazebo/Owner Goal/실제 odom/실제 SW 정지/인증 E-Stop 전부 `NOT_RUN`

**마지막 질문:** ① `NORMAL_POLICY`가 실제 모터 허가인가? ② `LIMITED_REQUEST`가 Supervisor 실제 전이인가? ③ 0.05초는 실측 RMW 지연인가? 세 문항에 모두 “아니다”라고 근거를 설명하면 실습 경계까지 이해한 것입니다.

