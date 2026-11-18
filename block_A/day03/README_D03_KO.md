# D03 학생 실습 가이드 — P1 상태 관측 → ROS Diagnostics → 단계적 Safe Mode

**교육 시간**: 21:00–23:00, 120분 · **배포**: `silverbjin/axia-robot-safety-student` 의 `D03` 브랜치.

## 1. 목적과 완료 조건

- LO1: `/axia/safety/state` (`std_msgs/msg/String`) JSON 속 `state`, `health_diagnostics`를 읽고 `DiagnosticStatus` (level=0 OK/1 WARN/2 ERROR/3 STALE)로 표준화한다.
- LO2: 진단 결과와 수신시간에 따라 `NORMAL_CANDIDATE`, `LIMITED_CANDIDATE`, `PROTECTIVE_STOP`, `SW_STOP_LATCHED`, `RECOVERY_REQUIRED`를 계산한다.
- 완료: **핵심 TODO 함수 2개**를 구현하고 필수 공개 pytest **30개 GREEN**, 합성 재생 9건 검사 완료, 보고서와 Git SHA 제출.

이 과제는 **진단 모니터링·교육용 후보 판단**이며 실제 P1 Safety Supervisor·Watchdog·FSM이나 인증 HW E-Stop을 구현하는 과제가 아니다. Gazebo 실행은 **선택**이고 필수 합격 기준이 아니다.

## 2. 사전조건·터미널 구성

- Windows 10/11의 WSL2 Ubuntu 24.04, 또는 Linux/Docker Ubuntu 24.04; **Python 3.12**, Git, 인터넷(최초 설치). `python3 -m venv` 지원 필요.
- 필수: `pytest==8.3.5`; ROS 2 Jazzy·Gazebo Harmonic은 **필수 아님**.
- 터미널 1: 실습 루트에서 Python·pytest·Git. ROS 선택 실습 시 터미널 2/3/4 추가. 실습 종료 때 추가 터미널은 `Ctrl+C`로 닫는다.

~~~bash
# 터미널 1 — 사용자 홈에 학습 코드만 저장. 원본 P1 비공개 Repo 접근 불필요.
cd ~
git clone --branch D03 --single-branch https://github.com/silverbjin/axia-robot-safety-student.git
cd axia-robot-safety-student
# 로컬 작업 브랜치를 별도 생성
git switch -c work/d03-your-id
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pytest==8.3.5
bash block_A/day03/scripts/run_lab.sh preflight
~~~

**예상**: `Python 3.12.x`, `pytest 8.3.5`, `INSPECT_OK`; ROS가 없으면 `[OPTIONAL] ROS Jazzy not detected`만 출력하고 필수 실습 계속.

## 3. 120분 실습 순서

| 시간 | 활동 | 실행/수정 | 기대 결과 |
|---|---|---|---|
| 21:00–21:15 | 합성 9사례 관측 | `bash block_A/day03/scripts/run_lab.sh inspect` | 9개 사례와 level 인쇄, `INSPECT_OK` |
| 21:15–21:30 | 공개 RED | `bash block_A/day03/scripts/run_lab.sh red` | `22 failed, 8 passed`, `ORIGINAL_PYTEST_EXIT=1`; **의도된 실패** |
| 21:30–22:05 | Adapter TODO | `block_A/day03/p1_adapter_todo.py`의 `diagnose_p1_state()` | 정상+불완전+고장+무수신 판정 |
| 22:05–22:30 | Safe Mode TODO | `block_A/day03/todo_safety.py`의 `assess_diagnostic()` | 우선순위와 복구 래치 테스트 |
| 22:30–22:45 | GREEN + 재생 | `bash .../run_lab.sh green` 및 `bash .../run_lab.sh run` | `30 passed` / `D03_REPLAY_RESULT ... failures=0` |
| 22:45–23:00 | 제출 | `git diff`, 보고서, 개인 Fork Push | 코드·테스트 로그·SHA·미검증 항목 |

