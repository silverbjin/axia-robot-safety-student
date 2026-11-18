# AXIA Block B D08 — 학생용 Gazebo·RViz2 실시간 시연 가이드 (2026-11-18 최종 후보)

> 대상: Ubuntu 24.04 WSL2/WSLg, ROS 2 Jazzy, Gazebo Harmonic, 공식 Nav2/TB3 Waffle. **교육용 실시간 센서 관찰**, 주행 제어/실제 회피는 하지 않습니다. 사용자 Owner가 2026-11-18 Gazebo GUI Ogre1 + RViz2 현장 성공을 보고했고, ZIP에서 센서 PASS와 Ogre1 GUI plugin 로드를 확인했습니다. 최신 Ogre1 실행의 구간 RTF는 별도로 계측하지 않았습니다.

## 1. 무엇을 시연하는가

```text
Gazebo world (Waffle + visual-only person)
    ├─ registered RGB-D 640×480 @10Hz candidate ── ros_gz_image ── /axia/d05/rgbd/image
    │                                                      └─────── /axia/d05/rgbd/depth_image
    ├─ /scan /odom /tf                                  (read-only RViz2)
    └─ upstream C++ yolo_ros  ← RGB  ─── /yolo/cam0/detections
                                      └── /yolo/cam0/debug_image → RViz2 (독립 image_view 없음)
```

- 공식 Nav2/TB3 Waffle 시작, GUI는 서버가 월드 토픽을 생성한 뒤 별도로 연결.
- WSLg GUI에만 `gz sim -g --render-engine ogre`를 선택하여 Ogre2 fixed-function material 오류를 회피합니다. **Gazebo 서버의 GPU/센서 렌더링은 변경하지 않습니다.**
- 시각용 Actor는 LiDAR 충돌 장애물이 아닙니다. ROS Nav2 Goal, `cmd_vel`, SW Stop, 인증된 HW E-Stop, Collision Monitor/Guard TTL, bbox–Depth 실제 거리(m) 등은 이 데모에서 검증하지 않습니다.
- Python 학생 TODO 6사례는 **별도 오프라인 L0 과제**이며 실제 ROS 실시간 판단 노드에 연결되지 않습니다.

## 2. 단일 WSL2 실행 명령

다른 D08 세션이 이미 실행 중이라면 해당 터미널에서 `Ctrl+C`로 정상 종료한 후 실행하십시오. 기존 `~/axia_d08_student_live_perf_nvidia`와 기존 증거 디렉터리는 삭제하거나 수정하지 않습니다. ROS Jazzy를 **바깥 셸에서 source 하지 않습니다**.

```bash
(
  set -Eeuo pipefail
  BOOT="$(mktemp)"
  trap 'rm -f -- "$BOOT"' EXIT
  curl -fL --retry 3 --max-time 90 \
    "https://raw.githubusercontent.com/silverbjin/axia-robot-safety-student/0239c33c1d4c5350a97e91d52edf5bbdc0134f47/block_B/day08/run_d08_student_live_bootstrap.sh" \
    -o "$BOOT"
  bash -n "$BOOT"
  env -u LIBGL_ALWAYS_SOFTWARE \
    GALLIUM_DRIVER=d3d12 \
    MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA \
    AXIA_D08_RELEASE_BRANCH="main" \
    AXIA_D08_DEMO_DIR="$HOME/axia_d08_student_live_ogre_main" \
    AXIA_D08_GUI_RENDER_ENGINE=ogre \
    AXIA_D08_RGBD_RATE_HZ=10 \
    AXIA_D08_DOMAIN_ID=49 \
    AXIA_D08_HOLD_S=300 \
    bash "$BOOT" --run
)
```

> **실행 시점 주의:** 위 명령은 이 가이드와 런타임이 `main`에 병합된 뒤 사용합니다. `main` 병합 전이라면 `AXIA_D08_RELEASE_BRANCH="release/d08-wslg-ogre-owner-accepted-20261118"`로 바꾸고 별도 디렉터리에서 시험합니다. Bootstrap은 기존 checkout이 변경되어 있으면 자동 덮어쓰지 않고 거부합니다.

## 3. 예상 출력과 현장 판정

```text
D08_STUDENT_RELEASE_SOURCE_SHA=<main SHA>
D08_RGBD_RATE_REQUEST_HZ=10
D08_GAZEBO_WORLD_READY_BEFORE_GUI partition=...
D08_GAZEBO_GUI_RENDER_ENGINE=ogre SERVER_ENGINE_UNCHANGED SENSOR_RTF_NOT_REVERIFIED
D08_DEBUG_IMAGE_WINDOW_SKIPPED RVIZ_YOLO_DEBUG_IMAGE_ENABLED
D04_STUDENT_PROCESS_STARTED name=rviz2 pid=...
D05_LIVE_VERDICT={"status":"PASS_REAL_GAZEBO_REGISTERED_RGBD_YOLO_MOVING_BBOX_ONLY",...}
D05_PUBLIC_SENSOR_ONLY_PASS REAL_RGBD_YOLO PRIVATE_D05_RANGE_NOT_RUN
D04_STUDENT_GUI_HOLD_STARTED seconds=300; press Ctrl+C when finished
```

