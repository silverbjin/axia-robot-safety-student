# AXIA D08 — 실제 Actor RTF 저하 분석·중복 디버그 창 제거 중간보고서

- 날짜: 2026-11-18 KST
- Owner 실측 근거: 사용자 첨부 `d08_actor_rtf_diagnostics.zip`, Gazebo 화면 RTF `5.27%`
- 공개 Student 저장소: `silverbjin/axia-robot-safety-student`
- 작업 브랜치: `fix/d08-gazebo-rviz-scene-mesh-20261118` / Draft PR #41
- 범위: D08의 불필요한 `image_view` 창만 제거. Gazebo SDF Actor/Navigation/YOLO/CM/Guard 로직, 정답 TODO, 비공개 Instructor 코드는 변경하지 않음.

## 1. 실제 증거와 원인

`summary.json` 실제 수치:

| 관측 | 실제 |
|---|---|
| RTF samples | 45 |
| Gazebo RTF median | 0.0079 (0.79%) |
| Gazebo RTF min/max | 0.0038 / 0.0117 |
| sim_time from first to last | 2.604→3.933 sec (증가 1.329 sec) |
| Gazebo real_time first/last | 37.215741025→56.738898915 sec (19.52315789 sec 증가) |
| sim_time/real_time 구간 평균 | 약 **0.0681 (6.81%)** |
| 스크린샷 RTF 표시 | 5.27% (다른 시점) |
| Actor x waypoints | 2.8→2.0→2.8 m, t=0/5/10 sim sec |
| 명목 Actor 속도 | 0.16m/s, 시뮬레이션 시간 기준 |
| Gazebo server CPU | 약 95.8% of a CPU core (ps cumulative) |
| Gazebo GUI CPU | 약 100% of a CPU core |
| RViz2 CPU | 약 37.0% of a CPU core |
| YOLO CPU | 약 12.4% |
| image_view CPU | 약 4.8% |
| 사용 가능 RAM | 29,580 MiB / total 31,804 MiB |
| nproc | 8 |

**결론:** WorldStats의 두 수치(실시간요소 reported median 0.79%, 기간 평균 약 6.81%)는 집계 방식상 차이가 있다. 둘 다 실제 시뮬레이션이 현저히 느리다는 점을 지지한다. 기간 평균 6.81% 기준 5 sim-sec Actor 한 방향 이동은 약 **73.4 wall-sec**로 추정되며, 화면의 5.27%라면 약 94.9초다. 이는 실제 Actor Pose 추적 결과가 아니라 시간 비율과 SDF로 추정한 값이다.

동일 로그에서 이미 Gazebo server, Gazebo GUI, YOLO, Bridge, `image_view`, RViz2는 **별도 PID·process group**으로 시작한다. 스크립트 하나에서 запуск한다고 교착상태라고 단정할 수 없고 실제 WorldStats 시간이 전진하므로 전체 시뮬레이션 deadlock이 확인되지 않았다. Actor 분리 프로세스 제작은 불필요하다.

CPU 코어별 부하와 GUI/Ogre2/센서 렌더링 부하가 후보이나 GPU 사용률·GL renderer와 개별 단계 wait 증거가 없어 확정하지 않는다. RAM 부족은 낮은 가능성. ROS→YOLO나 Nav2 제어 경계 장애라고 보기도 어렵다.

## 2. 이미 승인된 최소 변경

D08 렌더 복원 브랜치의 `run_d08_student_live_once.sh`가 `AXIA_D04_STUDENT_IMAGE_VIEW=0`을 지정한다. 공식 코드 재사용 `block_B/day04/run_student_gazebo_yolo_once.sh`는 해당 변수를 검증하고 **D08에서만** 중복 `image_view` 프로세스를 생성하지 않는다. D04/D05 단독 프로필 기본값은 1(유지). D08 RViz2 설정에는 `/yolo/cam0/debug_image`가 그대로 있고, upstream YOLO detector/`/yolo/cam0/detections`는 유지한다.

