# D03 v3 학생 실습 결과보고서 (제출 템플릿)

- 교육생 / 팀:
- 실습 날짜:
- 저장소: silverbjin/axia-robot-safety-student
- 실습 브랜치: D03_v3 기반 개인 작업 브랜치:
- Git HEAD SHA (git rev-parse HEAD):
- OS / WSL2 / ROS 2 / Gazebo:
- P1 source SHA: 0be687ee033233fcd53be1190e0b2f9e86730fc9
- 공개 CI 실행 URL:
- ROS_DOMAIN_ID (자격증명 없이 도메인 숫자만):
- GZ_PARTITION (세션 식별자, 필요시 비식별 처리):

## 1. 원인 가설 (S01–S03)

- 최초 관측 시점:
- 가설 A: 장애물 접근으로 Collision Monitor가 먼저 정지?
- 가설 B: LiDAR Scan Drop으로 Supervisor 보호정지?
- 증거를 모으기 전에는 어떤 가설이 우세했는가:

## 2. 아키텍처 해석 (S04–S06)

- Nav2 → P1 Supervisor → Collision Monitor → Waffle:
- P1 State → Diagnostics Adapter → Bridge → /diagnostics:
- Diagnostics WARN인데 주행하면 안 되는 예시:
- Software Stop과 인증 HW E-Stop의 차이:

## 3. 실행 명령 및 결과 (S07–S22)

| 구간 | 실제 실행 명령 | 터미널 | 실제 출력/Exit code | 판정 |
|---|---|---|---|---|
| Clone / branch 확인 | | T1 | | |
| session / prepare | | T1 | | |
| P1 preflight | | T2 | | |
| P1 Gazebo launch | | T2 | | |
| P1 state / odom 관측 | | T3 | | |
| 학생 Adapter RED | | T1 | | |
| Adapter GREEN | | T1 | | |
| Safe Mode GREEN | | T1 | | |
| 합성 9사례 replay | | T1 | | |
| Diagnostics Bridge 출력 | | T4/T3 | | |
| Proxy route / preview | | T3 | | |
| Proxy GUI 실제 이동 | | Gazebo | | |
| 기존 P1 승인 Goal, 정상 이동 | | T2/T3 | | |
| Live fault 및 보호정지 | | T3 | | |
| verify 판정 | | T3 | | |

*예상 출력이 아닌 실제 로그를 적는다. 테스트를 실행하지 않았으면 NOT_RUN으로 쓴다.*

## 4. 이벤트 타임라인과 증거

| 순서 | 이벤트 | monotonic/시각 | 관측 근거 |
|---|---|---|---|
| 1 | P1 NORMAL | | |
| 2 | odom 실제 이동 | | |
| 3 | proxy 생성·GUI 확인 | | |
| 4 | proxy 이동 1/8 등 | | |
| 5 | fault_status DROP_SCAN | | |
| 6 | Diagnostics ERROR(2) | | |
| 7 | P1 PROTECTIVE_STOP | | |
| 8 | odom 정지 1초 이상 | | |
| 9 | 운영자 HOLD 또는 END | | |

**정지 선후관계 판단:** fault보다 먼저 정지했다면 scan_drop 때문이라고 결론내리지 않는다.

## 5. 안전 판단 및 복구

- 학습자 후보 Safe Mode:
- 실제 P1 FSM:
- 상태가 다시 OK가 되어도 자동 재주행하면 안 되는 이유:
- 수동 복구 전 확인할 3가지:
- 최종 운영자 선택: HOLD / END / 결정 불가
- 선택 근거:

## 6. 현장 문제 해결 로그

- 최초 증상:
- 가능한 원인:
- 조사 명령 및 원본 로그:
- 원인 분리 방법:
- 수정한 학생 코드 파일/라인:
- 다시 실행한 테스트:
- 재발 방지책:

## 7. 검증 수준 — 반드시 각 항목을 표시

| 범위 | PASS / FAIL / NOT_RUN / INCONCLUSIVE | 증거 링크/파일 |
|---|---|---|
| Python 필수 공개 테스트 | | |
| Python 합성 재생 9사례 | | |
| 공개 패키지 CI | | |
| ROS 2 Jazzy 빌드 / 패키지 | | |
| 실제 ROS /diagnostics | | |
| Gazebo GUI proxy 이동 | | |
| P1 Goal 후 odom 이동 | | |
| Scan Drop 후 P1 정지 | | |
| odom 정지 최소 1초 | | |
| 교육용 DEMO_OBSERVED | | |
| 인증 HW E-Stop | **NOT_VERIFIED** | 인증 시험 대상 아님 |

- 미검증·차단 사항:
- 강사의 최종 확인:
- 학생 Git SHA:
- 제출 파일 위치:
