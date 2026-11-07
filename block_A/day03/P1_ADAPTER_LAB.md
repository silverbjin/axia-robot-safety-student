# D03 통합 실습 — P1 JSON → ROS Diagnostics Adapter

**목표**: ROS Diagnostics 메시지 구조를 이해하고 P1 Supervisor의 상태를 진단 메시지로 표현한다. Safe Mode 우선순위를 순수 Python에서 테스트한다. 진단 결과는 주행 허가가 아니다.

## 준비

현재 Student main에는 실습 파일이 없습니다. 강사에게 안내받은 실습 브랜치에서 시작합니다.

~~~bash
git clone --branch feat/d03-p1-diagnostics-adapter-tdd --single-branch https://github.com/silverbjin/axia-robot-safety-student.git
cd axia-robot-safety-student
git switch -c work/d03-my-submission
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pytest==8.3.5
~~~

## 실습 120분

| 단계 | 시간 | 작업 |
|---|---:|---|
| 합성 상태 해석 | 15분 | p1_states.jsonl 9개 사례 분석 |
| RED | 15분 | 기존·신규 공개 테스트 실패 확인 |
| Adapter TODO | 35분 | P1 JSON·시간 검증, Diagnostics 변환 |
| Safe Mode TODO | 25분 | 기존 todo_safety.py 구현 |
| GREEN | 15분 | 공개 테스트 모두 통과 |
| 제출 | 15분 | 코드·로그·Git SHA·CI 결과 제출 |

~~~bash
PYTHONPATH=block_A/day03 python -m pytest -q block_A/tests/test_safety_public.py block_A/tests/test_d03_adapter_public.py
~~~

**처음에는 실패가 정상**입니다. 두 TODO를 모두 구현하여 exit code 0을 만듭니다.

## Adapter 계약

- /axia/safety/state: P1 Supervisor가 내보내는 std_msgs/String JSON
- DiagnosticStatus: level(0 OK / 1 WARN / 2 ERROR / 3 STALE), name, message, hardware_id, values
- 메시지 미수신·수신 타임아웃(age > timeout_s): STALE(3), STATE_MESSAGE_STALE
- PROTECTIVE_STOP: ERROR(2)
- LIMITED, BOOT_SAFE, SW_STOP_LATCHED, RECOVERY_REQUIRED: WARN(1)
- NORMAL은 clock_ok, scan_ok, graph_ok, cm_lifecycle_ok, nav2_action_ready가 모두 True인 경우에만 OK(0)
- 건강 상태에 False가 있으면 HEALTH_BAD(2), None/누락은 HEALTH_UNKNOWN(1)
- 유효하지 않은 입력이나 인증 E-Stop 주장: ERROR(2)
- Goal UUID, 원문 JSON, 비밀 문자열을 진단 values에 넣지 않음

## 선택 실습: ROS 2 Jazzy

ROS 2가 설치된 **격리된 학습 환경**에서만 수행합니다. 학생용 ros_diagnostics_bridge.py는 읽기 전용 /axia/safety/state를 구독해 /diagnostics만 발행합니다.

터미널 2:
~~~bash
source /opt/ros/jazzy/setup.bash
PYTHONPATH=block_A/day03 python block_A/day03/ros_diagnostics_bridge.py
~~~

터미널 3:
~~~bash
source /opt/ros/jazzy/setup.bash
ros2 topic echo /diagnostics
~~~

P1 상태 메시지가 없다면 STATE_MESSAGE_STALE를 확인합니다. 공식 diagnostic_aggregator 실행은 별도 구성입니다. 종료는 Ctrl+C.

## 개인 제출 브랜치로 GREEN CI 검증

~~~bash
git add block_A/day03/p1_adapter_todo.py block_A/day03/todo_safety.py
git commit -m "feat(d03): complete diagnostic adapter and safe mode"
git push -u origin work/d03-my-submission
~~~

개인 Fork를 사용하면 origin을 본인 Fork로 바꿔야 합니다. GREEN 워크플로는 work/d03-* 등의 제출 브랜치에서 공개 테스트를 실행합니다. 템플릿의 expected RED CI와 별개입니다.

## 제출물과 안전 경계

코드 두 파일, RED/GREEN 테스트 로그·exit code, 자신의 커밋 SHA, GREEN CI URL, 상태 판단표, ROS/Gazebo 미검증 항목을 제출합니다.

**SW Stop은 인증된 HW E-Stop이 아니며**, 진단의 OK가 Nav2 Goal 또는 /cmd_vel 주행을 허용하지 않습니다. Python·Fake ROS·Gazebo 결과를 구별합니다.
