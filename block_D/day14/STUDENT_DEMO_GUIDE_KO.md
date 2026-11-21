# AXIA D14 — 학생용 라이브 데모 가이드 (Git clone부터 제출까지)

> **수업:** 2026-11-26(목) 19:00–22:00 · Ubuntu 24.04 / WSL2 Ubuntu 24.04 · Python 3 표준 라이브러리
>
> **검증 범위:** `OFFLINE_SYNTHETIC_L0_NO_ROS_GAZEBO`. 이 데모는 합성 JSON의 정책 요청을 표시할 뿐 ROS 2 / Gazebo / Nav2 Goal / 실제 Supervisor·CM·Guard / `/cmd_vel`을 실행하지 않는다. **SW STOP은 인증 E-Stop이 아니다.**

## 0. 학습 목표와 실제 실습 경계

1. **사람 접근·예측 위험**: D13 P/N/U가 D14 정책 요청 `NORMAL_POLICY` 또는 `LIMITED_REQUEST`로 연결되는 이유를 설명한다.
2. **고장 신호**: G10 합성 `SCAN_FAULT → CM_LOST → GUARD_LATCH`의 최초 사건 순서와 후속 Reset/Rearm 조건을 설명한다.
3. **감속·회피·정지**: 실무에서 SLOW(속도 제한), AVOID(Nav2 Planner/Costmap), STOP(안전 계층)이 맡는 역할을 구분한다. **별도 `choose_action_intent()` 선택기는 NOT_IMPLEMENTED이며 이 수업의 현재 배포 코드는 실제 동작을 선택하거나 구동하지 않는다.**
4. `risk_policy_student.py`의 두 TODO를 스스로 구현하고 공개 20개 단위 테스트, 16개 합성 정책 사례를 확인한다.

**시연에 앞서 종이에 질문:** “P를 받았는데 0.1초 뒤 N이 오면 로봇 제한을 즉시 해제할까?” → 학생의 답을 먼저 받고 `P_then_N_never_autoclears`로 확인한다.

## 1. 클론·도구 확인 (2~3분)

강사가 안내한 공개 Student `main`에서 작업을 시작한다. 아래 명령은 **기존 폴더를 덮어쓰지 않는다**. 이미 클론했다면 2번 `cd`부터 시작한다.

```bash
cd ~
git clone --depth 1 --branch main \
  https://github.com/silverbjin/axia-robot-safety-student.git axia-d14-student
cd ~/axia-d14-student
git rev-parse HEAD
python3 --version
test -f block_D/day14/risk_policy_student.py && echo "D14_STUDENT_SOURCE_FOUND"
test -f block_D/day14/fixtures/g10_events.json && echo "D14_FIXTURE_FOUND"
```

**예상:** 40자리 Git SHA(강사 공지 SHA와 비교), Python 버전, `D14_STUDENT_SOURCE_FOUND`, `D14_FIXTURE_FOUND`. 버전·SHA는 실제 사용한 출력 그대로 기록하며 이 문서의 과거 SHA를 최신 `main`이라고 가정하지 않는다.

> `git clone`에서 *destination path already exists*가 나오면 기존 `~/axia-d14-student`를 삭제하지 말고 다른 폴더명(`axia-d14-student-2`)으로 클론한다. `git` 미설치 시 `sudo apt update && sudo apt install -y git`만 수행한다. D14에는 ROS/Gazebo 설치가 필요 없다.

## 2. 시연 A: 학생 TODO의 정상적인 최초 RED (5분)

아래 코드 블록을 **하나씩** 실행해 종료 코드를 보존한다. 파이프에 `tee`를 쓰는 경우 `$?`만 확인하면 `tee`의 성공을 테스트 성공으로 오인할 수 있으므로 `PIPESTATUS[0]`를 사용한다.

```bash
cd ~/axia-d14-student
mkdir -p "$HOME/axia-d14-evidence"
set +e
python3 -m unittest discover -s block_D/day14/tests -p 'test_*.py' -v \
  2>&1 | tee "$HOME/axia-d14-evidence/d14_red_unittest.log"
TEST_RC=${PIPESTATUS[0]}
set -e
printf 'UNITTEST_RC=%s\n' "$TEST_RC"
```

**초기 배포 상태의 예상 출력(실제 실행 기록 아님):**

```text
Ran 20 tests in ...s
FAILED (failures=11)
UNITTEST_RC=1
```

5개 fixture/scaffold 테스트는 GREEN이지만 학생의 정책 TODO에는 의도된 11개 실패가 남아 있다. **이것은 학생의 최초 RED이며 기능 PASS 또는 학생 실습 완료가 아니다.** 실행할 때 다른 수치가 나오면 먼저 실제 Git SHA와 변경 여부를 확인한다.

## 3. 시연 B: 16개 정책 사건의 HTML·JSON Replay (7분)

```bash
cd ~/axia-d14-student
set +e
python3 block_D/day14/run_lab.py --out /tmp/axia-d14 \
  2>&1 | tee "$HOME/axia-d14-evidence/d14_red_runner.log"
RUNNER_RC=${PIPESTATUS[0]}
set -e
printf 'RUNNER_RC=%s\n' "$RUNNER_RC"
ls -lh /tmp/axia-d14/d14_policy_results.json /tmp/axia-d14/d14_policy_timeline.html
```

**초기 TODO 기준 예상 출력(실제 실행 기록 아님):**

```text
D14_G10_SYNTHETIC_EVENT_COUNT=15
D14_STUDENT_RESULT=RED_EXPECTED_TODO
D14_REPORT=/tmp/axia-d14/d14_policy_results.json
RUNNER_RC=2
```

