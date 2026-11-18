# AXIA D08-PERF-P03 — Owner WSL2/WSLg 실제 RTF·GPU ZIP 검토 및 최소 해법

- 기준일: 2026-11-18 KST
- 입력 원본: `d08_actor_rtf_diagnostics(1).zip`, `d08_wslg_renderer_probe.zip` (Owner 제공)
- 소스 브랜치: `perf/d08-wslg-rtf-sensor-profile-20261118`, Draft PR #47 (기반 PR #41)
- 본 작업: 원본 ZIP 내용 분석 및 기술적 후속 실험 제안. **새로운 WSL2 로봇 주행·새로운 Gazebo 실행은 하지 않았다.**
- 원본 ZIP은 사용자 증거로 유지하고 GitHub 공개 문서에는 개인정보·로컬 원본 로그·개인 경로를 업로드하지 않는다.

## 1. 실제 RTF 비교 — 집계값을 혼동하지 않는다

| 메트릭 | 기존 Owner ZIP | 2026-11-18 이번 ZIP |
|---|---:|---:|
| `rtf_samples` | 45 | 44 |
| `rtf_median` (WorldStats 개별 통계 필드 중앙값) | 0.0079 (0.79%) | 0.0083 (0.83%) |
| 첫 `sim_time` | (구간 증가만 기재) | 2.505 s |
| 마지막 `sim_time` | (구간 증가만 기재) | 5.403 s |
| `sim_time` 진행 | 1.329 s | **2.898 s** |
| 동일 구간 `real_time` 진행 | 19.523 s | **19.273897085 s** |
| **구간 평균 RTF = ΔSim / ΔReal** | **6.81%** | **15.04%** |
| 상대 개선 | 기준 | **약 2.21배** |

현재 ZIP `world_stats_raw.txt` 44개 모두에서 `sim_time`, `real_time`, `iterations`, `real_time_factor`가 확인된다. 구간 평균 RTF **0.150358798**는 원본 first/last time으로 독립 재계산했다. `real_time_factor` 샘플은 0.0029~1.3373까지 출렁이며 중앙값 0.0083, 평균 약 0.2937이다. 평균/중앙값 개별 RTF 필드를 다른 실행의 구간 평균과 직접 비교하면 안 된다.

Actor `x=2.8→2.0→2.8m`, `t=0/5/10 sim-sec`, 속도 0.16m/s(sim). 구간 RTF 0.1504가 유지된다면 **0.8m 이동에 33.25초(real)**, 이전 구간 RTF 0.0681에서는 73.45초(real)의 추정값. Actor 물리 Pose 실측이 아니라 SDF와 구간 RTF로 계산한 근사값이다.

10Hz 성능 후보를 실행했던 것으로 추정되나 이번 ZIP 자체에는 `scene_manifest.json`, `student_waffle_rgb.sdf.xacro`, `D08_RGBD_RATE_REQUEST_HZ` 원본이 없어 **실제 센서 update_rate=10Hz 증명은 미흡**. 따라서 향상을 이 한 변수의 인과효과라고 단정하지 않는다.

## 2. 실제 WSLg/OpenGL·자원

`d08_wslg_renderer_probe.zip` 실제 `glxinfo -B` 결과:

| glxinfo 자식 환경 | 실제 GPU | OpenGL Core | Mesa |
|---|---|---|---|
| inherited/default/d3d12_auto | D3D12 Intel Iris Xe | **4.1** | 26.2.6 kisak-mesa PPA |
| d3d12_nvidia | D3D12 NVIDIA RTX 2060 Max-Q | **4.6** | 26.2.6 kisak-mesa PPA |

모두 `Accelerated: yes`, 정상 `rc=0`. 이번 사용자 기기에서는 흔히 보고된 `llvmpipe` CPU 소프트웨어 폴백은 **해당 glxinfo 자식 과정에서 관측되지 않았다**. 다만 이 자식 테스트는 **Gazebo 서버 Ogre2의 실제 GL_RENDERER를 증명하지 않는다**.

이번 프로세스 1회 snapshot: Gazebo server 약 95.5% CPU core, Gazebo GUI 약 85%, RViz2 약 45.8%, YOLO node 약 19.1%; `image_view` PID가 없어 D08 중복 디버그 창 제거가 반영된 것으로 보인다. WSL2 8 logical CPU, RAM available 약 29.5 GiB, swap 0. CPU 수치는 ps 누적 평균이지 순간 샘플/프로파일링 결과가 아니다. 메모리 부족·swap 병목 증거 없음.

**가장 중요한 미확인 경계:** 기존 소스에서 D08 staged GUI `D08_RENDER_ENV`(NVIDIA d3d12)가 `gz sim -g`와 RViz2에만 적용되고, `ros2 launch nav2_bringup tb3_simulation_launch.py ... headless:=True`로 구동한 Gazebo **서버에는 명시되지 않는다**. WSLg 기본 GPU Intel + GUI/RViz NVIDIA라는 서로 다른 어댑터가 선택될 수 있다. 이 차이가 GPU readback/copy·동기화에 미치는 실제 영향은 아직 **가설**이며 반드시 성능 A/B로 확인한다.

