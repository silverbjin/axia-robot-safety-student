# AXIA D03 훈련생 실습 가이드 — P1 Diagnostics → Safe Mode

- 과정: D03 (19:00–23:00), **실습 21:00–23:00 / 120분**
- 기준: ROS 2 Jazzy + Ubuntu 24.04 + Gazebo Harmonic의 교육용 P1. 필수 과제는 Python 3.12/pytest만 사용하며 **Gazebo 실행은 필수 아님**.
- 학생 저장소: <https://github.com/silverbjin/axia-robot-safety-student>
- 배포용 **기능 브랜치**: `D03` / 검토 당시 SHA `afbdfdc3df205d373dbae695683b42dacf0632e9`.
- 학생 `main`에는 아직 실습 파일이 없으므로 `main`을 Clone하지 않는다. 강사가 별도 릴리스를 확정하면 SHA/태그를 그 값으로 교체한다.
- 핵심 안전 문장: **ROS Diagnostics의 OK=이동 승인 아님. SW Stop≠인증된 하드웨어 E-Stop.**

## 1. 학습 목표 및 결과물

1. **ROS Diagnostics 기반 상태 모니터링 구조 이해**: P1 `/axia/safety/state`의 `std_msgs/String` JSON에서 건강·고장·상태 정보를 읽어 `DiagnosticStatus`의 level/name/message/values로 변환하는 원리를 설명한다.
2. **Safe Mode 설계 및 단계적 안전 동작 실습**: 정상/경고/오류/무수신과 SW Stop·수동복구를 구별하는 정책을 작성하고 자동 테스트로 검증한다.

**제출**: `p1_adapter_todo.py`, `todo_safety.py`, RED/GREEN 콘솔 출력·exit code, Git SHA, 상태 매핑표, 실습 보고서. 학생 코드에는 `/cmd_vel` 발행이나 Goal/Fault 호출을 추가하지 않는다.

## 2. 환경 준비 — 터미널 1 (필수)

Windows는 WSL2 Ubuntu 24.04, Linux는 Ubuntu 24.04, macOS는 **검증된 교육용 Docker 이미지의 Python CLI**를 권장한다. Docker 이미지가 실제 Docker Hub에 배포되지 않았다면 아직 존재한다고 가정하지 않는다. 모든 OS에서 필수 실습은 Python으로 진행할 수 있다.

```bash
python3 --version
# 권장: Python 3.12.x. Python 3.13에서도 순수 Python 시험 가능하나 강사 검증판과 구분

git clone --branch D03 --single-branch \
  https://github.com/silverbjin/axia-robot-safety-student.git
cd axia-robot-safety-student

git rev-parse HEAD
# 기준 파일 검증 시: afbdfdc3df205d373dbae695683b42dacf0632e9

git switch -c work/d03-myname
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pytest==8.3.5
```

**예상 결과**: `.venv`가 생기고 `python -m pytest --version`에서 `pytest 8.3.5`를 확인한다. 설치에 실패하면 DNS/프록시, Python·venv 설치, 터미널 현재 경로부터 확인한다. 비공개 Instructor 저장소는 Clone하지 않는다.

## 3. 120분 실습 순서

| 시각 | 실습 | 완료 확인 |
|---|---|---|
| 21:00–21:15 | `p1_states.jsonl` 9개 합성 상태 확인 | 정상/제한/보호정지/무수신 예측표 |
| 21:15–21:30 | 공개 테스트 초기 RED | 실패 로그, `exit=1` |
| 21:30–22:05 | P1 JSON → Diagnostics Adapter TODO | JSON·시간·건강 플래그 검사 |
| 22:05–22:30 | Safe Mode TODO | 우선순위·수동복구 규칙 |
| 22:30–22:45 | RED→GREEN, 수정, 회귀 검사 | **30개 공개 테스트** 전체 PASS 목표 |
| 22:45–23:00 | 결과 보고 및 코드 제출 | Git SHA·스크린샷·미검증 사항 |

### 3-A. 상태 JSON 조사

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path('block_A/day03/p1_states.jsonl')
for line in p.read_text(encoding='utf-8').splitlines():
    row = json.loads(line)
    print(f"{row['case_id']:24} -> level={row['expected_level']} {row['expected_message']}")