`inspect`, `preflight`, `d03_synthetic_ros_publisher.py --dry-run`은 **TODO 작성 전에도 동작**한다. `run`은 TODO 완성 전에 `D03_REPLAY_RESULT ... failures>0`, 종료 3일 수 있으며 정상적인 개발 과정이다.

## 4. TODO 1 — P1 JSON → 진단 상태

주어진 인터페이스는 **바꾸지 않는다**.

~~~python
# block_A/day03/p1_adapter_todo.py
def diagnose_p1_state(raw_json: str | None, *, received_mono: float | None,
                      now_mono: float, timeout_s: float = 1.0) -> DiagnosticRecord:
    # TODO: 유효성·수신시간·state/health 판정과 보안상 안전한 values만 구현
    ...
~~~

| 입력 조건 | 진단 level | 고정 message | 이유 |
|---|---:|---|---|
| `state=NORMAL`, 5개 핵심 건강 Boolean 모두 True | 0 | `NORMAL` | 관측상 건강 (주행 허가 아님) |
| `state=LIMITED`, `BOOT_SAFE`, `SW_STOP_LATCHED`, `RECOVERY_REQUIRED` | 1 | 상태 문자열 | 상태 관측 (실제 FSM 제어 아님) |
| `state=PROTECTIVE_STOP` | 2 | `PROTECTIVE_STOP` | 고장 시 ERROR |
| NORMAL에서 건강 신호 중 하나라도 명시적 False | 2 | `HEALTH_BAD` | 불건전 신호 우선 |
| NORMAL에서 건강 신호 누락·None | 1 | `HEALTH_UNKNOWN` | 불명확 상태를 OK로 표시 금지 |
| 메시지 없음/수신 후 시간 초과 (`age > timeout_s`) | 3 | `STATE_MESSAGE_STALE` | 수신 관측 신선도 문제 |
| 잘못된 JSON·미지원 상태·가짜 E-Stop 인증 주장 | 2 | `INVALID_STATE_MESSAGE` | fail closed |

시간 입력의 NaN/Inf·음수·미래 수신시간은 `INVALID_INPUT`으로 보수적으로 처리한다. `now_mono - received_mono == timeout_s`는 **정상 경계**이다. `values`는 `state`, `scan_fault_code`, `stop_is_certified_estop=false` 등 **허용목록만** 남기며 원본 JSON·Goal UUID·비밀번호·외부 입력 문구를 그대로 담지 않는다.

## 5. TODO 2 — Safe Mode 후보

파일: `block_A/day03/todo_safety.py`의 `assess_diagnostic()` 함수. 반환형 `Verdict(mode, reason, requires_manual_recovery)` 유지.

**우선순위**: 명시적 SW STOP 래치 > 잘못된 입력/시간 초과 > ERROR/STALE > 과거 보호정지로부터 복구 필요 > WARN > OK. `prior_protective_stop=True` 뒤 새 OK 입력은 **`RECOVERY_REQUIRED`**, 자동 재주행 아님.

~~~bash
# 수정 후 필수 공개 테스트. 최초 실패는 미완성이므로 정상.
bash block_A/day03/scripts/run_lab.sh green
bash block_A/day03/scripts/run_lab.sh run
~~~

**기대 출력**: `30 passed`, 합성 사례 `D03_REPLAY_RESULT cases=9 failures=0`(정답 구현 기준); `ROS_VERIFIED=NOT_RUN`, `GAZEBO_VERIFIED=NOT_RUN`은 정상적인 검증 경계 표기.

## 6. 선택 — ROS 2 Jazzy 표준 Diagnostics 실제 발행 (추가 터미널 3개)

**선행조건**: 강사가 격리된 ROS_DOMAIN_ID 확인하고 ROS 2 Jazzy 설치 확인. 실물과 공유 ROS 도메인 금지. 완성된 Adapter만 사용한다.

~~~bash
# 터미널 2 — 별도의 ROS Jazzy 터미널. 환경 변수를 각각 설정.
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=73
PYTHONPATH=block_A/day03 python3 block_A/day03/ros_diagnostics_bridge.py
~~~

