# AXIA D08 — WSLg Ogre2 셰이더 경고 분석·GUI 전용 최소 대체안 (2026-11-18 KST)

## 1. 실제 입력 증거 / 결론

- Owner 현장 SDF, manifest **RGB-D update_rate=10Hz** 일치.
- Ogre2 로그 `GL_RENDERER = D3D12 (NVIDIA GeForce RTX 2060 with Max-Q Design)`, `OpenGL 3+ Renderer Started`.
- 이후 `OGRE EXCEPTION ... Fixed Function pipeline ... scene::Material(65518)`와 `Default/TransGreen` 발생.
- 이 로그는 **일부 Ogre2 머티리얼 셰이더 경로의 문제**이지 GPU 가속 실패, 종료, 검은/흰 3D 화면을 단독으로 증명하지 않는다.
- 이전 Owner 10Hz+NVIDIA 후보: **구간 평균 RTF 약 0.9186**, D05 센서 ROS/Gazebo/YOLO PASS, `NO_GOAL NO_CMD_VEL`. 새 실험으로 이 결과를 덮어쓰거나 새로운 성능 PASS로 승격하지 않는다.
- 현재 Ogre2 로그의 실제 서버/GUI 프로세스 귀속, GUI 실제 픽셀 표시, 수정 후보 GUI의 결과: **NOT_VERIFIED**.

## 2. 공식 근거

- https://gazebosim.org/docs/harmonic/troubleshooting/ — Ogre2 OpenGL 요구와 별도의 Ogre1 대체 `--render-engine ogre` 선택.
- https://github.com/gazebosim/gz-sim/issues/2670 — WSLg 검은 화면 사례에서 동일한 `scene::Material(65518)`, `Default/TransGreen` 로그; 동일 원인 확정 근거는 아님.
- https://github.com/gazebosim/gz-sim/issues/3801 — 2026년에도 동일 머티리얼 메시지 보고.
- 이미 계측된 NVIDIA 4.6 및 높은 RTF 때문에 `LIBGL_ALWAYS_SOFTWARE=1`, `MESA_GL_VERSION_OVERRIDE`, 시스템 Mesa/드라이버 교체는 이번 MVP에서 **불채택**.

## 3. 변경 (새 브랜치만, 기존 성공본 불변)

- 브랜치: `fix/d08-gui-ogre-fallback-20261118` (부모 `perf/d08-wslg-rtf-sensor-profile-20261118`, Draft PR #48).
- `block_B/day04/run_student_gazebo_yolo_once.sh`:
  - D08 staged GUI 전용 `AXIA_D08_GUI_RENDER_ENGINE` 옵션 `ogre2` (기본), `ogre` (현장 화면 실패일 때 대체)만 허용.
  - 명시적 `ogre` 옵션일 때 `gz sim -g -v 4 --render-engine ogre` 실행.
  - 기존 공식 Nav2 Gazebo **서버**, RGB-D 10Hz SDF, NVIDIA D3D12 환경, YOLO, RViz, Actor, Goal/control 유지.
- `block_B/day08/tests/test_d08_gui_engine_fallback.py`: 기본 불변, 잘못된 값 차단, GUI 전용 렌더러, 로봇 제어 발행 없음, Bash 구문 등 4개 L0 테스트.
- `.github/workflows/d08-online-integration-student.yml`: 위 테스트 공개 CI에 연결.

## 4. RED → GREEN → REFACTOR → REVIEW → COMMIT

- **RED:** PR HEAD `0d0e0f0ff1db88d43c61c32ac3e36d7c21631414`, https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44225840785 — **3 failed, 43 passed**. 미구현 GUI 전용 fallback 계약이 원인.
- **GREEN:** HEAD `3dd04abb830117d9f28060b24a9d0fb8fdcc7dc4`, https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44225910230 — **46 passed**, Student expected RED TODO도 별도 정상 확인.
- D04/D05 Python https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44225910212 — success.
- **REFACTOR/REVIEW:** 변경이 D08 staged GUI에서만 옵트인되는지 정적 확인. 기존 입력 증거 보존, `main` 미병합. 변경 사항은 기능 1곳+L0 회귀 및 문서뿐.
- **미검증:** 실제 WSL2 Ogre1 GUI 표시, RTF, RGB-D/YOLO 재현, UI 픽셀. 원본 문제에서 검은 화면인지 경고만 있는지도 현장 화면 증거 미제공.

## 5. Owner WSL2 필요할 경우에만 실행 (기존 성공 체크아웃 보존)

**현재 Gazebo와 RViz2 3D 장면이 제대로 보인다면 실행할 필요가 없다.** 로그 메시지 제거만을 위해 렌더러를 바꾸지 않는다.

기존 창이 흰색/검은색이거나 모델이 없다면, 기존 D08 실행을 Ctrl+C로 종료하고 아래 독립 디렉터리에서 **한 번만** 실험한다.

```bash
(
  set -Eeuo pipefail
  BOOT="$(mktemp)"
  trap 'rm -f -- "$BOOT"' EXIT
  curl -fL --retry 3 --max-time 90 \
    "https://raw.githubusercontent.com/silverbjin/axia-robot-safety-student/3dd04abb830117d9f28060b24a9d0fb8fdcc7dc4/block_B/day08/run_d08_student_live_bootstrap.sh" \
    -o "$BOOT"
  bash -n "$BOOT"
  env -u LIBGL_ALWAYS_SOFTWARE \
    GALLIUM_DRIVER=d3d12 MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA \
    AXIA_D08_RELEASE_BRANCH="fix/d08-gui-ogre-fallback-20261118" \
    AXIA_D08_DEMO_DIR="$HOME/axia_d08_student_live_gui_ogre_trial" \
    AXIA_D08_GUI_RENDER_ENGINE=ogre \
    AXIA_D08_RGBD_RATE_HZ=10 AXIA_D08_DOMAIN_ID=49 AXIA_D08_HOLD_S=300 \
    bash "$BOOT" --run
)
```

기대 로그 패턴 (아직 실측하지 않음):

```text
D08_STUDENT_RELEASE_SOURCE_SHA=<현재 브랜치 SHA>
D08_RGBD_RATE_REQUEST_HZ=10
D08_GAZEBO_GUI_RENDER_ENGINE=ogre SERVER_ENGINE_UNCHANGED SENSOR_RTF_NOT_REVERIFIED
D05_PUBLIC_SENSOR_ONLY_PASS REAL_RGBD_YOLO PRIVATE_D05_RANGE_NOT_RUN
```

판단:
- 화면 정상+센서 PASS면 `GUI_FALLBACK_CANDIDATE_PASS` (현장 화면 검증 포함), 이후 **동일 계산법** RTF 비교.
- 화면만 개선됐으나 RTF 하락 또는 YOLO 실패면 `HOLD`, 원래 Ogre2 NVIDIA 10Hz 성공본으로 복귀.
- Ogre2에서 이미 화면이 정상이면 `NO_CHANGE`: 경고만으로 시연 실패로 판단하지 않는다.
- `D04_STUDENT_EXIT_CODE=130`은 Ctrl+C 종료 시 정상.
- 이 작업은 안전 TTL, 경로 재계획, 주행 제어, 물리 충돌 및 인증 E-Stop을 검증하지 않는다.

**출고:** L0 PASS만으로 Owner WSL2 L3 인수나 전체 실제 Gazebo L2 PASS 선언 금지. 본 변경은 Draft PR로 유지, `main` 병합 별도 승인.
