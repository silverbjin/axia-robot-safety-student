# AXIA BLOCK_D D14 — 위험 예측 이후 무엇이 로봇을 제한할까?

**일시:** 2026-11-26(목) 19:00–22:00, 3시간.  
**대상:** ROS 2 초심자 포함. **Python 3 및 표준 라이브러리**만 있으면 실행 가능.  
**인수 범위:** synthetic offline L0. **실제 Supervisor 상태전이, Nav2 Goal, Gazebo, ROS Topic, Fault 주입을 실행하지 않습니다.** SW STOP은 인증 E-Stop이 아닙니다.

## 1. 이야기: 위험을 발견한 뒤 바로 다시 달려도 될까?

D13의 G09에서 사람과 로봇이 같은 시각 겹치면 `P`, 안전하게 분리된 예측은 `N`, 관측을 신뢰하지 못하면 `U`라고 했습니다. D14는 예측 결과를 받아 **속도 제한 요청을 결정하는 기존 S04 위험정책**을 연습합니다.

- 시작이 정상이고 신선한 `N`이면 **NORMAL_POLICY**(제한 요청 없음).
- `P` 또는 `U`가 오면 **LIMITED_REQUEST**.
- `P/U`로 이미 제한된 뒤 신선한 `N`이 와도 **자동 해제 금지**.
- 중복/역순 `seq`, 출처 위변조, 복수 발행자, 오래된 메시지는 **제한 요청 유지**.
- 호스트 수신 시간의 TTL은 **0.5초**. `expired_verdict()`는 stale **여부만 반환**합니다. 실제 Supervisor의 `NORMAL→LIMITED` 요청/상태 전이는 별도 연결이 필요합니다.
- Goal이 본 Supervisor의 소유가 아니거나 장치가 비정상이면 새 안전제어 권한을 만들 수 없습니다.

`risk_policy_student.py`는 ROS-free 순수 정책 함수입니다. `run_lab.py`는 반환된 제한 요청을 HTML로 **보여주기만** 하며, 실제 Collision Monitor, Guard, `/cmd_vel`은 건드리지 않습니다. **NORMAL_POLICY는 실제 속도 허용 승인이 아닙니다.**

## 2. 수업 운영 (180분)

| 시간 | 활동 | 확인 |
|---|---|---|
| 19:00–19:20 (20분) | 복도 사람 P→U→N 상황, 즉시 해제의 위험 | 상태 전이 예측 |
| 19:20–19:50 (30분) | S04 메시지: verdict/seq/scope/provenance, monotonic TTL | 합성 JSON |
| 19:50–20:00 (10분) | 휴식 | |
| 20:00–20:55 (55분) | RED→TODO: P/U/중복/N 제한 유지, stale 판정 | `test_d14_policy.py` |
| 20:55–21:05 (10분) | 휴식 | |
| 21:05–21:40 (35분) | G10 합성 Scan+CM 복합 장애·Stop/Reset/Rearm 시간 순서 | Timeline HTML |
| 21:40–22:00 (20분) | 결과 보고·워크시트·교차 안전 계층 한계 | 16개 시나리오 결과 |

## 3. GitHub 클론부터 시작

```bash
cd ~
git clone --branch feat/block-d-d14-risk-policy-20261121 \
  https://github.com/silverbjin/axia-robot-safety-student.git \
  axia-d14-student
cd ~/axia-d14-student
python3 --version
git rev-parse HEAD
```

**현재는 개발 검증 브랜치입니다.** 정식 `main` 배포 승인 전에는 강사가 최종 확인된 SHA를 지정해야 합니다. 기존 D13/G07 파일을 건드릴 필요가 없습니다.

## 4. 첫 번째 RED 실행

```bash
python3 -m unittest discover -s block_D/day14/tests -p 'test_*.py' -v
echo "test_rc=$?"
```

`risk_policy_student.py`의 핵심 정책 TODO가 미완성이므로 P/U/N, 불변성, replay, TTL 테스트는 실패해야 정상입니다. **RED가 자동으로 사라지도록 테스트 기대값을 바꾸지 마세요.**

## 5. TODO 구현할 단 하나의 파일

`block_D/day14/risk_policy_student.py`의 **`apply_verdict()`와 `expired_verdict()` 두 함수**만 구현합니다. 순서는 다음과 같습니다.

1. **검증:** `RiskState`와 유한한 `now_mono` 검사(잘못된 시계는 예외).
2. **Goal 권한:** `owned_goal=False` 혹은 `healthy=False`면 `NO_OWNED_HEALTHY_GOAL`을 반환하고 제한/완화 권한을 추가하지 않습니다.
3. **출처:** `unique_source=False` 또는 payload가 dict가 아니면 `LIMIT_ON_UNTRUSTED`, 잘못된 seq는 `LIMIT_ON_INVALID_SEQUENCE`로 제한 요청.
4. **순서/무결성:** `seq <= last_seq`는 `REJECT_REPLAY_OR_REORDERED`. `scope`, `gate_accepted=False`, `goal_sent=False`, `certified_estop=False`를 검증하고 위변조는 `LIMIT_ON_INVALID_PROVENANCE`.
5. **판정:** `P`는 `LIMIT_ON_PREDICTED_P`, `U`나 알 수 없는 라벨은 `LIMIT_ON_UNKNOWN_U`. `N`은 `NORMAL_UNCHANGED_NO_FALSE_RISK`이되 이미 제한된 경우 `KEEP_LIMITED_NO_AUTOMATIC_CLEAR`.
6. **TTL:** 최초 데이터 수신 전에는 `expired_verdict=False`, 첫 수신 이후 수신시각보다 시간이 역행하거나 `now_mono-last_rx_mono > 0.5`면 True. TTL은 D13의 관측시각 `observed_sec`와 다른 **정책 수신 TTL**입니다.

