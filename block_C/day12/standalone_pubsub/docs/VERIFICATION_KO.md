# 검증 범위

- 독립 공개 입문 예제. D11/기존 C05/강사 정답 변경 및 사용 없음.
- 로컬 RED: Jazzy char strict stand-in test failed (int is not bytes).
- 로컬 GREEN: 14 passed. 이 증거는 ROS 미설치 Python 환경에서 확보되었고 실제 ROS 검증은 아님.
- 실제 빌드 및 DDS: GitHub Actions의 d12-standalone-pubsub-real-ros 워크플로에서 해당 커밋의 L0/L1 결과와 로그 확인. 실행 전에는 미검증으로 취급.
- WSL2 현장, Gazebo, Nav2, 안전 TTL, 생산 제어, 인증 E-Stop: 범위 밖/미검증.
