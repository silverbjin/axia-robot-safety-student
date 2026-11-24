# AXIA D12 — ROS 2 Publisher / Subscriber 독립 입문 실습

ROS 2 Jazzy / Ubuntu 24.04 / WSL2. D11, 기존 C05, AI 모델, CSV, Gazebo, Nav2 없이 동작하는 독립 공개 입문 예제입니다. 기존 채점용 TODO 또는 강사 정답을 대체하지 않습니다. 모든 이벤트는 임의로 생성한 교육용 합성값입니다. 기존 D12 NORMAL/CAUTION/WARNING/INSUFFICIENT_DATA 계약과 달리 ROS 표준 진단 레벨 OK/WARN/ERROR/STALE를 직접 입력합니다. 안전제어 권한이 없으며 Goal, cmd_vel, E-Stop과 무관합니다.

## 1. 준비

공개 CI 통과 후 승인된 main을 사용합니다. Ubuntu 터미널에서:

~~~bash
mkdir -p ~/axia_d12_course
cd ~/axia_d12_course
git clone https://github.com/silverbjin/axia-robot-safety-student.git d12-standalone
cd d12-standalone/block_C/day12/standalone_pubsub
git rev-parse HEAD
source /opt/ros/jazzy/setup.bash
sudo apt update
sudo apt install -y python3-colcon-common-extensions python3-pytest ros-jazzy-rclpy ros-jazzy-std-msgs ros-jazzy-diagnostic-msgs
colcon build --symlink-install --packages-select axia_basic_pubsub axia_json_diagnostics
source install/setup.bash
ros2 pkg executables axia_basic_pubsub
ros2 pkg executables axia_json_diagnostics
~~~

기존 폴더를 덮어쓰지 마십시오. clone 경로가 이미 존재하면 새 폴더 이름을 사용하거나 깨끗한 기존 clone에서 git pull --ff-only origin main 후 경로를 조정합니다. 첫 패키지는 실행기 2개, 두 번째는 3개입니다. colcon은 독립 실습 폴더의 src 두 패키지만 빌드합니다.

모든 터미널에서 공통 환경:

~~~bash
source /opt/ros/jazzy/setup.bash
cd ~/axia_d12_course/d12-standalone/block_C/day12/standalone_pubsub
source install/setup.bash
export ROS_DOMAIN_ID=86
export EVENT_FILE="$PWD/data/events.jsonl"
~~~

도메인 86은 교육 예시입니다. 다른 ROS 실습과 겹치면 모든 터미널에서 다른 동일한 도메인을 선택합니다.

## 2. 실습 1 — String 발행·구독 (20분)

터미널 A: ros2 run axia_basic_pubsub basic_subscriber
터미널 B: ros2 run axia_basic_pubsub basic_publisher

~~~text
PUB: Hello ROS 2: 1
SUB: Hello ROS 2: 1
SUB: Hello ROS 2: 2
~~~

위는 예상 출력이며 실제 실행 로그가 아닙니다. 발견 시점에 따라 첫 번호는 다를 수 있습니다.

터미널 C:

~~~bash
ros2 node list
ros2 topic info /axia/basic/chatter -v
ros2 topic echo /axia/basic/chatter
# Ctrl+C 후
ros2 topic hz /axia/basic/chatter
~~~

기대 결과: String 메시지 data가 증가하고 약 1Hz. echo/hz 역시 subscriber를 생성하므로 노드 수를 셀 때 종료합니다. 설치되어 있으면 rqt_graph로 연결을 시각화합니다. Subscriber를 먼저 종료해도 Publisher는 계속 발행합니다. 기본 volatile QoS에서는 늦게 연결한 Subscriber가 과거 메시지를 자동으로 받지 않습니다.

### 코드 읽기

- src/axia_basic_pubsub/axia_basic_pubsub/basic_publisher.py: Node 초기화, create_publisher(String, topic, 10), create_timer(1.0, callback), msg.data, publish.
- basic_subscriber.py: create_subscription(String, topic, listener_callback, 10), 수신 시 executor가 callback을 실행.
- rclpy.spin은 콜백 처리를 계속합니다. QoS depth 10은 큐 깊이이며 10Hz 또는 10초가 아닙니다.
- 미니 과제: 개인 복사본에서 타이머를 0.5초로 바꾸고 topic hz를 관찰합니다. 다음 실습에서는 기본 노드를 종료합니다.

## 3. 실습 2 — JSONL → DiagnosticArray (30분)

터미널 C에서 기존 실행을 모두 종료한 뒤 새 파일 이름을 정합니다. 세 터미널에 같은 EVENT_FILE 값을 설정합니다.

~~~bash
export EVENT_FILE="$PWD/data/events.jsonl"
~~~

이전 events.jsonl이 있으면 보존 후 새 경로를 선택합니다. 실행 중 파일을 삭제·회전·truncate하지 않습니다.

터미널 A:

~~~bash
ros2 run axia_json_diagnostics diagnostic_subscriber
~~~

터미널 B:

