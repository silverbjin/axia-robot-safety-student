# AXIA D08 — WSLg/Gazebo RTF 성능 개선: 공식 문서·Issue 근거와 현장 원샷 비교

- 날짜: 2026-11-18 KST / ROS 2 Jazzy · Gazebo Harmonic · WSL2 Ubuntu 24.04
- 범위: 읽기 전용 GPU 렌더러 사전진단과 **D08 등록 RGB-D 센서의 update_rate만 30Hz↔10Hz** 비교
- 비범위: D06/D07/G07 이동 제어, 새 Actor 노드, physics, TF, LiDAR, YOLO 모델 교체, Windows GPU 드라이버 변경
- GitHub: 공개 Student Draft PR #47 (`perf/d08-wslg-rtf-sensor-profile-20261118`). `main` 미병합

## 1. 현장 실패 경계 및 공식 조사

Owner `d08_actor_rtf_diagnostics.zip` 원본: `rtf_samples=45`, WorldStats `rtf_median=0.0079`(0.79%), 시뮬레이션 진행 1.329초/실제 시간 진행 19.523초의 **구간 평균 약 6.81%**, GUI RTF 표시 5.27%. GPU 사용률이나 `GL_RENDERER`는 미측정. Actor는 시뮬레이션 시간에 0.8m/5초(0.16m/s). Gazebo server와 Gazebo GUI CPU 각각 약 1코어, RViz 약 0.37코어, 남은 RAM 약 29.6GiB. 교착상태 증거는 없음.

검토한 **공식 자료와 해결 이력**:

