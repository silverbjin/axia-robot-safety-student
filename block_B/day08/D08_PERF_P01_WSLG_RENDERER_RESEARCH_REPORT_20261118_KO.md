# AXIA D08-PERF-P01 — WSLg 렌더링 경로 진단·공식 이슈 조사 보고서

- 날짜: 2026-11-18 KST / Public Student Draft PR #47
- 브랜치: `perf/d08-wslg-rtf-sensor-profile-20261118`
- 작업 목표: Owner RTF 5~7% 저하의 첫 경계 중 **Gazebo 서버·GUI 렌더러 경로**를 구분, 시스템 변경 없는 단일 진단기.
- 수정 파일: `block_B/day08/tools/d08_wslg_renderer_probe.py`, `block_B/day08/tests/test_d08_wslg_renderer_probe.py`, `.github/workflows/d08-online-integration-student.yml`, 성능 비교 가이드.
- Owner 원본: `d08_actor_rtf_diagnostics.zip`의 WorldStats `rtf_median=0.0079`(0.79%), 실구간 RTF `1.329/19.523≈0.0681`, GUI 화면 `5.27%`. GPU 실측 renderer는 원본 ZIP에 없음.

## 공식 출처와 적용 판단

- Gazebo Harmonic Troubleshooting: https://gazebosim.org/docs/harmonic/troubleshooting/ — Ogre2 OpenGL 3.3 초과, `glxinfo`와 `ogre2.log` 검사.
- Gazebo Harmonic Sensors: https://gazebosim.org/docs/harmonic/sensors/ — sensor update_rate 정의.
- WSLg GPU selection wiki: https://github.com/microsoft/wslg/wiki/GPU-selection-in-WSLg — Mesa D3D12 및 GPU 선택.
- Microsoft WSL #12412: https://github.com/microsoft/WSL/issues/12412 — NVIDIA 강제 선택 후 llvmpipe 폴백 사례; `GALLIUM_DRIVER=d3d12` 회피 사례 있으나 2026-10-15 자동 비활성 종료로 보편 해결 확정 아님.
- WSLg #1332: https://github.com/microsoft/wslg/issues/1332 — 최신 Mesa에 d3d12 미선택 사례; driver를 지정했다고 Gazebo 가속이 증명되지 않음.
- Gazebo #2873: https://github.com/gazebosim/gz-sim/issues/2873 — WSLg D3D12의 메모리·렌더링 부하.
- WSLg #1498: https://github.com/microsoft/wslg/issues/1498 — D3D12 화면 readback 제한의 별도 문제.
- Gazebo #2982: https://github.com/gazebosim/gz-sim/issues/2982 — physics는 CPU, 렌더 센서는 GPU라는 경계.

**설계 결정:** `glxinfo -B` 자식만 4개 환경(Inherited, Default, d3d12 auto, d3d12 NVIDIA)으로 실행해 GL_RENDERER를 비교한다. 파일은 모두 새 폴더, ZIP으로 기록. `.bashrc`, Ubuntu Mesa, Windows GPU 설정을 수정하지 않는다. `glxinfo` 결과는 Gazebo 서버의 실제 Ogre2 렌더러 증거가 아니며 후속 비교에 이용한다.

## RED → GREEN → REVIEW → COMMIT

- RED: 먼저 sensor/launcher 미구현 L0 Run [#44216948775](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44216948775) — **2 failed,36 passed** (전체 PERF 작업의 시작 경계).
- GREEN: renderer fallback 분류 synthetic `llvmpipe`/D3D12/NVIDIA 케이스 및 `--self-check`와 D08 sensor fixture 포함 [#44217902028](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44217902028) — **41 passed**.
- 기존 D04/D05 Python 회귀 [#44217902049](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44217902049) — **56 passed**.
- 실행 예: `python3 block_B/day08/tools/d08_wslg_renderer_probe.py --self-check`; 실제 WSLg `python3 .../d08_wslg_renderer_probe.py`는 User PC에서 실행해야 함.
- 검증 수준: Python L0 PASS. **Owner 실제 D3D12 렌더러 NOT_RUN, 실제 Gazebo CPU/GPU 가속 여부 NOT_VERIFIED.**
- REVIEW: no ROS/Gazebo control publisher, no sudo/apt, no global environment changes, no physical actor/Goal, no Guard TTL claims.
- COMMIT: 본 보고서를 같은 브랜치에 추가. `main` 병합하지 않음.

다음 단계는 사용자가 생성한 `d08_wslg_renderer_probe.zip`의 `summary.json`으로 NVIDIA 강제 폴백 여부를 판별하는 것. WSLg 표면의 실제 GPU 경로가 확인될 때까지 Gazebo 서버를 D3D12로 강제하지 않는다.
