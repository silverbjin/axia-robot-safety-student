# AXIA Domain AI Labs (Student TODO)

다섯 개 독립 ROS 2 Jazzy ament_python 예제. 실물 로봇/실제 Nav2 Goal을 움직이지 않는 Python L0 실습입니다. 공식 AXIA G07 안전제어를 수정하지 않습니다.

## 오프라인 테스트
```bash
cd velog_domain_labs
export PYTHONPATH="$(find ros2_ws/src -mindepth 1 -maxdepth 1 -type d | paste -sd: -)"
python3 -m unittest discover -s tests -p 'test_contracts.py' -v
```

학생 TODO 상태에서는 24개 테스트가 의도적으로 RED입니다. 구현 뒤 GREEN으로 전환하십시오.

SW Stop은 인증 E-Stop이 아닙니다. ROS/colcon 빌드 및 Gazebo 물리 검증은 L0과 분리합니다.