~~~bash
ros2 run axia_json_diagnostics diagnostic_publisher --ros-args -p event_file:="$EVENT_FILE"
~~~

A/B에서 Waiting/Watching 출력 확인 후 터미널 C:

~~~bash
ros2 topic info /axia/education/diagnostics -v
ros2 run axia_json_diagnostics emit_event --file "$EVENT_FILE" --id E001 --level OK --model AE --score 0.12 --cutoff 0.50
ros2 run axia_json_diagnostics emit_event --file "$EVENT_FILE" --id E002 --level WARN --model AE --score 0.72 --cutoff 0.50
ros2 run axia_json_diagnostics emit_event --file "$EVENT_FILE" --id E003 --level ERROR --model IF --score 0.91 --cutoff 0.50
ros2 run axia_json_diagnostics emit_event --file "$EVENT_FILE" --id E004 --level STALE --model AE --score 0.22 --cutoff 0.50
cat "$EVENT_FILE"
~~~

예상 출력: PUB event=E002 level=WARN / SUB #2 event=E002 level=WARN model=AE score=0.72 cutoff=0.5. 처음부터 정상 연결되면 네 이벤트 ID를 한 번씩 순서대로 확인합니다. STALE은 여기서 명시적으로 입력한 모의 진단 레벨이며 실제 시간 초과 탐지가 아닙니다.

### 파일 → ROS 메시지 변환 원리

emit_event.py는 일반 Python CLI이며 ROS Node가 아닙니다. 한 줄 JSON을 append하고 종료합니다. events.py의 JsonlReader는 이전 바이트 offset부터 완성된 줄만 읽습니다. JSON 줄이 완성될 때까지 보류하고 잘못된 행은 parse_event가 거절합니다. diagnostic_publisher.py는 0.2초 타이머마다 최대 10줄을 읽으며 subscriber 발견 전에는 소비하지 않습니다. 이는 교육용 polling 주기이지 AI 윈도우 길이, 보장된 지연 또는 안전 TTL이 아닙니다.

to_message()는 JSON dict를 DiagnosticStatus로 바꾸고 DiagnosticArray.status에 담습니다. Jazzy의 char 필드 level은 Python bytes([n])로 대입합니다. Subscriber의 level_number는 바이트를 숫자로 해석합니다.

| JSON | ROS |
|---|---|
| event_id | status.values의 event_id |
| level | status.level 0/1/2/3 및 values |
| model | status.name / values |
| score, cutoff | status.values 문자열 |
| 선택 message | status.message |
| 없음 | header.stamp (ROS 노드 현재 시각, 추론 시각 아님) |

~~~bash
ros2 interface show diagnostic_msgs/msg/DiagnosticArray
ros2 interface show diagnostic_msgs/msg/DiagnosticStatus
ros2 interface show diagnostic_msgs/msg/KeyValue
ros2 topic echo /axia/education/diagnostics
~~~

echo를 먼저 실행하고 별도 터미널에서 새 이벤트를 추가하면 변환 구조를 관찰할 수 있습니다.

## 4. 실습 3 — 오류와 복구 (10분)

~~~bash
printf '%s\n' '{bad json}' >> "$EVENT_FILE"
printf '%s\n' '{"event_id":"E005","level":"OK"}' >> "$EVENT_FILE"
~~~

잘못된 행은 Publisher에서 SKIP 경고, E005는 Subscriber에서 수신됩니다. 점수 생략 시 '-'가 출력됩니다. 완성되지 않은 줄은 개행을 추가할 때까지 읽지 않습니다. 단일 writer, UTF-8, append-only 전제입니다. offset은 메모리에만 있어 Publisher 재시작 시 파일 처음부터 재생합니다. 동일 ID 제거/영구 ACK/exactly-once는 제공하지 않습니다.

## 5. 자체 검증 및 확인 문제

~~~bash
PYTHONPATH=src/axia_json_diagnostics python3 -m pytest -q tests src/axia_json_diagnostics/test
export ROS_DOMAIN_ID=87
timeout --signal=TERM --kill-after=10s 100s python3 tools/ros_smoke.py
~~~

다른 노드가 없는 도메인 87을 사용하십시오. L0는 14개 Python 계약 테스트입니다. L1 성공 문자열은 D12_REAL_ROS_L1_PASS입니다. L1은 별도 실행 프로세스 네 개, 실제 DDS observer, 네 진단 레벨/ID/점수/임계값, 실제 subscriber 로그 및 cmd_vel 발행자 부재를 검증합니다. 로봇/Gazebo/안전 TTL/현장 WSL2 승인은 검증하지 않습니다.

확인 질문: JSON 파일이 ROS topic인가? 파일 polling과 ROS 수신 callback의 차이는 무엇인가? score가 바뀌면 이 예제가 자동으로 위험을 판정하는가? ERROR가 실제 E-Stop이 아닌 이유는? 학생은 node/topic info 및 수신 로그를 제출합니다. 답안은 기존 비공개 정답과 무관한 별도 구두 확인이며 본 예제를 채점용 정답으로 사용하지 않습니다.
