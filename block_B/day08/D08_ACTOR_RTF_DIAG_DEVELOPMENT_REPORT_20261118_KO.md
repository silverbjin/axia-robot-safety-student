# AXIA D08 — Actor RTF 관측기 개발·검증 중간보고서

- 시점: 2026-11-18 KST.
- 목표: D08 Gazebo+RViz2 렌더링 복원 이후 visual-only Actor가 느려 보이는 첫 시간 경계(RTF·sim_time·SDF 속도)를 한 번의 읽기 전용 실행으로 계측.
- 기준 현장: Owner ZIP d04-gazebo-FoAq7eRu.zip, 기존 Gazebo/YOLO 센서 L2 성공과 GUI 표시 관찰. RTF는 당시 ZIP에 없었음.
- 코드 저장소/브랜치: silverbjin/axia-robot-safety-student / diagnostics/d08-actor-rtf-20261118.
- PR: https://github.com/silverbjin/axia-robot-safety-student/pull/45 (Draft, main NOT_MERGED)

## 재사용·범위 축소

기존 Gazebo Actor SDF가 0→5→10 sim-sec 동안 x=2.8→2.0→2.8m 이동한다. 애니메이션 기준 0.16m/s. Gazebo server, Gazebo GUI, YOLO, RViz2는 실행기에서 이미 분리된 setsid 프로세스 그룹이다. 교착상태 단정 또는 Actor 외부 구동 ROS 노드 제작은 보류.

- 신규 read-only 스크립트: block_B/day08/tools/d08_actor_rtf_diagnose.py
- L0 회귀: block_B/day08/tests/test_d08_actor_rtf_diagnose.py
- 학생 및 강사 공용 공개 안내: block_B/day08/D08_ACTOR_RTF_DIAGNOSTIC_GUIDE_20261118_KO.md
- 변경된 CI: .github/workflows/d08-online-integration-student.yml (진단 L0 테스트 1개만 추가)
- 기존 D04/D05/D06/D07/D08 Gazebo 실행기, Actor PATH, ROS sensors, YOLO, Nav2, CM/Guard, 학생 TODO, 비공개 강사 솔루션: **수정하지 않음**.

## RED → GREEN → REFACTOR → REVIEW → COMMIT

| 단계 | 실제 실행·근거 | 결과 |
|---|---|---|
| RED | 공개 Student Actions [Run 44210674140](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44210674140): 스크립트가 없는 상태에서 L0 계약 실행 | 4 failed, 26 passed (예상 RED) |
| GREEN | 공개 Student Actions [Run 44210884633](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44210884633): 실제 스크립트 추가 후 synthetic stats + SDF + ZIP 테스트 | **30 passed**, CI SUCCESS |
| 기존 코드 | 공개 Student Actions [Run 44210884605](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44210884605): 기존 Block B 경량 Python 계약 | **56 passed**, CI SUCCESS |
| 문서 포함 HEAD | 공개 Student Actions [Run 44211061952](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44211061952) | **30 passed**, CI SUCCESS |
| REVIEW | 원본 실시간 Goal/command 발행 없음, sim_time/RTF 부족 시 INCONCLUSIVE, overwrite 차단, WSL2 원샷 외부 ROS source 없음 | 정적 점검 완료 |
| COMMIT | 이 보고서를 진단 브랜치에 후속 커밋, 최신 SHA는 GitHub PR HEAD에서 확인 | main 병합하지 않음 |

현장 수동 실행 명령: D08 Live가 켜진 상태에서 별도 WSL2 터미널에서 안내문의 Bash 원샷 실행. 동일 GZ_PARTITION으로 WorldStats를 20초 읽고 새 결과 ZIP 한 개 생성. 이 스크립트가 실제로 Gazebo를 실행하지 않는다.

## 진단 판정과 증거

- category=LOW_RTF_CANDIDATE: real_time_factor median < 0.8, GPU/CPU/WSLg/센서 자원 병목 후보.
- category=SLOW_ACTOR_TRAJECTORY_CANDIDATE: RTF 정상인데 기본 Actor 0.16m/s. D08만 waypoint 시간을 0/2/4초로 빠르게 설정하는 최소 수정 후보.
- category=RTF_OK_GUI_FPS_UNVERIFIED: sim RTF 양호, GUI 픽셀/프레임률 별도 관측 필요.
- category=SIM_PAUSED, SIM_TIME_STALLED, RTF_NOT_MEASURED: 성공 판정 불가/경계 구분.

자동 저장은 summary.json, REPORT.md, gazebo_topics.txt, world_stats_raw.txt, processes.txt, resources.txt와 ZIP. 입력 자료의 runtime process/env에는 로컬 경로가 있을 수 있으므로 공개 첨부 전 확인한다.

## 부수적으로 트리거된 기존 전체 Gazebo L2 — 별도 실패

공개 CI가 DAY08/** 경로 변경만으로 기존 GUI L2를 트리거했다. 이 진단 브랜치는 기존 Gazebo 런타임 및 YOLO 소스를 전혀 변경하지 않았으므로, 해당 L2를 진단 스크립트 자체의 PASS/FAIL로 혼동하지 않는다.

- [Run #44210674189](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44210674189), [Run #44210884596](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44210884596): **FAILURE**.
- **최초 실패:** yolo_onnxruntime_vendor가 ONNX Runtime 1.20.0 다운로드에서 9바이트 파일을 받았고 CMake에서 Unrecognized archive format으로 중단됨. 실제 Gazebo/Actor RTF 측정 단계에 도달하지 못했다.
- 이 실패를 Actor의 교착/RTF 저하 원인으로 해석하지 않는다. 같은 종류의 다운로드 실패는 YOLO 의존성 경계의 별도 회귀 과제로 관리하며, 이번 교육용 수동 진단 배포를 위해 기존 ROS/Nav2/YOLO 패키지 수정은 하지 않는다.
- **현장 실기 측정은 여전히 NOT_RUN.** L0 GREEN의 범위는 synthetic stats 파서, 판정, ZIP·무수정 계약이다.

## 검증 수준 / 미검증

- **검증:** Python 구문/파서·SDF 0.16m/s·RTF 분류·정상/실패 경계·ZIP·중복 경로 차단: 공개 CI L0 GREEN.
- **미검증:** 사용자 WSL2 실제 RTF 측정, GUI FPS, Actor 실 pose 궤적, Gazebo 동작 시간 동기화.
- **미실행/범위외:** moving Goal, cmd_vel, CMonitor/Guard TTL, Odom/Contact, 인증 E-Stop.
- script_only=True, read_only=True, no_goal=True, safety_ttl_verified=False. Robot Safety MVP 전체 통합 PASS가 아님.
- 이번 테스트를 이유로 성공했던 Gazebo/YOLO 기능을 반복 재실행하지 않는다.

## 다음 결정 게이트

Owner WSL2 진단 ZIP의 실제 RTF가 낮다면: D08 전용 센서/GUI 부하 비교만 우선하고 최초 타이밍 위반을 찾는다.
RTF가 양호하면: 기존 D05 PATH 기본값은 보존하고 D08 전용 Actor waypoint 0,2,4초 하나만 변경하여 RED→GREEN→CI L2 한 번 검사한다.
실제 수집이 없으면: 원인 판정 INCONCLUSIVE. Actor 외부 프로세스화하지 않는다.
