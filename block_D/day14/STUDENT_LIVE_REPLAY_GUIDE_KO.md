# AXIA D14 — Safety Control Room 실감형 Live Replay 학생 실습 가이드

**수업:** 2026-11-26(목), ROS 2 입문자 포함 / **대상:** WSL2 Ubuntu 24.04 또는 Ubuntu 24.04, Python 3  
**실행 범위:** `OFFLINE_SYNTHETIC_L0_NO_ROS_GAZEBO` — ROS/Gazebo/Goal/Collision Monitor/Guard/Fault Injector/실제 SW Stop을 실행하지 않음. SW Stop은 인증된 E-Stop과 다르다.  
**기존 자료:** [초심자 단계별 D14 TODO 실습서](STUDENT_LAB_GUIDE_KO.md) · [데모 가이드](STUDENT_DEMO_GUIDE_KO.md) · [작성 워크시트](STUDENT_WORKSHEET_KO.md)

## 0. 오늘 학생이 직접 하게 될 일

식당에서 음식을 운반하는 로봇이 사람 접근, 카트 통로 점유, 센서 고장을 만난다고 상상한다. **26장 PPTX의 S08, S17, S21–S22, S23–S24**에 대응하는 별도의 D14 라이브 화면을 이용한다.

1. **P→N 퀴즈:** 사람 접근 판정 P 다음 N이 들어오면 과거 제한을 자동 해제해야 할까?
2. **정책 코드와 비교:** 기대 결과, 실제 Student TODO `actual`, 내 예상답을 세 개로 분리해 본다.
3. **정책 의도 분류:** SLOW·AVOID·STOP 중 무엇을 먼저 선택할까? 이것은 **워크시트 토론**이며 `choose_action_intent()`는 **NOT_IMPLEMENTED**.
4. **복합 장애 조사:** G10 합성 `SCAN_FAULT→CM_LOST→GUARD_LATCH`를 재생하고 `FINAL_CMD`, odom 유지, Goal Cancel, Reset 승인의 순서를 말로 설명한다.

이 Live Replay는 `block_D/day14/run_lab.py`의 `load_cases()`, `load_g10_events()`, `replay()`를 **호출해 결과만 보여주는 보조 화면**이다. 학생 정책 두 TODO를 대신 구현하지 않는다.

## 1. 클론부터 시작 — 한 터미널에서 직접 실행

**Windows Terminal → Ubuntu 24.04**를 열고 아래를 한 줄씩 입력한다. PowerShell에 붙여 넣는 것이 아니다.

```bash
cd ~
git clone --branch main --depth 1 \
  https://github.com/silverbjin/axia-robot-safety-student.git \
  axia-d14-live-student
cd ~/axia-d14-live-student
pwd
git rev-parse HEAD
python3 --version
ls -l block_D/day14/live_replay.py block_D/day14/live_replay_template.html
```

**예상:** `.../axia-d14-live-student` 경로, 40자리 Git SHA, Python 버전과 위 두 파일 목록이 출력된다. 이전 클론이 있다면 삭제하지 말고 **다른 폴더 이름을 지정**하고 이후 `cd`도 동일하게 바꾼다.

기억할 단어: **fixture**는 실제 로봇의 측정이 아닌 미리 정한 합성 사건, **manifest**는 화면을 생성한 당시의 사례와 정책 결과를 보관한 JSON, **replay**는 사건을 순서대로 재생하는 기능이다.

## 2. 하나의 명령으로 라이브 화면 만들기

```bash
cd ~/axia-d14-live-student
python3 block_D/day14/live_replay.py --out /tmp/axia-d14-live
echo "LIVE_GENERATOR_RC=$?"
ls -lh /tmp/axia-d14-live/
```

**원본 Student Starter에서 예상하는 출력(학생 컴퓨터에서 직접 확인한 결과로 간주하면 안 됨):**