**핵심 보안 원칙:** `N` 한 번으로 보호 제한·수동 정지·Fault Latch를 해제하는 코드는 작성하지 않습니다. `expired_verdict=True`면 실행기는 제한 요청이라고 표시하지만, **원본 정책 함수가 직접 Supervisor 상태를 변경한 것은 아닙니다.**

## 6. 16개 합성 정책 사례

`block_D/day14/fixtures/policy_events.json`을 읽어 `steps`와 `expected_last_action`를 비교합니다. 판정 유형은 정상 N, P 제한, U 제한, P→N/U→N 제한 유지, duplicate/reordered N, scope/gate 위변조, 복수 발행자, 음수 seq, 미확인 라벨, N stale, host clock 역행, Goal 소유권 없음, 로봇 비정상입니다.

```bash
python3 block_D/day14/run_lab.py --out /tmp/axia-d14
echo "runner_rc=$?"
ls -lh /tmp/axia-d14/
```

미완성 TODO의 `D14_STUDENT_RESULT=RED_EXPECTED_TODO`, 종료 코드 **2**가 정상입니다. 직접 구현한 뒤 `D14_STUDENT_RESULT=GREEN`, 종료 코드 **0**을 목표로 합니다.

결과물:
- `/tmp/axia-d14/d14_policy_results.json`: 예상 action/실제 action, 요청 제한 여부, 각 이벤트 trace.
- `/tmp/axia-d14/d14_policy_timeline.html`: NORMAL_POLICY→LIMITED_REQUEST와 해제 금지, 15개 G10 합성 이벤트 시간표.

선택적 WSL2 GUI 확인:

```bash
explorer.exe "$(wslpath -w /tmp/axia-d14/d14_policy_timeline.html)"
```

HTML은 로컬 파일이며 인터넷 연결이 필요하지 않습니다. 실제 브라우저에서 그림이 열렸는지는 현장에서 확인해야 합니다.

## 7. G10 합성 복합 장애 사건의 의미

`block_D/day14/fixtures/g10_events.json`에는 **15개의 합성 사건**이 있습니다. 핵심 순서는:

```text
GOAL_EXECUTING → ODOM_MOVING → SCAN_FAULT → CM_LOST
→ GUARD_LATCH → FINAL_CMD ZERO → ODOM_STOP_DWELL
→ NAV2_GOAL_CANCELED → RESET_REJECTED_ACTIVE_FAULT
→ HEALTH_RESTORED → OWNER_RESET_APPROVED → RESET_OK
→ OWNER_REARM_APPROVED → REARM_OK → NO_AUTO_RESUME
```

왜 Fault가 남아 있을 때 Reset이 거부되는지, Owner 승인 없이 재출발하면 왜 안 되는지 설명하세요. **이벤트 파일은 실제 Nav2 Goal/Stop/고장 주입 증거가 아닙니다.** G10 강사 검증은 기존 비공개 `p3_g10_compound.py`를 재사용합니다. 별도 제어 코드를 작성하지 않습니다.

## 8. 흔한 오류 분석

- `P`가 제한되지 않음: `limited_by_risk`와 `last_verdict` 확인.
- `P→N` 뒤 제한이 풀림: **첫 안전 상태 전이 P**, 그 뒤 N의 자동 해제 로직부터 추적.
- 중복 N으로 상태가 바뀜: `last_seq`와 수신 `seq` 순서를 우선 검토.
- N stale인데 여전히 NORMAL: **최초 수신 monotonic 시각과 TTL 0.5초 초과**를 비교.
- `U`를 `N`으로 처리: 출처·레이블 오류를 fail-closed로 처리하지 않은 것.
- G10이 단순 단일 Fault로 PASS: `SCAN_FAULT`와 `CM_LOST` 두 사건의 시간 관계 및 최초 Guard Latch 순서를 확인.
- `ModuleNotFoundError`: 저장소 루트에서 명령했는지 확인.
- 시각화 창이 비었음: `d14_policy_results.json` 및 HTML 파일 존재 여부 확인. 파일 생성 PASS는 브라우저 화면 PASS를 뜻하지 않습니다.

## 9. 제출할 것

`STUDENT_WORKSHEET_KO.md`의 상태 전이표와 G10 시간표를 완성하고 `risk_policy_student.py`, 공개 테스트 출력, `d14_policy_results.json`, HTML 관찰 기록, Git SHA를 제출합니다. **실습 성공은 synthetic L0 정책 구현과 설명**입니다. 실제 ROS/Gazebo·인증 E-Stop·정식 G10 인수는 해당하지 않습니다.