~~~bash
# 터미널 3 — 합성 P1 상태 메시지 전송. 절대 실제 P1 네트워크에서 실행 금지.
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=73
export AXIA_D03_ISOLATED_SYNTHETIC_ONLY=YES
python3 block_A/day03/scripts/d03_synthetic_ros_publisher.py --case NORMAL_HEALTHY --count 8
~~~

~~~bash
# 터미널 4 — ROS Diagnostics 읽기 전용 확인.
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=73
ros2 topic echo /diagnostics --once
~~~

**기대**: `diagnostic_msgs/msg/DiagnosticArray`, `AXIA/P1/SafetySupervisor`. `STATE_MESSAGE_STALE`가 처음 나오는 것은 합성 메시지 미수신인 정상 관측이다. 이는 **실제 Scan 고장**이 아니다. 컨테이너·호스트 DDS 네트워크 문제는 ROS 통합을 미검증으로 남기고 Python 필수 실습을 계속한다.

## 7. 제출·CI

공용 `silverbjin` 원본 저장소에 직접 Push하지 말고 개인 Fork를 사용한다. 개인 Fork의 Actions가 허용되는 경우 `work/d03-*` Push에서 **GREEN CI**가 실행된다. 아니면 강사가 D03을 대상으로 PR을 열어 검증한다. 템플릿의 expected RED Actions 성공은 학생 정답의 GREEN이 아니다.

~~~bash
git status --short
git add block_A/day03/p1_adapter_todo.py block_A/day03/todo_safety.py
git commit -m 'feat(d03): complete P1 diagnostics and safe-mode TODO'
git rev-parse HEAD
# 개인 Fork를 origin으로 지정한 경우에만:
git push -u origin work/d03-your-id
~~~

`block_A/day03/REPORT_TEMPLATE_KO.md`에 본인 SHA·명령·원시 테스트 출력과 검증 수준을 기입한다. 강사 정답과 Hidden Tests는 제출물에 포함하면 안 된다.

## 8. 장애 대응

| 증상 | 원인 | 조치 |
|---|---|---|
| `.venv/bin/activate: No such file` | venv 미설치 | Ubuntu에서 `sudo apt install python3-venv`; `python3 -m venv .venv` 재실행 |
| `ModuleNotFoundError: pytest` | venv 활성화·설치 누락 | `source .venv/bin/activate; python -m pip install pytest==8.3.5` |
| `No module named p1_adapter_todo` | 현재 폴더/PYTHONPATH 오류 | 저장소 루트에서 `bash block_A/day03/scripts/run_lab.sh green` |
| `TODO_NOT_IMPLEMENTED` | 핵심 판단 미구현 | 실패 테스트 하나씩 선택해 RED→GREEN 구현 |
| `22 failed, 8 passed` | 처음 제출된 TODO 그대로 | **정상 초기 RED**; 30/30 통과 전에는 제출 GREEN 아님 |
| `ROS Jazzy not detected` | 선택 ROS 미설치 | Python 필수 실습 계속; 과제 실패가 아님 |
| `/diagnostics` 출력 없음 | ROS_DOMAIN_ID 불일치·브리지 미기동 | 3개 ROS 터미널의 ID와 `source` 확인, 필요시 선택 실습 중단 |
| `STATE_MESSAGE_STALE` | 메시지 없음/수신 시간 초과 | 합성 퍼블리셔 실행 확인; 실제 고장으로 오해하지 않기 |
| `git push: permission denied` | 교육 공용 저장소 Push 권한 없음 | 본인 Fork에 Push 또는 강사 지정 제출 경로 |

**종료**: Python 실습은 터미널 1 유지 또는 종료. ROS 선택 실습은 터미널 2/3/4 각각 `Ctrl+C`. P1의 `/start`, `/cmd_vel`, `/navigate_to_pose`, `/axia/fault/*` 호출 금지.