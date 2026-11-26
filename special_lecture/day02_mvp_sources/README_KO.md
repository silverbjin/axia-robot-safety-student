# AXIA DAY 02 — 성공·실패 G07 MVP 전체 소스 및 직접 빌드

**두 버전의 실제 G07 전체 런타임 소스가 같은 공개 학생용 저장소에 들어 있습니다.** Git submodule, 외부 소스 다운로드 또는 강사 비공개 저장소가 필요하지 않습니다. 대상 환경은 **WSL2 Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic**입니다.

## 1. 소스 위치와 실제 인수 이력

| 버전 | 학생 저장소 내부의 경로 | 원본 Student 소스 SHA | 과거 Native Moving L2 |
|---|---|---|---|
| 완성 G07 | `special_lecture/day02_mvp_sources/accepted/runtime/` | `f7edb2d126502eeeed58ae014adadc7a2096d41b` | [2/2 PASS #44965035965](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44965035965) |
| 실패 G07 | `special_lecture/day02_mvp_sources/failed/runtime/` | `a04f9a7da8d54bbd9f944d05388792cb706adf28` | [0/2 FAIL #44914827138](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44914827138) |

전체 `h01_runtime` Git tree SHA는 각각 `1ad1d424358345420b8bfc67a6a7ca44d634a974`(186개 파일), `0d44f39c8f5927d21411c33e7a793ca1a3f6f368`(187개 파일)입니다. `ros2_ws/src`만이 아니라 `configs`, `scripts`, `tools`, `training`까지 정확히 포함했습니다. **런타임 전체가 원본 그대로이므로 SHA 기준의 과거 인수 범위를 보존합니다.**

학습상 중요한 사실: 두 버전은 네 ROS 2 패키지 소스 트리가 **동일**(SHA `767c3d10187280303f5226a90ede205eb0059033`)합니다. 차이는 상위 런타임의 도구/검증 계층 등에 있습니다. 따라서 **양쪽의 패키지 빌드 PASS가 실제 Moving L2 성공을 뜻하지 않습니다.**

## 2. 무엇을 빌드하나요?

```text
accepted/runtime/ros2_ws/src/
  axia_fault_injector/      # LaserScan Fault Relay
  axia_safety_bringup/      # Official Nav2/Gazebo 실행 래퍼
  axia_safety_supervisor/   # FSM/Goal/Command Gate
  axia_scenario_verifier/   # Scenario & Evidence

failed/runtime/ros2_ws/src/
  동일한 4개 ROS 2 Python 패키지
  (전체 runtime/tools 등은 서로 다름)
```

모두 **`ament_python`** 타입입니다. `compileall`은 Python 구문 및 바이트코드를 검사하고, `colcon build`가 실제 ROS 2 패키지 빌드·설치를 수행합니다. **C++ 컴파일이 아닙니다.**

## 3. WSL2 원샷 명령 — 전체 소스 받고 두 번 빌드

```bash
cd ~
git clone --single-branch \
  --branch release/day02-dual-mvp-full-source-build-20261126 \
  https://github.com/silverbjin/axia-robot-safety-student.git \
  axia-day02-full-sources

cd ~/axia-day02-full-sources

# 먼저 소스와 역사적 검증 결과를 읽기 전용 L0 확인
bash special_lecture/day02_mvp_sources/scripts/build_dual_mvp.sh --verify

# /opt/ros/jazzy와 colcon, ament_python 사전 확인
bash special_lecture/day02_mvp_sources/scripts/build_dual_mvp.sh --doctor

# 두 버전을 각각 분리된 빌드 공간으로 복사하고 실제 colcon build
bash special_lecture/day02_mvp_sources/scripts/build_dual_mvp.sh --both \
  --out "$HOME/axia-day02-colcon-builds"
```

사전 점검에서 `MISSING_colcon`이 표시된다면 다음 명령으로 도구를 설치한 뒤 재실행하십시오.

```bash
sudo apt-get update
sudo apt-get install -y python3-colcon-common-extensions python3-setuptools
```

`--accepted` 또는 `--failed`만 선택하면 해당 소스만 빌드합니다. 이때 `--out` 경로는 서로 달라야 합니다. 이미 존재하는 출력 경로는 **자동 삭제·덮어쓰지 않습니다**. 소스와 결과가 뒤섞이지 않도록, 전체 소스를 빌드 출력 폴더에 복제한 후 빌드합니다.

## 4. 실제 생성되는 결과

```text
~/axia-day02-colcon-builds/
  accepted/
    runtime/ros2_ws/src/          원본과 같은 코드의 격리된 복사본
    build/                        colcon 빌드 결과
    install/                      ROS 패키지 설치 결과
    logs/colcon_build.log         실제 빌드 stdout/stderr
    BUILD_RESULT.json             4개 패키지 PASS 후만 생성
  failed/
    runtime/ros2_ws/src/
    build/
    install/
    logs/colcon_build.log
    BUILD_RESULT.json
```

설치가 끝나면 **성공본 전용 새 터미널**에서 다음을 실행하십시오.

```bash
source /opt/ros/jazzy/setup.bash
source "$HOME/axia-day02-colcon-builds/accepted/install/local_setup.bash"
ros2 pkg prefix axia_fault_injector
ros2 pkg prefix axia_safety_bringup
ros2 pkg prefix axia_safety_supervisor
ros2 pkg prefix axia_scenario_verifier
```

실패본의 설치 결과를 확인할 때는 **다른 새 터미널**에서 Jazzy 환경을 다시 읽고, `failed/install/local_setup.bash`만 활성화하십시오.

## 5. 차이 분석 실습 (Goal 자동 실행 없음)

```bash
cd ~/axia-day02-full-sources
git diff --no-index --stat \
  special_lecture/day02_mvp_sources/accepted/runtime \
  special_lecture/day02_mvp_sources/failed/runtime || true

diff -u \
  special_lecture/day02_mvp_sources/accepted/runtime/tools/p2_g07_ordered_shutdown.py \
  special_lecture/day02_mvp_sources/failed/runtime/tools/p2_g07_ordered_shutdown.py || true
```

두 소스의 차이는 **실패 원인 가설의 시작점**이지 FastDDS 지연의 근본 원인 입증이 아닙니다. 심화 워크북에서는 실제 0/2 실패의 최초 `/scan` 439ms, `/odom` 362ms 등 수신 타이밍을 분리해 분석하고 반증 가능한 테스트를 설계합니다.

## 6. 학생 증거 및 검증 범위

- 두 스냅샷의 정확한 SHA 및 전체 파일 수, 수정 여부(`--verify`).
- 각 버전 `colcon build` 실제 출력/exit code, 네 패키지 설치 경로.
- 직접 수행한 **Python 구문/L1 ROS 패키지 빌드**와 과거 **Native Moving L2 2/2 PASS / 0/2 FAIL**을 분리한 보고서.
- 실패본 런타임 차이와 최초 안전 상태 전이·수신 지연, 학생 개인 브랜치/커밋 SHA.
- 실패 수정 후 신규 Moving L2 증거가 없으면 **HOLD** 표기.

과거 성공 Owner WSL2 L3는 **원본 수치·Lifecycle `PASS_SCOPED`**입니다. 원래 자동 판정 `HOLD_RAW_REVIEW_AND_VISUAL_PENDING`은 덮어쓰지 않습니다. 실패본 Owner L3 `NOT_RUN`, RMW root cause `UNDETERMINED`, 소프트웨어 STOP≠인증 E-Stop입니다.

빌드 스크립트는 ROS 노드, Gazebo, 실제 Goal을 **실행하지 않습니다**. 전체 Nav2/Gazebo 실행은 추가 공식 의존성(`nav2_bringup`, `nav2_minimal_tb3_sim`, `ros_gz_sim`)과 별도 안전 승인·인수 계약이 필요합니다. 강사 정답·개인 rosbag·비밀 파일은 배포에서 제외했습니다. 이번에는 `main` 병합을 수행하지 않습니다.
