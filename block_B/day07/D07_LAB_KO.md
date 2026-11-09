# D07 Nav2 Human-aware Avoidance — 교육생 3시간 실습

학습목표: (1) Nav2 costmap ObstacleLayer/InflationLayer가 실제 LaserScan 점을 경로 비용으로 반영하는 방식을 설명한다. (2) planner의 경로 변경과 Collision Monitor의 감속/정지를 구별한다. (3) 사람 track/Scan이 사라지거나 오래되면 경로 안전성을 보증하지 않는 이유를 설명한다.

## 실습 구성
**이론 1h**: D04 사람 Bounding Box -> D05 거리 측정 -> D06 Collision Monitor 감속·정지 -> D07 Nav2 Costmap/Planner 재계획. 공식 Nav2 코드를 수정하거나 새로운 경로 계획기를 만들지 않는다.
**실습 1h**: synthetic fixture routes.json에 기록된 기존 경로(사람 장애물 교차), 외곽 우회 경로를 비교한다. 장애물까지 점거리뿐 아니라 path segment까지의 최단 거리를 적용해야 한다.
**실습 1h**: 강사의 공식 Nav2 PlannerServer ROS L1 실측 결과와 학생의 오프라인 판정이 의미하는 바를 비교한다. 실제 Gazebo 주행 및 사람 충돌 회피 여부는 별도 증거 없으면 NOT_RUN.

## 실행 (학생 repo ROOT에서 새 터미널 1개)
    python3 -m pytest -q block_B/day07/tests/test_d07_public.py
처음에는 TODO 두 함수가 NotImplementedError로 실패한다(의도적 RED). block_B/day07/route_todo.py만 채우고 같은 명령으로 GREEN을 확인한다. 종료 후 터미널을 닫는다.

## 예상 판정
- before: BLOCKED (사람 proxy 0.8m,0m이 원본 직진 경로와 교차)
- detour: CLEAR (외곽으로 우회한 별도 기록 경로)
- before vs detour: REPLAN_EVIDENCED **단, 이 fixture는 학생 학습 데이터**. Nav2 실제 실행을 의미하지 않는다.
- person None, NaN, age>0.5s, missing path: UNKNOWN (CLEAR 금지).
- 함수의 robot_moved/collision_free_verified/safety_certified는 항상 False.

제출: TODO 코드, pytest 실제 출력, 기존/우회 2D 경로 스케치, 공식 Costmap·Planner·Controller·Collision Monitor의 역할 비교표, UNKNOWN이 안전한 주행 명령이 아닌 이유. /cmd_vel 직접 발행 금지.
