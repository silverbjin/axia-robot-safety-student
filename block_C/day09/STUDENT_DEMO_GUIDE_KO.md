# D09 학생용 라이브 데모 가이드 — 시계열 신호에서 학습 데이터까지

- 대상: ROS 2 Jazzy / Ubuntu 24.04 / WSL2, Python **3.12**
- 수업: 2026-11-19, 19:00–22:00 (이론 60분 + 실습 120분)
- 학습 주제: **① 전류·토크·가속도 등 시계열 데이터 특성 이해 ② 장비 상태 데이터 수집 및 학습 데이터 구성 실습**
- 본 실습의 데이터: `SYNTHETIC_COURSE_FIXTURE`, seed=2409, **10 Hz**, trace-local 시간
- 구별: 수업의 가상 전류·토크·가속도는 **실제 TurtleBot3 Waffle 계측값이 아닙니다**. 교육용 분석에는 자동주행·제어 권한이 없으며 인증된 E-Stop과 무관합니다.

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
cd ~/axia-robot-safety-student  # 실제 clone 위치가 다르면 그 경로로 이동
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

기록이 가능한 경우에만, 별도 터미널에서 토픽을 확인한 뒤 아래 명령을 실행하고 Ctrl+C로 기록을 종료합니다.

```bash
mkdir -p "$HOME/axia_d09_lab"
ros2 bag record -o "$HOME/axia_d09_lab/rosbag_$(date +%Y%m%d_%H%M%S)" "$TOPIC"
# Ctrl+C 후 새로 생성된 bag 경로를 지정해 ros2 bag info 명령으로 검사
```

주기는 수신 PC/ROS 네트워크 상황에 좌우되며, 측정되지 않은 `Hz` 수치를 성공으로 쓰면 안 됩니다. 토픽이 없다면 `TOPIC_UNAVAILABLE`로 기록하고 필수 합성 데이터 실습을 계속합니다. 이 데모는 **읽기 전용**이며 `cmd_vel`, Nav2 Goal, 인증 E-Stop 동작을 포함하지 않습니다.

## 6. 학생이 관찰해야 하는 종료 조건

- `generator.py --check`의 무결성 검사 성공과 46 Trace / 4,599행 확인
- 시계열의 이상 후보와 품질 오류 `MISSING_VALUE` / `SAMPLE_GAP` / `STAMP_REGRESSION` / `TIMESTAMP_DRIFT` 구분
- 특징 생성 목표: 총 **424행** 중 **420 VALID + 4 INSUFFICIENT_DATA**, 숫자 특징은 6개
- 학생 TODO 구현 전 테스트의 실패는 `EXPECTED_RED`입니다. **단순 함수 반환 테스트 통과만으로 424행 내용까지 검증한 것이 아닙니다.**

다음 순서의 상세 실습과 제출 기준은 [STUDENT_LAB_GUIDE_KO.md](STUDENT_LAB_GUIDE_KO.md)를 참고하세요.
