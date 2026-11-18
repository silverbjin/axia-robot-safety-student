# AXIA D08 — WSL2/WSLg Gazebo 렌더링 사고 분석·해결 전 과정 (교육용)

- **작성:** 2026-11-18 KST
- **검증 범위:** TurtleBot3 Waffle / ROS 2 Jazzy / Gazebo Harmonic / RViz2 / RGB-D·YOLO / **NO_GOAL**
- **증거 원본:** Owner WSL2 제공 `d04-gazebo-sROFIPHQ.zip` (SHA256: `7238cf82ef6330cd1f67acac011f14bdae1da38245876acbb03585d958f66057`). ZIP 내부 16개 항목의 CRC 검사는 **PASS**. 개인 경로·원본 로그/가중치/비공개 정답은 GitHub에 공개하지 않음
- **최종 소스 계열:** Student `fix/d08-gui-ogre-fallback-20261118` → `release/d08-wslg-ogre-owner-accepted-20261118`; Instructor는 자체 독립 저장소의 문서·재사용 가이드만 반영
- **인수 용어:** Owner가 Gazebo·RViz2 GUI 성공을 직접 보고했으며 ZIP은 Gazebo GUI Ogre1 로드와 센서 출력을 뒷받침함. **화면 픽셀 스크린샷·새 RTF 수치가 ZIP에 없어 파일만으로 픽셀/RTF PASS를 재계산할 수는 없음**.

## 1. 장애 원인 분리 — 첫 실패 경계를 추적한 순서

