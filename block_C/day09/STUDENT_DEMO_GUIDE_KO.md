# D09 학생용 라이브 데모 가이드 — 시계열 신호에서 학습 데이터까지

- 대상: ROS 2 Jazzy / Ubuntu 24.04 / WSL2, Python **3.12**
- 수업: 2026-11-19, 19:00–22:00 (이론 60분 + 실습 120분)
- 학습 주제: **① 전류·토크·가속도 등 시계열 데이터 특성 이해 ② 장비 상태 데이터 수집 및 학습 데이터 구성 실습**
- 본 실습의 데이터: `SYNTHETIC_COURSE_FIXTURE`, seed=2409, **10 Hz**, trace-local 시간
- 구별: 수업의 가상 전류·토크·가속도는 **실제 TurtleBot3 Waffle 계측값이 아닙니다**. 교육용 분석에는 자동주행·제어 권한이 없으며 인증된 E-Stop과 무관합니다.


## 0. GitHub 저장소 클론부터 시작 (최초 1회)

**Ubuntu 24.04 / WSL2의 새 터미널에서 시작합니다.** 학생 저장소는 공개이므로 GitHub 로그인 없이 읽기 전용으로 클론할 수 있습니다. 이미 클론한 경우에는 파일을 덮어쓰거나 재클론하지 않습니다.

```bash
git --version
mkdir -p "$HOME/axia_d09_course"
cd "$HOME/axia_d09_course"
if [ ! -d axia-robot-safety-student/.git ]; then
  git clone https://github.com/silverbjin/axia-robot-safety-student.git
fi
cd axia-robot-safety-student
# 기존 clone이 깨끗한 main인 경우에만 안전하게 최신 상태로 갱신합니다.
if [ "$(git branch --show-current)" = "main" ] && [ -z "$(git status --porcelain)" ]; then
  git pull --ff-only origin main
else
  echo "기존 브랜치/수정 사항 보존: 자동 pull 생략"
fi
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --short HEAD
```

예상 결과: `~/axia_d09_course/axia-robot-safety-student` 저장소가 준비되고 현재 브랜치가 `main`으로 표시됩니다(새 클론 기준). 기존 브랜치·수정 파일은 덮어쓰지 않습니다. **이후 명령은 같은 터미널에서 학생 저장소 루트에 머문 상태로 실행**합니다. `git clone` 실패 시 네트워크·Git 설치·접근 URL부터 확인하고, `git pull --ff-only` 실패 시 충돌을 강제 해결하지 말고 `git status`를 확인하세요.

## 0-A. 12분 오프닝 — 강사의 D08 실제 LiDAR Live Plot을 관찰합니다

