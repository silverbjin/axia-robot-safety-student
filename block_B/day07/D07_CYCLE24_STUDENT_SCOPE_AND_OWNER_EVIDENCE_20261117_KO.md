# AXIA Block B D07 — 전체 학습 개발·현장 증거·학생 배포 완료 보고

**작성:** 2026-11-17 KST. **학생 독립 저장소** 배포본. 강사 정답/비공개 테스트/비밀 저장소 소스 미포함.

## 1. 학습 목표와 구현 범위

- 핵심 구조: **실제 Gazebo 물리 장애물 → TurtleBot3 Waffle LaserScan → 공식 Nav2 Costmap → 공식 ComputePathToPose → RViz2 표시**.
- RViz2에 그려진 경로는 **주행 명령이 아닌 읽기 전용 Planner 결과**이다. 경로가 변경됐다는 사실로 로봇이 움직였거나 사람을 물리적으로 피했다는 결론을 내리지 않는다.
- 학생 코드 범위: `block_B/day07/route_todo.py`의 **두 TODO 함수**(장애물 상태와 재계획 판단)만 실습. 학생 fixture·공개 테스트는 그대로 둔다. Instructor 답안과 hidden tests 배포 금지.
- 교육 운영: D07 3시간 강의 중 이론 60분·실습 120분. 설명→실제 출력 증거 관찰→학생 TODO 구현→테스트/토론. 기존 `D07_STUDENT_DEMO_GUIDE_20261117_KO.md`, `D07_STUDENT_3H_CLASSROOM_GUIDE_20261117_KO.md` 사용.

## 2. 실패에서 실제 성공까지의 인과

| 교육 사례 | 관찰과 배울 점 |
|---|---|
| 과거 `POST_RESTORE_COSTMAP_DRIFT` | Count가 복원되어도 격자의 각 셀이 같다는 보장이 없다. 전체 Map/Path 비교 필요 |
| GUI SceneBroadcaster 누락 | Gazebo 창 출현 ≠ 3D 월드 로드. 실제 Scene transport를 확인 |
| Lifecycle ACK 유실 | ROS 노드 ACTIVE와 서비스 응답 수신이 다를 수 있다. 새로운 STARTUP을 무작정 재전송하지 않고 공식 상태만 읽어 검증 |
| 최초 상태 조회 미발견 | 두 번 연속 Manager + map_server + amcl ACTIVE가 있어야 정지 로봇 시연에서만 진행 가능. Goal/안전 신뢰 주장 금지 |
| 실제 Owner WSL2 | 공식 Planner Before/Intrusion/Restored **52/52/52 poses**, 경로 변화 **0.3659m**, 침입 신규 lethal cells **92**, 제거 후 Costmap 차이 **0**. 사용자 현장 시연 성공, 원본 무결성 확인 |

원본 `d07-h01-owner-kCqVL7Gc`의 파일 해시 78/78 및 real-l2 59/59 PASS. **실제 이동 Goal은 NOT_RUN**. 자동 GUI 픽셀 판정 `D07_H01_OWNER_GUI_VISUAL_HOLD`, 종료 중 Supervisor context 예외, 종단 간 Scan/CM/Guard 안전 TTL 검증은 미완료. `AXIA_MVP_DEMO_ACCEPTED=HOLD` 유지.

## 3. 검증·배포 및 변경하지 않은 것

- 공개 학생 문서 계약 RED 2 failed, 54 passed → GREEN [#43894768817](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43894768817): **56 PASS**. 당시 오류는 학생 설명에서 `NOT_RUN` 표기가 빠진 문서 계약 회귀.
- 공개 실제 ROS/Gazebo L2 [#43912555634](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43912555634): D07 No-Goal official Nav2 Path 및 CI 전용 인위적 ACK 누락 대응 성공. 실제 WSL2 RMW 고장 강제 재현은 아님.
- 실제 Owner 증거는 **강사 측 WSL2에서 실행**되었고, 학생이 동일 환경에서 직접 3D 물리 시연을 수행했다고 주장하지 않는다.
- **변경 없음:** 학생 TODO 정답, Navigation Goal, `/cmd_vel` 발행, Safety Supervisor/Collision Monitor/Guard 로직, TTL 완화, 인증된 E-Stop 기능.
- 개별 학생 저장소의 main에는 **D07 실습 문서·원본 증거 해설·교육 보고서만 선별 병합**한다. 비공개 Instructor 기능 코드는 절대 가져오지 않는다.

## 4. 강의 후 확인 질문

1. `ComputePathToPose`와 `NavigateToPose`는 어떤 차이가 있는가?
2. Costmap lethal cell 개수의 복원과 공간 격자 전체 복원은 무엇이 다른가?
3. 성공한 Path 결과가 왜 실제 주행 안전성·E-Stop 인증의 근거가 아닌가?
4. 최초 서비스 타이밍 위반이 발견됐을 때 어떤 로그 순서로 원인을 좁힐 것인가?

**교육 범위 인수:** 공식 Path 시연 증거 확인, 학생 실습 코드 독립성 유지. **실제 로봇 주행/안전 시스템 전체 인수는 별도**이며 `AXIA_MVP_DEMO_ACCEPTED=HOLD`를 해제하지 않는다.