| 단계 | 관찰·증거 | 진단 및 최소 조치 | 근거 commit / CI |
|---|---|---|---|
| 01. 센서 vs 3D 화면 분리 | D05의 실제 RGB/Depth/YOLO 출력은 있는데 Gazebo는 흰 화면, RViz3D는 검은 화면/로봇 메시 누락 | 공식 Nav2 launch 재사용, D05 생성 world의 `SceneBroadcaster`를 headless에서도 1개 유지; RViz RobotModel에 공식 설치 메시 경로만 보정; Gazebo 서버가 먼저 구동되고 GUI가 후속 연결되도록 변경 | 학생 Draft PR [#41](https://github.com/silverbjin/axia-robot-safety-student/pull/41), `test_d08_scene_mesh_restore.py` / CI scene 토픽 게이트 |
| 02. 중복 GUI 제거 | Gazebo + RViz + image_view의 불필요한 3창 및 렌더 부하 | D08에서만 `image_view=0`, YOLO 디버그 이미지는 RViz 안에서 확인. D04/D05 기본은 보존 | 학생 PR #41, `test_d08_no_duplicate_debug_window.py` |
| 03. Actor가 느려 보임 | Actor SDF x=2.8→2.0→2.8m, waypoint 0/5/10 sim-sec; 초기 구간 RTF **6.81%**, GUI 5.27% | Actor 제어 노드를 새로 만들지 않고 WorldStats `Δsim/Δreal`로 물리 시계와 waypoint 속도를 분리. 개별 `rtf_median` 0.79%와 구간 평균 6.81%는 다른 통계이므로 혼용 금지 | 읽기 전용 진단 [PR #45](https://github.com/silverbjin/axia-robot-safety-student/pull/45); `D08_ACTOR_RTF_DIAGNOSTIC_GUIDE_20261118_KO.md` |
| 04. 렌더러·센서 부하 격리 | WSLg child `glxinfo -B`: 기본 Intel D3D12 GL 4.1, NVIDIA D3D12 GL 4.6; RGB-D 원래 30Hz | 전역 Mesa/Windows 드라이버를 수정하지 않고 D08에서만 등록 RGB-D 센서 update_rate 10Hz 선택. GPU 선택은 각 자식 프로세스 환경으로 한정 | 학생 Draft [PR #47](https://github.com/silverbjin/axia-robot-safety-student/pull/47), P01/P02 문서, `test_d08_perf_sensor_profile.py` |
| 05. RTF 개선 검증 | Owner 기존 관측 15.04% → NVIDIA 환경+10Hz 실험 ZIP에서 **91.86% 구간 평균** (18.117 sim-sec / 19.722 real-sec), 센서 PASS. SDF 및 manifest의 `rgbd_update_rate_hz` **둘 다 10** | 이미 성공한 NVIDIA/10Hz 서버·센서 설정 **동결**. 두 변수의 순수 인과효과는 분리되지 않으므로 단일 원인으로 단정 금지 | 커밋 [`4ac64a45`](https://github.com/silverbjin/axia-robot-safety-student/commit/4ac64a45a2aa0e0474f6f5ff76ae48d7a6a2d88e), P03 보고서 |
| 06. 남은 Ogre2 셰이더 경고 | `~/.gz/rendering/ogre2.log`에서 `GL_RENDERER=D3D12 (NVIDIA RTX 2060 Max-Q)`, `OpenGL 3+ Renderer Started` 확인 후 `Fixed Function pipeline...` (`scene::Material(65518)`, `Default/TransGreen`) 반복 | GPU 가속 부재가 아니라 **Ogre2의 특정 머티리얼/셰이더 경로** 문제 후보. 오류 문구만으로 실제 검은 화면·서버 실패 단정 금지. 성공한 서버를 바꾸지 않고 `gz sim -g` **GUI에만** 명시적 Ogre1 대체 옵션 구현 | 학생 [PR #48](https://github.com/silverbjin/axia-robot-safety-student/pull/48), `3d131ceb` RED test → `3dd04abb` GREEN code → `0239c33c` 리뷰 보고 |
| 07. Owner 성공 검증 | 사용자 **“성공하였다”**. 첨부 새 ZIP `gazebo_gui.log`에는 `Loading plugin [gz-rendering-ogre]`, `Create scene [scene]`; Ogre2의 동일 `Fixed Function` 예외 **0건**. `rviz2.log`: GL 4.6. `live_verdict.json`: 실제 ROS/Gazebo RGB 10, Depth 9, YOLO 7, person 5, bbox span 0.3316, registered RGB-D 2, `passed=true` | **Owner GUI 관찰 PASS + 실제 센서 관측 PASS**로만 기록. `scene_gui_pixels_verified=false`는 생성 manifest의 *실행 전 기본값*이므로 Owner 관찰과 모순이 아님. `valid_samples=0`, 거리 null은 D05 private range 노드를 실행하지 않는 센서 전용 범위에서 정상 | Owner ZIP SHA256 상기; 본 인계 문서에 근거 요약, 소스/로그 원본은 Owner에 보관 |

## 2. TDD·공개 CI 증거와 성공 범위

- Renderer 복구 이전 공개 학생 Python L0/scene·mesh·no-third-window 회귀와 D04/D05 기존 fixture 증거를 재사용. ROS/P1/G07 안전 로직 수정 **없음**.
- **GUI Ogre1 opt-in RED:** [#44225840785](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44225840785) `3 failed, 43 passed`; `test_d08_gui_engine_fallback.py`의 GUI-only 계약 미구현.
- **GUI Ogre1 opt-in GREEN:** [#44225910230](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44225910230) `46 passed`; 기존 D04/D05 Python 워크플로도 [#44225910212](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44225910212) 성공.
- **실제 Owner WSL2 L3:** 새 ZIP은 Ogre1 GUI 렌더 플러그인, 실제 YOLO/RGB-D 및 사용자 화면 성공 진술을 검증. 이전 91.86% RTF ZIP은 **이전 실행**의 증거로만 유지. 이번 Ogre1 실행의 RTF는 **NOT_MEASURED**.
- **공개 CI 실제 Gazebo L2:** [#44226150859](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44226150859) 및 D05 [#44226150835](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44226150835) **FAIL before Gazebo**, `yolo_onnxruntime_vendor`가 `onnxruntime.tgz` 다운로드 결과를 archive로 풀지 못함(`Unrecognized archive format`). 실제 GUI·센서 회귀 **CI에서 검증되지 않았음**; Owner 현장 성공으로 공개 L2 PASS를 대체하지 않는다.
- 인증된 E-Stop, 로봇 이동 Goal, /cmd_vel, Collision Monitor→Guard TTL, LiDAR가 visual-only Actor를 충돌 장애물로 인식하는지, D05 실제 거리(m), D07 회피 주행 모두 **NOT_RUN / 대상 외**.

## 3. 재발 시 분기 진단

1. **센서 PASS, GUI도 화면 정상:** Ogre2 예외 문자열만 이유로 수정하지 않는다. 정상인 경우 기본 Ogre2 유지 가능.
2. **센서 PASS, Gazebo 3D 검은/흰 화면:** `scene/info`, `pose/info`와 Ogre log를 먼저 확인하고, **GUI 전용** `AXIA_D08_GUI_RENDER_ENGINE=ogre`로 실행한다. 서버/센서 렌더러는 손대지 않는다.
3. **GUI 정상, Actor가 느림:** 0.16m/s SDF waypoint의 원래 이동 시간과 실제 RTF를 구분. `ΔSim/ΔReal` 20초 계측; RTF가 낮을 때만 렌더/GPU 경계를 단일 변수로 비교.
4. **YOLO FPS/Depth 쌍 부족:** `live_verdict.json`을 기준으로 실제 메시지 주기·stamp/동기화 별도 점검. `passed=true`는 단기간 센서 관측만 의미.
5. **public Gazebo L2 FAIL, Owner PASS:** ONNX 외부 tar 실패는 CI의 **사전 빌드 실패 경계**로 유지. 해당 재현을 CI에서 우선 해결하며 WSL2 재주행만 반복하지 않는다.

## 4. 15분 실습 강의 흐름

| 시간 | 강사 질문 | 학생이 확인할 증거 |
|---|---|---|
| 0–3분 | 센서 토픽이 살아 있어도 Gazebo GUI는 왜 백지일 수 있는가? | `SceneBroadcaster`와 `rviz2.log` 메시 리소스 분리 |
| 3–6분 | 사람이 느리게 보이는 것은 Actor 코드 문제인가? | SDF waypoint와 WorldStats 구간 RTF 6.81%→15.04%→91.86% 구분 |
| 6–9분 | GPU로 렌더링한다는데 왜 에러가 나는가? | GL_RENDERER NVIDIA와 Ogre2 `Fixed Function` 예외를 함께 관찰 |
| 9–12분 | 서버까지 Ogre1로 바꿔도 되는가? | **아니요:** 이미 성공한 10Hz RGB-D 서버 유지, `gz sim -g --render-engine ogre`만 대체 |
| 12–15분 | 무엇이 최종 PASS인가? | RED→GREEN CI L0, 실제 GUI Ogre1 plugin, Owner 화면 확인, ROS RGB/Depth/YOLO PASS, CI L2 BLOCKED·새 RTF 미측정 분리 |

**교육용 핵심 메시지:** 마지막 에러 문자열이 아니라 **최초 실패 경계**를 찾고, 성공한 계층은 보존하며, 원인 후보 하나씩 검증합니다. CI PASS는 어느 실행 계층을 검증했는지 함께 기록합니다.

## 5. 파일·실행·Git 정책

- 공개 학생 런타임: `block_B/day04/run_student_gazebo_yolo_once.sh`, `block_B/day05/gazebo_live/prepare_scene.py`, `block_B/day08/run_d08_student_live_once.sh`, `block_B/day08/run_d08_student_live_bootstrap.sh`.
- GUI 대체: `AXIA_D08_GUI_RENDER_ENGINE=ogre`; 기본 `ogre2`, **오직 D08 staged GUI에서만**. 실제 한 줄: `gz sim -g -v 4 --render-engine ogre`.
- 학습자 TODO/공개 CI와 강사용 reference/hidden tests는 서로 다른 저장소를 유지. 비공개 정답을 공개 저장소로 복사하지 않는다.
- 모든 `main` 병합은 사용자 요청으로 명시 승인되었으나, **병합 전 CI 검증 범위와 남은 L2 오류를 공개 보고**한다. 소스·증거 ZIP은 immutable SHA로 추적한다.
