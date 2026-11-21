# AXIA D14 학생 실습 워크시트 — 사람 접근·고장·예측 위험 → 정책 요청

**팀/이름:** __________ / __________　 **Student main SHA (`git rev-parse HEAD`):** __________  
**수업:** 2026-11-26 19:00–22:00　 **검증 레벨:** `SYNTHETIC_L0_ONLY`

이 문서는 **학생이 직접 채우는 활동지**다. 실제 Supervisor 상태 전이나 로봇 정지를 측정하는 도구가 아니다. **SW Stop ≠ 인증 E-Stop**.

## A. 첫 장 학습 목표 확인

1. D13의 P/N/U는 미래의 어떤 정보를 판단하는가? (동일 시간·위치·입력 신뢰성) __________________
2. D14의 `LIMITED_REQUEST`는 Supervisor가 실제로 LIMITED로 바뀌었다는 증거인가? 이유: __________________
3. `NORMAL_POLICY`는 실제 `/cmd_vel` 구동 허가인가? 이유: __________________
4. P→N 직후 자동 해제가 금지되는 이유를 실무 사고 사례로 설명하라: __________________

## B. 코드·입력 데이터 계약 해설

| 필드 | 의미 (직접 작성) | 잘못되면 어떤 위험이 생기는가? |
|---|---|---|
| `RiskState.last_seq` | | |
| `RiskState.last_rx_mono` | | |
| `RiskState.limited_by_risk` | | |
| `verdict=P/N/U` | | |
| `seq` 및 `unique_source` | | |
| `scope` / `gate_accepted` | | |
| `goal_sent` / `certified_estop` | | |
| `owned_goal` / `healthy` | | |
| `expired_verdict(now_mono)` | | |

**두 TTL의 구분:** D13 사람 관측시각의 stale 0.5초와 D14 호스트 메시지 수신 TTL 0.5초는 어떤 데이터가 기준인가? __________________

## C. RED → GREEN 증거

| 항목 | 최초 RED | 본인 구현 후 GREEN |
|---|---|---|
| `python3 -m unittest discover -s block_D/day14/tests -p 'test_*.py' -v` 종료 코드 | | |
| 테스트 수 | | |
| 실패 수 | | |
| `python3 block_D/day14/run_lab.py --out /tmp/axia-d14` 종료 코드 | | |
| `D14_STUDENT_RESULT` | | |
| 16개 중 `pass` 수 | | |

**초기 기대:** 테스트 20개 중 의도된 실패 11개, unittest rc 1; 정책 러너 `RED_EXPECTED_TODO`, rc 2. **목표:** 학생 코드 자체 20/20 및 16/16, rc 0. 실제 출력과 다르면 관찰한 값을 기록한다.

## D. 정책 fixture 16개 — 실제 action·제한 여부 기록

`block_D/day14/fixtures/policy_events.json`과 `/tmp/axia-d14/d14_policy_results.json`을 비교한다.

| ID | actual_last_action | actual_limited | expected와 일치? |
|---|---|---|---|
| `N_fresh_keeps_normal` | | | |
| `P_predicted_requests_limit` | | | |
| `U_unknown_requests_limit` | | | |
| `P_then_N_never_autoclears` | | | |
| `U_then_N_never_autoclears` | | | |
| `duplicate_N_rejected` | | | |
| `reordered_N_rejected` | | | |
| `invalid_scope_requests_limit` | | | |
| `invalid_gate_requests_limit` | | | |
| `two_sources_requests_limit` | | | |
| `invalid_sequence_requests_limit` | | | |
| `invalid_label_unknown` | | | |
| `N_receipt_stale_requests_limit` | | | |
| `N_clock_regression_requests_limit` | | | |
| `no_owned_goal_cannot_arm` | | | |
| `unhealthy_robot_cannot_arm` | | | |

**질문:** 소유한 Goal이 없을 때 `actual_limited=False`가 나와도 주행이 허용된다는 뜻일까? __________________

## E. 원래 수업 주제: 감속·회피·정지 의도 설계

**지금은 개념·워크시트 판단 활동이다.** Student Starter에는 `choose_action_intent()`가 **NOT_IMPLEMENTED**이며 새 SLOW/AVOID/STOP 실행기 및 자동 테스트는 포함되지 않는다.

| 식당 실무 상황 | 내 선택(SLOW/AVOID/STOP) | 선택한 이유·필요한 신뢰 조건 | 실행 책임(Planner/CM/Guard/Supervisor) |
|---|---|---|---|
| 사람이 멀리서 접근하나 신뢰 가능한 센서 여유가 있음 | | | |
| 고정된 카트가 통로를 막음, 지도상 우회로 확인됨 | | | |
| 사람이 가까워짐, P 판정 | | | |
| 사람 트랙이 stale, U 판정 | | | |
| Scan Fault와 CM Lost가 연이어 나타남 | | | |
| 새로운 N이 오지만 이전 P로 제한됨 | | | |

**우선순위 질문:** 보호 정지 상태에서 Planner가 새 경로를 발견했다고 자동 재출발해도 되는가? __________________

## F. G10 복합 고장 15개 합성 사건의 최초 경계 추적

`block_D/day14/fixtures/g10_events.json`의 이벤트명은 정확히 확인한다. 실제 이벤트는 `FINAL_CMD`이며, **`vx=0, wz=0` 속성**으로 합성 zero 명령을 확인한다.

- 최초 `SCAN_FAULT`: t = ______초
- `CM_LOST`: t = ______초, 최초 Fault와 차이 = ______초
- `GUARD_LATCH`: t = ______초, CM Lost 이후 차이 = ______초
- `FINAL_CMD`: t = ______초, vx = ______, wz = ______
- `ODOM_STOP_DWELL`: 기록된 사건 t = ______초, 내부 합성 `stop_t` = ______초, dwell = ______초
- `NAV2_GOAL_CANCELED`: t = ______초, 최초 `GOAL_EXECUTING` UUID와 같은가? ______
- Fault가 남아 있을 때 RESET 거부 명칭 = __________________
- HEALTH 회복 → Owner RESET 승인 → RESET OK → Owner REARM 승인 → REARM OK 순서의 이유: __________________
- 마지막 `NO_AUTO_RESUME`의 의미: __________________

**주의:** 위 사건 시각은 합성이다. 차이를 실제 DDS/RMW 수신 지연, 최초 타이밍 위반, 실제 제어 명령 반응시간, odom 정지 증거로 보고하지 않는다.

## G. 제출 전 점검

- [ ] 최초 실패 로그와 실제 종료 코드 (정상 RED를 GREEN이라고 적지 않았는가?)
- [ ] 수정한 `block_D/day14/risk_policy_student.py`, `git rev-parse HEAD`, `git diff --check`
- [ ] 구현 후 테스트 결과와 `d14_policy_results.json` (16개 기대값/실제값)
- [ ] HTML 관찰 결과 또는 `HTML_BROWSER_NOT_RUN`
- [ ] F절 첫 안전 사건·합성 사건 간 차이·정식 인수 아님을 설명
- [ ] 실습만으로 실제 Supervisor/CM/Guard 및 SW Stop 또는 인증 E-Stop 성공을 주장하지 않음

**자료:** `STUDENT_DEMO_GUIDE_KO.md`, `STUDENT_LAB_GUIDE_KO.md`, ROS 2 Jazzy QoS 및 Nav2 Collision Monitor/Planner 공식 문서.
