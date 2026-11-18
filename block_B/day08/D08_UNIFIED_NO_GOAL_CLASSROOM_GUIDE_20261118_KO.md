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

## 6. 실제 공개 CI로 확인한 계층별 관찰 예시 (릴리스 전 교육용 로그)

- [D08 공개 Run #44227457087](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44227457087), HEAD `d37d1a36507cfe5c99cd41f4384cc9c7cac3c5ca`: 실제 Gazebo 한 World에서 공식 `ComputePathToPose` before/intrusion/restored 세 경로를 원본 Path로 관측. 같은 물리 사람 Proxy의 실제 LaserScan 해당 방향 거리 **1.875→0.552→1.876m**, 공식 Costmap 장애물 lethal cell **0→73→0**, 우회로의 물리 Proxy 최소거리 **0.003→0.327→0.018m** (단위 m). 이 결과는 실제 로봇의 주행·감속·충돌방지 인증 증거가 아님.
- [통합 후보 Run #44229304083](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44229304083), HEAD `d06c00a3846b1fcdcc8a5f3532b54a523de78283`: **같은 World**의 실제 RGB/Depth·YOLO DetectionArray·D05 미터 값 연결을 최초로 확인, VALID 두 건 **0.475343m/0.534589m**, UNKNOWN `NO_PERSON_CLASS_IN_ACTUAL_YOLO` 한 건. 단, 물리 사람은 가까워졌는데 D05 ROI 값이 오히려 증가하므로 당시 판정은 **HOLD**. 정확한 거리·의미는 ROI/BBox 검증 완료 뒤 설명할 것.
- 현재 본 학생용 원샷 `run_d08_student_live_once.sh`는 기존 **D04/D05 시각 관측** 실행기를 재사용하며, 상기 D07 공식 Nav2 3상 통합 런타임과 **아직 동일하지 않음**. 기존 실행기로 3상 공식 Path가 자동으로 보인다고 안내하지 않는다. 공개 CI 한 SHA 통합/WSLg GUI 준비 후 같은 실행기로 교체할 예정; 현재 `D08_LIVE_NO_GOAL_ACCEPTED=NO`.

### rqt_graph 실습 시 실제 데이터와 미배선 구분

1. **인지·계획**: RGB/Depth/Yolo DetectionArray를 표시한 후 `/scan`, `/global_costmap/costmap`, `/compute_path_to_pose`를 단계적으로 추가합니다. `ComputePathToPose`는 **읽기 전용 공식 Path Action 요청**이며 `NavigateToPose` 주행 명령이 아닙니다. 토픽 필터는 사용 중인 rqt_graph 버전의 노드·토픽 숨김 옵션에 맞게 적용합니다.
2. **Nav2·제어**: `/planner_server`, `/controller_server`, `/collision_monitor`를 표시하되, NO_GOAL에서는 실제 감속 Twist가 발생하지 않는 것이 정상입니다. 공식 CM이 `/scan`을 구독한다는 ROS Graph 증거만으로 SLOW/STOP state 메시지가 실제로 출력됐다고 해석하지 않습니다.
3. **안전·물리**: `/clock`, `/tf`, `/odom`, `/scan`과 실제 Contact topic의 존재·메시지 발행을 구분합니다. 실제 Guard 노드가 없는 수업 실행에서는 Guard TTL 간선을 그리지 않습니다. **미확인 연결은 비어 있는 선/미검증으로 표시**합니다.

원본 관찰 명령(시연이 실제 실행 중인 별도 터미널, Jazzy 소싱 후):
```bash
ros2 topic list -t
ros2 topic info -v /scan
ros2 topic hz /scan -w 20
ros2 topic info -v /axia/d08/rgbd/depth_image
ros2 topic info -v /yolo/cam0/detections
ros2 action info /compute_path_to_pose
ros2 run rqt_graph rqt_graph
```
위 명령은 토픽·QoS·주기 확인용이며, 실제 Goal 전송이나 Stop 제어를 실행하지 않습니다. 수업 중 검출 실패/UNKNOWN을 **CLEAR/이동 허가**로 치환하지 마십시오.