파일이 만들어지는 것과 학생 정책 코드가 GREEN인 것은 별개이다. 첫 시도에서는 16개 사례 중 기존 TODO로 우연히 일치하는 2개가 있어도 정상이다.

```bash
python3 - <<'PY'
import json
from pathlib import Path
p=Path("/tmp/axia-d14/d14_policy_results.json")
data=json.loads(p.read_text(encoding="utf-8"))
cases=data["cases"]
print("D14_CASES=", len(cases))
print("D14_PASS=", sum(c["pass"] for c in cases))
print("D14_ALL_PASS=", data["all_pass"])
for c in cases[:5]:
    print(c["case_id"], "expected=", c["expected_last_action"],
          "actual=", c["actual_last_action"], "limited=",c["actual_limited"])
PY
```

**초기 예상:** `D14_CASES=16`, `D14_PASS=2`, `D14_ALL_PASS=False`. 확인할 사건은 `N_fresh_keeps_normal`, `P_predicted_requests_limit`, `U_unknown_requests_limit`, `P_then_N_never_autoclears`이다.

## 4. 시연 C: 웹 화면 관찰 또는 GUI 없는 대체 운영 (5분)

**WSL2(Windows 브라우저):**

```bash
explorer.exe "$(wslpath -w /tmp/axia-d14/d14_policy_timeline.html)"
```

**일반 Linux:** `xdg-open /tmp/axia-d14/d14_policy_timeline.html` (선택).

브라우저에서 **NORMAL_POLICY / LIMITED_REQUEST** 두 표시, 16개 정책 사례 테이블, G10 15개 시간표를 확인한다. 정적 HTML이므로 인터넷·CDN이 필요 없으며, **화면이 열렸는지에 대한 브라우저 검증은 직접 확인할 때만 완료**로 기록한다.

**브라우저 실패 시 즉시 대체:** `python3 -m json.tool /tmp/axia-d14/d14_policy_results.json | head -80`과 3번의 출력으로 진행한다. `HTML_BROWSER_NOT_RUN` 또는 `HTML_BROWSER_FAILED`을 기록하고 Gazebo를 띄우지 않는다.

## 5. 시연 D: 위험과 고장의 원인 추적 (8분)

```bash
python3 - <<'PY'
import json
from pathlib import Path
j=json.loads(Path("block_D/day14/fixtures/g10_events.json").read_text(encoding="utf-8"))
for e in j["events"]:
    print(f'{e["t_sec"]:4.2f}s  {e["event"]}')
PY
```

이것은 **합성 시나리오**의 타임스탬프다. 우선 **첫 안전 사건** `SCAN_FAULT=0.20s`, `CM_LOST=0.25s`(합성 간격 50ms), `GUARD_LATCH=0.36s`(CM_LOST 이후 합성 간격 110ms)를 찾는다. 이 수치를 실제 ROS 메시지 RMW 지연이나 안전 TTL 검증으로 주장하지 않는다.

또한 실제 이벤트명은 `FINAL_CMD`이며 데이터의 `vx=0,wz=0`을 확인해야 **합성 zero 명령**으로 해석할 수 있다. `ODOM_STOP_DWELL`의 `stop_t=0.65`, `dwell_sec=1.05`는 **실제 odom 측정이 아니다**. `RESET_REJECTED_ACTIVE_FAULT → HEALTH_RESTORED → OWNER_RESET_APPROVED → RESET_OK → OWNER_REARM_APPROVED → REARM_OK → NO_AUTO_RESUME` 순서를 설명한다.

**토론:** "왜 `N` 한 번, 또는 `RESET_OK` 한 줄만으로 자율주행을 자동 재개하면 안 되는가?"

## 6. 실제 실습과 GREEN 확인

이제 `STUDENT_LAB_GUIDE_KO.md`를 따라 **오직** `block_D/day14/risk_policy_student.py`의 `apply_verdict()`, `expired_verdict()` TODO를 구현한다. 강사 정답 복사·테스트 수정·기존 Safety Supervisor 수정은 금지한다.

다시 2·3번을 실행한다. 개인 구현의 목표는:

```text
Ran 20 tests in ...s
OK
UNITTEST_RC=0
D14_G10_SYNTHETIC_EVENT_COUNT=15
D14_STUDENT_RESULT=GREEN
RUNNER_RC=0
```

**조건:** 본인이 구현한 후 실제로 위 값이 관측된 경우에만 GREEN이라고 보고한다. `NORMAL_POLICY`는 운행 승인, `LIMITED_REQUEST`는 실제 Supervisor FSM 전이, SLOW/AVOID/STOP은 실제 모션 명령이 아니다.

## 7. 제출 증거와 출처

다음 기록을 과제 제출물로 모은다.

- 자신의 `risk_policy_student.py` 수정본(학생 TODO만), 실제 `git rev-parse HEAD`와 `git diff -- block_D/day14/risk_policy_student.py` 출력
- RED `d14_red_unittest.log`, `d14_red_runner.log`, 구현 후 GREEN 로그(단위 테스트·러너 종료 코드 포함)
- `/tmp/axia-d14/d14_policy_results.json`과 HTML 관찰 결과(또는 `HTML_BROWSER_NOT_RUN`)
- `STUDENT_WORKSHEET_KO.md`의 16개 합성 사례 및 G10 사건 분석, P/N/U→정책 요청→실제 안전 계층 구분

**공식 참고:** [Nav2 Collision Monitor](https://docs.nav2.org/configuration/packages/collision_monitor/configuring-collision-monitor-node.html) · [Nav2 Navigation Concepts](https://docs.nav2.org/concepts/index.html) · [ROS 2 Jazzy QoS](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html). Collision Monitor의 보호 정지/감속과 Nav2의 우회 경로계획을 혼동하지 않는다.