```text
D14_LIVE_GENERATOR_L0_PASS cases=16 g10_events=15 intent=WORKSHEET_ONLY
D14_LIVE_STUDENT_GREEN=0
D14_LIVE_STUDENT_CASES_PASSED=2
D14_LIVE_HTML=/tmp/axia-d14-live/axia_d14_safety_control_room.html
D14_LIVE_MANIFEST=/tmp/axia-d14-live/d14_live_manifest.json
D14_LIVE_SCOPE=OFFLINE_SYNTHETIC_L0_NO_ROBOT_CONTROL NO_ROS_GAZEBO_GOAL
LIVE_GENERATOR_RC=0
```

**핵심:** 생성기 rc=0은 **HTML/JSON을 만들었다**는 뜻이다. `D14_LIVE_STUDENT_GREEN=0`은 학생 TODO가 미완성임을 의미하며 모순이 아니다. 본인이 정책 코드를 구현한 후 20개 테스트와 기존 16개 runner가 GREEN이라면 `D14_LIVE_STUDENT_GREEN=1`이 될 수 있다.

생성되는 정확한 파일:
- `/tmp/axia-d14-live/axia_d14_safety_control_room.html`: 로컬 단일 HTML, CSS/JS 내장. 인터넷, CDN, 별도 서버 불필요.
- `/tmp/axia-d14-live/d14_live_manifest.json`: **16개 정책 fixture 기대값 / 학생 코드 actual / 15개 G10 합성 사건**. 실제 로봇 원본 로그가 아니다.

## 3. 강의실 브라우저에서 열기 (1920×1080 권장)

WSL2에서는 다음 명령으로 Windows 브라우저를 연다.

```bash
explorer.exe "$(wslpath -w /tmp/axia-d14-live/axia_d14_safety_control_room.html)"
```

Edge/Chrome에서 페이지를 연 뒤 **F11 전체 화면**을 누른다. 일반 Ubuntu에서는 파일을 브라우저에서 직접 열거나 `xdg-open /tmp/axia-d14-live/axia_d14_safety_control_room.html`을 선택적으로 사용할 수 있다.

**브라우저가 열리지 않으면 10번의 JSON 대체 실습으로 진행한다.** 화면 GUI가 안 나온다고 G07 Gazebo를 설치하거나 실행하지 않는다. GUI를 직접 확인하지 않았다면 `HTML_BROWSER_NOT_RUN`을 기록한다.

## 4. 첫 번째 라이브 장면: P 뒤 N — 제한은 유지될까? (S08·S17)

화면 02번 패널에서 `P_then_N_never_autoclears`을 선택한다.

1. **답은 공개하지 않고** `▶ 재생`을 누른다. `5.00s / P(seq=0)` 뒤 `5.10s / N(seq=1)`이 나온다.
2. 학생이 `NORMAL_POLICY`, `LIMITED_REQUEST`, `NO_AUTHORITY` 중 하나를 고른다.
3. `예측 제출 · 답 공개`를 누르면 **내 예상 → Fixture 기대 → Student TODO actual**을 구분해 확인한다.
4. `답 가리기` 버튼으로 다른 사람에게 다시 퀴즈를 낼 수 있다.
5. 다른 사례 `N_fresh_keeps_normal`, `U_unknown_requests_limit`, `N_receipt_stale_requests_limit`도 비교한다.

**왜 P→N에서는 제한 유지인가?** 나중에 온 N은 새 예측 결과이지 이전 위험 상태를 해제할 Owner 승인 증거가 아니기 때문이다. `RiskState.limited_by_risk`에 위험 이력을 기억해야 한다.

**왜 예상·실제가 다를 수 있나?** 기본 `risk_policy_student.py`는 `D14_TODO_NOT_IMPLEMENTED`를 반환하므로 실제 출력과 fixture 기대가 일치하지 않을 수 있다. HTML은 이 오류를 **숨기지 않고 학습용 증거**로 표시한다.

**주의:** `NO_AUTHORITY`는 화면의 세 번째 정답 선택지일 뿐 실행기가 실제 Goal 권한을 생성하거나 승인하는 기능이 아니다.

## 5. 두 번째 라이브 장면: 감속·회피·정지 정책 의도 퀴즈 (S21–S22)

03번 패널에서 상황 카드를 고른다.