이 조치의 목적은 **불필요한 렌더러 1개 제거**이며 이것만으로 Gazebo RTF 정상화를 보장하지 않는다. 특히 실제 `image_view`는 CPU 약 4.8%, Gazebo Server/GUI는 각각 약 100%로 부담이 훨씬 크다. 사전 추정으로 `RTF_RECOVERED` 또는 `ACTOR_SPEED_PASS`를 주장하지 않는다.

## 3. RED → GREEN → REVIEW → COMMIT

| 단계 | 실행 위치/결과 | 검증 수준 |
|---|---|---|
| RED | 공개 D08 L0 [Run #44214103125](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44214103125): **3 failed, 32 passed** (실행기·토글·CI 2창 계약 미구현) | Python/스크립트 계약 |
| GREEN | 공개 D08 L0 [Run #44214442717](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44214442717): **35 passed**, 학생 D08 TODO는 의도된 RED 상태 유지 | Python/스크립트 계약 |
| 기존 Block B | 공개 [Run #44214440950](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44214440950): **56 passed** | 기존 D04/D05 Python |
| 실제 Gazebo L2 | 2창 새 CI Run #44214440895 — 결과 별도 확인 필요 | ROS·Gazebo/Xvfb |
| Owner WSLg RTF 재측정 | 수정 코드 현장 실행 이전, **NOT_RUN** | 최종 현장 |

변경 파일:
- `block_B/day04/run_student_gazebo_yolo_once.sh`
- `block_B/day08/run_d08_student_live_once.sh`
- `.github/workflows/d08-student-gazebo-rviz-l2.yml`
- `.github/workflows/d08-online-integration-student.yml`
- `block_B/day08/tests/test_d08_no_duplicate_debug_window.py`
- 본 보고서, 기존/새 안내 문서

**정적 확인:** `NO_GOAL`, `NO_CMD_VEL`; 기존 Actor SDF, D05 모니터, ROS 메시, Nav2, CM/Guard 및 학생 TODO는 변경하지 않았다. D08 L2는 실제 Gazebo+RViz Xvfb 두 창과 YOLO 메시, 시각화 리소스 경로를 별도 확인한다.

## 4. 다음 성능 개선 순서 (재시험 최소화)

1. Owner WSL2에서 수정 D08 Live를 실행하고 `GZ_PARTITION`이 맞는 기존 read-only RTF 스크립트로 한 번 재측정한다. 기존 파일을 덮어쓰지 않는다.
2. RTF가 계속 0.1보다 낮으면 먼저 Gazebo GUI/서버의 실제 렌더러·GPU 경로 및 RGB-D 640×480 30Hz/Depth 5Hz 병목을 좁힌다. D08 전용 센서 update_rate 저하(예: 30→10Hz)와 GUI 부하를 **후보 한 가지씩** 비교하고 RGB-D·YOLO 수신 및 경계 타이밍을 다시 검증한다. 기존 공식 D04/D05 기본 설정은 보존.
3. RTF가 회복돼도 Actor의 0.16m/s가 강의에서 느리다면 그때 D08 전용 0/2/4-s waypoint 시간을 검토한다.
4. Actor 별도 ROS Pose publisher, 새 Nav2 제어기, 범용 성능 모니터·센서 프레임워크 개발은 하지 않는다.

## 5. 미검증·배포 경계

- **아직 미검증:** 수정판 Owner WSL2 RTF, 2창 WSLg 실제 픽셀, 실제 Actor 이동 시간, GPU utilisation, D06/G07 종단 TTL.
- **미변경:** moving Goal, 안전 SW Stop, 인증 HW E-Stop.
- 기존 실제 RGB-D·YOLO Live 성공은 보존하지만 D08 `image_view` 제거가 RTF를 정상화했다는 새 주장은 금지.
- `main` 병합은 사용자 별도 승인 전 수행하지 않는다.