**수업에서 새 코드를 만들지 않습니다.** 강사가 사전에 실행한 [공개 D08 SHA `342c6355b27af5b8b11a79b7e345820be18a581f`](https://github.com/silverbjin/axia-robot-safety-ci-public/commit/342c6355b27af5b8b11a79b7e345820be18a581f)의 TurtleBot3 Waffle / Gazebo Harmonic **NO_GOAL** 장면을 화면으로 관찰합니다. 강사는 기존 ROS 2 `/scan`을 PlotJuggler의 **ROS2 Topic Subscriber**로 읽기 전용 시각화합니다. 이 **12분은 이론 60분의 첫 부분**이며, 뒤의 D09 합성 CSV·학생 TODO 실습 **120분은 그대로**입니다.

```text
[Gazebo: Waffle + 사람형 물리 장애물]
                 │ 기존 Waffle의 실제 GPU LiDAR
                 ▼
         /scan (sensor_msgs/msg/LaserScan)
                 ├── RViz: LaserScan 공간 표시
                 └── PlotJuggler: 선택한 ranges[i] 거리(m)의 시간 변화
                                  │
                      관찰/질문/데이터 품질 이해
                                  ▼
         D09 합성 current_a / torque_nm / accel_mps2
         → Trace별 10샘플 윈도우 → mean/std 6개 → 총 424행
```

**중요한 구분:** D08 Plot은 거리 **m**를 보여줍니다. 이것은 D09 전류 **A**, 토크 **N·m**, 가속도 **m/s²**를 실제 측정한 그래프가 **아닙니다**. `/scan` 메시지의 `ranges`는 각도별 빔의 배열이므로, **한 빔의 거리**와 **전방 섹터 최솟값**을 동일하다고 주장하지 않습니다. 빔 각도는 `angle_min + i × angle_increment`입니다. D08 사람이 움직여도 선택한 빔이 장애물을 향하지 않으면 그래프가 변하지 않을 수 있습니다.

### 12분 관찰 활동

| 시간 | 강사 화면에서 볼 것 | 학생이 기록할 것 |
|---|---|---|
| 0~2분 | Gazebo·RViz·PlotJuggler 창 | 어떤 물리 현상이 어떤 데이터가 되는가? |
| 2~5분 | ROS 2 `/scan`의 `header.stamp`, `ranges`, 빔 각도 | 단위(m), 배열/시간축의 의미 |
| 5~9분 | D08 장애물 before → near → restore 루프와 **실제 수신 그래프** | 그래프가 가까움/멀어짐에 따라 어떻게 변하는가? |
| 9~11분 | `ros2 topic hz /scan`, Plot 갱신 상태 | 관측 주기와 데이터 누락은 어떻게 구분할까? |
| 11~12분 | 전류·토크·가속도 합성 시계열로 전환 | 시간·Trace·품질 검사가 두 문제에서 왜 공통인가? |

관찰 결과는 **실제로 본 숫자와 파형만** 기록합니다. 이전 공개 D08 실행에서 관찰된 약 `1.867 → 0.568 → 1.869m`는 과거 **전방 섹터** 예시로, 오늘 Plot의 `ranges[i]` 결과나 수업 성공 기준값이 아닙니다.

**장애 대응 및 안전:** 현장 WSLg 화면이나 `ranges` 빔 Plot이 표시되지 않으면 강사는 `D09_LIVE_LIDAR_PLOT=HOLD`로 기록하고 기존 RViz LaserScan/터미널 수신 화면으로 설명합니다. **없는 그래프를 PASS라고 하지 않습니다.** 새로운 ROS Publisher, `cmd_vel`, Nav2 이동 Goal, CM/Guard 안전 TTL 수정, 인증 E-Stop 시연은 하지 않습니다. 강사의 D08/Plot GUI는 학생 저장소·학생 PC에서 자동 실행되거나 자동 연결되지 않습니다. 학생은 강의 화면을 관찰한 뒤 기존 합성 데이터 실습을 진행합니다.

**선택: 강사와 같은 WSL2 ROS 세션에 직접 접근할 때만 확인** (다른 학생 PC에서는 이 명령으로 강사 토픽이 보이지 않습니다).

```bash
set +u; source /opt/ros/jazzy/setup.bash; set -u
export ROS_DOMAIN_ID=69
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 topic list -t
ros2 topic info /scan -v
ros2 topic echo /scan --once --field ranges --qos-reliability best_effort
ros2 topic hz /scan  # 실제 관찰 후 Ctrl+C; 값은 환경마다 다름
```

**수업 성취 질문:** “LiDAR 거리 변화를 직접 보고, 이제 왜 전류·토크·가속도에는 샘플링·타임스탬프·품질 검사와 6개 특징 추출이 필요하다고 생각하나요?”

공식 참고: [PlotJuggler ROS 2 plugins](https://github.com/PlotJuggler/plotjuggler-ros-plugins), [ROS 2 Jazzy LaserScan](https://docs.ros.org/en/jazzy/p/sensor_msgs/msg/LaserScan.html), [ROS 2 QoS](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html).

## 1. 오늘 데모의 큰 그림

```text
[선택·실측] 모터 드라이버/IMU → ROS 2 토픽 발견 → 읽기 → ros2 bag 기록
        ↳ 실제 환경에 데이터가 있을 때만 관찰, 필수 실습 데이터로 혼합하지 않음

[필수·합성] generator.py → CSV 3종 + schema/manifest/SHA256
        → 해시 및 Trace/시간 품질 검사
        ├─ VALID: 10 samples/window → 3개 신호 × (mean,std) = 6개 특징
        └─ INSUFFICIENT_DATA: 숫자 특징 비움, 품질 사유 기록
        → features.csv: 240 Train + 80 Valid + 100 Test 유효 + 4 품질 = 424행
```

왜 이 구성이 필요할까요? **장비의 이상징후**와 **잘못 기록된 데이터**는 다릅니다. 큰 전류 스파이크를 본 것만으로 모터 고장을 확정할 수 없습니다. 반대로 토크 공백이나 타임스탬프 역행은 모델에 수치 0을 넣어 해결할 문제가 아닙니다.

## 2. 실습 전 안전·환경 확인 (터미널 A)

다음 명령은 학생 저장소 **루트**에서 실행합니다. 새 터미널은 Windows Terminal의 Ubuntu 24.04 탭으로 열고, 기존 ROS 주행 데모를 종료시키지 마세요.

```bash
test -d block_C/fixtures   # 앞 단계에서 클론한 저장소 루트인지 확인
python3 --version
bash block_C/scripts/block_c_once.sh --doctor
```

예상 출력 (환경에 따라 Python 패치 버전은 달라짐):

```text
Python 3.12.x
BLOCK_C_STUDENT_DOCTOR python=3.12.x role=student ros_required_for_unit=false gazebo_required=false
BLOCK_C_NO_GOAL_NO_CMD_VEL_NO_CERTIFIED_ESTOP
```

`--doctor`가 중단되면 Python 3.12 및 실행 위치부터 점검하세요. D09 필수 실습은 ROS 2·Gazebo를 실행하지 않아도 됩니다.

## 3. 수업 데이터 생성과 기록의 차이

```bash
# 제공 원본의 결정성·해시·스키마·Trace 분할을 검사합니다.
python3 block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures

# 덮어쓰지 않는 별도 폴더에 동일한 합성 데이터를 재생성합니다.
OUT="$HOME/axia_d09_lab/generated_$(date +%Y%m%d_%H%M%S)"
python3 block_C/fixtures/generator.py --write --output-dir "$OUT"
ls "$OUT"
```

예상 고정 결과: `C01_FIXTURE_CONTRACT_PASS` 및 `C01_GENERATED source=SYNTHETIC_COURSE_FIXTURE`. 원본은 **46 Trace / 4,599행**, Train 24 Trace(2,400행), Valid 8 Trace(800행), Test 14 Trace(1,399행)입니다. `--write`는 이미 존재하는 폴더를 덮어쓰지 않도록 설계되었습니다.

데이터의 주요 필드는 `trace_id`, `sample_idx`, `timestamp_ns`, `current_a`(A), `torque_nm`(N·m), `accel_mps2`(m/s²), `truth_label`입니다. `timestamp_ns`는 합성 Trace별 경과시간이지 ROS `/clock`이나 실제 UTC 시간이 아닙니다.

## 4. 세 신호의 의미와 그래프 읽기

| 신호 | 수업에서 볼 특징 | 해석상의 제한 |
|---|---|---|
| 전류 `current_a` | `CURRENT_SPIKE` (TST_A_00 등) | 부하 변화 후보이지 고장 확정이 아님 |
| 토크 `torque_nm` | `TORQUE_DRIFT` (TST_A_02 등) | 서서히 누적되는 변화; 구동 모드 맥락 필요 |
| 가속도 `accel_mps2` | `ACCEL_VIBRATION` (TST_A_04 등) | 진동은 평균이 상쇄될 수 있으므로 표준편차도 관찰 |

`10 Hz`는 **샘플 간격 100ms**를 의미합니다. 10개 샘플의 첫 점과 마지막 점 사이의 시간차는 **0.9초**이며, 전체 윈도우는 다음 시작 시각까지 명목상 1초 블록입니다.

현장 질문: “TST_A_00에서 전류가 증가했을 때, 이것을 장비 고장이라고 단정하려면 추가로 무엇을 기록해야 할까요?” 부하, 동작 상태, 토크, 가속도, 시간 정합 등을 비교해야 합니다.

## 5. 선택 데모: 실제 ROS 2 토픽을 읽기 전용으로 관찰

이 부분은 ROS 2 Jazzy 노드가 이미 실행되어 있고 관련 토픽을 발견했을 때만 진행합니다. **실제 측정 성공을 보장하지 않으며** 필수 합성 실습과 데이터를 섞지 않습니다. `/joint_states`의 `effort`가 비어 있거나 실제 토크가 아닐 수 있고, `/imu` 토픽이 없을 수 있습니다.

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic list -t
# 발견된 실제 토픽 이름을 아래 명령에 입력하세요.
read -rp "실제 발견한 토픽 이름 입력: " TOPIC
ros2 topic info "$TOPIC"
ros2 topic echo "$TOPIC" --once
ros2 topic hz "$TOPIC"    # 관측 후 Ctrl+C
```

기록이 가능한 경우에만 **기록용 터미널**을 새로 열어 아래를 실행하세요. 터미널 간 셸 변수 `TOPIC`은 자동 공유되지 않으므로 반드시 **새 터미널에서 토픽을 다시 입력**해야 합니다. ROS_DOMAIN_ID가 설정되어 있다면 관찰 터미널과 동일한 값인지 확인합니다.

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic list -t
read -rp "기록할 토픽 이름 (실제로 발견한 토픽): " TOPIC
ros2 topic info "$TOPIC"  # 토픽이 없으면 기록을 진행하지 않음
mkdir -p "$HOME/axia_d09_lab"
BAG="$HOME/axia_d09_lab/rosbag_$(date +%Y%m%d_%H%M%S)"
ros2 bag record -o "$BAG" "$TOPIC"
# Ctrl+C로 기록을 종료한 뒤, 동일한 기록용 터미널에서:
ros2 bag info "$BAG"
```

주기는 수신 PC/ROS 네트워크 상황에 좌우되며, 측정되지 않은 `Hz` 수치를 성공으로 쓰면 안 됩니다. 토픽이 없다면 `TOPIC_UNAVAILABLE`로 기록하고 필수 합성 데이터 실습을 계속합니다. 이 데모는 **읽기 전용**이며 `cmd_vel`, Nav2 Goal, 인증 E-Stop 동작을 포함하지 않습니다.

## 6. 학생이 관찰해야 하는 종료 조건

- `generator.py --check`의 무결성 검사 성공과 46 Trace / 4,599행 확인
- 시계열의 이상 후보와 품질 오류 `MISSING_VALUE` / `SAMPLE_GAP` / `STAMP_REGRESSION` / `TIMESTAMP_DRIFT` 구분
- 특징 생성 목표: 총 **424행** 중 **420 VALID + 4 INSUFFICIENT_DATA**, 숫자 특징은 6개
- 학생 TODO 구현 전 테스트의 실패는 `EXPECTED_RED`입니다. **단순 함수 반환 테스트 통과만으로 424행 내용까지 검증한 것이 아닙니다.**

다음 순서의 상세 실습과 제출 기준은 [STUDENT_LAB_GUIDE_KO.md](STUDENT_LAB_GUIDE_KO.md)를 참고하세요.
