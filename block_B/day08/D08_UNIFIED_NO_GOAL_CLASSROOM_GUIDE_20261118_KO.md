# AXIA Block B D08 — 통합 NO_GOAL 학생용 Live 시연 가이드 (개발 후보 v0.1)

> **배포 HOLD / 새 통합 실행기 미검증**. 2026-11-18. 이 문서는 관측 절차 초안이지 통합 성공 가이드가 아니다. 정식 원샷은 Public CI #166의 정확한 SHA에서 한 Gazebo 세계의 sensor+CM+Nav2 L2가 PASS한 뒤 연결한다. 현재 별도의 D07과 D08 실행을 합쳐서 한 E2E라고 주장하지 말 것.

## 1. 실습 목표와 기대 경계
- ROS 2 Jazzy + Gazebo Harmonic + 공식 Waffle, **한 World**, 동일 사람형 **물리 collision + visual** Proxy. 영상만 있는 Actor를 LiDAR 장애물로 취급하지 않는다.
- D04 YOLO person, D05 registered RGB-D 미터 거리와 UNKNOWN, 실제 /scan, 공식 Nav2 Costmap·ComputePathToPose와 Collision Monitor의 read-only 안전 상태를 한 타임라인에서 이해한다.
- **NO_GOAL**: NavigateToPose/FollowPath/최종 /cmd_vel 출력 금지. Planner가 계산한 Path는 주행 결과가 아니고, CM 관측은 실제 감속/충돌방지 인증이 아니다.
- D06/D07/D08 TODO 파일은 실습자가 수정하는 과제로 그대로 유지. 강사 정답 코드 없음.

## 2. 인수 선행 조건과 한 번의 실행
- 현재 Public CI 개발 PR: https://github.com/silverbjin/axia-robot-safety-ci-public/pull/166
- GUI/메시 복구 후보: https://github.com/silverbjin/axia-robot-safety-student/pull/41 (별도 Xvfb L2, WSLg 3D 픽셀 미검증)
- 반복 공식 Planner 후보: https://github.com/silverbjin/axia-robot-safety-student/pull/36 (현재 main과 diverged).
- 두 후보를 수동으로 병행 실행하지 않는다. 통합 CI PASS + Student exact-SHA 실행기 커밋 및 수업 리허설 이후에만 이 문서의 --run 원샷을 확정한다.
- 사용자는 ROS setup을 미리 실행할 필요가 없어야 한다. 실제 통합 원샷은 소유 프로세스만 Ctrl+C 종료하고 원본 폴더/가상환경/로그를 삭제하지 않는다.

## 3. 화면 관측 — 터미널 B (추후 한-world --run 실행 중)
아래 명령은 관측 도구이며 새 Goal/속도 명령을 발행하지 않는다. 실제 노드·토픽명은 설치 런타임을 기준으로 조회한다.

```bash
set +u
source /opt/ros/jazzy/setup.bash
set -u
ros2 node list
ros2 topic list -t | grep -E 'rgbd|yolo|scan|clock|odom|tf|costmap|path|cmd_vel|collision'
ros2 action list -t
ros2 topic info -v /scan
ros2 topic hz /scan -w 20
ros2 action info /compute_path_to_pose
ros2 run rqt_graph rqt_graph
```

rqt_graph에서 가시성 필터(플러그인 버전에 따라 정규식/부분문자열 지원 차이)와 Dead sinks, leaf topics 등을 단계적으로 조절한다. **토픽을 보이게 한 것이 실제 메시지 전달 증거는 아니다.** 필터링 전 전체 그래프 원본을 캡처한다.

| 단계 | 중심 노드/토픽 필터 예 | 해설 및 추가 원본 확인 |
|---|---|---|
| ① 인지·계획 | rgbd, camera, yolo, scan, costmap, planner_server, compute_path_to_pose, path | 실제 RGBD/DetectionArray의 stamp·optical frame·Depth median; 실제 scan obstacle로 갱신된 costmap과 공식 Path의 BEFORE/NEAR/RESTORED 구분 |
| ② Nav2·제어 | controller_server, velocity_smoother, collision_monitor, cmd_vel | NO_GOAL에서는 Navigation Goal/명령 출력이 발생하지 않아야 함. isolated CM synthetic Twist는 실제 주행이 아님. 억지로 노드를 채우지 않음 |
| ③ 안전·물리 증거 | scan, odom, clock, tf, collision_monitor, guard, contacts | scan source/QoS/첫 전달 gap과 Contact 토픽 provenance 확인. 실제 가드가 실행되지 않았다면 **NOT_CONNECTED**로 표시 |

## 4. 수업 중 판정 유의
- VALID: 같은 실제 ROS RGB+Depth+YOLO triad skew ≤50ms, monotonic 수신 age ≤0.5s, camera registration 증거, YOLO person ROI 유효 32FC1 median. 한 거리만으로 2단계 인수가 아니다.
- UNKNOWN: person 유실/Depth 무효/오래된 센서/TF/등록 실패. **CLEAR 또는 이동 허가가 아니다**.
- 실제 0.65m/0.30m 근접은 native set_pose 명령 좌표가 아니라 LaserScan 실측으로 확인.
- 공개 CI Xvfb 창 PASS는 WSLg 실제 3D 화면 검증이 아니다.
- 예상 출력과 검증 상태: D08_LIVE_NO_GOAL_ACCEPTED=NO (현 단계), D08_MOVING_E2E_ACCEPTED=HOLD, D08_OWNER_WSLG_VISUAL=NOT_RUN.
- 이전 D04/D05 또는 D07만의 PASS 문자를 D08 최종 통합 PASS로 바꾸지 않는다.

## 5. 증거 수집과 종료
- 단일 실행기의 verdict.json / trace.jsonl / source SHA / world+robot+proxy / ROS_DOMAIN_ID / GZ_PARTITION / scan/TF/CM first gaps / costmap Path 원본 / SHA256SUMS가 같은 증거 묶음이어야 한다.
- 각 소스의 설치된 type/QoS/주기 확인 전 미검증으로 남긴다. 기본 종료는 실행 소유 터미널에서 Ctrl+C. 수업 중 임의 pkill 또는 reset --hard 금지.

이 가이드는 **Task04 문서 초안**으로서 Task01·Task02 실제 L2 완료 및 학생용 정확한 실행기 배포 전까지 릴리스하지 않는다.
