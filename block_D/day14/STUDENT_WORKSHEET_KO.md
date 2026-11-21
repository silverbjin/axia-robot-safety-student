# AXIA D14 학생 워크시트 — 정책 요청·복합 장애

팀: ______ 이름: ______ Git SHA: ______ 시험 날짜: ______

## A. NORMAL과 LIMITED 요청을 구분해보세요

- D13의 P/N/U는 사람-로봇 미래 위치의 무엇을 판정하나요? ______
- `NORMAL_POLICY`는 실제 /cmd_vel 주행 허가와 같은가요? 왜? ______
- `LIMITED_REQUEST`는 기존 Supervisor 실상태가 바뀌었다는 증거인가요? ______
- P 이후 N이 들어와도 자동 해제하지 않는 이유: ______

## B. 입력 계약

| 필드 | 역할 | 잘못되면 어떻게 처리하나? |
|---|---|---|
| verdict=P/N/U | | |
| seq | | |
| scope | | |
| gate_accepted / goal_sent / certified_estop | | |
| unique_source | | |
| owned_goal / healthy | | |
| last_rx_mono / now_mono | | |

## C. 정책 16사례 검증

`policy_events.json`의 16개 id를 확인하고 action, LIMITED 요청 여부를 적습니다.

| 항목 | 실제 action | 제한 요청? | 최초 안전 오류 경계 |
|---|---|---|---|
| N_fresh | | | |
| P_predicted | | | |
| U_unknown | | | |
| P_then_N | | | |
| U_then_N | | | |
| duplicate/reordered N | | | |
| invalid scope/gate/sequence | | | |
| multiple sources | | | |
| stale N / clock regression | | | |
| no owned Goal / unhealthy | | | |

## D. G10: 15개 합성 이벤트 시간표

- 최초 안전 사건 (SCAN_FAULT): t=____
- CM_LOST: t=____. 두 이벤트 차이: ____초
- GUARD_LATCH: t=____
- FINAL_CMD ZERO: t=____
- 실제 STOP 주장이 아니라 합성된 `stop_t`: ____
- Odom dwell: ____초
- Nav2 Goal CANCELED와 최초 EXECUTING UUID 동일한가? ____
- Fault가 남았을 때 reset 거부 이벤트 명칭: ______
- Owner RESET, REARM 승인 순서: ______
- NO_AUTO_RESUME는 왜 필요한가? ______

## E. 제출 증거

- 최초 RED의 failing assertion 수: ____
- 구현 후 GREEN 테스트 수: ____
- HTML과 JSON 결과 생성 경로: ____
- 첫 LIMITED 요청을 발생시킨 사건과 수신 시각: ____
- 전송 TTL 0.5초와 D13 관측 stale 0.5초는 무엇이 다른가? ____
- SW Stop과 인증 E-Stop의 차이: ____