PY
```

**예상 결과**: NORMAL_HEALTHY→0, LIMITED→1, SCAN_DROPPED→2, SW_STOP→1, RECOVERY_REQUIRED→1, BOOT_SAFE→1, STALE_RX→3, NORMAL_BUT_HEALTH_BAD→2, NORMAL_UNKNOWN_HEALTH→1.

**생각할 질문**: 왜 `SW_STOP_LATCHED`의 Diagnostics 레벨은 WARN(1)인데, P1의 실제 FSM에서는 이동을 금지할까? 진단 레벨은 *운영 상태를 관측하는 정보*이지 로봇의 주행 권한이 아니기 때문이다.

### 3-B. RED 확인

```bash
set +e
PYTHONPATH=block_A/day03 python -m pytest -q \
  block_A/tests/test_safety_public.py \
  block_A/tests/test_d03_adapter_public.py | tee d03_red.log
RC=${PIPESTATUS[0]}
set -e
echo "D03_RED_EXIT=$RC"
```

**예상 결과(기준 TODO)**: `22 failed, 8 passed`, `D03_RED_EXIT=1`. **이것은 의도된 초기 상태**다. 테스트가 수집되지 않거나 `ImportError`가 나오면 RED로 인정하지 말고 경로와 `PYTHONPATH`를 바로잡는다. 위 수치는 이전 Python 격리 실행 근거이며 해당 학생 PC에서 동일하게 실행됐다고 주장하지 않는다.

### 3-C. Adapter 구현

파일: `block_A/day03/p1_adapter_todo.py`

`diagnose_p1_state(raw_json, received_mono, now_mono, timeout_s=1.0)`은 **진단용 데이터** `DiagnosticRecord`를 반환한다. 실제 ROS 메시지 발행은 별도의 `ros_diagnostics_bridge.py`가 수행한다.

| 입력 | 기대 동작 | 구현 힌트 |
|---|---|---|
| `raw_json is None`, 미수신, `age > timeout_s` | `STALE=3`, `STATE_MESSAGE_STALE` | `time.monotonic()` 수신시각 기반 |
| `PROTECTIVE_STOP` | `ERROR=2` | 실제 P1 FSM 이름 유지 |
| `BOOT_SAFE`, `LIMITED`, `SW_STOP_LATCHED`, `RECOVERY_REQUIRED` | `WARN=1` | 상태 보고이며 안전 허가 아님 |
| `NORMAL` + 건강 플래그 5개 모두 `True` | `OK=0` | `clock_ok`, `scan_ok`, `graph_ok`, `cm_lifecycle_ok`, `nav2_action_ready` |
| `NORMAL` + 건강 플래그 한 개라도 `False` | `ERROR=2`, `HEALTH_BAD` | 명시적 실패는 누락보다 우선 |
| `NORMAL` + 누락 또는 `None` | `WARN=1`, `HEALTH_UNKNOWN` | 불확실성을 OK로 처리하지 않기 |
| 유효하지 않은 JSON, 인증 E-Stop 주장 | `ERROR=2` | 잘못된 입력은 fail-closed |

`DiagnosticRecord.values`에는 허용된 키만 담아야 한다. `goal_id`, 전체 원본 JSON, 토큰·개인정보는 복사하지 않는다.

### 3-D. Safe Mode 구현

파일: `block_A/day03/todo_safety.py`

- 소프트웨어 Stop 래치가 최우선이다.
- 무효 입력, ERROR(2), STALE(3), 수신시간 초과는 보호정지 후보로 판정한다.
- 이전 보호정지가 있었다면 정상 정보가 돌아와도 `RECOVERY_REQUIRED`로 판정한다.
- WARN은 `LIMITED_CANDIDATE`, OK는 `NORMAL_CANDIDATE`이다. 둘 다 직접 주행을 승인하지 않는다.

### 3-E. GREEN 테스트

```bash
PYTHONPATH=block_A/day03 python -m pytest -q \
  block_A/tests/test_safety_public.py \
  block_A/tests/test_d03_adapter_public.py \
  --junitxml=d03_public_junit.xml
