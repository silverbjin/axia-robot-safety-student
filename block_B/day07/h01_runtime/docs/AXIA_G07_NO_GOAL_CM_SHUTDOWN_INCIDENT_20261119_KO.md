# G07 NO_GOAL 안전 종료 이슈와 재현 가능한 해결 절차 (2026-11-19)

## 증상 — 실제 WSL2 현장 관측

기존 Ubuntu 24.04 WSL2 / ROS 2 Jazzy / Gazebo Harmonic NVIDIA 시연에서 Nav2 Goal을 보내지 않고 LiDAR 데이터를 관찰한 뒤 종료하였을 때, Collision Monitor 자식 프로세스가 `exit -11`로 종료됐다.

증거:
- 현장 UCMOonHr 원본 SHA256: `4d374b1caf58ffe113dcecffd315a84356834cd4c8bac2a3143251ae03d4ed3e`
- `collision_monitor-16 exit -11`, launch.log 429행, `P2_L2_FORCED_TEARDOWN`
- 동시에 Gazebo native /scan 첫 호스트 간격 314.467ms, ROS /scan 312.642ms, ROS /safety/scan 322.424ms. 기존 안전 Scan TTL 300ms 위반으로 NO_GOAL 유지.
- 둘을 동일 원인으로 취급할 수 없다. 센서 판정 실패를 종료 실패 뒤에 숨기거나 반대로 종료 마커만으로 clean 처리하지 않는다.

## 가설과 최소 변경

공식 Nav2 Lifecycle Manager의 관리 대상 노드를 종료하지 않은 상태에서 런치 프로세스 그룹 전체에 SIGINT를 보내면, 자식 노드들의 lifecycle preshutdown이 서로 경합할 가능성이 있다. 이는 **원인 가설**이지 실제 SIGSEGV 스택 백트레이스가 증명된 근본 원인은 아니다.

기존 `tools/p2_g07_ordered_shutdown.py`는 Navigation Lifecycle Manager, Localization Lifecycle Manager에 순서대로 shutdown을 요청하고 ACK를 검증한다. 기존 `tools/p2_g07_owner_shutdown_audit.py`는 원본 launch.log에서 Collision Monitor 프로세스의 **실제 exit 0**을 검사한다. 새로운 Nav2/CM 기능을 개발하지 않고 이 두 도구를 재사용한다.

한 파일 `scripts/p2_no_goal_smoke_ci.sh`에 opt-in `AXIA_G07_NO_GOAL_ORDERED_SHUTDOWN=1`을 추가했다. 이 플래그는 반드시 기존 `AXIA_G07_OWNER_SENSOR_TRUTH_NO_GOAL=1`과 함께 사용한다. NO_GOAL 센서 테스트가 이미 rc=3으로 실패했더라도 ROS 네비게이션 서비스가 정상적으로 존재한다면 shutdown ACK를 시도한다. 성공해도 센서 실패를 PASS로 승격시키지 않는다. 26초는 OS 프로세스 종료 유예 시간일 뿐 Safety TTL이 아니다.

## RED → GREEN → REFACTOR → REVIEW → COMMIT

1. **RED:** 공개 CI [#44443045828](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44443045828)에서 NO_GOAL 공식 순서화 종료와 CM child exit0 감사 계약 실패 재현.
2. **GREEN (L0):** 공개 CI [#44443348889](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44443348889)에서 기존 계약 포함 성공. Student 코드 SHA `835a5285c49300a8d9943d2e19d0c07f3fa06901`, 수정 파일 blob `5a4a97078aacc7f5b382d1c2ebdcdee82d8f09e1`.
3. **CI 경로 회귀:** 최초 실제 L2 [#44443519321](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44443519321)은 테스트 파일이 `ci/student/`를 찾는 경로 오류로 Gazebo 이전 단계에서 종료됨. 실제 CI checkout은 형제 `ci/`, `student/`이므로 공개 테스트 경로만 최소 수정, Gazebo 오류로 오진하지 않음.
4. **실제 Gazebo Harmonic L2 GREEN:** [#44443813171](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44443813171), Student 동일 코드 SHA, 실제 Xvfb Gazebo+RViz 두 창, 공식 Nav2 Navigation ACK=true, Localization ACK=true, Collision Monitor 실제 child `exit0`, `P2_L2_GRACEFUL_TEARDOWN`, 강제 종료 없음. 원래 센서 결과 `NO_GOAL_SENSOR_UNSAFE_HOLD`, 원인은 RAW_RECEIPT_TTL_300MS_BLOCKED이며 원본 run rc=3으로 유지. 이 **종료 계층만 L2 PASS**라고 판정해야 함.
5. **REVIEW:** 기존 학생 코드/World/Waffle/Nav2 코드 재사용, Goal/cmd_vel/fault injection 신규 개발 없음. Scan300/CM120/Guard150 임계값 변경 없음. WSLg NVIDIA 현장 L3 성공 주장은 금지.

## 검증 레벨과 인수 제한

- PUBLIC L0: PASS, 해당 정적/TDD 범위.
- PUBLIC L2: Gazebo+official Nav2 실제 NO_GOAL lifecycle shutdown/CM child exit0 한 세션 성공.
- PUBLIC L2: Raw Scan TTL300ms는 실패, 시연 전체는 HOLD.
- 강사 WSL2 NVIDIA 재검: 이 커밋 적용 이후 NOT_RUN; Goal 송신하지 않음.
- `AXIA_MVP_DEMO_ACCEPTED=HOLD`, `CERTIFIED_ESTOP=false`.
- Student 공개 PR은 Draft 유지. Main 병합은 사용자 승인 전 금지.

