# AXIA Block B D08 — WSLg Gazebo 흰 화면·RViz2 검은 3D 화면 복원 후보

> **상태:** 공개 CI 실 Gazebo+YOLO+RViz **L2 PASS** / Owner WSL2 렌더 픽셀 최종 인수 **NOT_VERIFIED**. 수정 브랜치 `fix/d08-gazebo-rviz-scene-mesh-20261118`. 기존 센서 Live 성공은 보존한다. 공식 ROS 2 Jazzy / Gazebo Harmonic / Nav2 / TurtleBot3 Waffle을 재사용하며 NO_GOAL·NO_CMD_VEL이다.

## 1. 증거로 확인한 최초 실패 경계

**Owner가 제공한 실제 2026-11-18 화면**: YOLO 이미지 창에서 사람 bbox, RViz Image 패널에서 D05 RGB·YOLO 이미지는 보이지만, **Gazebo 클라이언트 본문은 흰색**, **RViz 중앙 3D 뷰는 검정**. CPU/GPU 고장 또는 ROS 전체 중단으로 단정할 근거는 없다.

**원본 증거 ZIP:** `d04-gazebo-2GH7zxgm.zip` 내 `gazebo_nav2.log`, `rviz2.log`, `scene/student_human_world.sdf.xacro`, `live_verdict.json`. 사용자가 전달한 원본은 덮어쓰지 않는다.

- `live_verdict.json`은 `PASS_REAL_GAZEBO_REGISTERED_RGBD_YOLO_MOVING_BBOX_ONLY`, registered RGB-D 8쌍 / RGB 5 / Depth 10 / YOLO 4 / person 검출 2건이다. **센서 게이트 PASS ≠ GUI 렌더링 PASS**.
- Gazebo 세계에 `SceneBroadcaster`가 `<xacro:unless value="$(arg headless)">` 조건으로 존재한다. 원래 D08 실행은 `headless:=False`였으므로 **이 파일의 조건만으로 실제 런타임 플러그인 부재를 단정하지 않는다.** D07-H01에서 실측 성공한 **서버 먼저 시작(headless:=True) + 임시 월드에 SceneBroadcaster 1개 무조건 포함 + 준비 후 독립 `gz sim -g` 연결** 방식을 D08에만 적용한다.
- `rviz2.log`: `Could not load resource [package://nav2_minimal_tb3_sim/models/waffle_base.dae]`; 같은 오류가 `lds.dae`, `r200.dae`, `tire.dae`에도 존재. 기존 `/robot_description`이 ROS 배포판에 실제 설치된 메시 폴더를 가리키지 않는 별도 오류다. `base_scan` 옛 timestamp 메시지 필터 드롭은 **또 다른 TF/시간 경계**이며 화면 패치로 해결됐다고 주장하지 않는다.

## 2. 최소 수정·안전 경계

1. **D05 임시 월드만 변경:** 실제 D07-H01의 SceneBroadcaster 복원법을 재사용하며 공식 Nav2 월드 원본은 변경하지 않는다. `headless:=True`에서도 정확히 1개 브로드캐스터가 남도록 한다.
2. **D08 Live에서만 단계적 GUI:** ROS·Gazebo 서버 world clock/stats를 확인한 뒤 `gz sim -g`를 별도 하위 프로세스로 실행한다. CI는 소프트웨어 렌더링, WSLg는 D07-H01과 동일한 D3D12 GPU 트라이얼을 자식 GUI에만 적용한다. 기존 D04/D05 기본 실행은 바꾸지 않는다.
3. **RViz 표시용 사본만 보정:** 공식 Nav2 installed URDF와 메시 파일을 확인해 임시 private view URDF의 `package://` 경로만 교정, RViz RobotModel은 `Description Source: File`로 표시한다. 공식 `robot_state_publisher`, `/robot_description`, Gazebo 충돌/센서 모델은 그대로다.
4. **동작 제한:** moving Goal, cmd_vel, Collision Monitor→Guard 150ms 실측, 실제 bbox→Depth 거리, 인증 E-Stop, 안전 TTL 및 물리 충돌은 이 패치로 증명되지 않는다. 시각 전용 Actor도 그대로다.

