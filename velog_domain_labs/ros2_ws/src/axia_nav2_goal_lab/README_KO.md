# 03편 — Cancel ACK≠terminal CANCELED

## AXIA 실제 문제와 도메인 지식
이 실습은 AXIA의 Cancel ACK≠terminal CANCELED 문제를 축약해 재현합니다. 데모는 실제 안전제어 노드나 인증 E-Stop이 아닙니다.

## 시스템·데이터 파이프라인
```mermaid
flowchart TD
  Active[Goal ACTIVE] --> Stop[SW_STOP_LATCHED]
  Stop --> Ack[Cancel ACK]
  Ack --> Terminal{Terminal CANCELED?}
  Terminal -->|yes and UUID match| Recovery[RECOVERY_REQUIRED]
  Terminal -->|no| Stop
  Recovery --> Reset[Reset healthy]
  Reset --> Rearm[Rearm READY_NO_GOAL]
  Rearm -->|new UUID| Active
```

입력 → `axia_nav2_goal_lab/core.py`의 검사 함수 → 상태/등급 → 예상 결과. 오프라인 함수 호출이며 실제 ROS 메시지 발행이 아닙니다.

## 코드 해설과 학습 순서
1. `core.py`의 함수 이름과 입력 파라미터가 어떤 ROS 데이터를 모델링하는지 분석합니다.
2. `tests/test_contracts.py::Lab03`의 정상/경계/무효 케이스를 확인합니다.
3. 예외·UNKNOWN·ZERO·INCONCLUSIVE와 같은 보호 분기가 왜 필요한지 설명합니다.
4. NotImplementedError 구간을 한 함수씩 구현하여 RED → GREEN으로 변경합니다.

## 실행 (Python만 필요)
```bash
cd velog_domain_labs
export PYTHONPATH="$(find ros2_ws/src -mindepth 1 -maxdepth 1 -type d | paste -sd: -)"
python3 -m unittest discover -s tests -p 'test_contracts.py' -v
python3 -m axia_nav2_goal_lab
```
완성 후 예상 CLI 결과: `ACTIVE`. Student TODO는 미완료 함수에서 오류가 나는 것이 정상입니다.

## ROS 2 Jazzy colcon 설치 (선택·별도 L1)
```bash
source /opt/ros/jazzy/setup.bash
cd velog_domain_labs/ros2_ws
colcon build --packages-select axia_nav2_goal_lab --symlink-install
source install/setup.bash
ros2 run axia_nav2_goal_lab axia_nav2_goal_lab_demo
```

## AI 프롬프트 설계
- 일반: "로봇이 이상합니다. 고쳐 주세요."
- 도메인 기반: "Cancel ACK≠terminal CANCELED의 기존 AXIA 계약을 설명하고 실패 원인과 최초 위반을 증명한 뒤, 실제 G07 코드 변경 없이 오프라인 RED 테스트를 작성하고 최소 구현으로 GREEN을 확인하세요."

## 검증 해석
Python 단위 PASS는 L0만 증명합니다. ROS2 DDS L1, Gazebo L2, WSL2 L3 인수 증거가 없다면 성공했다고 주장하지 않습니다.