| 상황 카드 | 토론할 의도 | 왜? 실제 담당 계층은? |
|---|---|---|
| 신뢰 가능한 거리와 여유가 있는 사람 접근 | SLOW | 감속 정책 검토. 별도 Nav2 속도 제한 또는 Collision Monitor slowdown 검증 필요 |
| 통로를 막는 카트, 정상 지도와 우회로 | AVOID | Nav2 Planner/Controller/Costmap이 경로 재계획·실행을 별도로 담당 |
| /scan 손실 또는 CM Lost 가능성 | STOP | 신뢰할 수 있는 주행 판단이 안 되므로 보호 정지 의도가 우선 |
| 우회로가 있어도 P와 보호 제한이 존재 | STOP | 보호 상태가 우회 계획보다 우선, 자동 재출발 금지 |

`설계 해설 보기`는 강사가 준비한 **개념 정답과 이유**를 보여준다. 이것은 **실제 Python 선택기**가 아니며 **NOT_IMPLEMENTED**이므로 별도의 자동 테스트 8/8 또는 실제 속도 변화에 대한 증거로 보고하지 않는다.

**학생에게 물어볼 질문:** “카트 우회 경로가 있어도 Scan이 끊겼다면 왜 바로 회피 주행을 시작하면 안 되나요?”

## 6. 세 번째 라이브 장면: G10 15사건 조사 (S23–S24)

04번 패널의 `▶ 사건 재생`, `Ⅱ 일시정지`, `← 이전 사건`, `다음 사건 →`, 타임라인 슬라이더를 사용한다. **실제 이벤트 간 시간차를 애니메이션 재생 속도로 사용하지 않는다**; 화면의 사건 시각은 fixture 원본을 그대로 표기한다.

| t(s) | 합성 이벤트명 | 학생이 답할 질문 |
|---:|---|---|
| 0.20 | `SCAN_FAULT` | 최초 고장은 무엇인가? |
| 0.25 | `CM_LOST` | 첫 고장과 차이는? **0.05초(합성)** |
| 0.36 | `GUARD_LATCH` | CM Lost 이후? **0.11초(합성)** |
| 0.40 | `FINAL_CMD` | 이벤트 속성의 `vx=0,wz=0`을 찾아 보자 |
| 1.70 | `ODOM_STOP_DWELL` | 내부 `stop_t=0.65`, `dwell_sec=1.05`는 무엇인가? |
| 1.80 | `NAV2_GOAL_CANCELED` | 최초 Goal UUID와 일치하는가? |
| 2.00 | `RESET_REJECTED_ACTIVE_FAULT` | Fault가 남아 있을 때 Reset이 거부되는 이유는? |
| 2.20–2.60 | 복구→Owner 승인→Reset/Rearm→`NO_AUTO_RESUME` | 왜 자동 재출발하지 않나? |

`FINAL_CMD ZERO`는 **실제 이벤트명 아님**. `FINAL_CMD`라는 사건에 `vx=0`, `wz=0`의 필드가 기록되어 있을 뿐이다. `ODOM_STOP_DWELL` 역시 실제 odom 센서 데이터를 읽은 결과가 아니다.

합성 사건 간 0.05초·0.11초와 계산된 0.45초 정지 간격을 실제 RMW 지연·안전 TTL·정식 Gazebo STOP 성능으로 설명하지 않는다.

## 7. 학생 코드 GREEN 검사는 기존 실행기에서 별도로 한다

새 화면이 성공적으로 뜬 것과 **학생 TODO 구현 완료**는 별개다. 테스트 코드를 변경하지 말고 `STUDENT_LAB_GUIDE_KO.md`에 따라 `apply_verdict()`, `expired_verdict()`만 직접 구현한다.

```bash
cd ~/axia-d14-live-student
(
  set +e
  python3 -m unittest discover -s block_D/day14/tests -p 'test_*.py' -v
  echo "UNITTEST_RC=$?"
  python3 block_D/day14/run_lab.py --out /tmp/axia-d14-original
  echo "ORIGINAL_RUNNER_RC=$?"
)
```