관련 근거:
- [D07-H01 실제 사용된 SceneBroadcaster 보정 코드](https://github.com/silverbjin/axia-robot-safety-student/blob/main/block_B/day07/h01_runtime/tools/d07_h01_scene_broadcaster_overlay.py)
- [D07-H01 서버-준비 후 GUI 시작 코드](https://github.com/silverbjin/axia-robot-safety-student/blob/main/block_B/day07/h01_runtime/scripts/p2_no_goal_smoke_ci.sh)
- [Gazebo Harmonic 공식 Troubleshooting](https://gazebosim.org/docs/harmonic/troubleshooting/)
- [Nav2 minimal TurtleBot3 메시 경로 Issue #19](https://github.com/ros-navigation/nav2_minimal_turtlebot_simulation/issues/19)

## 3. 학생·강사 WSL2에서 단일 명령 (기존 폴더 보존)

**검증 브랜치 전용**, 공개 CI L2 검증 성공을 확인한 후 실행한다. 새로운 `~/axia_d08_student_live_renderfix` 폴더만 사용해 이전 `~/axia_d08_student_live`·D04/D05 증거를 건드리지 않는다. 새 소스는 Git에서 직접 내려받는다.

```bash
(
  set -Eeuo pipefail
  BOOT="$(mktemp)"
  trap 'rm -f -- "$BOOT"' EXIT

  curl -fL --retry 3 --max-time 90 \
    "https://raw.githubusercontent.com/silverbjin/axia-robot-safety-student/35b5bdd3f070cdf40cc01bd554a26860ac858604/block_B/day08/run_d08_student_live_bootstrap.sh" \
    -o "$BOOT"

  bash -n "$BOOT"
  AXIA_D08_DOMAIN_ID=49 AXIA_D08_HOLD_S=300 bash "$BOOT" --run
)
```

**정상일 때만 기대하는 출력 패턴:**

```text
D08_STUDENT_RELEASE_SOURCE_SHA=<fix 브랜치의 실제 Git SHA>
D08_RVIZ_OFFICIAL_MESH_VIEW_READY ...
D08_GAZEBO_WORLD_READY_BEFORE_GUI partition=...
D08_GAZEBO_GUI_BACKEND=D3D12_OWNER_TRIAL_NOT_VISUAL_PROOF
D04_STUDENT_PROCESS_STARTED name=gazebo_gui ...
D04_STUDENT_PROCESS_STARTED name=rviz2 ...
D05_LIVE_VERDICT={"status":"PASS_REAL_GAZEBO_REGISTERED_RGBD_YOLO_MOVING_BBOX_ONLY", ...}
D05_PUBLIC_SENSOR_ONLY_PASS REAL_RGBD_YOLO PRIVATE_D05_RANGE_NOT_RUN
D04_STUDENT_SHUTDOWN: stopping only child process groups
D04_STUDENT_EXIT_CODE=0
```

위 문자열은 **기대 결과**이며 현재 Owner WSL2에서 수정판을 실행했다는 뜻이 아니다. Gazebo 월드와 RViz 모델·TF·Grid·LaserScan 화면이 실제로 보이는지 확인한다. 보이지 않으면 기존 센서 PASS를 시각 인수로 승격하지 않고 `OWNER_WSLG_3D_RENDER_NOT_VERIFIED`로 기록한다.

### 선택: WSLg 그래픽 드라이버 대응

D07-H01과 동일한 기본 D3D12 렌더링이 WSLg 장치에서 지원되지 않는 경우에만 다음 환경변수로 **GUI 자식에 한정한 소프트웨어 렌더링 프로파일**을 시도할 수 있다. 이는 GPU 하드웨어 경로의 검증이 아니며 성능·전달 주기가 달라질 수 있다. 동일 오류를 무한 재실행하지 않고 최초 GUI 에러 로그를 보존한다.

**별도 셸에서 `bash "$BOOT"`만 실행하지 않는다.** 첫 번째 원샷 코드 전체를 다시 복사하고 맨 마지막 명령만 다음과 같이 바꿔 실행한다. 임시 `BOOT` 경로는 해당 코드 블록 안에서만 유효하다.

```bash
  AXIA_D08_GUI_BACKEND=software AXIA_D08_DOMAIN_ID=49 AXIA_D08_HOLD_S=300 bash "$BOOT" --run
```

즉, 마지막 행만 교체하고 나머지 `curl` 다운로드와 `trap`을 포함한 동일한 괄호 블록 안에서 실행한다. 기본 GPU 프로파일이 정상일 때는 이 옵션을 사용하지 않는다.

## 3-A. 실제 RED→GREEN 검증·재현 가능한 최초 실패

**수정한 런타임 검증 HEAD:** `689025f915730e4e26af5376d639addbf6b8436a`. 추가 문서 커밋은 실행기·메시 보정기·D05 장면 생성기를 변경하지 않는다.

| 게이트 | 실제 공개 CI 결과 | 의미 |
|---|---|---|
| RED L0 | [Run #44116046097](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44116046097) — `5 failed, 26 passed` | 새 SceneBroadcaster/RViz 메시 복원 기능이 없음 |
| GREEN L0 | [Run #44119696426](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44119696426) — `32 passed` | 두 복원 경로와 No-Goal 실행 계약 |
| 기존 Block B | [Run #44119696463](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44119696463) — `56 passed` | D04/D05 기존 동작 회귀 정상 |
| 기존 D05 실제 Gazebo | [Run #44119696470](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44119696470) — SUCCESS | 공통 D04/D05 실행 경계 보존 |
| **D08 실제 GUI L2** | [Run #44119696238](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44119696238) — **SUCCESS** | 실제 Gazebo world pose/SceneBroadcaster 전송, RViz 공식 메시 4개 보정, 3창 생성, 센서 Live, 정상 종료 |

L2 원본 출력:

```text
D08_GZ_SCENE_BROADCASTER_POSE_GATE_PASS
D08_STUDENT_RELEASE_SOURCE_SHA=689025f915730e4e26af5376d639addbf6b8436a
D08_RVIZ_OFFICIAL_MESH_VIEW_READY ... fixed_meshes=4
D08_GAZEBO_WORLD_READY_BEFORE_GUI ...
D05_PUBLIC_SENSOR_ONLY_PASS REAL_RGBD_YOLO PRIVATE_D05_RANGE_NOT_RUN
D04_STUDENT_EXIT_CODE=0
D08_RVIZ2_ACTUAL_X11_WINDOW_PASS
D08_RVIZ_MESH_RESOURCE_ERRORS_NONE_PASS
D08_STUDENT_GAZEBO_YOLO_RVIZ_GUI_L2_PASS_NO_GOAL
```

실측 `registered_rgbd_pairs=3`, `rgb_frames=4`, `depth_frames=5`, `yolo_frames=4`, `person_count=4`. 화면이 공백이었던 원래 Owner WSL2와 같은 **WSLg D3D12 화면 픽셀**을 CI Xvfb에서 관찰할 수는 없으므로 `OWNER_WSLG_3D_RENDER_NOT_VERIFIED`다. 센서 검출 수치는 로봇의 이동이나 물리적 사람 인식 정합을 증명하지 않는다.

개발 도중 공개 L2에서 CI 스크립트의 중첩 쉘 따옴표 오류 및 장면 게이트 출력의 동시 기록 경쟁이 발생했다. 이를 공개 CI 회귀 검사에 포함해 수정한 결과, *실제 월드 장면 토픽 확인* 후 `SCENE_GATE` 별도 증거로 저장하여 GREEN. 추후 같은 오류는 로그 최종 에러가 아니라 최초 실패 경계부터 점검한다.

## 4. 장면/GUI/안전 검증 구분

| 검증 수준 | 필요한 증거 | 판정 |
|---|---|---|
| L0 | XML 1개 unconditional SceneBroadcaster, 공식 설치 메시 경로 검증, 실행기 Bash 문법 | **32 passed — CI PASS** |
| L2 센서 | 실제 Gazebo RGB/Depth 및 YOLO person/bbox 관측 | **CI PASS** (Owner 기존 센서 PASS도 별도 보존) |
| L2 GUI 전달 | 같은 Git SHA에서 Gazebo `/world/default/pose/info` 및 RViz 공식 메시 로딩 오류 없음, X11 3창 생성 | **CI L2 PASS, WSLg pixels unverified** |
| Owner WSLg 시각 | Gazebo 월드/로봇/사람, RViz 3D Grid/RobotModel/Scan 화면의 **실제 스크린샷** | 수정판 실행 전 NOT_VERIFIED |
| 안전·실제 회피 | moving Goal, `/cmd_vel`, Contact/odom, CM→Guard 타이밍, 인증 E-Stop | 이번 범위 OUT |

**종료:** 주 실행 터미널에서 `Ctrl+C`; 기존 개인 프로세스 전체를 죽이는 `pkill`이나 `wsl --shutdown`은 사용하지 않는다. 원본 증거는 `~/axia_d04_student_evidence/d04-gazebo-*`에 새 폴더로 남는다. ROS/Gazebo를 실제 수행하지 않은 곳에서 성공으로 기록하지 않는다.