RC=$?
echo "D03_GREEN_EXIT=$RC"
```

**목표 출력**: `30 passed`, `D03_GREEN_EXIT=0`, `d03_public_junit.xml` 생성. 실제 학생 코드가 통과한 경우에만 본인의 결과에 PASS를 기록한다.

## 4. 선택 실습 — ROS 2 Jazzy에서 `/diagnostics` 보기

이 선택 실습은 **학생의 Python 구현이 GREEN이고**, ROS 2 Jazzy가 설치되어 있으며, **P1 실제 구동 도메인과 분리된 실습 DDS 도메인**에서만 시행한다. 필수 실습 이수에 Gazebo/Goal/Fault는 필요 없다.

**터미널 2** (새 터미널; 가상환경은 해제하고 ROS 시스템 Python 사용 권장):

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=73  # 강사가 확인한 빈 교육용 도메인으로 조정
cd ~/axia-robot-safety-student
PYTHONPATH=block_A/day03 python3 block_A/day03/ros_diagnostics_bridge.py
```

**터미널 3**:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=73
ros2 topic echo /diagnostics --once
```

상태 Publisher가 없으면 `level: 3`, `message: STATE_MESSAGE_STALE`인 DiagnosticStatus를 관측하는 것이 정상적이다. 이 명령은 ROS API 연습일 뿐, 실제 TurtleBot3의 주행/정지 성공 증거가 아니다. 완료 후 터미널 2는 `Ctrl+C`, 터미널 3도 종료한다.

> ROS 2가 없는 Docker/Python 환경에서는 선택 실습을 생략하고, `ROS_RUNTIME=NOT_RUN`이라고 보고한다. Windows WSLg/macOS의 Gazebo GUI는 필수 범위가 아니다.

## 5. 제출 및 GREEN CI

```bash
git status --short
git add block_A/day03/p1_adapter_todo.py block_A/day03/todo_safety.py
git commit -m "feat(d03): implement diagnostics adapter and safe mode"
git rev-parse HEAD
# 개인 Fork를 origin으로 설정한 상태에서만 push:
git push -u origin work/d03-myname
```

`.github/workflows/d03-green-grading.yml`은 지정된 제출 브랜치(`work/d03-*`, `submissions/d03-*`, `student/d03-*`) Push에 대해 공개 테스트를 실행하도록 작성돼 있다. **개인 Fork에서는 GitHub Actions 활성화가 필요할 수 있으며**, 원본 저장소에서 강제 통과시키지 않는다.

### 제출 보고서 항목

- 내 Git SHA / Python 버전 / OS / 이미지 digest(도커 사용 시)
- RED 22F/8P 여부와 종료코드 / GREEN 30P 여부와 종료코드 / 공개 CI URL
- P1 JSON → DiagnosticStatus 매핑 표
- `NORMAL_CANDIDATE`와 실제 이동 권한의 차이, Reset과 Rearm 차이
- **검증 범위:** `PYTHON_UNIT`, `ROS_RUNTIME`(옵션), `GAZEBO`(원칙상 NOT_RUN), `CERTIFIED_ESTOP`(NOT_VERIFIED)

## 6. 실패 시 바로 확인할 것

| 증상 | 원인 후보 / 점검 |
|---|---|
| `ModuleNotFoundError: p1_adapter_todo` | 저장소 루트 실행 여부, `PYTHONPATH=block_A/day03` |
| `pytest: command not found` | venv 활성화, `python -m pytest --version` |
| 22개 실패가 지속 | TODO 반환값 `TODO_NOT_IMPLEMENTED` 여부, 입력·시간·레벨 검사 확인 |
| 1개만 경계조건 실패 | `age > timeout`과 `age >= timeout` 차이 |
| `import rclpy` 실패 | ROS setup 미적용 또는 venv가 apt ROS 패키지를 가림; ROS 터미널에서 `python3 -c 'import rclpy'` |
| `/diagnostics` 없음 | ROS Bridge 실행 여부, 같은 `ROS_DOMAIN_ID`, 올바른 ROS 설치 확인 |
| GitHub Actions 실패 | 개인 Fork Actions 설정, push 브랜치 이름, CI 출력의 실제 assertion 확인 |

**금지:** `/axia/safety/start`, `/axia/fault/*`, `/cmd_vel`, Nav2 Goal을 학생 실습 중 실행하지 않는다.