**기존 Student Starter 예상:** 20개 단위 테스트 중 의도된 실패 11개, `UNITTEST_RC=1`; 기존 실행기 `D14_STUDENT_RESULT=RED_EXPECTED_TODO`, `ORIGINAL_RUNNER_RC=2`. 학생 구현 완료 목표는 20/20 및 16/16, 두 종료 코드 모두 0.

학생 코드를 수정했다면 **다시** `python3 block_D/day14/live_replay.py --out /tmp/axia-d14-live`를 실행하고 브라우저를 새로고침해야 새로운 actual이 반영된다. 화면의 투표는 Python 파일을 바꾸지 않는다.

## 8. JSON으로 원인 찾기 — GUI 없어도 학습 지속

```bash
python3 - <<'PY'
from pathlib import Path
import json
p=Path("/tmp/axia-d14-live/d14_live_manifest.json")
j=json.loads(p.read_text(encoding="utf-8"))
print("D14_LIVE_SCOPE=",j["scope"])
print("STUDENT_POLICY_GREEN=",j["student_policy_green"])
print("CASE_COUNT=",len(j["policy_cases"]))
print("G10_EVENT_COUNT=",len(j["g10_events"]))
for item in j["policy_cases"]:
    r=item["result"]
    if not r["pass"]:
        print("FIRST_MISMATCH=",item["id"])
        print("EXPECTED_ACTION=",item["expected_last_action"])
        print("ACTUAL_ACTION=",r["actual_last_action"])
        break
for e in j["g10_events"]:
    if e["event"] in ("SCAN_FAULT","CM_LOST","GUARD_LATCH","FINAL_CMD"):
        print("G10=",e)
PY
```

최초 실패의 `expected`와 `actual`이 다르면 **처음 다른 값을 반환한 단계**에서 학생 정책을 디버깅한다. 마지막 예외만 쳐다보지 않고 최초 잘못된 상태 전이·순서·수신 TTL을 확인한다.

## 9. 흔한 질문과 장애 대응

- **HTML 화면은 정상인데 실제 학생 코드가 RED:** 정상. 생성기가 학생 코드를 대신 해결하지 않는다.
- **`ModuleNotFoundError`:** `pwd`를 확인하고 저장소 루트에서 `python3 block_D/day14/live_replay.py --out ...`로 실행한다.
- **이미 같은 디렉터리가 있음:** 기존 클론 삭제 금지, 새 폴더명 사용.
- **브라우저에서 버튼이 동작하지 않음:** 로컬 HTML의 JavaScript 지원·다른 브라우저를 점검. 실패 시 JSON 읽기로 대체.
- **화면 확대 시 화면이 잘림:** 1920×1080 프로젝터에서 브라우저 F11 전체화면, 필요하면 페이지 확대 축소. 화면의 정책과 G10을 세로로 나눠 볼 수 있다.
- **SLOW/AVOID/STOP이 실제 로봇을 움직이는가?** 아니다. 브라우저 퀴즈이며 `choose_action_intent()`는 `NOT_IMPLEMENTED`.
- **인증 E-Stop인가?** 아니다. 소프트웨어 **SW Stop**과 실제 인증된 하드웨어 **E-Stop**은 다르다.

## 10. 제출·평가 증거

학생은 자신의 실제 `git rev-parse HEAD`, `risk_policy_student.py` 수정 내용, 단위 테스트 20개 출력, 원본 실행기 16사례 JSON, `d14_live_manifest.json`, HTML 관찰 또는 `HTML_BROWSER_NOT_RUN`, G10 15사건의 최초 경계 해설, `STUDENT_WORKSHEET_KO.md`의 정책 선택 이유를 제출한다.

**한 문장으로 최종 정리:** "D14 라이브 화면은 합성 위험 판단과 정책 요청을 읽어 보여주는 교육 자료이며, 실제 ROS 2·Gazebo의 안전 주행·정지·RMW TTL·E-Stop을 검증하지 않았다."

**기술 참고:** [Nav2 Collision Monitor](https://docs.nav2.org/configuration/packages/collision_monitor/configuring-collision-monitor-node.html), [Nav2 Concepts](https://docs.nav2.org/concepts/index.html), [ROS 2 Jazzy QoS](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html).
