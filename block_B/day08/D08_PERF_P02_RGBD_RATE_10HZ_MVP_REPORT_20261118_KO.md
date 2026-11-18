# AXIA D08-PERF-P02 — RGB-D 10Hz 가변 프로필 MVP 단위보고서

- 날짜: 2026-11-18 KST
- 저장소/브랜치: `silverbjin/axia-robot-safety-student` / `perf/d08-wslg-rtf-sensor-profile-20261118`
- 목적: 사용자 제공 실제 Gazebo 저속 RTF 원인 중 30Hz RGB-D 렌더링 부하를 **다른 조건을 그대로 두고 한 변수만** 측정.
- 원본 RTF: GUI 5.27% / WorldStats reported median 0.79% / Sim Time÷Real Time 구간 평균 6.81%, 실제 GPU 사용 여부 미측정.
- **채택 상태:** D08 10Hz 옵션 코드 CI L0 GREEN. 실제 RTF 회복 **NOT_VERIFIED**, 기본 프로필 30Hz는 유지.

## 재사용 범위

- 공용 `block_B/day05/gazebo_live/prepare_scene.py`의 D04 공식/기존 월드 생성 경로 재사용.
- D08에서만 `--d08-rgbd-rate-hz 10`을 선택하면 `axia_d05_registered_rgbd` **센서 1개의 `<update_rate>`만** 변경.
- `block_B/day04/run_student_gazebo_yolo_once.sh`는 `AXIA_D08_STAGED_GUI=1`인 때만 새 인수를 전달. D04·D05 단독 기본 30Hz 동작/fixture 유지.
- `block_B/day08/run_d08_student_live_once.sh`: `AXIA_D08_RGBD_RATE_HZ=30` 기본; 성능 후보는 `AXIA_D08_RGBD_RATE_HZ=10` 환경변수로 선택.
- RGB 640×480, 등록 Depth, 프레임 ID, LiDAR 5Hz, 기존 Depth 5Hz, YOLO 설정·모델, Actor 궤적·world, 주행/Goal/Collision Monitor/Guard 수정 없음.

## RED → GREEN → REFACTOR → REVIEW → COMMIT

| 단계 | 실제 CI 실행 증거 | 검증 의미 |
|---|---|---|
| RED | [Run #44216948775](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44216948775) — **2 failed, 36 passed** | D08 전용 rate 인수·런처 연결 미구현 |
| 초기 GREEN 시도 문제 | [Run #44217279800](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44217279800) — **2 failed, 36 passed** | 기존 synthetic D05 fixture에는 `update_rate`가 없어 오류. 기본 D05 변경을 요구하면 안 됨 |
| REFACTOR | rate 인수 미지정이면 기존 `<update_rate>` 유무 모두 보존, 옵션 설정일 때만 태그 쓰기. 새 테스트는 **실제 Owner SDF 30Hz**와 동일한 fixture 사용 | 기존 D05 regression compatibility |
| GREEN | [Run #44217902028](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44217902028) — **41 passed** | 10Hz 후보, 30Hz 기준, 토픽·해상도·Actor 불변 |
| 기존 Block B | [Run #44217902049](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44217902049) — **56 passed** | D04·D05 일반 Python 계약 |
| 실제 Gazebo L2 | [Run #44217902163](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/44217902163) — **FAILURE before Gazebo** | ONNX Runtime 1.20.0 vendor가 9바이트 비압축 응답을 받아 `CMake Error: Problem extracting tar`; 10Hz 기능 결함이라고 판정 불가 |
| Owner WSL2 | **NOT_RUN** | 실제 GPU·RTF 개선, YOLO 실제 프레임률, WSLg 2창 화면은 아직 미검증 |
| REVIEW | D05 legacy fixture와 기존 Python 56개 통과, 안전 제어 파일 수정 없음 | MVP 필수 검증 L0 통과 |
| COMMIT | 본 보고서를 관련 코드·테스트와 같은 브랜치에 기록 | `main` 미병합 |

## 변경 파일

- `block_B/day05/gazebo_live/prepare_scene.py`
- `block_B/day04/run_student_gazebo_yolo_once.sh`
- `block_B/day08/run_d08_student_live_once.sh`
- `block_B/day08/tests/test_d08_perf_sensor_profile.py`
- `block_B/day08/tools/d08_wslg_renderer_probe.py`
- `block_B/day08/tests/test_d08_wslg_renderer_probe.py`
- `.github/workflows/d08-online-integration-student.yml`
- `block_B/day08/D08_WSLG_RTF_PERFORMANCE_RESEARCH_AND_FIELD_GUIDE_20261118_KO.md`
- P01 보고서 및 본 P02 보고서

## 최종 인수·다음 결정

현장 검증은 새 디렉터리 `~/axia_d08_student_live_perf`를 사용. 기존 `~/axia_d08_student_live_renderfix`와 원본 ZIP 보존. 먼저 WSLg GPU 자식 `glxinfo -B` 후보를 확인하고, `AXIA_D08_RGBD_RATE_HZ=10`으로 D08 Live를 시작한 다음 기존 읽기 전용 RTF 관측기로 20초 기록한다.

**선택 게이트:** 최초 ZIP의 구간 RTF(약 6.81%)와 신규 동일 계산값을 비교하여 실제 개선이 확인되고 RGB-D·YOLO person 관측 및 RViz2/Gazebo 2창이 유지될 때만 교육용 프로필 채택 고려. 미달 시 Actor 속도나 외부 제어기를 수정하지 않고 GPU 렌더러/서버 부하 경계로 다음 가설을 이동한다.

**상태:** `D08_PERF_RATE_L0_PASS / L2_BLOCKED_BY_ONNX_VENDOR / OWNER_RTF_NOT_RUN / NO_GOAL / MAIN_NOT_MERGED`. 이 기능으로 D06/G07 120ms·150ms TTL, 물리 Contact, 로봇 움직임 또는 인증 HW E-Stop을 검증했다고 주장하지 않는다.