## 3. 공식 자료·GitHub Issue: WSL2/Native 차이

1. Gazebo Harmonic Ogre2 Troubleshooting: https://gazebosim.org/docs/harmonic/troubleshooting/ — OpenGL **3.3 초과, 4.3+ 권장**, `~/.gz/rendering/ogre2.log` 및 `glxinfo -B`로 실제 환경을 확인. Intel 4.1은 기본 요구를 넘지만 권장 4.3에는 못 미침. NVIDIA 4.6은 권장치 충족.
2. Microsoft WSLg GPU Selection Wiki: https://github.com/microsoft/wslg/wiki/GPU-selection-in-WSLg — Mesa d3d12 `MESA_D3D12_DEFAULT_ADAPTER_NAME`로 특정 GPU를 고를 수 있고 기본값은 integrated Intel일 수 있다.
3. Microsoft WSLg 공식 README: https://github.com/microsoft/wslg — dGPU 프레임을 WSLg Weston에서 Windows 호스트로 표시할 때 **VRAM→시스템 RAM→Windows-side GPU** 복사 비용이 발생할 수 있다고 명시. Native Ubuntu의 일반적인 표시 경로와 다르다.
4. WSLg Issue #1498: https://github.com/microsoft/wslg/issues/1498 — D3D12가 실제 GPU 가속되어도 640×480급 화면 전송이 CPU readback bound가 되는 독립 재현 사례. **사용자 Gazebo의 동일 원인이라는 증명은 아니다**.
5. Gazebo Issue #2670: https://github.com/gazebosim/gz-sim/issues/2670 — WSL2 Gazebo black screen과 GPU 선택, `GALLIUM_DRIVER=d3d12` 해결 보고. 이번 GL 자식에는 이미 d3d12 GPU 가속이 있으므로 전역 Mesa 수정 불필요.
6. Gazebo WSLg Issue #2873: https://github.com/gazebosim/gz-sim/issues/2873 — Gazebo Harmonic WSLg d3d12 renderer memory/resource 관련 보고. 이번 ZIP은 RAM 충분하고 누적 시간만 짧으므로 해당 메모리 누수로 판단하지 않는다.

## 4. 가장 작은 다음 성능 실험

**A (기준):** 현재 RGB-D 프로필을 유지하고, Gazebo 서버 환경 기본 Intel(추정), GUI/RViz NVIDIA. 관측 `interval_rtf=0.1504`.

**B (단일 변수):** 동일 D08 체크아웃·10Hz RGB-D/640x480·월드·창 크기·RMW·도메인·YOLO 모델·Actor·GUI NVIDIA를 유지하고, **Gazebo 서버 상속 환경에만** `GALLIUM_DRIVER=d3d12 MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA`를 전달. 기존 runner는 Gazebo server가 부모 환경을 상속하므로 별도 노드 변경 불필요. 안전을 위해 독립 폴더/프로세스에서 1회 실행.

- B가 A보다 의미 있게 높은 **동일 계산 방식의 `ΔSim/ΔReal`**을 나타내고 실 RGB-D·YOLO 관측/GUI/RViz가 유지되면 D08 전용 서버 GPU override 후보 채택.
- B가 A보다 낮거나 흰 화면·GPU 오류가 생기면 즉시 환경변수 제거해 A로 되돌린다. 시스템 전체 `~/.bashrc`나 Mesa 버전·Windows GPU 드라이버를 변경하지 않는다.
- B에서도 RTF 매우 낮으면 Gazebo server Ogre2 render log·카메라 readback 및 WSLg 창 표시 overhead를 **한 경계씩** 분리한다. Actor 외부 프로세스화·physics 튜닝·일괄 패키지 업그레이드는 MVP에서 제외한다.
- 비교하려면 각 실행의 `scene_manifest.json`에서 실제 `rgbd_update_rate_hz`와 `ogre2.log`의 장면/시각화 오류를 보존. 현재 RTF 진단 스크립트의 개별 rtf median 보조 지표를 `interval_rtf` 중심으로 개선하는 단일 CI 회귀를 추후 수행한다.

## 5. 검증 수준·Git

- **실제 사용자 Gazebo 통계/GLX 측정:** 입력된 ZIP으로 확인 완료.
- **원인 확정:** 미완료. Intel/NVIDIA 분리 프로세스는 소스+glxinfo로 도출한 가설; Gazebo server 실제 GL renderer 미측정.
- **실험 B 실제 실행:** NOT_RUN. 이 보고서 작성을 성능 개선 실기 성공으로 승격하지 않는다.
- **안전:** NO_GOAL / NO_CMD_VEL. D06/G07 CM120ms·Guard150ms TTL, Contact/Odom/인증 E-Stop 미검증.
- **출고:** Draft PR #47 유지, 기존 성공본·원본 ZIP 보존, main 미병합.