**PASS 조건 (현장 관찰):** Gazebo 3D에서 Waffle 및 왕복 Actor 확인, RViz2 3D RobotModel/TF 및 RGB/Depth/YOLO debug 패널 확인, `D05_PUBLIC_SENSOR_ONLY_PASS` 확인, GUI 로그에 `Loading plugin [gz-rendering-ogre]` 확인. 창 제목/PID만으로 픽셀 PASS를 선언하지 않습니다. 로그 소유자는 화면 스크린샷을 별도 보존할 수 있습니다.

**기존 Owner 성공 증거:** `d04-gazebo-sROFIPHQ.zip`(SHA256 `7238cf82ef6330cd1f67acac011f14bdae1da38245876acbb03585d958f66057`)에서 `rgb_frames=10`, `depth_frames=9`, `yolo_frames=7`, `person_count=5`, `registered_rgbd_pairs=2`, `cmd_vel_published=false`. `valid_samples=0`은 이 공개 센서 전용 데모에서 D05 거리 Observer를 실행하지 않았다는 뜻입니다.

## 4. 관찰용 터미널 B (선택)

첫 터미널을 중단하지 말고 별도 터미널에서 다음을 확인합니다.

```bash
set +u; source /opt/ros/jazzy/setup.bash; set -u
export ROS_DOMAIN_ID=49
ros2 topic list | grep -E '^(/scan|/odom|/tf|/axia/d05/rgbd/(image|depth_image)|/yolo/cam0/(detections|debug_image))$'
ros2 topic hz /axia/d05/rgbd/image
```

데이터 간격은 실제 RTF 영향을 받으므로 10Hz `SDF update_rate`와 벽시계 10Hz 수신을 같은 것으로 보지 않습니다. 프레임이 없거나 갑자기 느려지면 기존 [RTF 진단 가이드](D08_WSLG_RTF_PERFORMANCE_RESEARCH_AND_FIELD_GUIDE_20261118_KO.md)를 활용해 `ΔSim/ΔReal`을 별도로 측정하십시오.

## 5. 장애별 후속 조치

| 증상 | 우선 분석 | 조치 |
|---|---|---|
| Gazebo/RViz 정상, Ogre2 경고만 존재 | 경고가 실제 화면 장애인지 구분 | 불필요한 시스템 변경 없음. 기본 Ogre2도 사용 가능 |
| Gazebo 흰 화면 / RViz 검은 화면 | `SceneBroadcaster`, 월드 토픽, 메시 리소스, Ogre2 로그 | 검증된 **GUI 전용 Ogre1** 옵션으로 실행; 서버 유지 |
| 센서 PASS지만 Actor 매우 느림 | Actor 궤적 0/5/10 sim-sec와 실제 구간 RTF | waypoint 임의 변경 전 RTF·GPU 경로 진단 |
| GUI가 바뀌었지만 RTF 급락/센서 실패 | GUI/server GPU 설정 혼합 여부 | `AXIA_D08_GUI_RENDER_ENGINE=ogre2`로 원복하여 기존 NVIDIA·10Hz 증거와 비교 |
| ONNX Runtime CI tar 오류 | 공개 CI vendor 외부 다운로드 실패 | 현장 재주행 반복 대신 CI 사전 의존성 실패를 별도 회귀로 해결 |
| 터미널 끝에 `D04_STUDENT_EXIT_CODE=130` | 사용자의 Ctrl+C | 정상 SIGINT 종료, 별도 수정 불필요 |

## 6. 교육 연계 및 근거

- [전체 디버깅 타임라인·커밋별 RED/GREEN 보고서](D08_WSLG_OGRE_RENDERING_FULL_INCIDENT_REPORT_20261118_KO.md)
- [D08 실시간 데모 원형과 관찰 설명](D08_GAZEBO_RVIZ_LIVE_GUIDE_20261115_KO.md)
- 공개 CI: `GUI fallback` L0 [RED 3 failed / 43 passed](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44225840785) → [GREEN 46 passed](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44225910230). **실제 public Gazebo L2는 ONNX vendor 다운로드 오류로 FAIL (가상 화면 인수 아님)**.
- `main` 배포는 해당 검증 범위와 현장 Owner 증거를 구분한 상태에서만 승인합니다.
