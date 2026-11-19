# AXIA G07 Task04 — 교육용 라이브 시연 기준선 (Demo Baseline)

**기준선 ID:** `AXIA-G07-T04-DEMO-BASELINE-20261119-CZObXAdP`  
**범위:** ROS 2 Jazzy / Gazebo Harmonic / TurtleBot3 Waffle / 공식 Nav2 / Collision Monitor / WSL2·WSLg  
**판정:** **교육용 시연 baseline 인수** (실제 로봇 하드웨어 안전 인증 및 정식 안전 TTL 인수와 별개)

## 1. 인수 범위와 현장 증거

강사 WSL2 현장 `owner-moving-CZObXAdP` 원본 TAR·작은 진단 ZIP의 SHA256 및 내부 manifest가 모두 일치하며, ROS bag 14토픽 SQLite quick_check=ok:

- TAR SHA256 `7fd07eb7b60330b3940d5501f2fc6629c1be8cff709dadd8acf396fdcbd5cd5b`
- ZIP SHA256 `016b18799adaf4525d810cda564a3d367908c383e2f2e43b2ff68a49db039c53`
- 원본 파일은 강사 WSL2에 보존. 공개 저장소에 원본 rosbag·환경정보·개인 경로를 게시하지 않음
- 실행 Student SHA `954fc2f054c50df783bc81c4d0835a6ee6f8645d`, CI Run [#44478344652](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44478344652) native Gazebo+RViz scoped PASS, Owner Bootstrap [#44480154746](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44480154746) 9/9 PASS

| 시연 계약 | 실제 관측 | 교육용 판정 |
|---|---|---|
| Gazebo + RViz | 동일 Owner 세션 각각 1개 창 감지 | 인수 |
| 실물 Nav2 Goal | 단일 Goal UUID, 실제 EXECUTING | 인수 |
| CLEAR 실제 이동 | SLOW 전환 전 Odom **0.120313m**, 전체 **0.128216m** | 인수 |
| SLOW 물리 감속 | 실제 LaserScan 0.684568m; Supervisor 0.010706 → CM/final 0.003212m/s (약 30%) | 인수 |
| STOP 물리 정지 | 전방 0.391334m, CM 및 최종 cmd 0m/s | 인수 |
| 실제 STOP 유지 | Odometry ZERO 1.038867초 | 인수 |
| 정확 UUID 취소 | Nav2 ActionStatus=5(CANCELED), `goal_cancel_ack=true` | 인수 |
| Guard Latch | `first_guard_latch=null`, `guard_latched=false` | 인수 |

**검증 한계:** GUI 창 존재는 검증되었으나 관객이 체감한 감속 장면 선명도에 대한 화면 캡처·교실 관찰은 별개입니다. 매우 작은 SLOW 출력 속도(~3.2mm/s)는 수치상 감속과 화면상 가시성을 혼동하지 않는 수업 설명에 포함합니다.

## 2. 안전 타이밍은 '안전 감시 교육 사례'로 분리

현장 Observer는 STOP 장애물 전환 경계에서 실제 `/scan` 간격 **339.177ms**를 측정했고, 기존 검증 기준은 **300ms**입니다. 같은 구간 `/safety/scan` 수신 공백도 약 335.783ms로 rosbag에서 확인됩니다. 이 **시간 경계 검출 사실**은 교육에 활용하고, **이번 교육용 시연의 인수 제외 항목**으로 관리합니다.

- 실제 최초 안전 관련 상태 변화는 Guard `AWAITING_CM_RECONCILIATION_ZERO` 임시 진입 및 정상 복귀; **Guard Latch는 발생하지 않았습니다.**
- 339.177ms 초과는 **사후 시나리오 검증기(Observer/Oracle)가 기록한 사건**입니다. 이를 Guard 자체가 Latch로 검출했다고 가르치지 않습니다.
- CM 0m/s 및 Guard 최종 0m/s 출력, Odometry ZERO 유지, Action CancelGoal(5)은 실물 데이터로 검증됐습니다.
- **LaserScan 10Hz, Scan 300ms 및 CM/Guard 안전 TTL 등 설정은 변경하지 않습니다.** 검증기의 원본 판정·첫 타이밍 경계 및 임계값을 삭제하거나 정상으로 위장하지 않습니다.
- 별도 고도화 과제: WSL2 GPU LiDAR/ros_gz_bridge/스케줄러/STOP `set_pose` 1.112s 부근의 최초 수신 공백 원인 분리와 타이밍 보장. **향후 정식 안전 시스템 인수 항목**이며 이번 데모 기능의 재개발 사유가 아닙니다.
- 종료 뒤 ROS Context 경고는 기록 보존·향후 정리 대상이며, 실제 STOP·Goal 취소 완료 뒤 발생했습니다.

## 3. 실습 설명 및 종료 기준

강사는 현행 공개 Owner 원샷을 그대로 사용합니다. 기존 Safety Supervisor, Fault Injector, 공식 Nav2, Collision Monitor, Guard의 운영 판단 코드를 시연 판정에 맞게 수정하지 않습니다.

학생들에게 **인식(LaserScan) → 계획(Nav2 Goal) → 제어(Supervisor/CM/Guard) → 물리 증거(Odom) → 검증(Observer/Oracle)**을 연결해 설명합니다. Scan 시간 경계는 '안전 감시와 사후 검증의 차이'를 보여 주는 독립 사례로 활용합니다.

**세 가지 판정은 혼동하지 않습니다.**

1. `AXIA_G07_TASK04_DEMO_BASELINE=ACCEPTED`: **이번 강사 WSL2 현장 교육용 시연의 범위 한정 인수**
2. `FORMAL_SAFETY_TIMING_ACCEPTANCE=NOT_CLAIMED`: 기존 Strict Oracle 원본 결과는 변경하지 않음. 고도화 트랙에서 별도 검증
3. `CERTIFIED_ESTOP=false`: 시뮬레이션 SW STOP은 인증된 하드웨어 E-Stop이 아님

## 4. 인수/배포 이력

- Student 기능 기준 SHA `954fc2f054c50df783bc81c4d0835a6ee6f8645d`와 Public CI 실물 Gazebo L2 `44478344652` 보존
- 이 기준선은 기능 보존 및 문서화에 한정, 시연을 위한 안전 TTL 완화·새 Goal·새 주행 알고리즘·새 테스트 반복 없음
- 이번 `main` 통합은 **새 통합 브랜치에서 해당 G07 기능 파일의 동일 blob SHA를 옮기는 방식**. 작업 중인 다른 기능 브랜치 전체를 main에 병합하지 않음
- 강사 정답 비공개 정책 유지. 학생 공개 저장소에는 이미 공개된 시연 기능과 관찰 가이드를 둠.
