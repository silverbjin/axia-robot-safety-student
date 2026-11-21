# AXIA BLOCK_D D14 — 초심자부터 따라 하는 정책 안전 실습

**수업:** 2026-11-26(목) 19:00–22:00, 3시간 · **환경:** WSL2 Ubuntu 24.04 또는 Ubuntu 24.04, Python 3 · **준비:** 터미널 1개, Git, 텍스트 편집기 (ROS/Gazebo 불필요).
**실습 범위:** `OFFLINE_SYNTHETIC_L0_NO_ROS_GAZEBO`. 로봇/사람/센서/상태 전이는 합성 데이터다. 소프트웨어 **SW Stop**과 실제 인증된 **E-Stop**은 다르다.

- **실습 목표 1 — 사람 접근·고장 신호·예측 위험:** D13의 P/N/U를 검토하고 `LIMITED_REQUEST`를 내거나 유지하는 조건을 설명한다.
- **실습 목표 2 — 감속·회피·정지:** SLOW(속도 제한), AVOID(경로 재계획 요청), STOP(안전 정지)의 실제 담당 계층과 선택 기준을 시나리오로 분류한다. 이 Starter의 `choose_action_intent()`는 **NOT_IMPLEMENTED**; 별도 동작 선택기나 `/cmd_vel` 출력은 없다.
- **실습 목표 3 — 증거:** 정책 단위 테스트 20개와 합성 fixture 16개를 통과시킨 뒤 G10의 최초 장애·Latch·zero 명령·Cancel·Reset 순서를 설명한다.

[학생용 데모 순서](STUDENT_DEMO_GUIDE_KO.md)와 [빈칸 워크시트](STUDENT_WORKSHEET_KO.md)를 함께 사용한다.

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
git clone --depth 1 --branch main \
  https://github.com/silverbjin/axia-robot-safety-student.git axia-d14-student
cd ~/axia-d14-student
git rev-parse HEAD
python3 --version
ls -l block_D/day14/
```

**기대:** `risk_policy_student.py`, `run_lab.py`, `fixtures/`, `tests/`, 본 문서가 보인다. `git rev-parse HEAD`의 결과는 **강사가 당일 공지한 SHA**와 비교해 제출한다. 기존 폴더가 존재하면 삭제하지 말고 새로운 클론 폴더명을 쓴다.

폴더 위치를 잊었다면 `pwd`에서 `.../axia-d14-student`인지 확인한다. **모든 아래 명령은 저장소 루트에서 실행**한다.

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

## 5. RED: 실패를 먼저 확인하고 증거를 남긴다

```bash
mkdir -p "$HOME/axia-d14-evidence"
set +e
python3 -m unittest discover -s block_D/day14/tests -p 'test_*.py' -v \
  2>&1 | tee "$HOME/axia-d14-evidence/red_tests.log"
TEST_RC=${PIPESTATUS[0]}
set -e
printf 'UNITTEST_RC=%s\n' "$TEST_RC"
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

## 6. Python 코드 읽기: 구조부터 파악

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

## 8. 재실행: 16개 시나리오 / expected vs actual

```bash
set +e
python3 block_D/day14/run_lab.py --out /tmp/axia-d14 \
  2>&1 | tee "$HOME/axia-d14-evidence/runner.log"
RUNNER_RC=${PIPESTATUS[0]}
set -e
printf 'runner_rc=%s\n' "$RUNNER_RC"
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

## 9. 실무 상황 3개: 감속·회피·정지의 정책 **의도** 설계

이 단계는 26장 수업의 **사례 판단·워크시트 실습**이다. Starter에는 `choose_action_intent()`가 **NOT_IMPLEMENTED** 상태이며 SLOW/AVOID/STOP을 발행하는 새 실행기나 테스트도 없다.

| 현실적인 상황 | 학생이 기록할 의도 | 실제 처리 담당과 주의 |
|---|---|---|
| 사람 접근, 신뢰 가능한 거리·속도 정보, 아직 유효한 완충 공간 | `SLOW_INTENT` | Nav2 속도 제한/Collision Monitor slowdown 등으로 **별도** 구현·검증해야 한다 |
| 이동 경로를 막는 카트, 대체 경로가 지도·Costmap에 있고 센서·위치 추정 정상 | `AVOID_REQUEST` | Nav2 Planner/Controller/Costmap이 **경로를 재계획**; 학생 정책만으로 회피가 일어나지 않는다 |
| 사람 근접·예측 위험 P, 알 수 없는 U, Scan Fault 또는 보호신호 만료 | `STOP_INTENT` 또는 더 보수적 제한 | 실제 CM/Guard/Supervisor의 정지 여부와 측정은 별도; 소프트웨어 SW Stop≠인증 E-Stop |

**설계 질문:** 정지와 회피를 동시에 요청하고 싶을 때 어떤 보호 계층을 우선해야 할까? **보호 정지를 우선하며** 보호 상태가 해제되지 않은 경우 Planner의 새 경로를 로봇 동작으로 사용하면 안 된다. 또한 D14의 P/U 정책 결과 `LIMITED_REQUEST`를 임의로 `AVOID_REQUEST`로 치환하지 않는다.

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
