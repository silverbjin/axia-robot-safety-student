# AXIA D08 — 학생 공개 NO_GOAL 인수 증거·현장 L3 대기

- Public 기능 Source SHA: `a83629edd71ce51567e184451f2a76bafcf1318b`; [CI #44248098353](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44248098353) **SUCCESS**, L0 103 PASS, ROS 2 Jazzy + Gazebo Harmonic L2 원본 통합 PASS.
- Public PR [#166](https://github.com/silverbjin/axia-robot-safety-ci-public/pull/166); Student PR [#43](https://github.com/silverbjin/axia-robot-safety-student/pull/43); Instructor private PR #212. 세 저장소 main 병합 모두 **NO**, 사용자 승인 대기.
- 동일 World 실제 Waffle+사람형 물리 Proxy+LaserScan/Costmap/Nav2 3 Path PASS. 실제 Depth+YOLO 거리 `0.704022m`, `0.534589m` (차이 0.16943m), 실제 UNKNOWN `NO_PERSON_CLASS_IN_ACTUAL_YOLO`.
- Native official CM state `active`, configured observation_sources `scan`, `scan.topic=scan` PASS. **CM 내부 수신 gap, 실제 STOP/SLOW 출력, Guard TTL, Moving E2E와 인증 E-Stop은 NOT_VERIFIED/NOT_RUN**.
- ROS Scan observer max host gap은 source `a83629edd71ce51567e184451f2a76bafcf1318b`의 아티팩트 `d08-same-world-live-person-range-cm-nav2-evidence` (#14402713171) 기록에 한정; 이 값은 CM 내부 수신 age가 아님.
- Owner WSL2/WSLg 실제 GUI 픽셀 인수 `NOT_RUN`, 따라서 `D08_LIVE_NO_GOAL_ACCEPTED=NO` (배포 준비는 Public CI PASS 단계, 현장 승인 전 HOLD).
- 한 번의 실행 블록과 3계층 rqt_graph 필터는 `block_B/day08/D08_UNIFIED_NO_GOAL_CLASSROOM_GUIDE_20261118_KO.md` 제7절 참조. 기존 D04/D05 visual-only 원샷과 Student TODO는 보존. 비공개 강사 답안/hidden tests는 이 저장소에 없음.
- 실패 시 기존 Run만 반복 재시도하지 않고 원본 증거·최초 상태 전이·타이밍 및 WSLg 렌더 계층을 분리 분석.
