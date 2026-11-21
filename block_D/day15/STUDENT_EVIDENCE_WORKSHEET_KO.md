# D15 학생용 증거 분석 워크시트

팀 / 작성자: _________ 날짜: _________ Git SHA: _________

## A. 7개 증거 단계

| 순서 | 단계 | 실제 공개 파생 증거값 2개 이상 | 이 증거만으로 주장할 수 없는 것 |
|---|---|---|---|
| 1 | CLEAR | | |
| 2 | SLOW | | |
| 3 | STOP | | |
| 4 | CANCEL | | |
| 5 | ODOM_DWELL | | |
| 6 | SAFETY_TTL | | |
| 7 | PNU_AND_SCOPE | | |

## B. SLOW 제어 계층 분리

- `slow_supervised_vx_mps`: ______ m/s
- `slow_final_vx_mps`: ______ m/s
- 최종/감속 전 명령의 비율: ______ %
- 왜 Supervisor 속도와 Guard 최종 속도를 같은 값이라 하면 안 되는가? ______

## C. STOP 및 Goal 취소 증거

- STOP 전방 LiDAR: ______ m / final cmd_vel: ______ m/s
- 동일 Goal UUID: ______ / Nav2 ActionStatus: ______ (의미: ______)
- `zero_dwell_sec`: ______ s. 이 값은 단순 취소 상태와 무엇이 다른가? ______
- 한 회 보고된 실제 움직임 누계: ______ m

## D. 타이밍 경계

| 구간 | 실제 한 실행 최대 (ms) | 기준 (ms) | 판정 |
|---|---:|---:|---|
| scan_gap_max | | 300 | |
| cm_source_gap_max | | 120 | |
| cm_observer_gap_max | | 120 | |
| guard_internal_cm_age_max | | 150 | |
| guard_status_gap_max | | 150 | |

- 위 집계에서 '최초 실제 위반 시각'을 알 수 있는가? ______ (이유: ______)
- 과거 다른 CI에서 나타난 최초 Guard Latch 나이와 임계값: ______ / ______ ms
- 이번 Owner 단일 실행이 모든 안전계층 타이밍 경계를 영구 보장하는가? ______

## E. 합성 데이터의 정체

- D13 G09 P/N/U: ______ 데이터 / 실행 수준: ______
- D14 G09→제한 요청: ______ 데이터 / 실제 Supervisor 상태인가? ______
- 별도 S04 실제 Gazebo CI 번호: ______, G07 Owner와 같은 세션인가? ______
- G10 복합 사건은 실제 프로세스 종료/Reset을 증명하는가? ______

## F. 5개 결함 수치 주입의 탐지

| 변조 항목 | 실제 현장 사건인가? | 기대 실패 게이트 | 테스트 결과 |
|---|---|---|---|
| SCAN_301MS | | | |
| GUARD_151MS | | | |
| GOAL_WRONG | | | |
| DWELL_0_5S | | | |
| FALSE_CERTIFICATION | | | |

## G. 원본 판정·안전 경계

- 원본 `raw_machine_status`: ______
- `visual_content_verified`: ______
- `formal_safety_timing_accepted`: ______
- `certified_estop`: ______
- 교육용 수치 인수와 정식 시스템 인증이 다른 이유를 두 문장으로 작성: ______

## H. 발표 (3~5분)

1. **관찰:** CLEAR/SLOW/STOP을 정량 비교한다.
2. **증명:** Goal 취소 및 odom 정지 유지의 독립 기록을 설명한다.
3. **한계:** 동일 실행에서 나온 증거와 별도 G09/G10 증거를 구분한다.
4. **검증:** 수치 변조 5건과 최초 실패 게이트를 설명한다.
5. **안전:** SW STOP과 E-Stop, 원본 HOLD와 교육용 인수의 차이를 말한다.