1. [Gazebo Harmonic Troubleshooting](https://gazebosim.org/docs/harmonic/troubleshooting/): Ogre2는 OpenGL 3.3 초과, 4.3 이상 권장. `glxinfo`·`~/.gz/rendering/ogre2.log` 검사, software renderer 임시 시험 가능. **단, software rendering은 성능 개선책으로 가정하지 않는다.**
2. [Gazebo Harmonic Sensors](https://gazebosim.org/docs/harmonic/sensors/): SDF `<update_rate>`는 센서 생성 빈도. D08 실제 SDF `axia_d05_registered_rgbd`: **640×480, 30Hz**, 별도 Depth 320×240 5Hz, GPU LiDAR 5Hz. 본 후보는 RGB-D만 10Hz로 수정한다.
3. [Microsoft WSLg GPU selection Wiki](https://github.com/microsoft/wslg/wiki/GPU-selection-in-WSLg): `glxinfo -B`로 렌더러 확인, `MESA_D3D12_DEFAULT_ADAPTER_NAME`로 어댑터 선택 가능.
4. [microsoft/WSL #12412](https://github.com/microsoft/WSL/issues/12412): NVIDIA 강제 선택이 `llvmpipe`로 떨어진 사례. `GALLIUM_DRIVER=d3d12`가 유효했다는 현장 댓글이 있으나 **2026-10-15 자동 비활성 종료**, 공식 보편 해결 확정이 아님.
5. [microsoft/wslg #1332](https://github.com/microsoft/wslg/issues/1332): 최신 Mesa에서 d3d12 자동선택 실패 보고 및 `GALLIUM_DRIVER=d3d12` 사례. GPU 가속이 활성화되어도 어떤 작업은 llvmpipe보다 느릴 수 있음.
6. [gazebosim/gz-sim #2873](https://github.com/gazebosim/gz-sim/issues/2873) 및 [microsoft/wslg #1498](https://github.com/microsoft/wslg/issues/1498): WSLg D3D12 GUI 및 화면 readback이 별도의 병목이 될 수 있음을 보고. GPU 가속 존재와 RTF 개선은 별개.
7. [gazebosim/gz-sim #2982](https://github.com/gazebosim/gz-sim/issues/2982): Gazebo 물리 계산은 일반적으로 CPU, GPU는 렌더링 센서 처리. GPU가 보인다고 physics 멀티코어 가속을 주장할 수 없음.

**중요한 재사용 경계:** D08 현재 `GALLIUM_DRIVER=d3d12`, NVIDIA 어댑터 설정은 **Gazebo GUI·RViz2 자식에 적용**되지만 Nav2로 띄우는 **Gazebo 서버에는 강제로 적용되지 않는다**. GPU 진단 결과가 없으므로 서버 렌더링 경로를 무조건 바꾸지 않는다.

## 2. 최초 1회: WSLg GL 경로 읽기 전용 진단

기존 D08 실행을 종료할 필요 없음. **새 터미널에서 전체 블록 1회 실행**. `glxinfo`가 미설치라면 `RENDERER_NOT_MEASURED`로 안전하게 보고한다. 원하는 경우 공식 Ubuntu `mesa-utils` 패키지를 한 번 설치할 수 있으나 스크립트는 스스로 시스템 패키지를 설치하지 않는다.

```bash
(
  set -Eeuo pipefail
  PROBE="$(mktemp --suffix=.py)"
  trap 'rm -f -- "$PROBE"' EXIT
  curl -fL --retry 3 --max-time 90 \
    "https://raw.githubusercontent.com/silverbjin/axia-robot-safety-student/46b6d844a946fc82df3cdea074773f3ccc4609ae/block_B/day08/tools/d08_wslg_renderer_probe.py" \
    -o "$PROBE"
  python3 "$PROBE" --self-check
  python3 "$PROBE"
)
```

기대 형태(실제 값을 미리 가정하지 않는다):

```text
D08_GL_RENDERER_CLASSIFICATION=<분류>
D08_GL_RENDERER_INHERITED=<실제 렌더러>
D08_GL_RENDERER_DEFAULT=<실제 렌더러>
D08_GL_RENDERER_D3D12_AUTO=<실제 렌더러>
D08_GL_RENDERER_D3D12_NVIDIA=<실제 렌더러>
D08_GL_RENDERER_GAZEBO_SERVER=NOT_VERIFIED
D08_GL_PROBE_ZIP=/home/.../axia_d08_diagnostics/gl_.../d08_wslg_renderer_probe.zip
```

- `NVIDIA_SELECTION_LLVMPIPE_FALLBACK_CANDIDATE`: NVIDIA 강제 렌더러가 소프트웨어로 폴백. **Windows GPU/NVIDIA/Mesa 교체가 아니라**, 렌더 프로세스 선택 변경 후보를 나중에 한 가지씩 확인한다.
- `DEFAULT_SOFTWARE_FALLBACK_D3D12_AVAILABLE`: 현재 렌더러는 소프트웨어지만 d3d12 자식은 가용. Gazebo 서버에 D3D12를 적용하는 **후속 단일 변수 시험 후보**.
- `D3D12_AVAILABLE_RTF_NOT_VERIFIED`: 자식 GL이 GPU에 매핑되지만 Gazebo 서버의 실제 오프로딩은 입증되지 않음.
- `RENDERER_NOT_MEASURED`: `glxinfo` 부재·OpenGL 컨텍스트 실패. GPU 설정 변경 보류.

## 3. D08 RGB-D 10Hz 단일 비교 — 기존 데모 보존

원래 `renderfix` 체크아웃·증거는 보존하고, 별도 `~/axia_d08_student_live_perf`에 **검증 후보 브랜치**를 받는다. 두 프로필을 동일 WSL2 GPU·화면 크기·센서 배치에서 차례로 비교하며 **한 번에 한 변수만** 변경한다.

**터미널 A — 10Hz 후보 1회 실행:**

```bash
(
  set -Eeuo pipefail
  BOOT="$(mktemp)"
  trap 'rm -f -- "$BOOT"' EXIT
  curl -fL --retry 3 --max-time 90 \
    "https://raw.githubusercontent.com/silverbjin/axia-robot-safety-student/35b5bdd3f070cdf40cc01bd554a26860ac858604/block_B/day08/run_d08_student_live_bootstrap.sh" \
    -o "$BOOT"
  bash -n "$BOOT"

  AXIA_D08_RELEASE_BRANCH="perf/d08-wslg-rtf-sensor-profile-20261118" \
  AXIA_D08_DEMO_DIR="$HOME/axia_d08_student_live_perf" \
  AXIA_D08_RGBD_RATE_HZ=10 \
  AXIA_D08_DOMAIN_ID=49 AXIA_D08_HOLD_S=300 \
    bash "$BOOT" --run
)
```

`--run` 시작 시 `AXIA_D08_RGBD_RATE_PROFILE=10Hz baseline=30Hz candidate=10Hz RTF_NOT_VERIFIED`를 출력한다. 이것은 **설정 완료 표시이지 성능 PASS가 아니다**. 학생용 D05 모니터에서 실제 RGB·Depth·YOLO 메시와 person bbox가 유지되어야 한다. Gazebo와 RViz2 두 창, 별도 image_view 창 없음.

**터미널 B — Live 중 20초 RTF 자동 기록:**

```bash
(
  set -Eeuo pipefail
  DIAG="$(mktemp --suffix=.py)"
  trap 'rm -f -- "$DIAG"' EXIT
  curl -fL --retry 3 --max-time 90 \
    "https://raw.githubusercontent.com/silverbjin/axia-robot-safety-student/62ff3a5e74ea2b4fe83cf7a892432bb060c4144c/block_B/day08/tools/d08_actor_rtf_diagnose.py" \
    -o "$DIAG"
  python3 "$DIAG" --seconds 20
)
```

**비교 기준:** 최초 ZIP과 새 ZIP의 `sim_time` 진행 / 해당 구간 `real_time` 진행으로 계산한 구간 RTF끼리 비교한다. 기존 `summary.json`의 `rtf_median=0.0079`와 6.81% 구간 RTF는 다른 집계이므로 섞어 비교하지 않는다.

### 판단 기준 (수업용 MVP)

- 10Hz로 RTF가 의미 있게 개선되고 Gazebo·RViz 화면에서 사람 이동 및 YOLO 검출이 보이면 **10Hz 후보 채택 가능**. 과도하게 높은 RTF 절대 기준을 강제하지 않는다.
- RTF가 여전히 매우 낮다면 Actor 속도·프로세스 분리 대신, **GPU 경로와 카메라 해상도/렌더 부하**를 첫 실패 경계로 한 번 더 좁힌다. 이때 카메라 해상도부터 바꾸면 Depth alignment/YOLO 실습 검증을 다시 해야 하므로 마지막 후보로 둔다.
- 실제 RGB-D 타임스탬프 정합, 샘플 생성 주기, D06/G07 TTL은 이 실험에서 별도 검증된 것이 아니다. D08 교육용 관측 경계와 실제 이동 안전 경계를 혼합하지 않는다.

## 4. 개발·검증·보존

- 신규/수정: `block_B/day05/gazebo_live/prepare_scene.py` (D08 opt-in), `block_B/day04/run_student_gazebo_yolo_once.sh` (D08일 때만 전달), `block_B/day08/run_d08_student_live_once.sh` (30Hz 기본/10Hz 선택), `block_B/day08/tools/d08_wslg_renderer_probe.py`, 2개 단위 L0 테스트, 기존 공개 CI L0.
- 기존 D04/D05 기본 camera update_rate·Actor SDF·소유 Goal·ROS 센서 해상도·Nav2/Collision Monitor/Guard/Instructor 정답: 변경하지 않음.
- 공개 CI의 **실제 Gazebo L2**는 외부 `yolo_onnxruntime_vendor` ONNX Runtime 다운로드가 9바이트로 실패하는 기존 의존성 경계에 가로막힐 수 있다. L0 GREEN만으로 L2/Owner RTF를 PASS로 승격하지 않는다.
- 원본 증거는 새 `~/axia_d08_diagnostics/` 디렉터리에 각각 ZIP 보존. 종료는 D08 실행 터미널의 `Ctrl+C`. 기존 `renderfix`를 삭제하거나 `pkill`하지 않는다.
- 신규 코드 사용자 WSL2 인수 후 필요 시 PR 검토. `main` 병합은 명시 승인 전까지 금지한다.
